"""Find new appearances: read the YouTube channel feeds and radio podcast feeds, keep items whose
title names a candidate, and append them to data/queue.csv (same columns as m0/inventory.csv).

Runs on the VPS on a timer (YouTube feeds are readable from a data-centre IP; only the video
download is blocked). Standard library only, plus PyYAML for the source lists.

Usage:
    python3 src/discover.py [--since 2026-10-05]

Feed text is external data: it is only matched against names and copied into CSV cells.
"""
import argparse
import csv
import email.utils
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "data" / "queue.csv"
INVENTORY = ROOT / "m0" / "inventory.csv"
FIELDS = ["date", "person", "kind", "outlet", "title", "url", "tier", "duration_min",
          "has_text", "notes", "file"]
NS = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/",
      "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (archivo-discurso)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def matcher():
    people = json.loads((ROOT / "config" / "people.json").read_text(encoding="utf-8"))
    pats = [(p["name"], re.compile(r"\b(" + "|".join(map(re.escape, p["match"])) + r")\b", re.I))
            for p in people.values() if p.get("kind") == "candidate"]

    def who(text):
        # "Abascal: Sánchez es…" is an Abascal item, so order by where the name first appears
        hits = [(m.start(), name) for name, pat in pats if (m := pat.search(text or ""))]
        return [name for _, name in sorted(hits)]
    return who


# Radio titles mention candidates all day ("Tertulia: Sánchez convoca…"). Only titles shaped like
# the candidate speaking count: "Ada Colau: …", "Feijóo, sobre Milei: …", "Federico entrevista a …".
def speaks(title):
    t = title or ""
    lead = re.match(r"^\W*((?:[\wÀ-ſ]+\s){0,3}[\wÀ-ſ]+)\s*[:,(]", t)
    if lead and matcher_cache(lead.group(1)):
        return True
    return bool(re.search(r"entrevista", t, re.I)) and bool(matcher_cache(t))


def minutes(dur):
    """itunes:duration as seconds or [hh:]mm:ss -> minutes"""
    if not dur:
        return ""
    try:
        parts = [float(x) for x in dur.strip().split(":")]
    except ValueError:
        return ""
    s = parts[0] if len(parts) == 1 else sum(v * 60 ** i for i, v in enumerate(reversed(parts)))
    return round(s / 60, 1)


def youtube_items(ch):
    root = ET.fromstring(fetch(ch["rss"]))
    for e in root.findall("atom:entry", NS):
        yield {
            "date": e.findtext("atom:published", "", NS)[:10],
            "title": e.findtext("atom:title", "", NS),
            "url": e.find("atom:link", NS).get("href"),
            "outlet": f"{ch['name']} YouTube",
            "duration_min": "",
        }


def radio_items(feed):
    root = ET.fromstring(fetch(feed["rss_url"]))
    for it in root.iter("item"):
        enc = it.find("enclosure")
        if enc is None or not enc.get("url"):
            continue
        try:
            date = email.utils.parsedate_to_datetime(it.findtext("pubDate", "")).date().isoformat()
        except (TypeError, ValueError):
            continue
        yield {
            "date": date,
            "title": it.findtext("title", ""),
            "url": enc.get("url"),
            "outlet": f"{feed['station']} - {feed['programme']}",
            "duration_min": minutes(it.findtext("itunes:duration", "", NS)),
        }


matcher_cache = None


def main():
    global matcher_cache
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-10-05")
    args = ap.parse_args()
    who = matcher()
    matcher_cache = who

    seen = set()
    for f in (INVENTORY, QUEUE):
        if f.exists():
            seen |= {r["url"] for r in csv.DictReader(open(f, encoding="utf-8"))}

    ch_yaml = yaml.safe_load((ROOT / "m0" / "channels.yaml").read_text(encoding="utf-8"))
    feeds = yaml.safe_load((ROOT / "m0" / "feeds.yaml").read_text(encoding="utf-8"))
    regional = ROOT / "m0" / "feeds_regional.yaml"
    if regional.exists():
        feeds += yaml.safe_load(regional.read_text(encoding="utf-8")) or []
    # party channels: any title naming a candidate; TV channels and radio: only titles shaped
    # like the candidate speaking, because they post about everyone all day
    sources = [("youtube", c) for c in ch_yaml["channels"] if c.get("rss")] + \
              [("broadcast", c) for c in ch_yaml.get("broadcasters", []) if c.get("rss")] + \
              [("radio", f) for f in feeds if f.get("rss_url")]

    new, errors = [], 0
    for kind, src in sources:
        try:
            items = list(radio_items(src) if kind == "radio" else youtube_items(src))
        except Exception as e:  # one broken feed must not stop the others
            errors += 1
            print(f"feed error {src.get('name') or src.get('programme')}: {str(e)[:100]}", file=sys.stderr)
            continue
        for it in items:
            if it["date"] < args.since or it["url"] in seen or "/shorts/" in it["url"]:
                continue
            names = who(it["title"])
            if not names or (kind in ("radio", "broadcast") and not speaks(it["title"])):
                continue
            seen.add(it["url"])
            new.append({
                "date": it["date"], "person": names[0], "kind": "other", "outlet": it["outlet"],
                "title": it["title"], "url": it["url"], "tier": 2, "duration_min": it["duration_min"],
                "has_text": "no", "file": "discover",
                "notes": ("also names: " + ", ".join(names[1:]) + "; " if len(names) > 1 else "")
                         + f"found {datetime.now(timezone.utc).date()} by discover.py",
            })

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    first = not QUEUE.exists()
    with open(QUEUE, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if first:
            w.writeheader()
        w.writerows(new)
    print(f"{len(sources)} feeds read ({errors} errors), {len(new)} new appearance(s) queued")
    for r in new:
        print(f"  {r['date']}  {r['person']:<22} {r['outlet'][:30]:<30} {r['title'][:70]}")


if __name__ == "__main__":
    main()
