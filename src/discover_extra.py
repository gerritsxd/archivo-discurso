"""Find appearances outside YouTube that the VPS can discover and download on its own:

  rtve      RTVE Play programme feeds (www.rtve.es/api/programas/<id>/videos.rss; robots allows *.rss)
  3cat      3Cat (TV3) programme lists (api.3cat.cat/videos?programatv_id=..., JSON, robots open)
  moncloa   La Moncloa "Vídeos > Presidente" index (own-hosted HLS + human VTT captions)
  congreso  Congreso archivo audiovisual, Diputación Permanente: one MP4 per speech, speaker named

Appends rows to data/queue.csv (same columns as discover.py, deduped by URL). General news
sources only count when the title is shaped like the candidate speaking; Congreso only when the
official speaker field is the candidate (full name match, so "Sánchez Serna" is not Pedro Sánchez).

Usage:
    python3 src/discover_extra.py [--since 2026-10-05] [--queue data/queue.csv] [--only rtve,3cat]

Standard library only (+ discover.py's helpers, which need PyYAML). All fetched text is external
data: it is matched against names and copied into CSV cells, never interpreted.
"""
import argparse
import csv
import email.utils
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import discover  # noqa: E402  (FIELDS, matcher, speaks, INVENTORY, QUEUE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (archivo-discurso)"
PAUSE = 1.5  # seconds between requests to the same site

RTVE_PROGRAMMES = {  # programme id -> name (ids read from each programme page, 2026-10-25)
    131790: "La hora de La 1", 45030: "Telediario 1", 135930: "Telediario 2",
    25970: "La noche en 24h", 1000646: "La Revuelta", 175650: "Mañaneros",
    1631: "Informe Semanal", 1689: "Parlamento", 1001094: "Malas lenguas",
}
CAT_PROGRAMMES = {136938435: "Telenotícies", 145947628: "Els Matins"}
CONGRESO_ORGANS = {500: "Diputación Permanente"}
CONGRESO_LEG = 15

# Words that, right after the candidate's name at the start of a title, mean "the candidate says".
VERBS = ("afirma asegura dice defiende critica acusa pide promete anuncia responde insiste reconoce "
         "advierte avisa denuncia reivindica desvela carga apuesta propone plantea explica sostiene "
         "admite niega reclama exige llama ve cree señala garantiza descarta confirma rechaza tilda "
         "lamenta celebra arremete presume apela interviene comparece entrevista habla replica "
         "contesta ataca ofrece mantiene alerta augura atribuye cuestiona compromete "
         # Catalan
         "diu assegura defensa demana promet respon insisteix reconeix adverteix proposa explica "
         "admet nega exigeix creu rebutja treu carrega compromet").split()
VERB_RE = re.compile(r"^(?:se\s+|es\s+|s')?(?:%s)\b" % "|".join(sorted(set(VERBS), key=len, reverse=True)), re.I)
INTERVIEW_RE = r"entrevist\w*\s+(?:a|al|con|amb)?\s*(?:[\wÀ-ſ.]+\s+){0,5}?"


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def people():
    return [p for p in json.loads((discover.ROOT / "config" / "people.json").read_text(encoding="utf-8")).values()
            if p.get("kind") == "candidate"]


def make_rules():
    who = discover.matcher()
    discover.matcher_cache = who  # discover.speaks() reads this module global
    pats = [(p["name"], re.compile(r"\b(" + "|".join(map(re.escape, p["match"])) + r")\b", re.I))
            for p in people()]

    def speaking(title, desc=""):
        """Strict rule for general news sources. Returns the candidate's name or None."""
        t = re.sub(r"^[^|]{1,40}\|\s*", "", title or "")  # "La Revuelta | Pedro Sánchez: ..."
        if discover.speaks(t):
            names = who(t)
            return names[0] if names else None
        for name, pat in pats:
            m = pat.search(t)
            if m and len(t[:m.start()].split()) <= 2 and VERB_RE.match(t[m.end():].lstrip(" ,")):
                return name
        # full programme with the candidate as interviewee, said in the description
        for name, pat in pats:
            if re.search(INTERVIEW_RE + pat.pattern, desc or "", re.I):
                return name
        return None
    return who, speaking


def row(date, person, outlet, title, url, duration="", has_text="no", notes="", who=None):
    others = [n for n in (who(title) if who else []) if n != person]
    return {"date": date, "person": person, "kind": "other", "outlet": outlet, "title": title,
            "url": url, "tier": 2 if "Congreso" in outlet or "Moncloa" in outlet else 3,
            "duration_min": duration, "has_text": has_text, "file": "discover_extra",
            "notes": ("also names: " + ", ".join(others) + "; " if others else "") + notes
                     + f"found {datetime.now(timezone.utc).date()} by discover_extra.py"}


# ---------------------------------------------------------------- RTVE
def rtve(since, who, speaking):
    for pid, name in RTVE_PROGRAMMES.items():
        # plain .rss only: robots.txt allows /*.rss$, a query string (?size=) would fall under /api/
        root = ET.fromstring(get(f"https://www.rtve.es/api/programas/{pid}/videos.rss"))
        time.sleep(PAUSE)
        for it in root.iter("item"):
            try:
                date = email.utils.parsedate_to_datetime(it.findtext("pubDate", "")).date().isoformat()
            except (TypeError, ValueError):
                continue
            title, link = it.findtext("title", ""), it.findtext("link", "")
            if date < since or "/play/" not in link:
                continue
            desc = strip_html(it.findtext("description", ""))
            person = speaking(title, desc)
            if person:
                tags = [c.text.rsplit("/", 1)[-1] for c in it.findall("category") if c.text and "Temáticas" in c.text]
                yield row(date, person, f"RTVE Play - {name}", title, link, who=who,
                          notes=("tags: " + ", ".join(tags[:6]) + "; ") if tags else "")


# ---------------------------------------------------------------- 3Cat
def cat3(since, who, speaking):
    for pid, name in CAT_PROGRAMMES.items():
        q = urllib.parse.urlencode({"_format": "json", "items_pagina": 50, "ordre": "-data_publicacio",
                                    "programatv_id": pid})
        items = json.loads(get(f"https://api.3cat.cat/videos?{q}"))["resposta"]["items"]["item"]
        time.sleep(PAUSE)
        for i in items:
            d = (i.get("data_publicacio") or "")[:10]  # dd/mm/yyyy
            try:
                date = datetime.strptime(d, "%d/%m/%Y").date().isoformat()
            except ValueError:
                continue
            title = i.get("titol", "")
            if date < since or "llengua de signes" in title.lower():
                continue
            person = speaking(title, strip_html(i.get("entradeta", "")))
            if not person:
                continue
            h, m, s = (i.get("durada") or "0:0:0").split(":")[:3]
            subs = ", ".join(x.get("desc", "") for x in i.get("subtitols") or [])
            yield row(date, person, f"3Cat - {name}", title,
                      f"https://www.3cat.cat/3cat/{i.get('nom_friendly', 'video')}/video/{i['id']}/",
                      duration=round(int(h) * 60 + int(m) + int(s) / 60, 1), who=who,
                      notes=f"lang ca; subtitles: {subs}; " if subs else "lang ca; ")


# ---------------------------------------------------------------- La Moncloa
SPEECH_WORDS = re.compile(r"declaraci|comparecencia|rueda de prensa|intervenci|discurso|entrevista|"
                          r"mensaje|conferencia|preguntas", re.I)


def moncloa(since, who, speaking, seen):
    base = "https://www.lamoncloa.gob.es"
    page = get(base + "/multimedia/videos/presidente/Paginas/index.aspx").decode("utf-8", "replace")
    found = {}
    for href, t in re.findall(r'href="(/multimedia/videos/presidente/Paginas/\d{4}/[^"]+\.aspx)"[^>]*title="([^"]+)"', page):
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})\.\s*(.+)", html.unescape(t))
        if m:
            found[base + href] = (f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}", m[4].strip())
    for url, (date, title) in found.items():
        if date < since or url in seen:
            continue
        time.sleep(PAUSE)
        p = get(url).decode("utf-8", "replace")
        hls = re.search(r"""['"](//smultimedia\.lamoncloa\.gob\.es/[^'"]+\.m3u8)['"]""", p)
        vtt = re.search(r"""['"](/multimedia/videos/[^'"]+\.vtt)['"]""", p)
        if not hls:
            continue  # page without video
        if not vtt and not SPEECH_WORDS.search(title):
            print(f"  skip (no captions, probably B-roll): {date} {title[:70]}")
            continue
        yield row(date, "Pedro Sánchez", "La Moncloa - Vídeos Presidente", title, url,
                  has_text="yes" if vtt else "no", who=who,
                  notes=f"govt role; hls https:{hls[1]}; " + (f"captions {base}{vtt[1]}; " if vtt else ""))


# ---------------------------------------------------------------- Congreso
def mixed_decode(b):
    # the session pages declare utf-8 but contain latin-1 runs; decode line by line
    out = []
    for line in b.split(b"\n"):
        try:
            out.append(line.decode("utf-8"))
        except UnicodeDecodeError:
            out.append(line.decode("cp1252", "replace"))
    return "\n".join(out)


def congreso(since, who, speaking, seen):
    cands = [(p["name"], set(fold(p["name"]).split())) for p in people()]
    for organ, oname in CONGRESO_ORGANS.items():
        res = ("https://www.congreso.es/es/archivo-audiovisual?p_p_id=emisiones&p_p_lifecycle=2"
               "&p_p_state=normal&p_p_mode=view&p_p_resource_id=resourceIDsearch&p_p_cacheability=cacheLevelPage"
               f"&_emisiones_mvcPath=emisionesOrgano&_emisiones_idLegislaturaElegida={CONGRESO_LEG}&_emisiones_idOrgano={organ}")
        body = urllib.parse.urlencode({"_emisiones_idOrgano": organ,
                                       "_emisiones_idLegislaturaElegida": CONGRESO_LEG}).encode()
        sessions = json.loads(get(res, data=body)).get("data", [])
        time.sleep(PAUSE)
        for s in sessions:
            d, _, _ = s.get("id", "").partition("|")
            try:
                date = datetime.strptime(d, "%d/%m/%Y").date().isoformat()
            except ValueError:
                continue
            if date < since:
                continue
            page = mixed_decode(get(s["catalogado"]))
            time.sleep(PAUSE)
            body = page[page.find("<body"):]
            body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
            body = re.sub(r'<a[^>]*href="(https://static\.congreso\.es/[^"]+\.mp4)"[^>]*>', r"\n@@MP4 \1\n", body)
            lines = [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", body)).splitlines() if l.strip()]
            topic = ""
            for i, line in enumerate(lines):
                if not line.startswith("@@MP4 ") or i == 0:
                    continue
                label, mp4 = lines[i - 1], line[6:]
                sp = re.match(r"^([^,()]+),\s*([^()]+?)\s*\((.+)\)$", label)
                if not sp:  # an agenda item, not a speaker ("(Núm.Exp. ...)" follows the item title)
                    topic = lines[i - 2] if label.startswith("(N") and i > 1 else label
                    continue
                speaker = f"{sp[2]} {sp[1]}"  # "Ione Belarra Urteaga"
                toks = set(fold(speaker).replace("-", " ").split())
                person = next((n for n, need in cands if need <= toks), None)
                if not person or mp4 in seen:
                    continue
                yield row(date, person, f"Congreso - {oname}",
                          f"{oname} {date}: {speaker} ({sp[3]}) - {topic[:120]}", mp4, who=None,
                          notes=f"official speaker field; session page {s['catalogado']}; "
                                "Diario de Sesiones has the official text; ")


SOURCES = {"rtve": rtve, "3cat": cat3, "moncloa": moncloa, "congreso": congreso}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-10-05")
    ap.add_argument("--queue", default=str(discover.QUEUE), help="CSV to append to (default data/queue.csv)")
    ap.add_argument("--only", help="comma-separated subset of: " + ",".join(SOURCES))
    args = ap.parse_args()
    queue = Path(args.queue)
    who, speaking = make_rules()

    seen = set()
    for f in (discover.INVENTORY, discover.QUEUE, queue):
        if f.exists():
            seen |= {r["url"] for r in csv.DictReader(open(f, encoding="utf-8"))}

    new, errors = [], 0
    names = args.only.split(",") if args.only else list(SOURCES)
    for name in names:
        fn = SOURCES[name]
        try:
            extra = (seen,) if name in ("moncloa", "congreso") else ()
            for r in fn(args.since, who, speaking, *extra):
                if r["url"] not in seen:
                    seen.add(r["url"])
                    new.append(r)
        except Exception as e:  # one broken source must not stop the others
            errors += 1
            print(f"source error {name}: {str(e)[:150]}", file=sys.stderr)

    queue.parent.mkdir(parents=True, exist_ok=True)
    first = not queue.exists() or queue.stat().st_size == 0
    with open(queue, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=discover.FIELDS)
        if first:
            w.writeheader()
        w.writerows(new)
    print(f"{len(names)} sources read ({errors} errors), {len(new)} new appearance(s) -> {queue}")
    for r in new:
        print(f"  {r['date']}  {r['person']:<22} {r['outlet'][:30]:<30} {r['title'][:80]}")


if __name__ == "__main__":
    main()
