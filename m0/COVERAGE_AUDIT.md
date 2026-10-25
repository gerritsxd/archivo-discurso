# Coverage audit, 5-25 October 2026

Run 2026-10-25. Compares the public appearances of the five leaders with `data/items/*.json` (96 items), `data/queue.csv`, `data/queue_backfill.csv` and `m0/inventory.csv`. Fetchable gaps are in `data/missing.csv` (12 rows, 9 appearances).

## Summary

| Person | Known appearances | have | queued | missing | missing with fetchable URL | Coverage (have+queued) |
|---|---|---|---|---|---|---|
| Irene Montero (Podemos) | 9 | 7 | 1 | 1 | 1 | 89% |
| Ada Colau (Frente Amplio) | 19 | 11 | 0 | 8 | 2 | 58% |
| Santiago Abascal (Vox) | 17 | 12 | 0 | 5 | 3 | 71% |
| Pedro Sánchez (PSOE) | 18 | 15 | 0 | 3 | 2 | 83% |
| Alberto Núñez Feijóo (PP) | 20 | 18 | 0 | 2 | 1 | 90% |
| Total | 83 | 63 | 1 | 19 | 9 | 77% |

Coverage is measured against appearances I could see in news coverage, so it is an upper bound (see caveats). One row per appearance, not per recording: an interview cut into three RTVE clips counts once; a rally uploaded on two channels counts once.

## Method

- Moncloa agenda pages (`/presidente/agenda/Paginas/agenda.aspx?d=YYYYMMDD`) and the Moncloa video index for Sánchez.
- One Google News RSS query per person per day (21 days, about 1,100 to 2,000 headlines each), then reading the broadcaster pages behind the headlines (RTVE, laSexta, Antena 3, Onda Cero, SER, Telemadrid, Europa Press, EFE, elDiario.es).
- All followed radio feeds in `m0/feeds.yaml` and `m0/feeds_regional.yaml` scanned for the five names: every interview with a candidate in those feeds is already in `data/items`. Radio is not where the gaps are.
- Party sites: pp.es agenda 404, podemos.info 403. No usable party agenda, so the news lens carries the weight.
- No YouTube request was made. No media was downloaded (HEAD requests only on the 11 media URLs listed).

## Irene Montero (Podemos)

Known appearances 9: have 7, queued 1, missing 1. Estimated coverage 89% of the appearances found.

| Date (Oct) | Appearance | Status | Notes |
|---|---|---|---|
| 10-05 | Interview, SER Hoy por Hoy (Bretos) | have | items |
| 10-05 | Interview, TVE (clip via Podemos YT) | have | items |
| 10-08 | Interview, TVE Mañaneros 360 | MISSING | RTVE Play URL in missing.csv. Feed id 175650 is followed but holds only 20 items, so it rotated out before a run |
| 10-10 | Podemos act, Getafe (speech) | have | items |
| 10-13 | Interview, TVE La hora de La 1 (Intxaurrondo) | have | via RTVE Noticias YT; RTVE Play clip also exists |
| 10-13 | Interview, SER Hoy por Hoy | have | items |
| 10-17 | Consejo Ciudadano Estatal, speech | have | items |
| 10-22 | Video message to Feijóo (Podemos YT) | queued | queue.csv |
| 10-24 | Act with Rufián, Nou Barris | have | elDiario YT item; Montero YT also queued |

## Ada Colau (Frente Amplio)

Known appearances 19: have 11, queued 0, missing 8. Estimated coverage 58% of the appearances found.

| Date (Oct) | Appearance | Status | Notes |
|---|---|---|---|
| 10-05 | Statements to press, Barcelona ("no me postulo") | MISSING | only text (Europa Press); no recording found |
| 10-06 | Statements to press ("me han ofrecido liderar") | MISSING | only text (Europa Press); no recording found |
| 10-08 | Interview, SER Hoy por Hoy | have | items |
| 10-08 | Interview, TVE La hora de La 1 | have | items |
| 10-09 | laSexta Más Vale Tarde | have | items |
| 10-13 | Interview, La 2 / Ràdio 4 Cafè d'idees (Gemma Nierga) | MISSING | no URL found: RTVE feed 131940 only holds the 20 newest and the Colau item is gone |
| 10-14 | Interview, 3Cat Els Matins | have | items |
| 10-14 | Interview, RAC1 El món | have | items |
| 10-14 | Interview, TVE La hora de La 1 ("Compartimos programa") | have | via RTVE Noticias YT |
| 10-15 | Interview, Catalunya Ràdio | have | items |
| 10-15 | Zaragoza: CHA-Frente Amplio presentation, press statements | MISSING | video only on El Periódico de Aragón (WAF 406 blocks fetch); not fetchable |
| 10-17 | Frente Amplio opening rally, Madrid (Manzanares) | have | FA YT + comuns.cat text |
| 10-19 | Statements to press ("dejar de hablar de los partidos") | MISSING | only text (elDiario live blog, Europa Press); no recording found |
| 10-21 | laSexta Al Rojo Vivo | have | items |
| 10-23 | TVE El perro andaluz | have | item dated 10-24 |
| 10-23 | Interview, elDiario.es (Neus Tomàs), video | MISSING | video is elDiario YouTube only; no non-YouTube URL |
| 10-24 | 3Cat Telenotícies | have | items |
| 10-24 | Pensions demo, Madrid: speech and press statements | MISSING | Onda Cero mp3 + laSexta mp4 in missing.csv |
| 10-25 | Sunday statements and act ("llenar las calles") | MISSING | 3 clips in missing.csv (laSexta x2, Europa Press mp4) |

## Santiago Abascal (Vox)

Known appearances 17: have 12, queued 0, missing 5. Estimated coverage 71% of the appearances found.

| Date (Oct) | Appearance | Status | Notes |
|---|---|---|---|
| 10-05 | Interview, Antena 3 Espejo Público | have | items |
| 10-05 | Declaración institucional | have | items |
| 10-07 | Statements ("primero arruina a los españoles...") | MISSING | only text (Europa Press); no recording found |
| 10-11 | Rally, Estepona | have | items |
| 10-12 | Ceuta with Bardella (x2) | have | items |
| 10-14 | Forum Europa with Bardella; "29N ahora o nunca" | have | items (x2) |
| 10-15 | Interview, Telecinco El Programa de Ana Rosa | have | items |
| 10-17 | Statements, Senate pact ("haremos lo necesario") | MISSING | RTVE live only; no recording found |
| 10-18 | Statements, Senate pact (RTVE Informativo 24h) | MISSING | RTVE Play URL in missing.csv |
| 10-18 | Interview, La Razón (video) | MISSING | YouTube embed in article, in missing.csv |
| 10-19 | Declaración institucional | have | items |
| 10-20 | Rally, Ponferrada | have | items |
| 10-21 | A Coruña statement; rally Avilés | have | items (x2) |
| 10-22 | Cuatro Horizonte; Ana Rosa; Burgos statement; rally Segovia | have | items (x4) |
| 10-23 | Rally, Menorca | have | items |
| 10-24 | Rallies, Ibiza and Mallorca | have | items (x2) |
| 10-25 | Sunday statements (Senate, Catalan identity) | MISSING | laSexta mp4 in missing.csv |

## Pedro Sánchez (PSOE)

Known appearances 18: have 15, queued 0, missing 3. Estimated coverage 83% of the appearances found.

| Date (Oct) | Appearance | Status | Notes |
|---|---|---|---|
| 10-05 | Declaración institucional, elections | have | Moncloa + YT |
| 10-06 | Press conference after Consejo de Ministros | have | via RTVE Noticias YT; Moncloa video is in inventory |
| 10-07 | Interview, elDiario.es (Ferraz, Escolar), video; extension 10-08 | MISSING | elDiario YouTube only; no non-YouTube URL |
| 10-09 | PSOE act "Nuestro compromiso es con la gente" | have | items |
| 10-10 | Rally, Dos Hermanas | have | items |
| 10-11 | Rally, Ponferrada | have | items |
| 10-12 | Statements after Fiesta Nacional parade (Ceuta ships) | MISSING | Antena 3 mp4 in missing.csv |
| 10-14 | Rally, Zaragoza | have | items |
| 10-15 | European Council: arrival statements, Mínguez | have | Moncloa + RTVE YT |
| 10-16 | Statement after European Council | have | items |
| 10-17 | Comité Federal / rally, Fuenlabrada | have | items |
| 10-19 | Signing, Estatuto del Estudiantado (Moncloa) | have | items; Short also queued |
| 10-19 | Rally, Valladolid | have | items |
| 10-20 | Oliva (DANA) visit and institutional statement | have | items |
| 10-21 | Rally, Burgos | have | items |
| 10-22 | TVE La Revuelta | have | items (x3) |
| 10-24 | Rally, Granada | have | items |
| 10-24 | Video at Reina Sofía / Guernica | MISSING | Onda Cero mp4 in missing.csv |

## Alberto Núñez Feijóo (PP)

Known appearances 20: have 18, queued 0, missing 2. Estimated coverage 90% of the appearances found.

| Date (Oct) | Appearance | Status | Notes |
|---|---|---|---|
| 10-05 | Declaración institucional; Congreso Empresa Familiar | have | items (x2) |
| 10-07 | Ceuta with Vivas (precampaign start) | have | items |
| 10-08 | Junta Directiva Nacional | have | items |
| 10-10 | Act with Ayuso and Almeida, Madrid | have | items |
| 10-12 | Statements to press after Fiesta Nacional reception | MISSING | Antena 3 / El Mundo text; no clean recording found |
| 10-13 | Act, Huesca | have | items |
| 10-13 | Interview, esRadio Es la Mañana de Federico | have | items |
| 10-14 | Brussels arrival statements (Ceuta ships) | MISSING | Antena 3 mp4 in missing.csv; may be the same event as 10-15 |
| 10-15 | Brussels press statements | have | items |
| 10-16 | Act, Toledo | have | items |
| 10-17 | ONCE Unidad Progresista congress | have | items |
| 10-18 | Act, Barcelona (Albiol) | have | items; 10-19 YT queued (duplicate) |
| 10-19 | Contrato con España presentation | have | items |
| 10-20 | Interview, COPE Herrera | have | items |
| 10-21 | Housing act with Moreno, Seville | have | items |
| 10-23 | Interview, SER Hoy por Hoy | have | items |
| 10-23 | Interview, TVE (TD1, La hora de La 1, Noticias YT) | have | items (x3 recordings, one interview) |
| 10-23 | Rally, Valencia | have | items |
| 10-24 | Act, Vigo | have | items |
| 10-25 | Act with Mañueco, Salamanca | have | items + queue |

## Main gaps

1. **Montero**: nearly complete in what is visible. The one miss is a TVE morning interview (Mañaneros 360, 8 Oct) that rotated out of the 20-item RTVE feed. I found no radio or TV interview of hers after 13 Oct; the next ones (El perro andaluz, Wild Project) are not aired yet.
2. **Colau**: eight appearances missing, five of them with no recording I can reach. Two kinds of gap: (a) short statements to the press (5, 6, 19 Oct) that exist only as text; (b) the 13 Oct Cafè d'idees interview (La 2 / Ràdio 4) and two weekend acts (24 Oct pensions demo, 25 Oct) that only exist as broadcaster news clips. She depends on third-party channels.
3. **Abascal**: weekend statements and the Vox Senate-pact messaging (17 and 18 Oct, 25 Oct) are missing; the Vox channel did not upload them as full events. 7 Oct is a text-only report.
4. **Sánchez**: two print-and-video interviews (elDiario.es 7 Oct, El País 25 Oct, the latter text only) and the 12 Oct post-parade statements. The elDiario.es video exists only on YouTube. Three Moncloa videos (13 Oct Patronato Víctimas del Terrorismo, 19 Oct CENEM, 22 Oct ATRAE) are filtered out as B-roll by `discover_extra.py`; Sánchez may speak in 22 Oct ATRAE, worth a manual look.
5. **Feijóo**: well covered by the PP channel. Missing: 12 Oct press statements and the 14 Oct Brussels arrival (possible duplicate of 15 Oct).

## Sources that keep appearing and we do not follow

| Source | Why it matters | How to follow |
|---|---|---|
| Atresmedia news pages (laSexta, Antena 3, Onda Cero) | Every statement, rally and interview has a 1 to 8 MB mp4 or mp3 clip at `dpvclip.lasexta.com`, `dpvclip.antena3.com`, `dpvclip.ondacero.es`. No DRM, no login, HEAD returns 200. 8 of the 12 missing rows come from here | No RSS found (lasexta/antena3/ondacero rss URLs return 400/404). Discover with Google News RSS (`https://news.google.com/rss/search?q=...`), then read the page for the mp4. **`kind_of()` in `src/fetch.py` returns None for these URLs**; a rule like `"dpvclip." in url and url.endswith(".mp4")` is needed |
| Europa Press video | Longer act footage (19.6 MB for the 25 Oct Colau act) at `video4.europapress.net/ep/H264/.../*.mp4` | Article pages only; same `kind_of` change. RSS `https://www.europapress.es/rss/rss.aspx?ch=66` has just 10 items |
| RTVE Play programmes not in `RTVE_PROGRAMMES` | Candidate statements and interviews appear as clips under these programmes | `https://www.rtve.es/api/programas/<id>/videos.rss` (verified, 20 items each): Informativo 24h 46052, La tarde en 24h 30870, Telediario fin de semana 135932, Los desayunos de TVE 1655, Cafè d'idees 131940 (La 2 / Ràdio 4) |
| RTVE feed depth | All RTVE feeds hold only the 20 newest items; Mañaneros (already followed, id 175650) lost the Montero interview this way | Run `discover_extra.py rtve` at least every 12 h until the campaign ends |
| elDiario.es video interviews | Sánchez (7 Oct) and Colau (23 Oct) long interviews | YouTube channel only; no mp4. Needs the home-PC route, not the VPS |
| La Razón video interviews | Abascal interview 18 Oct | YouTube embed in the article |
| Canal Sur, Telemadrid | Both carry candidate statements. Telemadrid pages already work with the `rtve` kind; Canal Sur serves `static.canalsur.es/.../playlist.m3u8` (HLS, no login) | Telemadrid RSS `https://www.telemadrid.es/rss/section/653010/` (10 items) |
| The Wild Project (Jordi Wild) | Feijóo, Abascal, Colau and Sánchez have all accepted (20 to 24 Oct); episodes land after 25 Oct | Already in `feeds.yaml` (anchor.fm); video is YouTube only |

## Caveats

- The appearance list comes from news coverage. Anything not reported (regional TV and radio interviews, closed events, TikTok/Instagram lives, local acts without press) is invisible here. Real coverage is lower than the table, probably by 10 to 20 points.
- Google News date buckets drift by up to a day; where the same event was reported on two days I matched on content, not date.
- "have" means an item exists for that event from any source, including a clip or re-upload. Where the only recording is a news clip, it is partial.
- I did not verify that every listed clip is the candidate speaking for its whole length. The Colau 25 Oct laSexta and Europa Press clips and the Feijóo 14 Oct clip may overlap other recordings.
- No pp.es, psoe.es, voxespana.es, podemos.info or Frente Amplio agenda was reachable (404 or 403). The Moncloa agenda was, but it lists only 5 days.
- Not fetchable: the Zaragoza video (El Periódico de Aragón, WAF 406), Telecinco/mitele pages (403 and DRM), Atresplayer episodes (paid), Diario Red (403).
- Belarra appears in items and queue but is not one of the five, so she is excluded from the counts.
- Fetch kinds needed for the 12 rows in `data/missing.csv`: `rtve` (2 rows), `direct` (1 row, an m4a served as .mp3), `youtube` (1 row), and a new `direct_video` rule for the 8 mp4 rows (laSexta, Antena 3, Onda Cero, Europa Press hosts).
