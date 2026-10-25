# Debate-night recorder (task F, written 2026-10-25)

Goal: capture the audio of a ~2 h live TV debate into `data/raw/<id>/` so `src/process.py` transcribes it overnight and it is published next morning. No YouTube anywhere (home IP rate-limited; not needed).

## What was tested (2026-10-25, from the home PC in NL)
| Source | Result |
|---|---|
| RTVE La 1 HLS `https://rtvelivestream.rtve.es/rtvesec/la1/la1_main_dvr.m3u8` | OPEN, no DRM (no EXT-X-KEY), works from NL. 60 s capture OK via `record_live.py`: AAC-LC 48 kHz stereo, ~131 kb/s (audio only, copy). Master playlist: 720/576/360p video + separate audio groups (Castellano default, "Original", audio description) + subtitles in es/en/gl/ca/eu. |
| RTVE Canal 24h `.../rtvesec/24h/24h_main.m3u8` | OPEN, 60 s WAV capture OK. |
| RTVE La 2 `.../la2/la2_main.m3u8`, RNE Radio 5 / Radio Exterior (`rne_re_main.m3u8`) | HTTP 200 (playlist reachable; not recorded). `rne_r5_main` 404. |
| RNE Radio 1 `https://rtvelivestream.rtve.es/rtvesec/rne/rne_r1_main.m3u8` | OPEN audio HLS, 60 s OK, AAC 48 kHz stereo ~197 kb/s. |
| Same RTVE URLs from the OVH VPS (Frankfurt) | **HTTP 451** (blocked: geo or data-centre). So RTVE must be recorded from the PC; do not use the VPS. Not circumvented. |
| yt-dlp `rtve.es:live` extractor | Fails (`Unable to extract data_setup`); not needed, the HLS URLs above work directly with ffmpeg. |
| Mediaset (Telecinco / Cuatro) `mitele.es/directo/...` -> `mediasetinfinity.es/directo/...` | Page loads, but yt-dlp flags the site as DRM; the player needs login. **Not usable** (not bypassed). |
| Cadena SER (streamtheworld CADENASER.mp3) | Connection timed out from the PC; unverified. COPE / Onda Cero not tested (check exact URLs a week before). |
| Atresplayer live (Antena 3) | page 200, not tested (login/DRM likely; not pursued). |

Caveat: RTVE URLs are the ones the player uses today; they could change. Re-test on 14 Nov. Also the HLS may be geo-restricted to Spain-only for some events (rights); RTVE debates are RTVE's own, so should be fine. Test during a real live programme on 14-15 Nov.

## Plan per debate
| Date | Debate | Primary | Backup |
|---|---|---|---|
| 16 Nov | Sánchez–Feijóo cara a cara, Mediaset (Telecinco + Cuatro), hosts Franganillo and Alba Lago | Mediaset TV is DRM: unusable. Primary = a **radio simulcast** (Cadena SER / COPE / Onda Cero live stream, URL verified 14 Nov; RNE R1 only if RNE simulcasts, uncommon for a rival's debate) | RTVE does not broadcast it. Fallback: next-morning archive/replay (RTVE/radio podcast, YouTube replays by the home PC once the rate limit is gone, via fetch.py). The broadcaster's own full YouTube upload is the usual full-length source (normal pipeline). |
| 23 Nov | Spokespersons, RTVE | **La 1 HLS** `la1_main_dvr.m3u8` (PC) | RNE Radio 1 HLS `rne_r1_main.m3u8` (PC) if RNE simulcasts; La 1 via `Original` audio track is not needed |
| 26 Nov | Four-way, broadcaster disputed | If RTVE: La 1 HLS, backup RNE R1. If Atresmedia/Mediaset: radio simulcast, same as 16 Nov | replay download next morning |

Re-check the broadcaster/time on the day with a web search (all dates unconfirmed as of 25 Oct).

## Capture command
Preferred (script; resilient to stream drops, writes meta.json and audio.wav in the right place):
```
.venv\Scripts\python src\record_live.py https://rtvelivestream.rtve.es/rtvesec/la1/la1_main_dvr.m3u8 ^
  --minutes 180 --start "2026-11-23 21:50" --id 2026-11-23-debate-portavoces ^
  --title "Debate de portavoces (RTVE)" --outlet "RTVE La 1 en directo" --kind debate
```
(`--minutes` counts from the start time; `--start` is local PC time; omit it to start now.) Bare ffmpeg equivalent:
```
ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 -i URL -t 10800 -vn -map 0:a:0 -c:a copy audio.aac
```
Size: ~131 kb/s -> ~175 MB for 3 h; the wav is 16 kHz mono (~345 MB for 3 h).
Audio is the first track (Castellano). Radio streams: same command, URL = the icecast/HLS URL.

## Where / when
- Runs on the **home PC** (RTVE blocks the VPS). Needs the PC awake and online all evening: disable sleep (`powercfg /change standby-timeout-ac 0`) and keep it plugged in. Not in the sandboxed agent session: start it by hand or with a Task Scheduler job (action: the command above, trigger = debate day 21:50 minus 10 min).
- Start 10 min before the broadcast (pre-show; leave it), run 3 h total (`--minutes 180` from `--start`). The pre/post-show gets transcribed too; the item just becomes longer (process.py runs ~10x real time, so 3 h ~ 20 min on the 3060 Ti).
- Test on a normal live programme 3 days before (60-120 s: `--minutes 2 --raw-dir <temp>`).
- Do not record to the VPS and do not touch YouTube.

## Feeding the pipeline
1. The script leaves `data/raw/<id>/{audio.aac,audio.wav,meta.json}`; `meta.json` has the same fields as fetch.py output (`fetch_kind: live`, `kind: debate`, `person` = who speaks, e.g. "Pedro Sánchez; Alberto Núñez Feijóo").
2. `.venv\Scripts\python src\process.py` picks it up (it takes every raw dir with audio.wav + meta.json that has no `data/items/<id>.json`). Run it overnight once the GPU is free (it uses the same process as other items; do not run two at once).
3. Next morning: `deploy\pc_sync.sh` (items -> VPS DB, rebuild, site). Debates have multiple speakers: check m2 speaker naming (voiceprints exist for the six candidates; moderators are unknown, fine).
4. Do not commit audio (`data/raw` is not in git).
