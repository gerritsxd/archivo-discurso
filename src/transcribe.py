"""Transcribe one audio file with faster-whisper and write JSON with segments + word timestamps.

Usage (run with -I because the input audio is downloaded, untrusted data):
    .venv\\Scripts\\python -I src\\transcribe.py data\\raw\\<slug>\\audio.wav out.json
        [--model large-v3] [--device cuda] [--compute-type float16]
"""
import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path


def add_cuda_dll_dirs():
    """On Windows, CTranslate2 needs cuBLAS 12 + cuDNN 9 DLLs. Take them from the
    nvidia-cublas-cu12 / nvidia-cudnn-cu12 pip packages inside this venv."""
    if os.name != "nt":
        return []
    added = []
    for sp in sys.path:
        nv = Path(sp) / "nvidia"
        if not nv.is_dir():
            continue
        for bin_dir in nv.glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            added.append(str(bin_dir))
    return added


class GpuMemSampler:
    """Polls nvidia-smi for peak GPU memory used (whole GPU, MiB) and this process's usage."""

    def __init__(self, interval=0.5):
        self.interval = interval
        self.peak_total = None
        self.baseline = None
        self._stop = threading.Event()
        self._t = None

    def _read(self):
        import subprocess
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip().splitlines()
            return int(out[0])
        except Exception:
            return None

    def _loop(self):
        while not self._stop.is_set():
            v = self._read()
            if v is not None:
                self.peak_total = v if self.peak_total is None else max(self.peak_total, v)
            self._stop.wait(self.interval)

    def start(self):
        self.baseline = self._read()
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out_json")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--compute-type", default="float16")
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--language", default="es")
    ap.add_argument("--batch", type=int, default=0, help="batch size for batched decoding (0 = sequential)")
    ap.add_argument("--names", default=str(Path(__file__).resolve().parent.parent / "config" / "names.txt"),
                    help="file with names to expect (hotwords); empty string to disable")
    args = ap.parse_args()

    names = []
    if args.names and Path(args.names).is_file():
        names = [l.strip() for l in Path(args.names).read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.lstrip().startswith("#")]
    hotwords = ", ".join(names) or None

    dll_dirs = add_cuda_dll_dirs() if args.device == "cuda" else []
    from faster_whisper import WhisperModel  # import after DLL dirs are set

    sampler = GpuMemSampler() if args.device == "cuda" else None
    if sampler:
        sampler.start()

    t0 = time.perf_counter()
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    t_load = time.perf_counter() - t0

    t1 = time.perf_counter()
    if args.batch:
        # batched: VAD cuts the audio into chunks that are decoded in parallel (~3x faster);
        # chunks are independent, so there is no previous-text conditioning anyway
        from faster_whisper import BatchedInferencePipeline
        segments, info = BatchedInferencePipeline(model=model).transcribe(
            args.audio, language=args.language, hotwords=hotwords, word_timestamps=True,
            beam_size=args.beam_size, batch_size=args.batch)
    else:
        segments, info = model.transcribe(
            args.audio,
            language=args.language,
            vad_filter=True,
            hotwords=hotwords,  # unlike initial_prompt, applied to every window
            word_timestamps=True,
            beam_size=args.beam_size,
            condition_on_previous_text=False,  # reduces repetition loops on long audio
        )
    segs = []
    for s in segments:  # generator: decoding happens here
        segs.append({
            "id": s.id,
            "start": round(s.start, 3),
            "end": round(s.end, 3),
            "text": s.text.strip(),
            "avg_logprob": round(s.avg_logprob, 4),
            "no_speech_prob": round(s.no_speech_prob, 4),
            "words": [
                {"start": round(w.start, 3), "end": round(w.end, 3),
                 "word": w.word, "prob": round(w.probability, 4)}
                for w in (s.words or [])
            ],
        })
    t_trans = time.perf_counter() - t1
    if sampler:
        sampler.stop()

    result = {
        "audio": str(Path(args.audio).resolve()),
        "model": args.model,
        "device": args.device,
        "compute_type": args.compute_type,
        "beam_size": args.beam_size,
        "language": info.language,
        "hotwords": hotwords,
        "audio_duration_s": round(info.duration, 2),
        "audio_after_vad_s": round(info.duration_after_vad, 2),
        "load_time_s": round(t_load, 2),
        "transcribe_time_s": round(t_trans, 2),
        "rtf_audio_per_proc": round(info.duration / t_trans, 2) if t_trans else None,
        "gpu_mem_baseline_mib": sampler.baseline if sampler else None,
        "gpu_mem_peak_mib": sampler.peak_total if sampler else None,
        "cuda_dll_dirs": dll_dirs,
        "text": " ".join(s["text"] for s in segs),
        "segments": segs,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("segments", "text", "cuda_dll_dirs")}
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
