(Prepend tasks/_common.md.)

Milestone M0, **radio interviews and podcasts/streams**.
1. Podcast RSS feeds / on-demand pages for SER (Hoy por Hoy, Hora 25), COPE (Herrera en COPE, La Linterna), Onda Cero (Más de uno), RNE (Las mañanas de RNE), esRadio (Es la mañana de Federico) and others where candidates appeared. Verify each feed returns XML (curl). Note full-show vs per-segment items.
2. Every radio interview with these people since 5 Oct 2026: best audio URL, date, approx duration, start offset in long episodes if known.
3. Podcasts / long-form YouTube or Twitch shows (non-TV) since 5 Oct.

Output: m0/audio_sources.csv (tier=2; has_text=no unless a transcript exists), m0/feeds.yaml (station, programme, rss_url, verified, granularity), m0/audio_sources_NOTES.md.
