# Geo test: can the Frankfurt VPS reach the sources? (2026-10-25)

Method: `src/geo/geo_test.sh` resolves the audio stream with yt-dlp 2026.10.21 and fetches the first 64 KB; RTVE Play also checked with `yt-dlp --test` (first 10 KB). Same test from the VPS (OVH Frankfurt, DE) and from home (NL, residential). Raw output: `geo_frankfurt.txt`, `geo_home.txt`.

| Source | VPS Frankfurt | Home NL | Verdict |
|---|---|---|---|
| RTVE Play on demand (La Revuelta, Sánchez 22 Oct) | works | works | not geo-blocked outside Spain |
| YouTube (PP, Moncloa, Antena 3, RTVE, laSexta) | **blocked**: "Sign in to confirm you're not a bot" | works | YouTube blocks data-centre IPs, not countries |
| YouTube channel RSS feeds | works | works | discovery can run on the VPS |
| RTVE live La 1 / 24h | yt-dlp extractor broken ("data_setup") | same | not a geo result; needs its own recorder before the debates |
| Atresplayer live (Antena 3, laSexta) | unsupported URL in yt-dlp | same | not a geo result; check before 16 Nov |
| Mitele live (Telecinco, Cuatro) | DRM | DRM | off limits (DRM) |

## Decision
- **A Spanish VPS is not needed** for anything found so far, and it would not fix the real problem: YouTube blocks any data-centre IP, Spanish or not.
- **Split:** the VPS discovers (RSS, Moncloa, Congreso, pp.es, radio feeds) and downloads everything that isn't YouTube (radio MP3s, RTVE Play). The **home PC** downloads YouTube audio (residential IP, ~30 MB/h) and does the GPU work anyway.
- Not chosen: YouTube cookies on the VPS (a Google account would risk a ban, and the archive shouldn't depend on one), paid residential proxies (cost, murky).
- Debate nights: record from the broadcasters' YouTube live streams on the home PC; build an RTVE live recorder as backup before 16 Nov.

## VPS capacity
2 vCPU, 3.7 GB RAM (2.9 GB already used by other services), 30 GB free disk. Fine for discovery + radio downloads + the database; too small to transcribe. An upgrade can wait until M3 shows the real load.
