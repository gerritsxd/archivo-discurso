# DRAFT, never built or run. Build context = the discurso/ repo root:
#   docker build -f m3/gpu_runner/Dockerfile -t <registry>/discurso-gpu:0.1 .
# CUDA 12.6 + cuDNN 9 (what ctranslate2 4.x and torch cu126 wheels expect).
# NO tokens in the image. HF_TOKEN and the SSH key arrive as env vars at run time.
# Voiceprints and config/ are NOT baked in either: run.sh pulls them from the VPS.
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 \
    HF_HOME=/models/hf PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv ffmpeg rsync openssh-client curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Pin these to the versions in requirements.lock.txt / m1/pre_pyannote_freeze.txt before the first real build.
RUN pip install --index-url https://download.pytorch.org/whl/cu126 torch torchaudio \
 && pip install faster-whisper==1.2.1 ctranslate2==4.8.3 "pyannote.audio==4.0.7" soundfile numpy scipy

# Whisper large-v3 is public: bake it in (about 3 GB) so a fresh pod does not download it.
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-large-v3')"
# pyannote/speaker-diarization-community-1 is gated (needs accepted terms + HF_TOKEN),
# so it is NOT baked in: run.sh downloads it at start (small, seconds) with the runtime token.

WORKDIR /app
COPY src/ /app/src/
COPY m3/gpu_runner/run.sh m3/gpu_runner/transcribe_batched.py /app/gpu_runner/
RUN chmod +x /app/gpu_runner/run.sh
CMD ["/app/gpu_runner/run.sh"]
