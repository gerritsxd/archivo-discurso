"""Put speaker labels on a transcript: each word gets the diarization speaker it overlaps most.

Usage:
    .venv\\Scripts\\python -I src\\merge_speakers.py transcript.json diarization.json out.md [identity.json]

With identity.json (from voiceprints.py identify) the anonymous labels become names.
Writes a readable markdown transcript (one paragraph per speaker turn, with timestamps).
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def speaker_for(start, end, turns):
    best, best_ov = None, 0.0
    for t in turns:
        ov = min(end, t["end"]) - max(start, t["start"])
        if ov > best_ov:
            best, best_ov = t["speaker"], ov
    if best is None:  # word falls in a gap: take the nearest turn
        mid = (start + end) / 2
        best = min(turns, key=lambda t: min(abs(mid - t["start"]), abs(mid - t["end"])))["speaker"]
    return best


END = (".", "?", "!", "…")


def smooth(blocks, max_words=3):
    """Fix words that land on the wrong side of a speaker change.

    Diarization and Whisper timestamps disagree by a few hundred ms at turn edges, so the
    last words of a sentence often start the next speaker's block ("duda. Si para ganar…")
    or a lone word sits between two blocks ("hacerle" | "caso a lo que…"). Rules:
    1. If the previous block doesn't end a sentence, move the words up to this block's first
       sentence end (at most max_words) back to the previous block.
    2. A short block that doesn't end a sentence, followed by a block starting in lowercase,
       belongs to that next block.
    """
    for i in range(1, len(blocks)):
        prev, cur = blocks[i - 1], blocks[i]
        if not prev[2] or prev[2][-1].strip().endswith(END):
            continue
        # 0. "…¿Qué escenario prefiere usted? El Partido Socialista ha" | "convocado las…":
        #    a sentence start stranded at the end of the previous block moves forward
        if cur[2] and cur[2][0].strip()[:1].islower():
            ends = [k for k, w in enumerate(prev[2]) if w.strip().endswith(END)]
            k = ends[-1] + 1 if ends else None
            if k is not None and len(prev[2]) - k <= max_words + 1:
                cur[2][:0], cur[3][:0] = prev[2][k:], prev[3][k:]
                cur[1] = prev[3][k]
                del prev[2][k:], prev[3][k:]
                continue
        for k, w in enumerate(cur[2][:max_words]):
            if w.strip().endswith(END):
                if k + 1 < len(cur[2]):
                    prev[2].extend(cur[2][:k + 1])
                    cur[1] = cur[3][k + 1]
                    del cur[2][:k + 1], cur[3][:k + 1]
                break
    for i in range(len(blocks) - 1):
        cur, nxt = blocks[i], blocks[i + 1]
        if (0 < len(cur[2]) <= 2 and not cur[2][-1].strip().endswith(END)
                and nxt[2] and nxt[2][0].strip()[:1].islower()):
            nxt[2][:0], nxt[3][:0] = cur[2], cur[3]
            nxt[1] = cur[1]
            cur[2], cur[3] = [], []
    # drop emptied blocks and join neighbours that now have the same speaker
    out = []
    for b in blocks:
        if not b[2]:
            continue
        if out and out[-1][0] == b[0]:
            out[-1][2].extend(b[2]); out[-1][3].extend(b[3])
        else:
            out.append(b)
    return out


def fmt(s):
    return f"{int(s // 60):02d}:{s % 60:04.1f}"


def main():
    tr = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    di = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    turns = di["turns"]
    names = {}
    if len(sys.argv) > 4:
        ident = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
        names = {lab: r["name"] for lab, r in ident["speakers"].items()}
    words = [w for s in tr["segments"] for w in s.get("words", [])]

    blocks = []  # [speaker, start, [words], [word starts]]
    for w in words:
        spk = speaker_for(w["start"], w["end"], turns)
        if blocks and blocks[-1][0] == spk:
            blocks[-1][2].append(w["word"])
            blocks[-1][3].append(w["start"])
        else:
            blocks.append([spk, w["start"], [w["word"]], [w["start"]]])
    blocks = smooth(blocks)

    lines = [f"# {Path(sys.argv[1]).stem}", ""]
    for spk, start, ws, _ in blocks:
        lines.append(f"**[{fmt(start)}] {names.get(spk, spk)}:** {''.join(ws).strip()}")
        lines.append("")
    Path(sys.argv[3]).write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(blocks)} turns, {len(words)} words -> {sys.argv[3]}")


if __name__ == "__main__":
    main()
