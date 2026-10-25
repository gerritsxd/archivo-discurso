#!/usr/bin/env bash
# PC side (Windows Task Scheduler, daily, or by hand): pull the VPS queue, download the audio
# (YouTube needs this residential IP), transcribe + diarize + name on the GPU, update the
# database on the VPS, rebuild the site and publish it to gerritsxd.com/discurso/.
set -u
cd "$(dirname "$0")/.."
VPS=ubuntu@gerritsxd.com
PY=.venv/Scripts/python.exe
mkdir -p logs data
exec >> logs/pc_sync.log 2>&1
echo "== $(date -u +%FT%TZ)"
scp -q "$VPS:discurso/data/queue.csv" data/queue.csv || echo "queue pull failed, using local copy"
$PY -u src/fetch.py                              # the original M0 inventory (no-op once done)
[ -f data/queue.csv ] && $PY -u src/fetch.py --inventory data/queue.csv
$PY -u src/backfill_channels.py                  # channel uploads beyond the RSS window (PC only)
[ -f data/queue_backfill.csv ] && $PY -u src/fetch.py --inventory data/queue_backfill.csv
$PY -u src/process.py
# database on the VPS: push the item files, rebuild archivo.db (the API reads it live)
tar cf - -C data items | ssh "$VPS" 'mkdir -p ~/discurso/data && tar xmf - -C ~/discurso/data && cd ~/discurso && python3 -I src/build_db.py && set -a && . ~/armario/.env && set +a && python3 -I src/score_quotes.py && python3 -I src/tag_claims.py && python3 -I src/check_insults.py && python3 -I src/find_contradictions.py && python3 -I src/check_attribution.py'
$PY -I src/export_site.py
# publish: upload to a fresh dir, then swap, so visitors never see a half-copied site
tar czf - -C site . | ssh "$VPS" 'set -e; W=/var/www/gerritsxd; rm -rf $W/discurso.new; mkdir -p $W/discurso.new;
  tar xzmf - -C $W/discurso.new; rm -rf $W/discurso.old; [ -d $W/discurso ] && mv $W/discurso $W/discurso.old;
  mv $W/discurso.new $W/discurso; rm -rf $W/discurso.old'
echo "published"
