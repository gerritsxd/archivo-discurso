# Task board (resume point)

Any session (or the hourly resume check) reads this file first. A task is **done** when its output files exist and its final report is logged below. If a task is `running` but no agent is working on it (session ended, usage limit hit), relaunch it from its brief in `tasks/`; the agent must first look at what already exists in its output files and continue from there, not start over.

| Task | Brief | Outputs | State |
|---|---|---|---|
| M0-text | tasks/m0-text.md | m0/text_sources.csv, m0/text_sources_NOTES.md | done 2026-10-25 |
| M0-video | tasks/m0-video.md | m0/video_sources.csv, m0/channels.yaml, m0/video_sources_NOTES.md | done 2026-10-25 |
| M0-audio | tasks/m0-audio.md | m0/audio_sources.csv, m0/feeds.yaml, m0/audio_sources_NOTES.md | done 2026-10-25 |
| M1-transcribe | tasks/m1-transcribe.md | m1/RESULTS.md, src/transcribe.py, src/wer.py, README.md | done 2026-10-25 |
| M2-setup | (main session) install pyannote in .venv, test diarization on the M1 audio | m2/ | done 2026-10-25 (pyannote 4.0.7 installed; auto-naming via voiceprints.py); HF token saved as user env HF_TOKEN, access to all 3 pyannote models verified 2026-10-25 |
| GEO-test | (main session) from the OVH Frankfurt VPS, test yt-dlp metadata/stream access (no full downloads) for the TV/YouTube URLs in m0/video_sources.csv + RTVE/Atresmedia live streams; decide if a Spanish VPS is needed | m0/GEO_TEST.md | done 2026-10-25 |
| BACKFILL | (main session) fetch all M0 audio (src/fetch.py) + process on the PC GPU (src/process.py, logs/process_run1.log); when the process run has finished, run deploy/pc_sync.sh once to publish | data/items/*.json, gerritsxd.com/discurso/ | running (started 2026-10-25) |
| DB-GAME | VPS database (src/build_db.py → ~/discurso/data/archivo.db) + API (src/api.py, discurso-api.service :8431, nginx /discurso/api/) DONE; website agent adding juego.html + API search; then main session deploys the site | site/juego.html | done 2026-10-25 (live) |
| M0-merge | (main session) merge the three CSVs into m0/inventory.csv + hours per person | m0/inventory.csv, m0/SUMMARY.md | done 2026-10-25 |

## Log
| When | What |
|---|---|
| 2026-10-25 | Four agents launched (M0 text, video, audio; M1 transcription test). |
| 2026-10-25 | M0-audio done: 9 radio interviews + 1 replay (Feijóo 3, Colau 3, Montero 2, Belarra 1, Sánchez/Abascal 0 on radio), 29 feeds verified. Gaps: regional radio unchecked; Wild Project episodes expected ~9–13 Nov. |
| 2026-10-25 | M0-text done: 36 rows (Feijóo 17 pp.es, Abascal 11 voxespana, Sánchez 6 Moncloa, Belarra 1 Diputación Permanente, Colau 1, Montero 0). psoe.es + podemos.info behind CAPTCHA walls (not bypassed). Moncloa RSS + Congreso DSCD-15-PL-{N} + pp.es WP API are clean crawl targets. |
| 2026-10-25 | M1 done: large-v3 float16 on 3060 Ti, 10.6x real time, ~4.2 GB VRAM, WER 11.4% vs edited official text (upper bound; true error likely <5%). Pins: av<16. M2-setup started. |
| 2026-10-25 | M0 done: 121 appearances, ~55 h raw / ~28 h speaking (inventory.csv, SUMMARY.md). Geo test: no Spanish VPS needed; YouTube blocks the data-centre IP, so home PC fetches YouTube, VPS does the rest. M2: COPE Feijóo diarized into 3 speakers correctly; names list (config/names.txt) fixed Feijóo/Jorge. |
| 2026-10-25 | M2 first pass: voiceprints (src/voiceprints.py, config/people.json, voiceprints/). Feijóo recognised in SER at 0.96 from a COPE-only voiceprint; others ≤0.40; Bretos correctly unknown. Edge-word smoothing in merge_speakers.py. Outputs m2/cope_named.md, m2/ser_named.md for Gerrit to check. |
| 2026-10-25 | MVP live at https://gerritsxd.com/discurso/ (5 items). VPS: discurso-discover.timer every 2 h (discover.py + radio/RTVE archive). PC: deploy/pc_sync.sh (scheduled task NOT created: auto-mode denied it; Gerrit to create). Voiceprints for all 6 candidates. Local git repo, first commit; GitHub repo created on the personal account. GPU research: m3/GPU_ON_DEMAND.md. |
| 2026-10-25 | Backfill fetch done: 70/71 downloaded; 1 YouTube 403 (TorTIWtQUYo, Feijóo 15 Oct) will be retried by the next pc_sync. GPU processing still running. |
| 2026-10-25 | VPS database + API live (https://gerritsxd.com/discurso/api/stats). nginx backup in ~/discurso/nginx-gerritsxd.backup-*. pc_sync now pushes items + rebuilds DB. |
| 2026-10-25 | Game live: https://gerritsxd.com/discurso/juego.html ; search + stats from the API. |

## Autonomous work queue (Gerrit off 2026-10-25, said "you have permissions to work all day")
Rules: never kill the running process.py; one GPU job at a time (8 GB card); no money spent, no accounts created, no public announcements, repo stays private; publish = pc_sync steps (items → VPS DB, site).
| # | Task | State |
|---|---|---|
| A | When the backfill process run ends: retry failed YouTube fetches (home IP got a YouTube bot check after the channel listing burst on 2026-10-25 ~12:00; fetch.py now sleeps 20-45 s between downloads; retry no earlier than ~18:00), process new items, push items + rebuild DB + publish site | waiting for process run + YouTube cooldown |
| B | Batched faster-whisper test: REJECTED 2026-10-25. On the 8 GB 3060 Ti, batch 8 = 2.5x real time (vs 10.6x sequential) and WER 27.8% (vs 11.4%); VRAM maxed at 7.9 GB. Keep sequential locally; batched only on a 24 GB rented GPU, re-measure there | done (rejected) |
| C | Second voiceprint enrolment per candidate from a different setting (rally/TV/RADIO), confirmed from content; enrol recurring hosts. Evidence: Colau on SER radio scored 0.47 vs her TV voiceprint, so stayed unidentified (correct, but needs a radio enrolment) | after A |
| D | m3/UPGRADE_OPTIONS.md: VPS upgrade + GPU rental options with prices, for Gerrit's return | done |
| E | Discovery: TV broadcaster YouTube channels added (strict title rule, deployed). Still todo: Google News leads + regional radio feeds | partly done |
| F | Debate-night recorder plan + test on a live YouTube stream (16 Nov first debate) | todo |
| 2026-10-25 | UPGRADE_OPTIONS.md written (OVH VPS-2 8 GB ~$8.50/mo fits). discover.py now also reads 9 TV channels (strict rule), deployed to VPS. |
| 2026-10-25 | Completeness check: backfill_channels.py listed 18 channels' uploads since 5 Oct; only 4 new (M0 inventory was near-complete on party channels). YouTube now bot-checks the home IP too (rate limit): 15 queued YouTube items failed, retry later. Shorts excluded. Regional radio agent running (m0/feeds_regional.yaml). |
| 2026-10-25 | 12 regional radio feeds added (m0/feeds_regional.yaml: EITB, Radio Galega, À Punt, Canal Sur, CLM, SER regional); discover.py reads them on the VPS. No candidate interviews in them yet. |
| 2026-10-25 | Game quality: score_quotes.py rates every quote 1-5 for content with DeepSeek (cached, quotes sent as delimited data); daily game takes each candidate's best tier (5>4>3). Today's puzzle regenerated. Distribution 1:161 2:386 3:428 4:424 5:153. |
| 2026-10-25 | Privacy page (privacidad.html, footer link): no cookies, localStorage only for game stats; nginx access_log off for /discurso/ and its API (older lines age out with logrotate, 14 days; deleting them was refused by auto mode). Batched test rejected. Process run restarted (sequential). Non-YouTube agent done: Congreso, Moncloa video, RTVE Play programme RSS, 3Cat work from the VPS (src/discover_extra.py, m0/NON_YOUTUBE.md); integrate next. |
