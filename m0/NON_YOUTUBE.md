# Places candidates speak that are not YouTube (2026-10-25)

All tests run **from the VPS** (OVH Frankfurt, yt-dlp 2026.10.21, no ffmpeg) unless marked. Downloads checked with `yt-dlp --test` (first ~10 KB) or an HTTP range request. A few requests per site with 1.5 s pauses; robots.txt read first. No cookies, no alternative player clients, no proxies, no YouTube front-ends. Nothing in the fetched pages was addressed to an AI. One note: `cmmedia.es` robots.txt blocks `anthropic-ai` by name, so read that as "no AI crawlers wanted" (it's skipped anyway).

## Ranking

| # | Source | Discover from VPS? | Download from VPS? | Titles name the speaker? | Notes |
|---|---|---|---|---|---|
| 1 | **Congreso: Diputación Permanente** | **yes**: JSON list of sessions + session page | **yes**: plain MP4 per speech on `static.congreso.es` (HTTP 206 OK) | **yes, official field** "Belarra Urteaga, Ione (GMx)" | Best attribution we have: one file per speech, speaker named by the Cámara. Found Belarra ×2 on 16 Oct. Diario de Sesiones = ground truth. Only meets a few times while the Cortes are dissolved. |
| 2 | **La Moncloa: Vídeos > Presidente** | **yes**: index page, `title="D/M/YYYY. Título"` | **yes**: own HLS (Wowza `smultimedia.lamoncloa.gob.es/...smil/playlist.m3u8`), yt-dlp generic extractor works | always Sánchez (govt role) | **Human VTT captions** on speech videos (e.g. 5 Oct declaración), so free ground truth for WER. No audio-only rendition (480p ≈ 53 MB for 9 min). B-roll videos have no captions; the script skips those. robots.txt is empty. |
| 3 | **RTVE Play TV programmes** | **yes**: `https://www.rtve.es/api/programas/<id>/videos.rss` (20 newest, has `category` person tags) | **yes**: yt-dlp `rtve.es:alacarta`, DASH audio, no DRM | often ("Feijóo desvela…", "La Revuelta \| Pedro Sánchez: …"); news cuts need the strict rule | robots: `/api/` disallowed but `Allow: /*.rss$` wins for the plain `.rss` URL. `?size=60` / `?page=2` work but end the URL with a query, so they fall under `Disallow: /api/`: **don't use them**. With only 20 items, crawl at least daily (Telediarios ≈ 2 days deep). Programme ids are in `discover_extra.py`. |
| 4 | **RNE audio programmes** | yes, same feed type `.../audios.rss` | yes (yt-dlp `rtve.es:audio` → mp3; ztnr direct also works) | yes for interview clips | Already in `feeds.yaml`. **Fix:** those entries use host `api.rtve.es`, whose robots.txt is `Disallow: /` with a short allow list. Switch to `https://www.rtve.es/api/programas/<id>/audios.rss` (checked: same feed for 119312). |
| 5 | **3Cat (TV3)** | **yes**: `https://api.3cat.cat/videos?_format=json&items_pagina=50&ordre=-data_publicacio&programatv_id=<id>` (robots open) | **yes**: yt-dlp `CCMA`, DASH audio, `geolocalitzacio: TOTS` (not geo-blocked) | yes for clips ("Colau treu ferro…", "Ada Colau, disposada…") | Catalan subtitles listed per item (`subtitols: CAT_CA`), worth fetching later. Ids: Telenotícies 136938435, Els Matins 145947628. Full episodes are titled only by date. Their `entradeta` (description) names the guest. Mostly Colau and Catalan politics. |
| 6 | **Twitch** | listing works via yt-dlp (`/videos?filter=archives`); official discovery needs a free Helix API app (client-credentials), not done | **yes**: `-f audio_only` VOD fragments | stream titles rarely name guests | List only. No known candidate stream yet. Add a channel when one is announced. |
| 7 | **Telemadrid** | weak: one 10-item programmes RSS (`/rss/section/653010/`), no search | **yes**: page → Brightcove, audio-only DASH | sometimes | Low value for national candidates (mostly Ayuso/Madrid). Not in the script. |
| 8 | **Podcasts (Apple search)** | yes: `itunes.apple.com/search?entity=podcastEpisode&country=es&term=<name>` returns episode title, date, feedUrl, mp3 | direct mp3 | sometimes | Good **discovery-only** net across all podcasts, but it mostly returns feeds already in `feeds.yaml` plus a lot of commentary from unknown shows (whitelist problem). New broadcaster-grade feeds it surfaced: Per determinar (Catalan, Colau interview S15E01 6 Oct, `feeds.feedburner.com/PerDeterminar`), Radiocable/La Cafetera (`radiocable.com/secciones/audio/feed`), En casa de Herrero (esRadio, `esradio.libertaddigital.com/en-casa-de-herrero/podcast.xml`), Un tema al día (elDiario.es; journalists, not candidates). Not in the script. Pass them to the agent working on feeds. |
| — | Canal Sur Más | no: 403 AccessDenied (CloudFront), same from home NL | — | — | Probably limited to Spain. Stopped. |
| — | CRTVG / agalega.gal | no: crtvg.es "a carta" 502, agalega.gal 403 (VPS and home) | — | — | yt-dlp `Crtvg` extractor targets the dead URL. Stopped. |
| — | EITB | pages yes | **no**: media.eitb.eus 403 (VPS and home) | — | No yt-dlp extractor. Generic finds the MP4 but it's forbidden. Stopped. |
| — | À Punt | listing is JS-rendered, robots disallows `/api/` | not tested | — | No yt-dlp extractor. Stopped. |
| — | Aragón TV, CMM, IB3, RTVC (Canarias) | sites reachable | no yt-dlp extractor (`RTVCPlay` is Colombia) | — | CMM robots blocks AI crawlers. Not worth a custom scraper for national candidates. |
| — | **Atresplayer** (Antena 3, laSexta) | API `api.atresplayer.com/client/v1/...` lists episodes | **no**: yt-dlp `AtresPlayer` says "Required paid" for a 23 Oct Al Rojo Vivo clip | — | Blocked (premium). Stopped. Use their YouTube uploads (home PC) and Onda Cero podcasts. |
| — | **Mitele** (Telecinco, Cuatro) | — | **no**: yt-dlp "[DRM] … will NOT be supported" | — | DRM. Stopped. Matters for the 16 Nov cara a cara: plan the home-PC YouTube live recording. |

## `src/discover_extra.py`

Sources: `rtve`, `3cat`, `moncloa`, `congreso`. It imports `FIELDS`, `matcher` and `speaks` from `discover.py`, dedupes by URL against `m0/inventory.csv`, `data/queue.csv` and the target file, and appends to `--queue` (default `data/queue.csv`).

- **Strict "candidate speaking" rule for RTVE and 3Cat:** `discover.speaks()` (after stripping a "Programa |" prefix), **or** the candidate's name in the first three words followed by a speech verb (afirma, desvela, se compromete, ve, diu, treu…), **or** a description saying "entrevista a … <candidate>" (catches full episodes titled only by date). "Milei llama dictador a Sánchez" does **not** pass.
- **Congreso:** matches the official speaker field on the full name, so "Sánchez Serna, Javier" is not Pedro Sánchez.
- **Moncloa:** queues a video if it has a VTT track or a speech word in its title (declaración, comparecencia, rueda de prensa…). It skips captionless B-roll and prints the skip.

First run on the VPS (`--queue tmp_nonyt/queue_test.csv`, the real queue was not touched) found 13 rows: 5 RTVE (Feijóo ×2, Sánchez ×3 incl. 2 La Revuelta clips), 2 3Cat (Colau), 4 Moncloa (Sánchez, 5/15/19/20 Oct), 2 Congreso (Belarra, 16 Oct). One caveat: the "Feijóo se compromete…" RTVE item is a re-cut of his SER interview. Audio dedup (chromaprint) has to merge it with the SER item.

Suggested timer: run with `discover.py`, **twice a day** (the RTVE feeds hold only 20 items).

## Changes `fetch.py` needs (not made: another process is using it)

1. **`kind_of(url)`**, add before the final `return None`:
   ```python
   if "3cat.cat/3cat/" in url or "telemadrid.es/" in url:
       return "rtve"            # same path: yt-dlp, bestaudio (DASH m4a)
   if "lamoncloa.gob.es/multimedia/videos/" in url:
       return "moncloa"
   if "static.congreso.es/" in url and url.lower().endswith(".mp4"):
       return "direct_video"
   ```
   (Cleaner: rename `"rtve"` to `"ytdlp"`, but the `--only rtve` choice would change with it.)
2. **`download()`:**
   - `direct_video`: same as `direct`, but write `source.mp4` (the `direct` branch hard-codes `source.mp3`). Congreso speech files are ~57 MB (video). Fine for the PC. On the VPS with `--no-wav` they stay as video, so consider extracting audio on the PC and deleting the MP4.
   - `moncloa`: the yt-dlp branch, but `-f worst` instead of `bestaudio/best` (there is no audio-only rendition; `best` would take the 1080p ≈ 290 MB variant). Also fetch the captions URL from the row's `notes` (`captions https://…vtt`) into `d / "captions.vtt"`: free ground truth for M1.
3. **`--only` choices**: add `"moncloa"` and `"direct_video"`.
4. `CATALAN_OUTLETS` already contains `"3cat"`, so 3Cat rows get `language: ca` with no change.

The VPS has no ffmpeg: yt-dlp warns "writing DASH m4a" and "MPEG-TS in MP4". The files are still usable. The PC converts them to wav anyway.
