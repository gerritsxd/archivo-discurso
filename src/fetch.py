"""Download the audio of every appearance in an inventory CSV (default m0/inventory.csv).

For each row with an audio/video URL: data/raw/<item_id>/source.<ext>, audio.wav (16 kHz mono),
meta.json (inventory fields + fetch info + sha256). Already-fetched items are skipped, so it can
be re-run any time (also after an interruption).

Usage:
    .venv\\Scripts\\python src\\fetch.py [--inventory m0\\inventory.csv] [--only youtube|direct|rtve] [--limit N]

YouTube only works from a residential IP (the VPS gets a bot check), so on the VPS run with
--only direct / rtve and let the PC fetch YouTube.
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# Rows we deliberately don't fetch (matched against outlet + notes, case-insensitive).
SKIP = [
    "duplicate", "dedup",         # flagged by the M0 agents: cut of another item we already have
    "la revuelta) youtube",       # clips of the full La Revuelta episode, which we take from RTVE Play
]
CATALAN_OUTLETS = ["rac1", "catalunya ràdio", "catalunya radio", "tv3", "3cat"]


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return "-".join("".join(c if c.isalnum() else " " for c in s).split())


def item_id(row):
    h = hashlib.sha1(row["url"].encode()).hexdigest()[:6]
    surname = slug(row["person"]).split("-")[-1] if row["person"] else "x"
    return f"{row['date']}-{surname}-{h}"


def kind_of(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "rtve.es/play" in url:
        return "rtve"
    if "3cat.cat/3cat/" in url or "telemadrid.es/" in url:
        return "rtve"  # same path: yt-dlp, best audio
    if "lamoncloa.gob.es/multimedia/videos/" in url:
        return "moncloa"
    if "static.congreso.es/" in url and url.lower().endswith(".mp4"):
        return "direct_video"
    if url.split("?")[0].lower().endswith((".mp3", ".m4a", ".aac", ".ogg")) or "/play.mp3" in url:
        return "direct"
    return None


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, kind, d):
    if kind in ("direct", "direct_video"):
        out = d / ("source.mp4" if kind == "direct_video" else "source.mp3")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (archivo-discurso)"})
        with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
        return out
    # youtube / rtve: audio only, via yt-dlp (with retries; plain ffmpeg on streams loses chunks)
    # be gentle: YouTube answers a burst of downloads with "confirm you're not a bot" for hours
    cmd = [sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "--no-playlist",
           "--sleep-requests", "1.5", "--sleep-interval", "20", "--max-sleep-interval", "45",
           # Moncloa HLS has no audio-only rendition: the smallest video carries the same audio
           "-f", "worst" if kind == "moncloa" else "bestaudio/best",
           "--retries", "10", "--fragment-retries", "10",
           "-o", str(d / "source.%(ext)s"), url]
    subprocess.run(cmd, check=True, timeout=3600)
    found = [p for p in d.glob("source.*") if p.suffix not in (".part", ".ytdl")]
    if not found:
        raise RuntimeError("yt-dlp produced no file")
    return found[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", default=str(ROOT / "m0" / "inventory.csv"))
    ap.add_argument("--only", choices=["youtube", "direct", "rtve", "moncloa", "direct_video"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-wav", action="store_true",
                    help="archive the original file only (VPS: no ffmpeg, the PC makes the wav)")
    args = ap.parse_args()
    done_file = "meta.json" if args.no_wav else "audio.wav"

    rows = list(csv.DictReader(open(args.inventory, encoding="utf-8")))
    todo, skipped = [], 0
    for r in rows:
        kind = kind_of(r.get("url", ""))
        text = (r.get("outlet", "") + " " + r.get("notes", "")).lower()
        if not kind or any(s in text for s in SKIP) or "/shorts/" in r.get("url", ""):
            skipped += 1
            continue
        if args.only and kind != args.only:
            continue
        todo.append((r, kind))
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} to check, {skipped} rows without audio or skipped on purpose")

    ok = fail = have = 0
    for r, kind in todo:
        iid = item_id(r)
        d = RAW / iid
        if (d / done_file).exists() and (d / "meta.json").exists():
            have += 1
            continue
        d.mkdir(parents=True, exist_ok=True)
        try:
            src = download(r["url"], kind, d)
            if not args.no_wav:
                subprocess.run([ffmpeg(), "-loglevel", "error", "-y", "-i", str(src),
                                "-ac", "1", "-ar", "16000", str(d / "audio.wav")], check=True)
            lang = "ca" if any(o in r.get("outlet", "").lower() for o in CATALAN_OUTLETS) else "es"
            meta = dict(r) | {
                "id": iid, "fetch_kind": kind, "language": lang, "source_file": src.name,
                "sha256": sha256(src), "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            ok += 1
            print(f"ok   {iid}  {r['outlet'][:40]}")
        except Exception as e:  # keep going; the error is logged and the item retried next run
            fail += 1
            (d / "fetch_error.txt").write_text(f"{datetime.now().isoformat()} {e}\n", encoding="utf-8")
            print(f"FAIL {iid}  {r['url'][:70]}  {str(e)[:120]}")
    print(f"done: {ok} new, {have} already had, {fail} failed")


if __name__ == "__main__":
    main()
