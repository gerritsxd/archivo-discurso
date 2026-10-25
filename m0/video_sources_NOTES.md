# M0 video sources: notes

*2026-10-25. Covers 5 Oct to 25 Oct 2026. Party/candidate YouTube channels and TV interviews. Radio is out of scope here (see the end for radio items found by accident).*

Files: `video_sources.csv` (75 rows), `channels.yaml` (channel ids + RSS).

## Who the leads are (as of 25 Oct)

- **Frente Amplio:** Ada Colau, cabeza de lista and candidate for the presidency (RTVE 13 Oct: IU, Más Madrid, Movimiento Sumar and Comuns agreed she leads; Demócrata 16 Oct: "cabeza de lista, Ada Colau"). Emilio Delgado is number 1 for Madrid.
- **Podemos:** Irene Montero, launched as candidate 12 Sep 2026 (El País stream). She runs in a joint campaign with Gabriel Rufián (ERC) in Catalonia. Ione Belarra is the party leader and appears in Podemos uploads. Frente Amplio and Podemos only run together in Canarias and the Comunidad Valenciana.
- Still to confirm against the BOE candidaturas proclamadas.

## How it was gathered

- `yt-dlp 2026.10.21` (installed for `py -3.13`; the old 2025.10.14 on py3.9 is too old for YouTube). Metadata only (`skip_download`), never media.
- Each channel's `/videos` and `/streams` tabs were read flat, then each video was opened for date, duration and caption tracks, stopping after 4 videos in a row older than 5 Oct. `/shorts` was not crawled.
- TV: about 140 YouTube searches sorted by date (person x programme/outlet), keeping only broadcaster channels, then manual review. Plus RTVE Play program pages via curl.
- `has_text`: `captions` = a manual subtitle track, `auto_captions` = YouTube ASR only, `no` = none. **No video has manual captions.** Most have auto captions. La Moncloa uploads and several PSOE/PP live streams have none.

## How to crawl each source (for M3)

| Source | Method |
|---|---|
| PSOE, PP, VOX, Podemos, Frente Amplio, Sumar, Montero, Colau, La Moncloa | Poll the RSS feed (`channels.yaml`) every 30–60 min. The feed only holds the latest ~15 items, but finished live streams do appear in it. For backfill use `yt-dlp --flat-playlist` on `/streams` and `/videos`, then `--skip-download -J` per id. Use the **channel_id**, never the handle (VOX's handle has a non-ASCII "ñ"). |
| Title filters | PSOE: `Pedro Sánchez`; PP: `Feijóo` (the channel also streams Sémper, Tellado, Muñoz); VOX: `Abascal` (also posts Carlos Quero etc.); Podemos: `Montero|Belarra`. Spots under ~3 min skipped. |
| Scheduled lives | VOX had 2 upcoming lives (TCyUbVcWJb8, tKIvQAHtLmE) that yt-dlp cannot read until they start. Re-poll after the start time. |
| RTVE (TVE) | YouTube channels RTVE Noticias, RTVE Play and La Revuelta post interviews/clips. Full programmes on RTVE Play (`rtve.es/play/videos/<programa>/`); yt-dlp's RTVE extractor read the 22 Oct La Revuelta episode (103 min) and La Hora de La 1 of 23 Oct (165 min) **without a DRM error**. No subtitle track exposed through yt-dlp (TVE broadcasts teletext subtitles; worth checking the RTVE API later). |
| Atresmedia (Antena 3, laSexta) | Their YouTube channels post a lot: clips of 2–35 min, all with auto captions. Full programmes on atresplayer. **Not tested** for DRM; atresplayer is known to need login for much content and to use Widevine on some. Prefer YouTube. |
| Mediaset (Telecinco, Cuatro) | Mediaset Infinity España on YouTube posts mostly <1 min shorts. Full interviews on mitele (**not tested**; mitele commonly uses DRM). For Abascal on Ana Rosa/Horizonte the only full copies found are **VOX re-uploads**, which may be edited. Mark them as party-uploaded. |

## Gaps and problems

1. **Montero's 24 Oct Nou Barris rally:** her own upload (`wz0xMaI5Y-E`) returns "video not available". I used the elDiario.es live stream instead (press outlet, not on the whitelist: decide). El País has a copy too (rMp4yjDcIDI).
2. **Speakers not verified** in several rows (Podemos Getafe act, Consejo Ciudadano, PSOE 9-min video, laSexta Colau 9 Oct, RTVE Montero 13 Oct). Marked in `notes`.
3. **Live-stream durations include waiting time and other speakers** (e.g. PP Vigo 170 min). Candidate speaking time is roughly 25–50% of a rally stream.
4. **Duplicates** are kept and flagged in `notes`: edited cuts of streams (VOX, PP), the FA presentation on two channels, Espejo Público on Antena 3 and on VOX, La Revuelta clips and the full episode.
5. **TV coverage is thin.** No full sit-down TV interview found for Feijóo since 5 Oct (his 23 Oct interview was on SER radio; PP said he only does RTVE in-house programmes). Sánchez's only TV interview found is La Revuelta (22 Oct). Search is not exhaustive: atresplayer/mitele catalogues were not browsed, and YouTube search misses things.
6. Government role vs. candidate: Moncloa and RTVE press appearances by Sánchez are included and marked "govt role".
7. Frente Amplio channel `UCI0ufdFaYZQKBH7ixcWtbsg` is new (2 uploads) and its official status was not confirmed from a party site.
8. No prompt-injection text was seen in any titles/descriptions read.

## Estimated hours (5–25 Oct, from the CSV)

| Person | Rows | Raw hours in CSV | Without duplicates | Est. hours the candidate actually speaks |
|---|---|---|---|---|
| Alberto Núñez Feijóo | 16 | 18.1 | ~17.9 | ~7–9 |
| Pedro Sánchez | 24 | 15.3 | ~13.6 (clips counted, full episode not) | ~6–7 |
| Santiago Abascal | 22 | 12.9 | ~12.0 | ~6–7 |
| Ada Colau | 6 | 2.8 | 2.8 | ~1–1.5 |
| Irene Montero | 5 | 2.8 | 2.8 | ~1 (uncertain) |
| Ione Belarra | 2 | 0.9 | 0.9 | ~0.6 |

Roughly **50 h of raw video in 3 weeks (~2.4 h/day)**, of which maybe 20–25 h is the candidates speaking. That is below the architecture's 10–15 h/day campaign estimate; the volume should rise from 13 Nov (official campaign). The radio podcasts are not in this count.

## Radio found by accident (for the radio inventory)

- Feijóo, SER *Hoy por Hoy* / El Pulso, 23 Oct: tFolyGPFatg (96 min, Cadena SER), ilNPF6TaYhE (Hoy por Hoy channel), O08t6ZE8TYg (45 min).
- Feijóo on esRadio (8sR6IsLTd6E, 6uLI0C2ydHM) and COPE (8LXx9Pk-PoU). Dates not checked.
- Belarra on RNE, 15 Oct: in the CSV via the Podemos channel (vsQUyZNPRos).
