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
# TV channels, newspapers and agencies add a second shape: the event, with the candidate as its subject
# ("Mitin de Feijóo en Vigo", "Entrevista a Pedro Sánchez", "Abascal participa en un acto",
# "Irene Montero y Gabriel Rufián celebran un acto"). Not "Ábalos responde a Sánchez y habla de…".
EVENT_OF = re.compile(r"\b(mitin|acto|rueda de prensa|declaraci[oó]n(?:es)?|comparecencia|intervenci[oó]n|discurso|"
                      r"entrevista)\s+(?:de|a|con)\s+((?:[\wÀ-ſ.]+\s?){1,4})", re.I)
SUBJECT_DOES = re.compile(r"(?:^|[|:]\s*)((?:[\wÀ-ſ.]+\s){1,6}?)(?:participa|interviene|clausura|comparece|"
                          r"celebran? un acto|da un mitin|ofrece un mitin)", re.I)


def speaks(title, broadcast=False):
    t = re.sub(r"[🔴🟢🔵⚫]", "", title or "").strip()
    lead = re.match(r"^\W*((?:[\wÀ-ſ]+\s){0,3}[\wÀ-ſ]+)\s*[:,(]", t)
    if lead and matcher_cache(lead.group(1)):
        return True
    if re.search(r"entrevista", t, re.I) and matcher_cache(t):
        return True
    if broadcast:
        subjects = [m.group(2) for m in EVENT_OF.finditer(t)] + [m.group(1) for m in SUBJECT_DOES.finditer(t)]
        return any(matcher_cache(x) for x in subjects)
    return False


# The same rally is often streamed by the party and by two newspapers. Before queueing, skip a video
# of the same person on the same day whose title shares a place or event word with one we already have.
GENERIC = set("""directo vivo mitin acto actos rueda prensa declaraciones entrevista discurso participa interviene
clausura precampaña campaña elecciones partido popular psoe vox podemos frente amplio sumar gran público
publico presidente gobierno candidato candidata junto sobre tras para como desde hasta entre youtube""".split())


def place_words(title, person):
    own = {w.lower() for w in person.split()}
    words = re.findall(r"[A-ZÁÉÍÓÚÑ][\wáéíóúñü]{3,}", title or "")
    return {w.lower() for w in words if w.lower() not in GENERIC and w.lower() not in own}


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

    seen, events = set(), {}
    for f in (INVENTORY, QUEUE):
        if f.exists():
            for r in csv.DictReader(open(f, encoding="utf-8")):
                seen.add(r["url"])
                events.setdefault((r["date"], r["person"]), []).append(place_words(r["title"], r["person"]))

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

    health_f = ROOT / "data" / "source_health.json"
    try:
        health = json.loads(health_f.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        health = {}
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")
    new, errors = [], 0
    for kind, src in sources:
        label = f"{kind}: " + (src.get("name") or f"{src.get('station')} - {src.get('programme')}")
        h = health.setdefault(label, {"fails": 0})
        try:
            items = list(radio_items(src) if kind == "radio" else youtube_items(src))
        except Exception as e:  # one broken feed must not stop the others
            errors += 1
            h.update(fails=h.get("fails", 0) + 1, last_error=f"{now} {str(e)[:120]}")
            print(f"feed error {label}: {str(e)[:100]}", file=sys.stderr)
            continue
        h.update(fails=0, last_ok=now, items=len(items), newest=max((i["date"] for i in items), default=""))
        for it in items:
            if it["date"] < args.since or it["url"] in seen or "/shorts/" in it["url"]:
                continue
            names = who(it["title"])
            if not names or (kind in ("radio", "broadcast") and not speaks(it["title"], broadcast=kind == "broadcast")):
                continue
            pw = place_words(it["title"], names[0])
            if kind == "broadcast" and pw and any(pw & old for old in events.get((it["date"], names[0]), [])):
                print(f"  same event already queued, skipped: {it['title'][:80]}")
                continue
            events.setdefault((it["date"], names[0]), []).append(pw)
            seen.add(it["url"])
            new.append({
                "date": it["date"], "person": names[0], "kind": "other", "outlet": it["outlet"],
                "title": it["title"], "url": it["url"], "tier": 2, "duration_min": it["duration_min"],
                "has_text": "no", "file": "discover",
                "notes": ("also names: " + ", ".join(names[1:]) + "; " if len(names) > 1 else "")
                         + f"found {datetime.now(timezone.utc).date()} by discover.py",
            })

    health_f.parent.mkdir(parents=True, exist_ok=True)
    health_f.write_text(json.dumps(health, ensure_ascii=False, indent=1), encoding="utf-8")
    dead = [k for k, v in health.items() if v.get("fails", 0) >= 6]   # 6 runs = 12 hours failing
    if dead:
        print("SOURCES FAILING FOR 12+ HOURS: " + "; ".join(dead), file=sys.stderr)

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
