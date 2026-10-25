"""GPU stage: turn every fetched item into a named, timestamped transcript.

For each data/raw/<id>/ with audio.wav + meta.json and no data/items/<id>.json yet:
    transcribe.py  -> data/work/<id>/transcript.json
    diarize.py     -> data/work/<id>/diarization.json
    voiceprints.py -> data/work/<id>/identity.json
    assemble       -> data/items/<id>.json   (the format the website and the database read)

Re-runnable: finished steps are skipped, a failed item is logged and retried next run.

Usage:
    .venv\\Scripts\\python src\\process.py [--limit N] [--only <id>] [--reidentify]

--reidentify re-runs only the naming + assembly for every item (after adding voiceprints).
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
RAW, WORK, ITEMS = ROOT / "data" / "raw", ROOT / "data" / "work", ROOT / "data" / "items"
sys.path.insert(0, str(SRC))
from merge_speakers import speaker_for, smooth  # noqa: E402

PY = [sys.executable, "-I"]  # -I: inputs are downloaded, untrusted files


def run(args, log):
    with open(log, "a", encoding="utf-8") as f:
        subprocess.run(PY + args, check=True, stdout=f, stderr=subprocess.STDOUT)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def assemble(iid, meta, w):
    tr, di, ident = load(w / "transcript.json"), load(w / "diarization.json"), load(w / "identity.json")
    words = [x for s in tr["segments"] for x in s.get("words", [])]
    end_of = {x["start"]: x["end"] for x in words}  # word start -> word end
    blocks = []  # [speaker, start, [words], [word starts]], the shape smooth() expects
    for x in words:
        spk = speaker_for(x["start"], x["end"], di["turns"])
        if blocks and blocks[-1][0] == spk:
            blocks[-1][2].append(x["word"]); blocks[-1][3].append(x["start"])
        else:
            blocks.append([spk, x["start"], [x["word"]], [x["start"]]])
    sm = smooth(blocks) if blocks else []
    speakers = ident["speakers"]
    turns = []
    for b in sm:
        text = "".join(b[2]).strip()
        if not text:
            continue
        s = speakers.get(b[0], {})
        turns.append({
            "start": round(b[1], 2), "end": round(end_of[b[3][-1]], 2),
            "label": b[0], "person": s.get("person"), "name": s.get("name", b[0]), "text": text,
        })
    return {
        "id": iid,
        "date": meta.get("date"), "expected_person": meta.get("person"), "kind": meta.get("kind"),
        "outlet": meta.get("outlet"), "title": meta.get("title"), "url": meta.get("url"),
        "language": meta.get("language", "es"), "duration_s": tr.get("audio_duration_s"),
        "sha256": meta.get("sha256"), "fetched_at": meta.get("fetched_at"),
        "pipeline": {
            "asr": f"faster-whisper {tr.get('model')} ({tr.get('compute_type')})",
            "diarization": di.get("pipeline"), "voiceprint_threshold": ident.get("threshold"),
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reviewed": False,
        },
        "speakers": {lab: {k: v for k, v in s.items() if k != "scores"} for lab, s in speakers.items()},
        "turns": turns,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only")
    ap.add_argument("--reidentify", action="store_true")
    args = ap.parse_args()
    ITEMS.mkdir(parents=True, exist_ok=True)

    dirs = sorted(d for d in RAW.iterdir() if (d / "audio.wav").exists() and (d / "meta.json").exists())
    if args.only:
        dirs = [d for d in dirs if d.name == args.only]
    todo = [d for d in dirs if args.reidentify or not (ITEMS / f"{d.name}.json").exists()]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} item(s) to process")

    for d in todo:
        iid, meta = d.name, load(d / "meta.json")
        w = WORK / iid
        w.mkdir(parents=True, exist_ok=True)
        log = w / "process.log"
        t0 = time.time()
        try:
            if not (w / "transcript.json").exists():
                run([str(SRC / "transcribe.py"), str(d / "audio.wav"), str(w / "transcript.json"),
                     "--language", meta.get("language", "es")], log)
            if not (w / "diarization.json").exists():
                run([str(SRC / "diarize.py"), str(d / "audio.wav"), str(w / "diarization.json")], log)
            run([str(SRC / "voiceprints.py"), "identify", str(w / "diarization.json"),
                 str(w / "identity.json")], log)
            item = assemble(iid, meta, w)
            (ITEMS / f"{iid}.json").write_text(json.dumps(item, ensure_ascii=False, indent=1), encoding="utf-8")
            named = sorted({t["name"] for t in item["turns"] if t["person"]})
            print(f"ok   {iid}  {time.time() - t0:5.0f}s  {', '.join(named) or '(nadie identificado)'}")
        except Exception as e:
            print(f"FAIL {iid}  {e}  (see {log.relative_to(ROOT)})")


if __name__ == "__main__":
    main()
