#!/usr/bin/env bash
# DRAFT, never run against any provider. Job flow on the GPU box:
#   pull batch from the VPS -> process.py -> push data/items/*.json -> shut the box down.
#
# Required env (set as provider environment variables / secrets, never in files):
#   HF_TOKEN        Hugging Face read token (pyannote community-1 terms already accepted)
#   DATA_HOST       user@host of the VPS (or any ssh/rsync target)
#   SSH_KEY_B64     base64 of a DEDICATED ssh key, restricted on the VPS to the paths below
# Optional env:
#   DATA_DIR        remote project dir (default /srv/discurso)
#   BATCH_FILE      remote file, relative to DATA_DIR, listing item ids one per line (default queue/gpu_batch.txt)
#   BATCHED=1       use transcribe_batched.py (faster; re-check WER first)
#   MAX_MINUTES     hard wall-clock cap, then stop regardless (default 600)
#   STOP_CMD        how to terminate this box, e.g. 'runpodctl remove pod $RUNPOD_POD_ID'
#                   (default: shutdown -h now, which on many pod providers only ends the container)
#   DRY_RUN=1       print the batch and exit, transfer nothing
set -uo pipefail
DATA_DIR=${DATA_DIR:-/srv/discurso}
BATCH_FILE=${BATCH_FILE:-queue/gpu_batch.txt}
MAX_MINUTES=${MAX_MINUTES:-600}
STOP_CMD=${STOP_CMD:-shutdown -h now}
APP=/app
LOG=/tmp/run.log
SSH="ssh -i $HOME/.ssh/id_run -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30"
say() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG"; }

# Always stop the box, whatever happens (success, failure, signal). This is what ends idle billing.
finish() {
  rc=$?
  say "finished rc=$rc, stopping box"
  [ "${DRY_RUN:-0}" = 1 ] && exit $rc
  [ -n "${DATA_HOST:-}" ] && rsync -a -e "$SSH" "$LOG" "$DATA_HOST:$DATA_DIR/logs/gpu_last_run.log" 2>/dev/null
  eval "$STOP_CMD"
  sleep 30
  exit $rc
}
trap finish EXIT
# Watchdog: a hung job must not bill for days.
( sleep $((MAX_MINUTES * 60)); say "MAX_MINUTES hit, forcing stop"; eval "$STOP_CMD" ) &

: "${HF_TOKEN:?HF_TOKEN missing}"
: "${DATA_HOST:?DATA_HOST missing}"
: "${SSH_KEY_B64:?SSH_KEY_B64 missing}"
mkdir -p ~/.ssh && echo "$SSH_KEY_B64" | base64 -d > ~/.ssh/id_run && chmod 600 ~/.ssh/id_run
export HF_TOKEN
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | tee -a "$LOG"

# 1. what to do
rsync -a -e "$SSH" "$DATA_HOST:$DATA_DIR/$BATCH_FILE" /tmp/batch.txt || { say "no batch file"; exit 1; }
[ -s /tmp/batch.txt ] || { say "empty batch, nothing to do"; exit 0; }
say "$(wc -l < /tmp/batch.txt) items in batch"
if [ "${DRY_RUN:-0}" = 1 ]; then cat /tmp/batch.txt; exit 0; fi

# 2. inputs: config + voiceprints (not in the image), then the audio of this batch
mkdir -p $APP/data/raw $APP/data/items $APP/data/work $APP/config $APP/voiceprints
rsync -a -e "$SSH" "$DATA_HOST:$DATA_DIR/config/"      $APP/config/
rsync -a -e "$SSH" "$DATA_HOST:$DATA_DIR/voiceprints/" $APP/voiceprints/
rsync -a -e "$SSH" --files-from=/tmp/batch.txt "$DATA_HOST:$DATA_DIR/data/raw/" $APP/data/raw/
# Audio may be shipped as audio.opus/.flac to save transfer (about 14 MB/h vs 115 MB/h for 16 kHz wav);
# process.py wants audio.wav, so convert where needed.
for d in $APP/data/raw/*/; do
  [ -f "$d/audio.wav" ] && continue
  s=$(ls "$d"audio.* 2>/dev/null | head -1)
  [ -n "$s" ] && ffmpeg -loglevel error -y -i "$s" -ac 1 -ar 16000 "$d/audio.wav"
done

# 3. gated pyannote model: download now with the runtime token (cached under HF_HOME)
python - <<'PY' 2>&1 | tee -a "$LOG"
import os
from huggingface_hub import snapshot_download
snapshot_download("pyannote/speaker-diarization-community-1", token=os.environ["HF_TOKEN"])
PY

# 4. process
[ "${BATCHED:-0}" = 1 ] && cp $APP/gpu_runner/transcribe_batched.py $APP/src/transcribe.py
cd $APP && python -I src/process.py 2>&1 | tee -a "$LOG"

# 5. push results (also runs on partial success; process.py skips finished items on a re-run)
rsync -a -e "$SSH" $APP/data/items/ "$DATA_HOST:$DATA_DIR/data/items/"
say "pushed $(ls $APP/data/items | wc -l) item json files"
# data/work (transcript/diarization intermediates) stays on the box and dies with it. If you want
# it for later --reidentify runs, also rsync $APP/data/work/ to $DATA_DIR/data/work/.
