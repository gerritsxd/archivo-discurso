# Archivo del discurso político

Open-source archive of what Spain's main candidates say in public, from the day the 29 November 2026 general election was called. Live: **https://gerritsxd.com/discurso/** (search, transcripts with sources, and the daily game *¿Quién lo dijo?*).

Pipeline: discover appearances (party channels, radio podcasts, RTVE, Congreso, Moncloa) → download audio → Whisper large-v3 → pyannote speaker diarization → voiceprint identification → SQLite full-text database + static site. Only text, timestamps and links to the original source are published; audio and voiceprints (biometric data) stay private.

**Licences:** code MIT ([LICENSE](LICENSE)); transcripts and data CC BY 4.0. Transcripts are automatic and unreviewed: always check the source.

Design: [ARCHITECTURE.md](ARCHITECTURE.md). Milestone 1 results: [m1/RESULTS.md](m1/RESULTS.md) (large-v3 on an RTX 3060 Ti: 10.6× real time, ~4.2 GB GPU memory, 11.4 % WER against an *edited* official transcript).

## How to run (M1: transcribe one appearance and measure WER)

Windows, NVIDIA GPU (tested on an RTX 3060 Ti 8 GB), Python 3.13, ffmpeg on PATH. Commands are for Git Bash, run from this folder.

```bash
# 1. Environment. CUDA 12 cuBLAS and cuDNN 9 come from pip; transcribe.py adds their DLL folders itself.
#    Pin av<16: PyAV 19 breaks faster-whisper 1.2.1. Exact versions: requirements.lock.txt
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install faster-whisper "av<16" jiwer pypdf yt-dlp nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"

# 2. Fetch audio only (16 kHz mono) and the official transcript into data/raw/<date-slug>/
#    Use yt-dlp, not plain ffmpeg: ffmpeg silently lost ~14 s to TLS drops. Check the duration.
D=data/raw/2026-10-05-decl-inst-convocatoria; mkdir -p $D
.venv/Scripts/yt-dlp -f 480p --fragment-retries 100 -x --audio-format wav \
  --postprocessor-args "ffmpeg:-ac 1 -ar 16000" -o "$D/audio.%(ext)s" "<La Moncloa .m3u8 URL>"
curl -L -o $D/official_page.html "<La Moncloa intervención page URL>"

# 3. Transcribe. The first run downloads large-v3 (~3 GB). Always use -I: the inputs are untrusted downloads.
.venv/Scripts/python -I src/transcribe.py $D/audio.wav m1/ours.json --model large-v3 --compute-type float16

# 4. Official text, cut to the speech, then WER
.venv/Scripts/python -I src/extract_official.py $D/official_page.html m1/official_speech.txt \
  --start "Queridos ciudadanos" --end "Muchas gracias."
.venv/Scripts/python -I src/wer.py m1/ours.json m1/official_speech.txt --out m1/wer_report.json
```

- Prefer the HTML transcript to the PDF: pypdf splits words in the Moncloa PDFs.
- Scripts live in `src/`. Downloads go only in `data/`, which is private, never published, and never holds code.
- No GPU? Use `--device cpu --model small --compute-type int8` to check the pipeline.
