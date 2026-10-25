(Prepend tasks/_common.md.)

Milestone M0, **video: party/candidate YouTube channels and TV interviews**.
1. Official YouTube channels (PSOE, PP, VOX España, Podemos, Sumar/Frente Amplio, personal candidate channels): channel IDs + uploads RSS (https://www.youtube.com/feeds/videos.xml?channel_id=...).
2. Uploads since 5 Oct 2026 where a lead candidate speaks. yt-dlp metadata only (`--flat-playlist --print`, `--skip-download`, `--dateafter 20261005`): titles, dates, durations, subtitles/auto-captions. If missing: `py -3.13 -m pip install --user yt-dlp`.
3. TV interviews since 5 Oct on TVE/RTVE Play, Antena 3, laSexta, Telecinco, Cuatro: prefer the broadcaster's YouTube upload, else the player URL; note DRM.

Output: m0/video_sources.csv (tier=2 YouTube, 3 TV players; has_text = captions|auto_captions|no), m0/channels.yaml, m0/video_sources_NOTES.md (crawl approach, gaps, estimated hours per person).
