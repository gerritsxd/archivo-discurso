"""Find appearances that are the same event from two sources (the party's stream and a newspaper's)
and keep only one, so nothing is counted twice.

Two processed items are duplicates when the same candidate is the main speaker of both (most identified
speech), they are within 2 days, and the shorter one's words are almost all in the other (>= 80 % of its
8-word shingles). A clip of someone else inside an interview (Sánchez's statement played on Antena 3)
never makes the interview a duplicate. Kept: the longer recording; if they are about as long, the one
whose link can open at the exact second (YouTube, mp3), then the official source. The other one's JSON moves to data/duplicates/ and its id is
appended to config/exclude.txt, so process.py never rebuilds it.

    python src/dedup.py [--dry-run]
"""
import argparse
import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS, DUPS = ROOT / "data" / "items", ROOT / "data" / "duplicates"
EXCLUDE = ROOT / "config" / "exclude.txt"
OFFICIAL = ("PSOE", "La Moncloa", "Partido Popular", "VOX", "Podemos", "Frente Amplio", "Sumar", "Irene Montero",
            "Ada Colau", "Congreso")


def shingles(text, n=8):
    w = re.findall(r"\w+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    items = []
    for p in sorted(ITEMS.glob("*.json")):
        it = json.loads(p.read_text(encoding="utf-8"))
        by, talk = {}, {}
        for t in it["turns"]:
            if t.get("person"):
                by.setdefault(t["person"], []).append(t["text"])
                talk[t["person"]] = talk.get(t["person"], 0) + t["end"] - t["start"]
        if not talk:
            continue
        main_p = max(talk, key=talk.get)   # only the main speaker counts
        sh = shingles(" ".join(by[main_p]))
        if len(sh) >= 50:   # too little speech to compare reliably
            items.append((it, main_p, sh, p))
    gone = set()
    for i, (a, pa, sa, fa) in enumerate(items):
        for b, pb, sb, fb in items[i + 1:]:
            if pa != pb or a["id"] == b["id"] or a["id"] in gone or b["id"] in gone:
                continue
            if abs((date.fromisoformat(a["date"]) - date.fromisoformat(b["date"])).days) > 2:
                continue
            sim = len(sa & sb) / min(len(sa), len(sb))
            if sim < 0.8:
                continue
            da, db = a.get("duration_s") or 0, b.get("duration_s") or 0
            if abs(da - db) > 0.1 * max(da, db):
                keep, drop = (a, b) if da > db else (b, a)
            else:
                def rank(it):
                    return (bool(re.search(r"youtube\.com|youtu\.be|\.mp3", it.get("url") or "")),
                            any(it["outlet"].startswith(o) for o in OFFICIAL))
                keep, drop = (a, b) if rank(a) >= rank(b) else (b, a)
            print(f"duplicate ({sim:.2f}): keep {keep['id']} [{keep['outlet']}], drop {drop['id']} [{drop['outlet']}]")
            gone.add(drop["id"])
            if not args.dry_run:
                DUPS.mkdir(parents=True, exist_ok=True)
                shutil.move(str(ITEMS / f"{drop['id']}.json"), DUPS / f"{drop['id']}.json")
                with open(EXCLUDE, "a", encoding="utf-8") as f:
                    f.write(f"{drop['id']}  # duplicate of {keep['id']} (dedup.py, similarity {sim:.2f})\n")
    print(f"{len(gone)} duplicate(s){' (dry run)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
