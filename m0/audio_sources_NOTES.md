# M0: radio and podcast sources (5 Oct to 25 Oct 2026)

Checked on 2026-10-25. Files in this folder:
- `audio_sources.csv`: one row per appearance (9 interviews, 1 replay).
- `feeds.yaml`: 29 feeds, all checked with curl (HTTP 200 + valid RSS XML).

## Who counts
- **Frente Amplio lead = Ada Colau.** Público reports that the four parties (Sumar, IU, Más Madrid, Comuns) chose her as candidate for the Presidency; the proposal went public on 12 Oct. Emilio Delgado is the Frente Amplio no. 1 for Madrid, not the national lead. He was interviewed on SER Hoy por Hoy on 15 Oct and RNE 24 horas on 21 Oct. Neither is in the CSV; add them if the person list grows.
- **Podemos = Irene Montero** (the campaign is built around her). Ione Belarra is included as well.

## What was found
| Person | Radio interviews since 5 Oct | Outlets |
|---|---|---|
| Feijóo | 3 (+1 replay) | esRadio 13 Oct, COPE 20 Oct, SER 23 Oct |
| Colau | 3 | SER 8 Oct, RAC1 14 Oct, Catalunya Ràdio 15 Oct |
| Montero | 2 (short clips) | SER 5 Oct, SER 13 Oct |
| Belarra | 1 | RNE 15 Oct |
| Sánchez | 0 | none found |
| Abascal | 0 | none found |

Not radio and so not in the CSV, but useful for the TV/M0 table:
- Sánchez, *La Revuelta* (TVE, David Broncano), 22 Oct. Reported as his first pre-campaign interview. The press says this opens a round of media appearances.
- Abascal, *Espejo Público* (Antena 3), 5 Oct; print interviews in ABC (11 Oct) and La Razón (18 Oct).
- Montero, *La hora de La 1* (TVE, Silvia Intxaurrondo), 13 Oct; also by video call on *El perro andaluz* (TVE), 22 Oct.
- Colau, *El perro andaluz* (TVE), 22 Oct; print interview in elDiario.es, 23 Oct.

**Podcasts / streams:** no candidate appeared in a podcast or stream between 5 and 25 Oct. Coming up: **The Wild Project (Jordi Wild)**. Feijóo, Abascal and Colau have accepted, and Sánchez accepted on 23 Oct. Reported release is around 9-13 Nov, with no questions agreed in advance and no editing. These will be 4 long solo interviews, ideal for voiceprints, so put the feed on the daily crawl now. One report said Montero was interviewed on the podcast *Animales Humanos*, published 21 Oct. That episode is from January 2024 and was recirculated, so it is left out.

## How to crawl
1. **Daily discovery:** fetch every feed in `feeds.yaml`. Match names on title + description (regex on surnames, plus "entrevista"/"entrevista a"). Name matches alone are noisy: COPE/Catalunya Ràdio hour descriptions and commentary clips mention the candidates constantly. Of 284 name hits in 20 feeds, 9 were real interviews. Rules that worked:
   - SER: description "Aimar Bretos entrevista a <name>" (or another host + "entrevista a").
   - COPE: clip titled "<Name>, <cargo>" or a link path containing `/la-entrevista-de-las-9h-con-herrera/`.
   - esRadio: title "Federico entrevista a ..." / "Jiménez Losantos entrevista a ...".
   - RNE and RAC1: the title starts with the guest's name and quote; RAC1 "Entrevista" is interview-only.
   - Catalunya Ràdio: only hour files, so match the description and log `start=unknown`.
   Then a human looks the list over once a day.
2. **Prefer the clip over the hour:** SER, COPE, esRadio, RNE and RAC1 publish interviews as separate items. Fetch the clip and keep the hour/pulso file only as a fallback, for dedup and when the clip looks cut (Montero's 3 and 6.5 min SER clips look like excerpts).
3. **Shallow feeds, crawl daily:** RNE RSS keeps only 20 items (use the JSON API to backfill, which works back to 5 Oct). esRadio's own feed keeps 50 items (use the Spreaker feed/API, 1000 items). Onda Cero feeds keep ~300 items (about 1 month for Más de uno). Feeds of 600 items at SER/COPE cover 2-3 months.
4. **Parsing quirks:** COPE uses ISO 8601 pubDate. Catalunya Ràdio is ISO-8859-1. COPE's `enclosure length` is wrong (tiny), so don't trust it. RTVE `ztnr` mp3 links redirect to tokenised URLs and loop on HEAD, so use GET. SER Triton URLs carry `?dest=` tracking, which is harmless.
5. **Dedup:** SER reuses interview audio in El pulso, Las 8, and Hora 25 "Las ocho" bulletins. COPE has both the clip and the hour. Fingerprint all of them (chromaprint) before transcribing.

## Gaps and caveats
- **Onda Cero:** no candidate interview found in Más de uno / La Brújula / Julia since 25 Sep, the start of the feed window. The window does cover 5 Oct onward, so this is probably a real absence, but the feed is shallow.
- **COPE / Onda Cero / RNE regional editions** and other regional stations (Canal Sur Radio, Radio Galega, EITB, À Punt, Aragón Radio) were not checked. Abascal and Feijóo often do regional radio while touring. This is the biggest likely gap.
- **Abascal:** Vox's own site (voxespana.es/abascal) returned 403 to scripted fetches, so its news list was not checked for radio appearances. Abascal tends to skip SER/Onda Cero/RNE; esRadio and COPE showed nothing since 5 Oct.
- **Sánchez:** no radio. Moncloa transcripts (tier 1) and TV are where he is speaking.
- Start offsets inside hour files are approximate or unknown (Catalunya Ràdio 15 Oct; COPE 09:00H 20 Oct, which starts near the top of the hour).
- No transcripts found for any of these (`has_text=no`). Press articles quote the SER/COPE interviews but are not full text.
- Discovery leaned on web search, which is US-indexed and weak for Spanish radio. A Google News RSS per candidate would catch more ("Feijóo, en COPE:" style headlines).
- No prompt-injection or AI-addressed text was seen in any feed or page read.
