"""Backfill: list every upload and live stream since a date on the YouTube channels in
m0/channels.yaml (the RSS feeds that discover.py reads only show the last ~15 items), keep the
ones naming a candidate, and append them to data/queue_backfill.csv.

Metadata only (yt-dlp --flat-playlist), nothing is downloaded. Must run on the PC: YouTube
blocks the VPS. Then `src/fetch.py --inventory data/queue_backfill.csv` + `src/process.py`.

Usage:
    .venv\\Scripts\\python src\\backfill_channels.py [--since 2026-10-05] [--max 300]
"""
import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import discover  # noqa: E402  (shares the name matching and the "candidate speaking" rule)

OUT = ROOT / "data" / "queue_backfill.csv"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def list_tab(channel_id, tab, max_items):
    url = f"https://www.youtube.com/channel/{channel_id}/{tab}"
    cmd = [sys.executable, "-m", "yt_dlp", "--flat-playlist", "--no-warnings", "-q",
           # Spanish titles (YouTube auto-translates them to the viewer's language otherwise)
           "--extractor-args", "youtubetab:approximate_date;youtube:lang=es",
           "--playlist-end", str(max_items),
           "--print", "%(upload_date|)s\t%(id)s\t%(duration|)s\t%(title)s", url]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")  # Windows console is cp1252
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600, env=env)
    for line in r.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            yield parts


def exact_meta(url):
    """upload date + duration from the video page (flat listings often lack the date)"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--skip-download", "--no-warnings", "-q",
                        "--extractor-args", "youtube:lang=es",
                        "--print", "%(upload_date|)s	%(duration|)s", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, env=env)
    parts = (r.stdout.strip().splitlines() or [""])[-1].split("	")
    return (parts + ["", ""])[:2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-10-05")
    ap.add_argument("--max", type=int, default=60, help="items per channel tab to look at")
    args = ap.parse_args()
    since = args.since.replace("-", "")

    who = discover.matcher()
    discover.matcher_cache = who
    seen = set()
    for f in (ROOT / "m0" / "inventory.csv", ROOT / "data" / "queue.csv", OUT):
        if f.exists():
            seen |= {r["url"] for r in csv.DictReader(open(f, encoding="utf-8"))}

    ch = yaml.safe_load((ROOT / "m0" / "channels.yaml").read_text(encoding="utf-8"))
    sources = [("party", c) for c in ch["channels"]] + [("broadcast", c) for c in ch.get("broadcasters", [])]
    new = []
    for kind, c in sources:
        n_tab = 0
        for tab in ("videos", "streams"):
            for date, vid, dur, title in list_tab(c["channel_id"], tab, args.max):
                n_tab += 1
                if date and date < since:
                    continue
                url = f"https://www.youtube.com/watch?v={vid}"
                if url in seen:
                    continue
                names = who(title)
                if not names or (kind == "broadcast" and not discover.speaks(title)):
                    continue
                if not date or not dur:
                    d2, dur2 = exact_meta(url)
                    date, dur = d2 or date, dur2 or dur
                    if not date or date < since:
                        continue
                try:
                    minutes = round(float(dur) / 60, 1) if dur else ""
                except ValueError:
                    minutes = ""
                if minutes != "" and minutes < 1.5:  # shorts and spots: no real speech to quote
                    continue
                seen.add(url)
                d = f"{date[:4]}-{date[4:6]}-{date[6:]}" if date else ""
                new.append({"date": d, "person": names[0], "kind": "other", "outlet": f"{c['name']} YouTube",
                            "title": title, "url": url, "tier": 2, "duration_min": minutes, "has_text": "no",
                            "notes": f"backfill {datetime.now(timezone.utc).date()}" +
                                     "",
                            "file": "backfill"})
        print(f"{c['name'][:30]:<30} {n_tab:4d} listed")

    first = not OUT.exists()
    with open(OUT, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=discover.FIELDS)
        if first:
            w.writeheader()
        w.writerows(new)
    hours = sum(r["duration_min"] or 0 for r in new) / 60
    print(f"{len(new)} new appearance(s), ~{hours:.0f} h -> {OUT.relative_to(ROOT)}")
    for r in new:
        print(f"  {r['date']}  {r['person']:<22} {str(r['duration_min']):>6}  {r['outlet'][:24]:<24} {r['title'][:60]}")


if __name__ == "__main__":
    main()
