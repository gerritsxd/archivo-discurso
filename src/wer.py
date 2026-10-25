"""WER of our transcript vs an official transcript.

Usage:
    .venv\\Scripts\\python -I src\\wer.py ours.json official_speech.txt [--examples 15] [--out report.json]

`ours.json` is the output of transcribe.py. `official_speech.txt` is the official text, already
cut to the part we want to compare (headers/footers removed, Q&A removed if needed).

Normalisation (both sides): lowercase, strip accents? NO (accents carry meaning in Spanish),
remove punctuation and quotes, collapse whitespace. Numbers are left as-is (so "29" vs
"veintinueve" counts as an error; we report how many errors are number-format only).
"""
import argparse
import sys
import json
import re
import unicodedata
from pathlib import Path

import jiwer

PUNCT = re.compile(r"[^\w\s]|_", re.UNICODE)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = text.replace("­", "")  # soft hyphen
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # words hyphenated across lines
    text = re.sub(r"(?<=\d)[.,](?=\d)", "", text)  # 1.000 / 2,5 -> keep digits together
    text = PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("ours_json")
    ap.add_argument("official_txt")
    ap.add_argument("--examples", type=int, default=20)
    ap.add_argument("--out")
    args = ap.parse_args()

    ours = json.loads(Path(args.ours_json).read_text(encoding="utf-8"))["text"]
    ref = Path(args.official_txt).read_text(encoding="utf-8")
    r, h = normalize(ref), normalize(ours)

    out = jiwer.process_words(r, h)
    ref_words, hyp_words = out.references[0], out.hypotheses[0]
    diffs = []
    for chunk in out.alignments[0]:
        if chunk.type == "equal":
            continue
        rw = ref_words[chunk.ref_start_idx:chunk.ref_end_idx]
        hw = hyp_words[chunk.hyp_start_idx:chunk.hyp_end_idx]
        ctx_l = " ".join(ref_words[max(0, chunk.ref_start_idx - 5):chunk.ref_start_idx])
        ctx_r = " ".join(ref_words[chunk.ref_end_idx:chunk.ref_end_idx + 5])
        diffs.append({
            "type": chunk.type,
            "official": " ".join(rw),
            "ours": " ".join(hw),
            "context": f"{ctx_l} [{' '.join(rw)}] {ctx_r}",
            "number_related": any(re.search(r"\d", w) for w in rw + hw),
        })

    report = {
        "ref_words": len(ref_words),
        "hyp_words": len(hyp_words),
        "wer": round(out.wer, 4),
        "substitutions": out.substitutions,
        "deletions": out.deletions,
        "insertions": out.insertions,
        "diff_chunks": len(diffs),
        "number_related_chunks": sum(d["number_related"] for d in diffs),
        "diffs": diffs,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "diffs"}, indent=1))
    for d in diffs[: args.examples]:
        print(f"- {d['type']:<10} official='{d['official']}'  ours='{d['ours']}'  | {d['context']}")


if __name__ == "__main__":
    main()
