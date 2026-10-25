"""Voiceprints: enrol known voices, then name the anonymous speakers in a diarization.

A voiceprint is the average of the pyannote speaker embeddings (256 numbers) of every
recording where we *know* who the speaker is. Matching = cosine similarity.

Enrol (a human confirmed that SPEAKER_02 in this recording is Feijóo):
    python -I src\\voiceprints.py enrol m2\\cope_diarization.json SPEAKER_02 feijoo

Identify (automatic):
    python -I src\\voiceprints.py identify m2\\ser_diarization.json m2\\ser_identity.json

Compare every voiceprint with every speaker (for calibrating the threshold):
    python -I src\\voiceprints.py matrix m2\\*_diarization.json
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
VP_DIR = ROOT / "voiceprints"
PEOPLE = ROOT / "config" / "people.json"

# Decision rule (see ARCHITECTURE.md section 3). Calibrated on the first recordings in
# m2/CALIBRATION.md; revisit as more hand-checked recordings come in.
THRESHOLD = 0.65   # minimum cosine similarity to accept a name (0.55 let two PSOE-rally voices through as Colau, sim 0.58-0.59)
MARGIN = 0.10      # best match must beat the second best by this much
MIN_TALK_S = 20    # speakers with less speech than this are too short to judge


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cos(a, b):
    import numpy as np
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def people():
    return load(PEOPLE) if PEOPLE.exists() else {}


def voiceprints():
    """person -> list of enrolment embeddings. Each enrolment is one setting (TV studio, radio,
    phone line, rally PA); a speaker is compared with every one and the best counts, because
    the same voice through a phone line and a studio microphone can be far apart (Colau: 0.28)."""
    return {vp["person"]: [e["embedding"] for e in vp["enrolments"]]
            for vp in (load(f) for f in sorted(VP_DIR.glob("*.json")))}


def sim(emb, prints):
    return max(cos(emb, e) for e in prints)


def enrol(diar_path, label, person):
    d = load(diar_path)
    spk = d["speakers"][label]
    VP_DIR.mkdir(exist_ok=True)
    f = VP_DIR / f"{person}.json"
    vp = load(f) if f.exists() else {"person": person, "enrolments": []}
    vp["enrolments"] = [e for e in vp["enrolments"]
                        if not (e["audio"] == d["audio"] and e["label"] == label)]
    vp["enrolments"].append({
        "audio": d["audio"], "label": label, "talk_s": spk["talk_s"],
        "pipeline": d["pipeline"], "added": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "embedding": spk["embedding"],
    })
    f.write_text(json.dumps(vp, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{person}: {len(vp['enrolments'])} enrolment(s) -> {f.relative_to(ROOT)}")


def identify(diar_path, out_path):
    d, vps, ppl = load(diar_path), voiceprints(), people()
    # score every (speaker, person) pair
    scores = {lab: sorted(((sim(s["embedding"], v), p) for p, v in vps.items()), reverse=True)
              for lab, s in d["speakers"].items()}
    result, taken = {}, set()
    # strongest matches first, and one person can only be one speaker per recording
    order = sorted(scores, key=lambda lab: -(scores[lab][0][0] if scores[lab] else 0))
    unknown_n = 0
    for lab in order:
        talk = d["speakers"][lab]["talk_s"]
        cands = [(s, p) for s, p in scores[lab] if p not in taken]
        best = cands[0] if cands else (0.0, None)
        second = cands[1][0] if len(cands) > 1 else 0.0
        if talk < MIN_TALK_S:
            decision, reason = "too_short", f"only {talk:.0f}s of speech"
        elif best[0] >= THRESHOLD and best[0] - second >= MARGIN:
            decision, reason = "match", f"sim {best[0]:.2f}, next {second:.2f}"
        elif best[0] >= THRESHOLD:
            decision, reason = "ambiguous", f"sim {best[0]:.2f} but next is {second:.2f}"
        else:
            decision, reason = "unknown", f"best sim {best[0]:.2f} < {THRESHOLD}"
        if decision == "match":
            taken.add(best[1])
            info = ppl.get(best[1], {})
            name = info.get("name", best[1])
            if info.get("role"):
                name = f"{name} ({info['role']})"
        else:
            unknown_n += 1
            name = f"Hablante sin identificar {unknown_n}"
        result[lab] = {
            "person": best[1] if decision == "match" else None,
            "name": name, "decision": decision, "reason": reason, "talk_s": talk,
            "scores": {p: round(s, 3) for s, p in scores[lab]},
        }
    out = {"audio": d["audio"], "threshold": THRESHOLD, "margin": MARGIN, "speakers": result}
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for lab in sorted(result):
        r = result[lab]
        print(f"{lab}: {r['name']:<40} {r['decision']:<10} {r['reason']}  ({r['talk_s']:.0f}s)")


def matrix(paths):
    vps = voiceprints()
    names = list(vps)
    print("speaker".ljust(52) + "".join(n[:10].rjust(11) for n in names))
    for p in paths:
        d = load(p)
        for lab, s in d["speakers"].items():
            row = f"{Path(p).stem[:30]}:{lab} ({s['talk_s']:.0f}s)".ljust(52)
            print(row + "".join(f"{sim(s['embedding'], vps[n]):11.2f}" for n in names))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "enrol" and len(sys.argv) == 5:
        enrol(*sys.argv[2:5])
    elif cmd == "identify" and len(sys.argv) == 4:
        identify(*sys.argv[2:4])
    elif cmd == "matrix":
        matrix(sys.argv[2:])
    else:
        sys.exit(__doc__)
