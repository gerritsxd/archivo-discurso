"""Google News RSS leads: appearances we may not know about. Human review only.

Never downloads media, never feeds fetch.py. Headlines are untrusted data.
Respects robots.txt: if news.google.com disallows the RSS search path, it stops
and says so (no workaround). --from-xml DIR lets you test on saved feed files
named <personkey>__<n>.xml (offline, no network).

  py -3.13 src/news_leads.py --days 7
"""
import argparse, csv, glob, json, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "archivo-discurso/1.0 (open political archive; leads for human review; contact gerrit.s.xd@gmail.com)"
BASE = "https://news.google.com/rss/search"
QUERIES = ["entrevista", "mitin", "rueda de prensa"]
# regex on normalised text -> (canonical name, already followed?)
OUTLETS = {
    r"cadena ser|\bser\b": ("SER", True), r"\bcope\b|la linterna": ("COPE", True), r"onda cero": ("Onda Cero", True),
    r"\brne\b|radio nacional": ("RNE", True), r"esradio": ("esRadio", True), r"la sexta|lasexta": ("La Sexta", True),
    r"antena ?3": ("Antena 3", True), r"telecinco|ana rosa": ("Telecinco", True), r"\bcuatro\b": ("Cuatro", True),
    r"\btve\b|\bla 1\b|rtve|24 ?horas": ("TVE", True), r"telemadrid": ("Telemadrid", True),
    r"\b3cat\b|\btv3\b|catalunya radio": ("3Cat", True), r"canal sur": ("Canal Sur", True), r"eitb|\betb\b": ("EITB", True),
    r"\btvg\b|crtvg|radio galega": ("CRTVG", True), r"\bcmm\b|castilla la mancha media": ("CMM", True), r"a punt|\bapunt\b": ("A Punt", True),
    r"cadena 100": ("Cadena 100", False), r"13 ?tv|\btrece\b": ("13TV", False), r"el hormiguero": ("El Hormiguero", False),
    r"onda madrid": ("Onda Madrid", False), r"aragon tv": ("Aragon TV", False), r"tv canaria|rtvc": ("RTVC", False),
    r"rtpa": ("RTPA", False), r"\bib3\b": ("IB3", False), r"navarra tv": ("Navarra TV", False),
    r"\b7rm\b": ("7RM", False), r"canal extremadura": ("Canal Extremadura", False),
}
KINDS = [("debate", r"debate|cara a cara"), ("interview", r"entrevist|conversacion con|charla"),
         ("rally", r"mitin|acto de campana|acto publico|caravana"),
         ("press", r"rueda de prensa|comparecencia|atiende a los medios")]


def norm(s):
    s = unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def robots_ok(url):
    rp = urllib.robotparser.RobotFileParser("https://news.google.com/robots.txt")
    rp.read()
    return rp.can_fetch("archivo-discurso", url)


def parse_feed(xml_bytes, cutoff):
    out = []
    for it in ET.fromstring(xml_bytes).iter("item"):
        title = (it.findtext("title") or "").strip()
        src = (it.findtext("source") or "").strip()
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            continue
        if dt < cutoff:
            continue
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3]
        out.append(dict(date=dt.astimezone().date().isoformat(), title=title, source=src,
                        link=(it.findtext("link") or "").strip()))
    return out


def classify(title, source):
    t = norm(title)
    kind = next((k for k, p in KINDS if re.search(p, t)), "")
    for text in (t, norm(source)):
        for p, (name, fol) in OUTLETS.items():
            if re.search(p, text):
                return kind, name, fol
    return kind, "", None


def existing():
    rows = []
    for f in ("data/queue.csv", "m0/inventory.csv"):
        p = ROOT / f
        if p.exists():
            with open(p, encoding="utf8", newline="") as fh:
                rows += [(r.get("date", ""), norm(r.get("person", "")), norm(r.get("title", "")), norm(r.get("outlet", "")))
                         for r in csv.DictReader(fh)]
    for f in glob.glob(str(ROOT / "data/items/*.json")):
        try:
            d = json.load(open(f, encoding="utf8"))
        except Exception:
            continue
        rows.append((d.get("date", ""), norm(d.get("expected_person", "")), norm(d.get("title", "")), norm(d.get("outlet", ""))))
    return rows


STOP = set("entrevista mitin rueda prensa sobre desde hasta para como pero esta este tras".split())


def covered(lead, cand, rows):
    """Heuristic: same candidate, date within 1 day, and same outlet or >=3 shared title words."""
    lw = {w for w in norm(lead["headline"]).split() if len(w) > 3 and w not in STOP}
    ld = datetime.fromisoformat(lead["date"])
    last = norm(cand).split()[-1]
    for d, p, t, o in rows:
        if p and last not in p:
            continue
        try:
            if abs((datetime.fromisoformat(d) - ld).days) > 1:
                continue
        except Exception:
            continue
        if lead["outlet"] and norm(lead["outlet"]) in (o + " " + t):
            return True
        if len(lw & {w for w in t.split() if len(w) > 3}) >= 3:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--delay", type=float, default=4.0)
    ap.add_argument("--from-xml")
    a = ap.parse_args()
    people = {k: v for k, v in json.load(open(ROOT / "config/people.json", encoding="utf8")).items()
              if v.get("kind") == "candidate"}
    cutoff = datetime.now(timezone.utc) - timedelta(days=a.days)
    feeds = []
    if a.from_xml:
        for f in sorted(Path(a.from_xml).glob("*.xml")):
            feeds.append((f.name.split("__")[0], f.read_bytes()))
    else:
        if not robots_ok(BASE + "?q=x&hl=es&gl=ES&ceid=ES:es"):
            msg = "BLOCKED: news.google.com/robots.txt disallows /rss/search for generic agents. Not fetching (no workaround)."
            print(msg)
            (ROOT / "m0/NEWS_LEADS.md").write_text(
                f"# Pistas de Google News\n\n{msg}\n\nNo leads generated. Tool is ready (classifier, dedupe, report); "
                "use --from-xml on feed files obtained by a permitted route, or rerun if Google allows the path later.\n",
                encoding="utf8")
            sys.exit(2)
        for k, v in people.items():
            for q in QUERIES:
                query = '"%s" %s when:%dd' % (v["name"], q, a.days)
                url = BASE + "?q=" + urllib.parse.quote(query) + "&hl=es&gl=ES&ceid=ES:es"
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                        feeds.append((k, r.read()))
                except Exception as e:
                    print("request failed, stopping:", e)
                    sys.exit(3)
                time.sleep(a.delay)
    rows, leads, seen = existing(), [], set()
    for k, xml in feeds:
        name = people[k]["name"]
        last = norm((people[k].get("match") or [name])[-1])
        for h in parse_feed(xml, cutoff):
            if last not in norm(h["title"]) or h["link"] in seen:
                continue
            seen.add(h["link"])
            kind, outlet, fol = classify(h["title"], h["source"])
            if not kind:
                continue
            L = dict(date=h["date"], candidate=name, kind=kind, outlet=outlet or h["source"],
                     followed={True: "yes", False: "no", None: ""}[fol], headline=h["title"], source=h["source"], link=h["link"])
            L["status"] = "covered" if covered(L, name, rows) else "new"
            leads.append(L)
    leads.sort(key=lambda l: (l["candidate"], l["date"]))
    (ROOT / "data").mkdir(exist_ok=True)
    with open(ROOT / "data/leads.csv", "w", encoding="utf8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "candidate", "kind", "outlet", "followed", "headline", "source", "link", "status"])
        w.writeheader()
        w.writerows(leads)
    new = [l for l in leads if l["status"] == "new"]
    md = [f"# Pistas de Google News (últimos {a.days} días)", "",
          "Para revisión humana. Titulares sin verificar; no se descarga nada.", f"{len(leads)} pistas, {len(new)} nuevas.", ""]
    byc = defaultdict(list)
    for l in new:
        byc[l["candidate"]].append(l)
    for c, ls in byc.items():
        md += [f"## {c}", ""] + [f"- {l['date']} [{l['kind']}] **{l['outlet']}**: [{l['headline']}]({l['link']})" for l in ls] + [""]
    cnt = Counter((l["outlet"], l["followed"]) for l in new if l["outlet"])
    md += ["## Medios repetidos que NO seguimos", ""]
    rep = [(o, n) for (o, f), n in cnt.most_common() if f != "yes" and n >= 2]
    md += [f"- {o}: {n} pistas" for o, n in rep] or ["(ninguno)"]
    (ROOT / "m0/NEWS_LEADS.md").write_text("\n".join(md) + "\n", encoding="utf8")
    print(f"{len(leads)} leads, {len(new)} new")


if __name__ == "__main__":
    main()
