#!/usr/bin/env bash
# VPS side, every 2 hours (discurso-discover.timer): find new appearances, archive what the VPS
# can download (radio MP3s, RTVE Play). YouTube is fetched by the PC (data-centre IPs are blocked).
set -u
cd "$(dirname "$0")/.."
echo "== $(date -u +%FT%TZ)"
.venv/bin/python src/discover.py
.venv/bin/python src/discover_extra.py             # Congreso, Moncloa, RTVE Play, 3Cat
.venv/bin/python src/fetch.py --inventory data/queue.csv --only direct --no-wav
.venv/bin/python src/fetch.py --inventory data/queue.csv --only rtve --no-wav
.venv/bin/python src/fetch.py --inventory data/queue.csv --only moncloa --no-wav
.venv/bin/python src/fetch.py --inventory data/queue.csv --only direct_video --no-wav
