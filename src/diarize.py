"""Speaker diarization ("who spoke when") with pyannote, plus a per-speaker voice embedding.

Usage (run with -I because the input audio is downloaded, untrusted data):
    .venv\\Scripts\\python -I src\\diarize.py data\\raw\\<slug>\\audio.wav out.json
        [--pipeline pyannote/speaker-diarization-community-1] [--num-speakers N]

Needs the Hugging Face token in the HF_TOKEN environment variable (user env on Windows).
The audio is loaded in memory with soundfile, so pyannote never has to decode files itself.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def hf_token():
    tok = os.environ.get("HF_TOKEN")
    if not tok and os.name == "nt":
        # setx writes to the user registry; a shell opened earlier won't have it in its env
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            tok = winreg.QueryValueEx(k, "HF_TOKEN")[0]
    if not tok:
        sys.exit("HF_TOKEN is not set")
    return tok


def load_audio(path):
    import numpy as np
    import soundfile as sf
    import torch
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    data = data.mean(axis=1)  # mono
    wav = torch.from_numpy(np.ascontiguousarray(data)).unsqueeze(0)
    if sr != 16000:
        import torchaudio.functional as AF
        wav = AF.resample(wav, sr, 16000)
        sr = 16000
    return wav, sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out_json")
    ap.add_argument("--pipeline", default="pyannote/speaker-diarization-community-1")
    ap.add_argument("--num-speakers", type=int)
    args = ap.parse_args()

    import torch
    from pyannote.audio import Pipeline

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    t0 = time.time()
    pipe = Pipeline.from_pretrained(args.pipeline, token=hf_token())
    pipe.to(device)
    wav, sr = load_audio(args.audio)
    duration = wav.shape[1] / sr

    t1 = time.time()
    kw = {"num_speakers": args.num_speakers} if args.num_speakers else {}
    out = pipe({"waveform": wav, "sample_rate": sr}, **kw)
    elapsed = time.time() - t1

    # pyannote 4 returns an object with .speaker_diarization and .speaker_embeddings;
    # pyannote 3 returns the Annotation directly (embeddings need return_embeddings=True)
    ann = getattr(out, "speaker_diarization", out)
    # pyannote 4 also gives an "exclusive" version (one speaker at a time), made for
    # aligning with transcripts; use it for the turns so words at turn edges land better
    excl = getattr(out, "exclusive_speaker_diarization", None)
    embs = getattr(out, "speaker_embeddings", None)
    labels = ann.labels()

    turns = [{"start": round(seg.start, 3), "end": round(seg.end, 3), "speaker": spk}
             for seg, _, spk in (excl or ann).itertracks(yield_label=True)]
    speakers = {}
    for i, spk in enumerate(labels):
        talk = sum(t["end"] - t["start"] for t in turns if t["speaker"] == spk)
        speakers[spk] = {"talk_s": round(talk, 1)}
        if embs is not None:
            speakers[spk]["embedding"] = [round(float(x), 6) for x in embs[i]]

    result = {
        "audio": str(args.audio),
        "pipeline": args.pipeline,
        "duration_s": round(duration, 2),
        "elapsed_s": round(elapsed, 2),
        "load_s": round(t1 - t0, 2),
        "realtime_factor": round(duration / elapsed, 1) if elapsed else None,
        "device": str(device),
        "turns_from": "exclusive" if excl is not None else "regular",
        "speakers": speakers,
        "turns": turns,
    }
    Path(args.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("turns",)} |
                     {"speakers": {s: d["talk_s"] for s, d in speakers.items()},
                      "n_turns": len(turns)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
