# Development

How to run each part of the pipeline. Design and reasoning: [../ARCHITECTURE.md](../ARCHITECTURE.md).

## Layout

| Path | What |
|---|---|
| `src/discover.py`, `src/discover_extra.py` | Find new appearances (YouTube channel feeds, radio podcasts, RTVE Play, Congreso, Moncloa, 3Cat) → `data/queue.csv`. Runs on the VPS every 2 h |
| `src/backfill_channels.py` | Full channel listings beyond the RSS window → `data/queue_backfill.csv` (PC only: YouTube blocks data-centre IPs) |
| `src/fetch.py` | Download audio (+16 kHz mono wav) → `data/raw/<id>/` (private, never published) |
| `src/transcribe.py` | faster-whisper large-v3, word timestamps, names list `config/names.txt` |
| `src/diarize.py` | pyannote speaker diarization + one voice embedding per speaker |
| `src/voiceprints.py` | Enrol known voices; name anonymous speakers (threshold + margin) |
| `src/process.py` | GPU stage: transcribe → diarize → identify → `data/items/<id>.json` |
| `src/build_db.py` | `data/items` → `data/archivo.db` (SQLite + FTS5) |
| `src/score_quotes.py` | Rates game quotes 1–5 for content (DeepSeek, cached) |
| `src/api.py` | Read-only JSON API: search, stats, item, daily game |
| `src/export_site.py`, `web/` | Static website |
| `deploy/` | VPS timer/services, `pc_sync.sh` (PC side of the daily run) |

## Environment (Windows PC with an NVIDIA GPU)

Tested on an RTX 3060 Ti 8 GB, Python 3.13, ffmpeg on PATH, Git Bash.

```bash
py -3.13 -m venv .venv
# CUDA 12 cuBLAS and cuDNN 9 come from pip; transcribe.py adds their DLL folders itself.
# Pin av<16: PyAV 19 breaks faster-whisper 1.2.1. Exact versions: requirements.lock.txt
.venv/Scripts/python -m pip install faster-whisper "av<16" jiwer pypdf yt-dlp pyyaml \
    nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
.venv/Scripts/python -m pip install --index-url https://download.pytorch.org/whl/cu126 torch torchaudio
.venv/Scripts/python -m pip install pyannote.audio soundfile
```

pyannote needs a free Hugging Face account, accepted terms for `pyannote/speaker-diarization-community-1`, and the token in the `HF_TOKEN` environment variable.

## Daily run

```bash
./deploy/pc_sync.sh     # pull VPS queue → fetch → process on GPU → DB on VPS → publish site
```

Always run Python with `-I` on downloaded inputs: they are untrusted files. Scripts live in `src/`; downloads only in `data/`, which never holds code.

## Measuring transcription accuracy (M1)

```bash
D=data/raw/2026-10-05-decl-inst-convocatoria
.venv/Scripts/python -I src/transcribe.py $D/audio.wav m1/ours.json
.venv/Scripts/python -I src/extract_official.py $D/official_page.html m1/official_speech.txt \
  --start "Queridos ciudadanos" --end "Muchas gracias."
.venv/Scripts/python -I src/wer.py m1/ours.json m1/official_speech.txt --out m1/wer_report.json
```

Prefer the HTML transcript to the PDF (pypdf splits words in the Moncloa PDFs). No GPU: `--device cpu --model small --compute-type int8`.

## Voiceprints

```bash
.venv/Scripts/python -I src/voiceprints.py enrol data/work/<id>/diarization.json SPEAKER_02 feijoo
.venv/Scripts/python -I src/voiceprints.py matrix data/work/*/diarization.json
.venv/Scripts/python src/process.py --reidentify
```

Only enrol a speaker after a human has confirmed who it is from the content. Voiceprints are biometric data: `voiceprints/` is git-ignored and never published.
