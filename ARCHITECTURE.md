# Archivo del discurso político: architecture v0

*2026-10-25. Open-source database of everything Spain's main candidates say in public, starting the day the snap election was called (5 Oct 2026).*

## 0. Scope v1

- **Period:** 5 Oct 2026 → election day 29 Nov 2026 (campaign 13–27 Nov), then keep running.
- **People v1 (cabezas de lista):** Pedro Sánchez (PSOE), Alberto Núñez Feijóo (PP), Santiago Abascal (Vox), the Frente Amplio lead and the Podemos lead (still unclear in the press; Irene Montero for Podemos is likely). **Confirm against the official candidaturas proclamadas in the BOE** and keep the list in `people.yaml`, never hard-coded.
- **Fixed dates to hit:** cara a cara Sánchez–Feijóo **16 Nov** (Mediaset, agreed); spokespersons' debate **23 Nov** (RTVE); four-way debate **26 Nov** (venue disputed). Debates processed within 24 h is the headline moment.

## 1. Where they speak (source inventory)

Ranked by how much work it takes to get clean text out.

| Tier | Source | What we get | How |
|---|---|---|---|
| **1. Already text** | **La Moncloa "intervenciones"**: official transcripts (PDF/HTML) of Sánchez's government appearances | Exact text, date, place. Also **ground truth** to measure our transcription and to enrol his voice | scrape index + PDFs |
| | Congreso: Diputación Permanente sessions (the Cortes are dissolved, but this body still meets and is transcribed) | Official Diario de Sesiones | scrape |
| | Party press rooms (psoe.es, pp.es, voxespana.es…) | Quotes from rallies, often partial and edited by the party | scrape, mark `party_edited` |
| | X / official accounts | Their own written words | API or scrape; low priority |
| **2. Audio, easy to get** | **Party YouTube channels** (full rallies are uploaded daily during a campaign) | Long, clean audio of the candidate | `yt-dlp`, audio only |
| | **Morning radio interviews as podcasts** (SER *Hoy por Hoy*, COPE *Herrera*, Onda Cero *Más de uno*, RNE *Las mañanas*, esRadio…) | Long interviews, published as RSS | RSS + download |
| | Podcasts and streams with politicians (YouTube) | Long-form interviews | `yt-dlp` |
| **3. TV** | RTVE Play (TVE has subtitles), Atresplayer (Antena 3, laSexta), Mitele (Telecinco, Cuatro) | Interviews, debates, news cuts | Prefer the channel's own YouTube upload; RTVE Play second; the private players often use DRM, so skip them unless there's no other copy |
| | **The three debates** | The most important content of the campaign | Record or download the same night |
| **4. Discovery only** | TikTok, Instagram, X clips, news articles | Mostly cuts of tiers 2–3 | Use to *find* appearances, then fetch the full source |

**Discovery** (how we learn an appearance happened): party and Moncloa daily agendas, YouTube channel feeds, podcast RSS, a YouTube search per candidate per day, and Google News RSS per candidate. Each hit becomes an `appearance candidate` row; one human glance a day catches what the crawler missed.

## 2. Pipeline

```
discover → fetch → dedup → transcribe → diarize → identify → quote → review → publish
```

| Stage | What it does | Tool |
|---|---|---|
| **discover** | Finds new appearances (section 1) | Python crawlers on the VPS, daily timer |
| **fetch** | Downloads audio only, 16 kHz mono; stores the original URL, timestamp and a SHA-256 hash; asks archive.org to snapshot the page | `yt-dlp`, `ffmpeg` |
| **dedup** | The same rally appears on 3 channels, cut differently. Matches audio fingerprints so each moment is transcribed once and keeps every source | `chromaprint` |
| **transcribe** | Speech to text with word timestamps; voice-activity detection first, so Whisper doesn't invent text over music and applause | `faster-whisper` large-v3 + Spanish alignment (WhisperX) |
| **diarize** | "Who spoke when", as anonymous labels (SPEAKER_00, SPEAKER_01…) | `pyannote` |
| **identify** | Puts a name on each anonymous label (section 3) | voice embeddings + other signals |
| **quote** | Splits the text into citable sentences, each with speaker, start/end time and source link | rules first; cheap LLM later for topics |
| **review** | Anything below the confidence bar goes to a queue; a human confirms it in seconds | small web page on the VPS |
| **publish** | Only confirmed or high-confidence segments go public | dataset + search site |

Every stage is a separate script that reads a job from the database and writes back its result. A failed stage can be re-run alone, and swapping a model only means re-running from that stage.

## 3. Who is speaking? (the hard part)

You're right: voices are very characteristic. The standard method is:

1. **Voiceprint (enrolment).** For each candidate, take 5–10 minutes of clean audio where we *know* it's them (Moncloa appearances, solo rally speeches, solo interviews). A speaker-embedding model turns each few seconds of voice into a vector (a list of ~200 numbers). Average them → that person's **voiceprint**. Include phone-quality samples too, because radio interviews are often by phone.
2. **Matching.** Diarization gives anonymous speakers in a new recording. Embed each one, compare to every voiceprint (cosine similarity), and take the best match above a threshold. Below the threshold → `unknown` (interviewers, moderators, the public).
3. **Other evidence, combined with the voice score**, because voice alone fails in the noisy cases:
   - **TV lower thirds**: the name caption on screen. OCR on video frames gives "PEDRO SÁNCHEZ, Presidente del Gobierno" for free.
   - **Context**: the event title ("Mitin de Feijóo en Valencia"), the moderator saying "señor Abascal, tiene la palabra".
   - **Who else is there**: a one-to-one interview has exactly two voices, and one of them is the host.
4. **Confidence.** Each segment gets a score and the reasons for it. **Published = voice match above the threshold AND at least one other signal agrees, or a human confirmed it.** Everything else waits in the review queue.

**Why this rule matters:** a wrongly attributed quote means publishing words under someone's name that they never said. That's the real legal risk (defamation), much bigger than copyright, and one bad quote would damage the whole project's credibility.

**Known hard cases:**
- Debates: people talk over each other. Overlap segments get flagged, never auto-published.
- Rallies: crowd noise, music, chanting. VAD + a noise threshold; low-confidence segments go to review.
- **Impersonators** (Carlos Latre, *Polònia*, satire shows) sound like the real person, and a voice match will accept them. That's why we **only take sources from a whitelist** (official channels, broadcasters, radio stations) and never from random uploads.
- Deepfakes: same answer. The source is what makes a quote trustworthy, not the voice.

**Measuring it** (this is what makes it "beyond vibecoding"): hand-label ~2 hours of mixed audio (a rally, a radio interview, a debate clip). Report speaker-ID precision and recall and the transcription error rate (WER), with the Moncloa transcripts as free ground truth. Target: **≥ 99% precision on published segments**. Put the numbers in the README.

## 4. Data model (first version)

```
person(id, name, party, role, voiceprint_version)
source(id, url, outlet, kind[tv|radio|youtube|podcast|official_text|press],
       published_at, fetched_at, sha256, archive_url, whitelist_ok)
appearance(id, date, place, kind[rally|interview|debate|press_conf|parliament],
           title)                        -- one real-world event, many sources
media(id, source_id, appearance_id, duration_s, audio_path_private, fingerprint)
segment(id, media_id, start_s, end_s, text, speaker_label,
        person_id NULL, id_confidence, id_signals JSON,
        status[auto|review|confirmed|rejected], model_versions JSON)
correction(id, segment_id, old, new, reason, by, at)   -- public log of every fix
```

Start with **SQLite + full-text search (FTS5)** and publish with **Datasette**, which gives a searchable public site and an API for free. Move to Postgres only if it gets slow.

## 5. Compute and infrastructure

- **Your PC has an RTX 3060 Ti (8 GB).** That's enough to run faster-whisper large-v3 and pyannote locally for milestones 1–3, so there's no need to rent a GPU yet.
- **Volume estimate:** 5 candidates × ~2–3 h of public speaking a day, plus duplicates → roughly 10–15 h of audio a day in the campaign, **~1,000 h by end of December**.
- **Renting a GPU** (RunPod / vast.ai, a 4090 for about €0.30–0.50 an hour) for the backfill since 5 Oct and for debate nights. All of it is likely to cost **tens of euros**, not hundreds.
- **Split:** the VPS discovers, fetches, keeps the database and serves the site. GPU workers (your PC or a rented box) pull transcription jobs from the VPS and push results back.
- **Storage:** speech audio in Opus at ~32 kbps ≈ 15 MB/h → 1,000 h ≈ 15 GB. Kept **private**, only for reproducibility and re-processing.

## 6. Publishing and legal

- **Publish text, timestamps and links to the original source, never the audio or video.** Quoting public statements with attribution is what the press does every day; re-hosting broadcasters' footage is not.
- Every quote has a source link and an archive.org copy, so anyone can check it.
- **Corrections are public:** a visible log, an email address and a fix within 48 h.
- Dataset licence CC BY 4.0, code licence MIT or AGPL.
- GDPR: these are public statements by public figures in their public role, which is the best case for the public-interest and journalistic exemptions. We don't collect anything about private people (interviewers stay labelled by role only).
- **Prompt injection:** transcripts are external text. When a cheap LLM later tags topics, it receives the transcript as delimited *data*, never as instructions. Someone can literally say "ignore previous instructions" on air.

## 7. Where cheap models and agents fit (later, not now)

- Topic tags, claim detection ("this is a factual claim with a number"), linking quotes to the history graph (see `madrid/IDEAS.md`).
- An agent that reads the daily discovery list and flags appearances the crawlers missed.
- Only after milestone 3. Before that, plain scripts.

## 8. Milestones

| # | What | Done when |
|---|---|---|
| **M0** | Source inventory for 5 Oct → today: a table of every appearance found for the 5 candidates (date, kind, URL, tier) + `people.yaml` from the BOE | List exists; we know the real volume |
| **M1** | One Sánchez Moncloa appearance end to end: fetch → transcribe → compare with the official transcript | WER measured, number written down |
| **M2** | Voiceprints for the 5 candidates; identify speakers in 1 rally, 1 radio interview and 1 TV interview | Precision/recall on hand-labelled clips |
| **M3** | Daily crawler (party YouTube + 5 radio podcasts + Moncloa) on the VPS; backfill since 5 Oct | Runs unattended for a week |
| **M4** | Debates of 16, 23 and 26 Nov processed by the next morning | Searchable the day after each debate |
| **M5** | Public search (Datasette) + "¿Quién lo dijo?" daily quote game | Public URL |

## 9. Open questions

- Project name.
- Who exactly leads Frente Amplio and Podemos (BOE, early November).
- Repo: GitHub public from day 1, or private until M2 has numbers? (Recommended: private until M2.)
- pyannote models need a free Hugging Face account and accepting the model terms (Gerrit's account).
