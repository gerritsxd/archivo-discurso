"""Remove known Whisper artefacts from a word list, before turns are assembled.

Found in the attribution review (eval/ATTRIBUTION.md):
- the hotword list leaking into the text ("Yolanda Díaz, Alberto Núñez Feijóo, Santiago Abascal,
  Federico Jiménez…"): a run of 5+ consecutive words that are all name tokens from config/names.txt;
- stock YouTube-subtitle phrases Whisper invents on music or silence ("¡Suscríbete al canal!");
- repetition loops ("Junta de Junts per Catalunya, Junta de Junts per Catalunya, …"): an n-gram
  repeated 3+ times in a row is kept once.
Works on the word dicts (start, end, word) so timestamps stay aligned.
"""
import re
import unicodedata
from pathlib import Path

NAMES = Path(__file__).resolve().parent.parent / "config" / "names.txt"
PHRASES = ["suscribete al canal", "cc por antarctica films argentina", "subtitulos realizados por la comunidad de amara org",
           "gracias por ver el video", "subtitulado por la comunidad de amara org", "suscribete y dale like"]
MIN_NAME_RUN = 5


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))


def name_tokens():
    toks = set()
    for line in NAMES.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            toks.update(norm(t) for t in line.split())
    toks.discard("")
    return toks


def clean(words):
    keep = [True] * len(words)
    n = [norm(w["word"]) for w in words]
    # 1. hotword leaks
    toks, i = name_tokens(), 0
    while i < len(n):
        j = i
        while j < len(n) and n[j] in toks:
            j += 1
        if j - i >= MIN_NAME_RUN:
            keep[i:j] = [False] * (j - i)
        i = max(j, i + 1)
    # 2. stock phrases
    for ph in PHRASES:
        p = ph.split()
        for i in range(len(n) - len(p) + 1):
            if n[i:i + len(p)] == p:
                keep[i:i + len(p)] = [False] * len(p)
    # 3. repetition loops: an n-gram (n = 2..8) repeated 3+ times in a row is kept once
    for size in range(2, 9):
        i = 0
        while i + 3 * size <= len(n):
            g = n[i:i + size]
            reps = 1
            while n[i + reps * size: i + (reps + 1) * size] == g:
                reps += 1
            if reps >= 3 and any(g):
                keep[i + size: i + reps * size] = [False] * ((reps - 1) * size)
                i += reps * size
            else:
                i += 1
    return [w for w, k in zip(words, keep) if k]
