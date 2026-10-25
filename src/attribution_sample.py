"""Draw a fixed random sample of named candidate turns for a human attribution check.

Stratified: N turns per candidate (seeded, so the sample is reproducible), from data/items.
Writes eval/attribution_sample.jsonl with each turn's text, the turn before it (usually the
question), the appearance and a link to the source at that second. The reviewer fills in
eval/attribution_review.jsonl (one {"key", "verdict", "evidence"} per line); `--score` prints
the accuracy from that file.

    python src/attribution_sample.py [--per 15] [--seed 29]
    python src/attribution_sample.py --score

Verdicts: correcto (the content shows it is that candidate), probable (consistent, nothing
against), mixto (the turn also contains someone else's words: a speaker-boundary error),
incorrecto (it is someone else), indeterminable.
"""
import argparse
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS, EVAL = ROOT / "data" / "items", ROOT / "eval"


def sample(per, seed):
    rng = random.Random(seed)
    by_person = {}
    for p in sorted(ITEMS.glob("*.json")):
        it = json.loads(p.read_text(encoding="utf-8"))
        turns = it["turns"]
        for i, t in enumerate(turns):
            if t.get("person") and len(t["text"].split()) >= 15 and \
                    it["speakers"].get(t["label"], {}).get("decision") == "match":
                prev = next((turns[j] for j in range(i - 1, -1, -1) if turns[j]["label"] != t["label"]), None)
                by_person.setdefault(t["person"], []).append({
                    "key": f"{it['id']}#{i}", "person": t["person"], "item": it["id"], "date": it["date"],
                    "kind": it["kind"], "outlet": it["outlet"], "title": it["title"], "url": it["url"],
                    "start": t["start"], "seconds": round(t["end"] - t["start"]),
                    "sim": it["speakers"][t["label"]]["reason"],
                    "before": (prev["name"] + ": " + prev["text"][-400:]) if prev else "",
                    "text": t["text"] if len(t["text"]) <= 1500 else t["text"][:1000] + " […] " + t["text"][-500:],
                })
    out = []
    for person in sorted(by_person):
        pool = by_person[person]
        out += rng.sample(pool, min(per, len(pool)))
    return out


def score():
    rev = [json.loads(l) for l in (EVAL / "attribution_review.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    smp = {s["key"]: s for s in (json.loads(l) for l in (EVAL / "attribution_sample.jsonl").read_text(encoding="utf-8").splitlines())}
    c = Counter(r["verdict"] for r in rev)
    per = {}
    for r in rev:
        per.setdefault(smp[r["key"]]["person"], Counter())[r["verdict"]] += 1
    judged = sum(c[v] for v in ("correcto", "probable", "mixto", "incorrecto"))
    print(f"{len(rev)} turns reviewed: {dict(c)}")
    if judged:
        print(f"wrong person: {c['incorrecto']}/{judged} = {100 * c['incorrecto'] / judged:.1f}%")
        print(f"right person, clean turn (correcto+probable): {100 * (c['correcto'] + c['probable']) / judged:.1f}%")
        print(f"right person but turn mixes in another voice (mixto): {100 * c['mixto'] / judged:.1f}%")
    for p, pc in sorted(per.items()):
        print(" ", p, dict(pc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=15)
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.score:
        return score()
    EVAL.mkdir(exist_ok=True)
    s = sample(a.per, a.seed)
    (EVAL / "attribution_sample.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in s) + "\n",
                                                   encoding="utf-8")
    print(f"{len(s)} turns -> eval/attribution_sample.jsonl", Counter(x["person"] for x in s))


if __name__ == "__main__":
    main()
