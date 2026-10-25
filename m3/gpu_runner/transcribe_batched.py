"""Drop-in for src/transcribe.py using faster-whisper's BatchedInferencePipeline.
Same CLI and same output JSON (extra field "batch_size"). Used by run.sh when BATCHED=1.
DRAFT, never run: before trusting it, re-run the m1 test item and compare WER with m1/RESULTS.md (11.4 %).
Batched mode needs VAD (we use it anyway) and cuts each file into <=30 s VAD chunks decoded in
parallel, so there is no conditioning on previous text (we already disable that).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("out_json")
ap.add_argument("--model", default="large-v3")
ap.add_argument("--device", default="cuda")
ap.add_argument("--compute-type", default="float16")
ap.add_argument("--beam-size", type=int, default=5)
ap.add_argument("--language", default="es")
ap.add_argument("--names", default=str(Path(__file__).resolve().parent.parent / "config" / "names.txt"))
ap.add_argument("--batch-size", type=int, default=int(os.environ.get("WHISPER_BATCH", "16")))
a = ap.parse_args()

names = []
if a.names and Path(a.names).is_file():
    names = [l.strip() for l in Path(a.names).read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
hotwords = ", ".join(names) or None

from faster_whisper import BatchedInferencePipeline, WhisperModel  # noqa: E402

t0 = time.perf_counter()
model = BatchedInferencePipeline(model=WhisperModel(a.model, device=a.device, compute_type=a.compute_type))
t_load = time.perf_counter() - t0
t1 = time.perf_counter()
segments, info = model.transcribe(
    a.audio, language=a.language, batch_size=a.batch_size, hotwords=hotwords,
    word_timestamps=True, beam_size=a.beam_size, condition_on_previous_text=False)
segs = [{
    "id": s.id, "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
    "avg_logprob": round(s.avg_logprob, 4), "no_speech_prob": round(s.no_speech_prob, 4),
    "words": [{"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word,
               "prob": round(w.probability, 4)} for w in (s.words or [])],
} for s in segments]
t_tr = time.perf_counter() - t1
res = {
    "audio": str(Path(a.audio).resolve()), "model": a.model, "device": a.device,
    "compute_type": a.compute_type, "beam_size": a.beam_size, "batch_size": a.batch_size,
    "language": info.language, "hotwords": hotwords, "audio_duration_s": round(info.duration, 2),
    "audio_after_vad_s": round(info.duration_after_vad, 2), "load_time_s": round(t_load, 2),
    "transcribe_time_s": round(t_tr, 2),
    "rtf_audio_per_proc": round(info.duration / t_tr, 2) if t_tr else None,
    "text": " ".join(s["text"] for s in segs), "segments": segs,
}
Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
Path(a.out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k not in ("segments", "text")}, ensure_ascii=False))
