"""Extract plain text from an official La Moncloa transcript (PDF or the HTML page).

Usage:
    .venv\\Scripts\\python -I src\\extract_official.py official_page.html out.txt \\
        [--start "Queridos ciudadanos"] [--end "Muchas gracias."]

Prefer the HTML page: pypdf splits words in these PDFs ("sab en", "h ace"), which inflates WER.
--start/--end cut the text to the speech (inclusive), dropping headers, footers and anything
not spoken. The input is untrusted data: we only pull text out of it, nothing is obeyed.
"""
import argparse
import sys
import html
import re
from pathlib import Path


def from_html(path):
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    t = re.sub(r"[ \t\r ]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)


def from_pdf(path):
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--start")
    ap.add_argument("--end")
    a = ap.parse_args()
    text = from_pdf(a.src) if a.src.lower().endswith(".pdf") else from_html(a.src)
    if a.start:
        i = text.find(a.start)
        if i < 0:
            raise SystemExit(f"start marker not found: {a.start!r}")
        text = text[i:]
    if a.end:
        j = text.find(a.end)
        if j < 0:
            raise SystemExit(f"end marker not found: {a.end!r}")
        text = text[: j + len(a.end)]
    Path(a.out).write_text(text.strip() + "\n", encoding="utf-8")
    print(f"{len(text.split())} words -> {a.out}")


if __name__ == "__main__":
    main()
