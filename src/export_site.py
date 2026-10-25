"""Build the static public site from data/items/*.json + config/people.json.

    py -3.13 -I src/export_site.py                # writes site/
    py -3.13 -I src/export_site.py --items X --out Y

Pure stdlib. Re-runnable: site/ is rebuilt from scratch every time.
Transcript text is external speech: everything that goes into HTML passes
through esc(); URLs must be http(s) or they are not linked at all.

Output:
  site/index.html, buscar.html, como-funciona.html
  site/a/<item>.html          one page per appearance (full transcript)
  site/c/<person>.html        one page per candidate
  site/assets/                style.css, search.js (copied from web/)
  site/data/index.json        people + item metadata + list of quote shards (search page)
  site/data/q/<person>-<YYYY-MM>.json   quote shards, loaded only when searching
  site/data/items/<item>.json full item, as produced by process.py (open data)
"""
import argparse
import hashlib
import html
import json
import math
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_NAME = "Archivo del discurso"
SITE_SUB = "Lo que dicen en público los candidatos a las elecciones generales del 29 de noviembre de 2026"
BANNER = "Transcripción automática, sin revisar. Comprueba siempre la fuente."
# Corrections contact. Leave empty until a public address exists; pages then say so.
CONTACT_EMAIL = ""
# Text shown in the game's "Compartir" line (no scheme, so it stays short).
SHARE_URL = "gerritsxd.com/discurso/juego.html"

IDENTIFIED = {"match", "confirmed", "human", "reviewed"}  # decisions that count as identified
KIND_ES = {"interview": "Entrevista", "speech": "Discurso", "rally": "Mitin", "press_conf": "Rueda de prensa",
           "debate": "Debate", "parliament": "Parlamento", "other": "Otro"}
MEDIUM_ES = {"tv": "Televisión", "radio": "Radio", "official": "Canal oficial (partido o Gobierno)", "other": "Otro medio"}
DECISION_ES = {"match": "Identificado por la voz", "confirmed": "Confirmado por una persona",
               "human": "Confirmado por una persona", "reviewed": "Confirmado por una persona",
               "unknown": "Sin identificar", "too_short": "Sin identificar (poca voz)",
               "ambiguous": "Sin identificar (dudoso)"}
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre"]
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,120}$")
RADIO_RE = re.compile(r"\b(SER|COPE|RNE|Onda Cero|esRadio|RAC1|Catalunya R[aà]dio|Radio|R[aà]dio)\b", re.I)
TV_RE = re.compile(r"\b(Antena 3|TVE|La 1|laSexta|La Sexta|Telecinco|Cuatro|RTVE|24h|TV3|3Cat|Telemadrid|Canal Sur|ETB|TVG)\b", re.I)
OFFICIAL_RE = re.compile(r"\b(PP|PSOE|VOX|Podemos|Sumar|Moncloa|Frente Amplio|Comuns)\b", re.I)


# ---------------------------------------------------------------- helpers

def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def safe_url(u):
    u = (u or "").strip()
    return u if re.match(r"^https?://[^\s<>\"']+$", u, re.I) else ""


def source_type(url):
    u = url.lower()
    host = re.sub(r"^https?://", "", u).split("/")[0]
    if host.endswith("youtube.com") or host == "youtu.be":
        return "youtube"
    if "rtve.es/play" in u:
        return "rtveplay"
    if re.search(r"\.(mp3|m4a|ogg|opus|aac|wav)(\?|#|$)", u):
        return "audio"
    return "other"


def medium(outlet, url):
    o = outlet or ""
    if source_type(url) == "audio" or RADIO_RE.search(o):
        return "radio"
    if TV_RE.search(o):
        return "tv"
    if OFFICIAL_RE.search(o):
        return "official"
    return "other"


def at_time(url, st, t):
    """Link to the source at second t, or the plain URL (RTVE Play, other)."""
    t = max(0, int(t))
    if st == "youtube":
        return url + ("&" if "?" in url else "?") + f"t={t}s"
    if st == "audio":
        return url.split("#")[0] + f"#t={t}"
    return url


def clock(t):
    t = max(0, int(t))
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def dur_es(sec):
    sec = int(sec or 0)
    h, m = sec // 3600, sec % 3600 // 60
    if h:
        return f"{h} h {m:02d} min"
    return f"{m} min" if m else f"{sec} s"


def hours_es(sec):
    h = (sec or 0) / 3600
    if h < 1:
        return f"{round((sec or 0) / 60)} min"
    return f"{h:.1f}".replace(".", ",") + " h"


def date_es(d):
    try:
        y, m, dd = (int(x) for x in str(d).split("-"))
        return f"{dd} de {MONTHS[m - 1]} de {y}"
    except Exception:
        return esc(d or "fecha desconocida")


def num_es(n):
    return f"{n:,}".replace(",", ".")


def sort_key_name(name):
    last = (name or "").split()[-1] if name else ""
    return unicodedata.normalize("NFD", last).encode("ascii", "ignore").decode().lower()


SENT_RE = re.compile(r"(?<=[.!?…])\s+")


def sentences(text):
    return [s for s in SENT_RE.split(text.strip()) if s]


def chunks(turn):
    """Split a turn into citable chunks of ~1-3 sentences with an estimated start time.

    Turns only carry start/end, so a chunk's time is interpolated by character position
    and pulled back 2 s; approx=1 marks it as an estimate."""
    text, start, end = turn["text"], turn["start"], turn["end"]
    n = max(1, len(text))
    out, buf, buf_off, off = [], [], 0, 0
    for s in sentences(text):
        pos = text.find(s, off)
        pos = off if pos < 0 else pos
        if not buf:
            buf_off = pos
        buf.append(s)
        off = pos + len(s)
        if sum(len(x) for x in buf) >= 200:
            out.append((buf_off, " ".join(buf)))
            buf = []
    if buf:
        out.append((buf_off, " ".join(buf)))
    res = []
    for o, t in out:
        if o == 0:
            res.append((int(start), 0, t))
        else:
            est = start + (end - start) * o / n
            res.append((max(int(start), int(math.floor(est)) - 2), 1, t))
    return res


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- load

def load_people(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    people = {}
    for pid, p in raw.items():
        if SAFE_ID.match(pid):
            people[pid] = {"name": p.get("name", pid), "role": p.get("role", ""), "kind": p.get("kind", "host")}
    return people


def load_items(folder, people):
    items = []
    for f in sorted(folder.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip {f.name}: {e}", file=sys.stderr)
            continue
        iid = str(d.get("id") or f.stem)
        if not SAFE_ID.match(iid):
            print(f"skip {f.name}: unsafe id", file=sys.stderr)
            continue
        url = safe_url(d.get("url"))
        speakers = {}
        for lab, s in (d.get("speakers") or {}).items():
            s = s or {}
            pid = s.get("person")
            ok = bool(pid) and pid in people and s.get("decision") in IDENTIFIED
            speakers[str(lab)] = {
                "person": pid if ok else None,
                "decision": s.get("decision") or "unknown",
                "reason": s.get("reason") or "",
                "talk_s": float(s.get("talk_s") or 0),
                "raw_name": s.get("name") or str(lab),
            }
        # Unidentified speakers get stable public names in order of first appearance.
        unk_n = {}
        turns = []
        for t in d.get("turns") or []:
            text = str(t.get("text") or "").strip()
            if not text:
                continue
            lab = str(t.get("label") or "?")
            sp = speakers.setdefault(lab, {"person": None, "decision": "unknown", "reason": "", "talk_s": 0.0, "raw_name": lab})
            pid = sp["person"]  # identity comes only from the speakers table, never from the turn alone
            if not pid and lab not in unk_n:
                unk_n[lab] = len(unk_n) + 1
            try:
                st, en = float(t.get("start") or 0), float(t.get("end") or 0)
            except (TypeError, ValueError):
                st = en = 0.0
            turns.append({"start": st, "end": max(st, en), "label": lab, "person": pid, "text": text})
        for lab, sp in speakers.items():
            if not sp["person"] and lab not in unk_n:
                unk_n[lab] = len(unk_n) + 1
            if sp["person"]:
                sp["public"] = people[sp["person"]]["name"]
            elif re.match(r"^Hablante sin identificar \d+$", sp["raw_name"]):
                sp["public"] = sp["raw_name"]  # keep the pipeline's numbering so it matches the JSON
            else:
                sp["public"] = f"Hablante sin identificar {unk_n[lab]}"
        try:
            dur = float(d.get("duration_s") or 0)
        except (TypeError, ValueError):
            dur = 0.0
        date_s = str(d.get("date") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_s):
            date_s = ""
        items.append({
            "id": iid, "file": f, "date": date_s, "outlet": str(d.get("outlet") or ""),
            "title": str(d.get("title") or iid), "url": url, "src": source_type(url) if url else "none",
            "medium": medium(d.get("outlet"), url), "kind": str(d.get("kind") or "other"),
            "expected": str(d.get("expected_person") or ""), "duration": dur, "language": d.get("language") or "es",
            "sha256": str(d.get("sha256") or ""), "fetched_at": str(d.get("fetched_at") or ""),
            "pipeline": d.get("pipeline") or {}, "speakers": speakers, "turns": turns,
        })
    items.sort(key=lambda x: (x["date"], x["id"]), reverse=True)  # newest first
    return items


# ---------------------------------------------------------------- page shell

def page(root, title, body, active="", desc="", body_attrs=""):
    nav = [("index.html", "Inicio", "inicio"), ("juego.html", "Juego", "juego"), ("buscar.html", "Buscar", "buscar"),
           ("como-funciona.html", "Cómo funciona", "como")]
    links = "".join(
        f'<a href="{root}{h}"{" aria-current=page" if k == active else ""}>{esc(t)}</a>' for h, t, k in nav)
    full = f"{title} · {SITE_NAME}" if title != SITE_NAME else SITE_NAME
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full)}</title>
<meta name="description" content="{esc(desc or SITE_SUB)}">
<meta name="referrer" content="no-referrer">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap">
<link rel="stylesheet" href="{root}assets/style.css?v={ASSET_V}">
</head>
<body{body_attrs}>
<div class="banner" role="note">{esc(BANNER)}</div>
<header class="mast">
  <div class="wrap mast-in">
    <a class="brand" href="{root}index.html">{esc(SITE_NAME)}</a>
    <nav class="nav" aria-label="Principal">{links}</nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="foot">
  <div class="wrap">
    <p>{esc(SITE_SUB)}. Textos y marcas de tiempo; el audio y el vídeo están en la fuente original, enlazada en cada cita.</p>
    <p><a href="https://github.com/gerritsxd/archivo-discurso">Código abierto en GitHub</a>. Datos bajo licencia CC BY 4.0. <a href="{root}privacidad.html">Sin cookies, sin analítica, sin rastreo</a>. Generado el {esc(GENERATED)}. <a href="{root}como-funciona.html#correcciones">Comunicar un error</a>.</p>
  </div>
</footer>
</body>
</html>
"""


def person_label(people, pid, with_role=True):
    p = people[pid]
    role = f' <span class="role">{esc(p["role"])}</span>' if with_role and p["role"] else ""
    return f'{esc(p["name"])}{role}'


def src_link(it, t, label=None):
    """Anchor to the source at second t; RTVE Play / other sources get the plain URL + 'min mm:ss'."""
    if not it["url"]:
        return f'<span class="nosrc">min {clock(t)}</span>'
    href = at_time(it["url"], it["src"], t)
    text = label or clock(t)
    if it["src"] in ("youtube", "audio"):
        return f'<a class="ts" href="{esc(href)}" rel="noopener noreferrer" target="_blank" title="Abrir la fuente en el minuto {clock(t)}">{esc(text)}</a>'
    return f'<a class="ts" href="{esc(href)}" rel="noopener noreferrer" target="_blank" title="La fuente no admite enlace a un minuto: busca el minuto {clock(t)}">{esc(text)}</a>'


def item_meta_line(it):
    parts = [date_es(it["date"]), esc(it["outlet"]), esc(KIND_ES.get(it["kind"], it["kind"]))]
    if it["duration"]:
        parts.append(dur_es(it["duration"]))
    return " · ".join(p for p in parts if p)


# ---------------------------------------------------------------- build

def build(items_dir, people_path, out, vp_dir):
    global ASSET_V, GENERATED
    people = load_people(people_path)
    items = load_items(items_dir, people)
    voiceprints = {p.stem for p in vp_dir.glob("*.json")} if vp_dir.exists() else set()
    GENERATED = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")

    web = ROOT / "web"
    assets = {n: (web / n).read_text(encoding="utf-8") for n in ("style.css", "search.js", "juego.js", "home.js")}
    ASSET_V = hashlib.sha1("".join(assets.values()).encode()).hexdigest()[:8]

    candidates = sorted((pid for pid, p in people.items() if p["kind"] == "candidate"),
                        key=lambda pid: sort_key_name(people[pid]["name"]))

    # fresh output dir (only things we own)
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("a", "c", "data", "assets"):
        shutil.rmtree(out / sub, ignore_errors=True)
    for n, text in assets.items():
        write(out / "assets" / n, text)

    # ---- quotes, stats
    stats = {pid: {"secs": 0.0, "items": [], "sent": 0, "latest": None} for pid in candidates}
    shards = defaultdict(list)  # (pid, YYYY-MM) -> entries
    item_index = {it["id"]: i for i, it in enumerate(items)}
    item_quotes = defaultdict(lambda: defaultdict(list))  # item id -> pid -> [(t, approx, text, turn_start)]
    n_sent = 0
    for it in items:
        for t in it["turns"]:
            pid = t["person"]
            if not pid or people[pid]["kind"] != "candidate":
                continue
            st = stats[pid]
            st["secs"] += t["end"] - t["start"]
            st["sent"] += 1  # one intervention = one speaker turn (same unit as api/stats)
            n_sent += 1
            if it["id"] not in st["items"]:
                st["items"].append(it["id"])
            for tt, approx, text in chunks(t):
                item_quotes[it["id"]][pid].append((tt, approx, text, int(t["start"])))
                month = it["date"][:7] or "sin-fecha"
                shards[(pid, month)].append([item_index[it["id"]], tt, approx, text, int(t["start"])])
    for pid in candidates:
        for iid in stats[pid]["items"]:  # items are newest first
            qs = [q for q in item_quotes[iid][pid] if len(q[2]) >= 60] or item_quotes[iid][pid]
            if qs:
                stats[pid]["latest"] = (iid, qs[-1])
                break

    # ---- data files
    (out / "data" / "items").mkdir(parents=True, exist_ok=True)
    for it in items:
        shutil.copyfile(it["file"], out / "data" / "items" / f"{it['id']}.json")
    shard_list = []
    for (pid, month), entries in sorted(shards.items()):
        entries.sort(key=lambda e: (items[e[0]]["date"], -e[0], e[1]), reverse=True)
        fn = f"{pid}-{month}.json"
        body = jdump(entries)
        write(out / "data" / "q" / fn, body)
        shard_list.append({"p": pid, "m": month, "n": len(entries), "f": fn,
                           "v": hashlib.sha1(body.encode()).hexdigest()[:8]})
    index = {
        "generated": GENERATED,
        "people": {pid: {"name": p["name"], "role": p["role"], "kind": p["kind"]} for pid, p in people.items()},
        "candidates": candidates,
        "kinds": KIND_ES, "media": MEDIUM_ES,
        "items": [{"id": it["id"], "d": it["date"], "o": it["outlet"], "ti": it["title"], "k": it["kind"],
                   "m": it["medium"], "s": it["src"], "u": it["url"], "du": round(it["duration"])} for it in items],
        "shards": shard_list,
    }
    write(out / "data" / "index.json", jdump(index))

    total_secs = sum(it["duration"] for it in items)
    ctx = dict(people=people, items=items, stats=stats, candidates=candidates, voiceprints=voiceprints,
               item_quotes=item_quotes, n_sent=n_sent, total_secs=total_secs)
    write(out / "index.html", build_home(ctx))
    write(out / "buscar.html", build_search(ctx))
    write(out / "como-funciona.html", build_how(ctx, web))
    write(out / "juego.html", build_game(ctx))
    write(out / "privacidad.html", page("", "Privacidad y cookies",
                                        (web / "privacidad.html").read_text(encoding="utf-8"), "",
                                        desc="Sin cookies, sin analítica, sin registros de visitas."))
    for it in items:
        write(out / "a" / f"{it['id']}.html", build_item(ctx, it))
    for pid in candidates:
        write(out / "c" / f"{pid}.html", build_person(ctx, pid))
    print(f"site: {len(items)} items, {len(candidates)} candidates, {n_sent} intervenciones, "
          f"{len(shard_list)} shards -> {out}")


def search_form(root, big=False, person=None, placeholder="Busca una palabra o una frase entre comillas"):
    hidden = f'<input type="hidden" name="c" value="{esc(person)}">' if person else ""
    cls = "search big" if big else "search"
    return f"""<form class="{cls}" action="{root}buscar.html" method="get" role="search">
  <label class="sr" for="q-{'big' if big else 'small'}">Buscar en lo que dijeron</label>
  <input id="q-{'big' if big else 'small'}" type="search" name="q" placeholder="{esc(placeholder)}" autocomplete="off">
  {hidden}<button type="submit">Buscar</button>
</form>"""


def build_home(ctx):
    people, items, stats = ctx["people"], ctx["items"], ctx["stats"]
    by_id = {it["id"]: it for it in items}
    cards = []
    for pid in ctx["candidates"]:
        st = stats[pid]
        p = people[pid]
        if st["latest"]:
            iid, (tt, approx, text, ts) = st["latest"]
            it = by_id[iid]
            short = text if len(text) <= 240 else text[:237].rsplit(" ", 1)[0] + "…"
            quote = (f'<blockquote class="pull">{esc(short)}</blockquote>'
                     f'<p class="qmeta">{date_es(it["date"])} · {esc(it["outlet"])} · '
                     f'<a href="a/{esc(iid)}.html#t-{ts}">transcripción</a></p>')
        else:
            note = "" if pid in ctx["voiceprints"] else " Aún no tiene huella de voz registrada."
            quote = f'<p class="empty">Todavía no hay frases suyas identificadas.{note}</p>'
        n_it = len(st["items"])
        cards.append(f"""<article class="card" data-person="{esc(pid)}">
  <h3><a href="c/{esc(pid)}.html">{esc(p["name"])}</a></h3>
  <p class="role">{esc(p["role"])}</p>
  <p class="figs"><span><b class="f-time">{hours_es(st["secs"])}</b> de voz identificada</span><span><b class="f-items">{n_it}</b> <span class="f-items-l">{"aparición" if n_it == 1 else "apariciones"}</span></span></p>
  {quote}
</article>""")
    latest = "".join(
        f'<li><a href="a/{esc(it["id"])}.html">{esc(it["title"])}</a><span class="meta">{item_meta_line(it)}</span></li>'
        for it in items[:12]) or '<li class="empty">Aún no hay apariciones procesadas.</li>'
    body = f"""
<section class="hero">
  <p class="kicker">Elecciones generales · 29 de noviembre de 2026</p>
  <h1>Derecho a la información: lo que dijeron, con la fuente.</h1>
  <a class="game-promo" href="juego.html">
    <span class="gp-kicker">Juego diario</span>
    <span class="gp-title">5 frases, ¿quién lo dijo?</span>
    <span class="gp-text" id="game-status">Las mismas frases para todos, cada día. Un minuto.</span>
    <span class="gp-cta" id="game-cta">Jugar</span>
  </a>
  {search_form("", big=True)}
  <dl class="counts">
    <div><dt id="l-items">{"aparición" if len(items) == 1 else "apariciones"}</dt><dd id="n-items">{num_es(len(items))}</dd></div>
    <div><dt>horas de audio</dt><dd id="n-hours">{f"{ctx['total_secs'] / 3600:.1f}".replace(".", ",")}</dd></div>
    <div><dt>intervenciones de candidatos</dt><dd id="n-quotes">{num_es(ctx["n_sent"])}</dd></div>
  </dl>
</section>
<section>
  <h2 class="sect">Candidatos <span class="aside">por orden alfabético del apellido</span></h2>
  <div class="cards">{"".join(cards)}</div>
</section>
<section>
  <h2 class="sect">Últimas apariciones</h2>
  <ul class="list">{latest}</ul>
</section>"""
    body += f'\n<script src="assets/home.js?v={ASSET_V}" defer></script>'
    return page("", SITE_NAME, body, "inicio")


def build_search(ctx):
    people = ctx["people"]
    opts = "".join(f'<option value="{esc(pid)}">{esc(people[pid]["name"])}</option>' for pid in ctx["candidates"])
    media = "".join(f'<option value="{k}">{esc(v)}</option>' for k, v in MEDIUM_ES.items())
    kinds = "".join(f'<option value="{k}">{esc(v)}</option>' for k, v in KIND_ES.items())
    body = f"""
<h1 class="ptitle">Buscar</h1>
<p class="lede">Solo se buscan las palabras de candidatos identificados. Lo que dicen periodistas y hablantes sin identificar está en cada transcripción, pero no aquí.</p>
<form id="sf" class="filters" role="search" action="buscar.html" method="get">
  <div class="frow q">
    <label for="q">Palabras</label>
    <input id="q" name="q" type="search" autocomplete="off" placeholder="vivienda, &quot;sanidad pública&quot;…">
  </div>
  <div class="frow"><label for="c">Candidato</label><select id="c" name="c"><option value="">Todos</option>{opts}</select></div>
  <div class="frow"><label for="desde">Desde</label><input id="desde" name="desde" type="date"></div>
  <div class="frow"><label for="hasta">Hasta</label><input id="hasta" name="hasta" type="date"></div>
  <div class="frow"><label for="medio">Medio</label><select id="medio" name="medio"><option value="">Todos</option>{media}</select></div>
  <div class="frow"><label for="tipo">Tipo</label><select id="tipo" name="tipo"><option value="">Todos</option>{kinds}</select></div>
  <div class="frow go"><button type="submit">Buscar</button></div>
</form>
<p id="status" class="status" aria-live="polite">Escribe una palabra o elige un candidato.</p>
<ol id="results" class="results"></ol>
<p><button id="more" class="more" type="button" hidden>Mostrar más resultados</button></p>
<noscript><p class="empty">La búsqueda necesita JavaScript. Las transcripciones y las páginas de cada candidato funcionan sin él.</p></noscript>
<script src="assets/search.js?v={ASSET_V}" defer></script>"""
    return page("", "Buscar", body, "buscar")


def id_table(ctx, it):
    people = ctx["people"]
    rows = []
    for lab, sp in sorted(it["speakers"].items(), key=lambda kv: -kv[1]["talk_s"]):
        m = re.search(r"sim\s+([0-9.]+)", sp["reason"])
        sim = m.group(1).replace(".", ",") if m else "–"
        pid = sp["person"]
        if pid:
            who = person_label(people, pid)
            cls = "cand" if people[pid]["kind"] == "candidate" else "host"
        else:
            who = esc(sp["public"])
            cls = "unk"
        rows.append(f'<tr class="{cls}"><td>{who}</td><td class="num">{sim}</td>'
                    f'<td>{esc(DECISION_ES.get(sp["decision"], sp["decision"]))}</td>'
                    f'<td class="num">{dur_es(sp["talk_s"])}</td><td class="lab">{esc(lab)}</td></tr>')
    return f"""<div class="tablewrap"><table class="idt">
<caption>Identificación de voces</caption>
<thead><tr><th scope="col">Quién</th><th scope="col" class="num">Similitud</th><th scope="col">Decisión</th><th scope="col" class="num">Habla</th><th scope="col">Etiqueta</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="note">Similitud: coseno entre la voz de este hablante y la huella de voz más parecida (1 = idéntica). Se acepta un nombre con 0,55 o más, al menos 0,10 por encima de la segunda huella y 20 s de voz. Por debajo, el hablante queda sin identificar.</p>"""


def build_item(ctx, it):
    people = ctx["people"]
    root = "../"
    turns, used = [], set()
    for t in it["turns"]:
        sp = it["speakers"].get(t["label"], {})
        pid = t["person"]
        if pid and people[pid]["kind"] == "candidate":
            cls, name = "turn cand", f'<span class="spk">{person_label(people, pid)}</span>'
        elif pid:
            cls, name = "turn host", f'<span class="spk">{person_label(people, pid)}</span>'
        else:
            cls, name = "turn unk", f'<span class="spk">{esc(sp.get("public", "Hablante sin identificar"))}</span>'
        ts = int(t["start"])
        aid = f' id="t-{ts}"' if ts not in used else ""
        used.add(ts)
        turns.append(f'<div class="{cls}"{aid}><div class="th">{src_link(it, t["start"])}{name}</div>'
                     f'<p>{esc(t["text"])}</p></div>')
    src = (f'<a href="{esc(it["url"])}" rel="noopener noreferrer" target="_blank">{esc(it["outlet"] or it["url"])}</a>'
           if it["url"] else esc(it["outlet"]) + " (sin enlace)")
    rtve_note = ('<p class="note">Esta fuente no permite enlazar a un minuto concreto: cada marca de tiempo abre la fuente y '
                 'muestra el minuto que hay que buscar.</p>') if it["src"] in ("rtveplay", "other") else ""
    pipe = it["pipeline"]
    reviewed = "sí" if pipe.get("reviewed") else "no"
    cands = sorted({t["person"] for t in it["turns"] if t["person"] and people[t["person"]]["kind"] == "candidate"},
                   key=lambda p: sort_key_name(people[p]["name"]))
    cand_links = ", ".join(f'<a href="../c/{esc(p)}.html">{esc(people[p]["name"])}</a>' for p in cands) or "ninguno identificado"
    body = f"""
<article class="item">
<p class="kicker">{esc(KIND_ES.get(it["kind"], it["kind"]))} · {date_es(it["date"])}</p>
<h1 class="ptitle">{esc(it["title"])}</h1>
<dl class="meta-dl">
  <div><dt>Fuente</dt><dd>{src}</dd></div>
  <div><dt>Fecha</dt><dd>{date_es(it["date"])}</dd></div>
  <div><dt>Duración</dt><dd>{dur_es(it["duration"]) if it["duration"] else "–"}</dd></div>
  <div><dt>Candidatos identificados</dt><dd>{cand_links}</dd></div>
  <div><dt>Revisado por una persona</dt><dd>{reviewed}</dd></div>
  <div><dt>Datos</dt><dd><a href="../data/items/{esc(it["id"])}.json">JSON de esta aparición</a></dd></div>
</dl>
{id_table(ctx, it)}
<details class="tech"><summary>Detalles técnicos</summary>
<dl class="meta-dl small">
  <div><dt>Transcripción</dt><dd>{esc(pipe.get("asr", "–"))}</dd></div>
  <div><dt>Separación de voces</dt><dd>{esc(pipe.get("diarization", "–"))}</dd></div>
  <div><dt>Procesado</dt><dd>{esc(pipe.get("processed_at", "–"))}</dd></div>
  <div><dt>Descargado</dt><dd>{esc(it["fetched_at"] or "–")}</dd></div>
  <div><dt>SHA-256 del original</dt><dd class="hash">{esc(it["sha256"] or "–")}</dd></div>
</dl></details>
<h2 class="sect">Transcripción</h2>
<div class="tbar">
  <input type="checkbox" id="solo"><label for="solo">Mostrar solo a los candidatos identificados</label>
</div>
{rtve_note}
<div class="transcript">
{"".join(turns) or '<p class="empty">Sin texto.</p>'}
</div>
</article>"""
    return page(root, it["title"], body, desc=f"Transcripción automática: {it['title']}")


def build_person(ctx, pid):
    people, items, stats = ctx["people"], ctx["items"], ctx["stats"]
    p, st = people[pid], stats[pid]
    root = "../"
    by_id = {it["id"]: it for it in items}
    vp = ("Huella de voz registrada." if pid in ctx["voiceprints"] or st["items"]
          else "Aún no tiene huella de voz registrada: sus palabras no se pueden atribuir automáticamente todavía.")
    groups = defaultdict(list)
    for iid in st["items"]:
        groups[by_id[iid]["date"][:7]].append(by_id[iid])
    tl = []
    for month in sorted(groups, reverse=True):
        try:
            y, m = month.split("-")
            mlabel = f"{MONTHS[int(m) - 1].capitalize()} de {y}"
        except Exception:
            mlabel = "Sin fecha"
        rows = []
        for it in groups[month]:
            qs = ctx["item_quotes"][it["id"]][pid]
            secs = sum(t["end"] - t["start"] for t in it["turns"] if t["person"] == pid)
            pick = [q for q in qs if len(q[2]) >= 80][:3] or qs[:3]
            quotes = "".join(
                f'<li><blockquote>{esc(q[2])}</blockquote><p class="qmeta">{src_link(it, q[0], ("≈ " if q[1] else "") + "min " + clock(q[0]))} · '
                f'<a href="../a/{esc(it["id"])}.html#t-{q[3]}">en la transcripción</a></p></li>' for q in pick)
            more = f'<p class="more-q">{len(qs)} fragmentos en total. <a href="../a/{esc(it["id"])}.html">Leer la transcripción completa</a>.</p>'
            rows.append(f"""<li class="tl-item">
  <p class="tl-date">{date_es(it["date"])}</p>
  <div>
    <h3><a href="../a/{esc(it["id"])}.html">{esc(it["title"])}</a></h3>
    <p class="meta">{esc(it["outlet"])} · {esc(KIND_ES.get(it["kind"], it["kind"]))} · habla {dur_es(secs)}</p>
    <ul class="quotes">{quotes}</ul>{more}
  </div>
</li>""")
        tl.append(f'<h3 class="month">{esc(mlabel)}</h3><ol class="timeline">{"".join(rows)}</ol>')
    # items that were fetched for this person but where the voice was not identified
    pending = [it for it in items if it["id"] not in st["items"] and it["expected"]
               and sort_key_name(it["expected"]) == sort_key_name(p["name"])]
    pend = ""
    if pending:
        li = "".join(f'<li><a href="../a/{esc(it["id"])}.html">{esc(it["title"])}</a><span class="meta">{item_meta_line(it)}</span></li>'
                     for it in pending)
        pend = f"""<section><h2 class="sect">Apariciones sin identificar</h2>
<p class="note">Apariciones recogidas por estar relacionadas con {esc(p["name"])} en las que su voz no se ha identificado. Su texto no se le atribuye ni aparece en la búsqueda.</p>
<ul class="list">{li}</ul></section>"""
    body = f"""
<p class="kicker">Candidato · {esc(p["role"])}</p>
<h1 class="ptitle">{esc(p["name"])}</h1>
<dl class="counts small">
  <div><dt>de voz identificada</dt><dd>{hours_es(st["secs"])}</dd></div>
  <div><dt>{"aparición" if len(st["items"]) == 1 else "apariciones"}</dt><dd>{len(st["items"])}</dd></div>
  <div><dt>intervenciones</dt><dd>{num_es(st["sent"])}</dd></div>
</dl>
<p class="note">{esc(vp)}</p>
{search_form(root, person=pid, placeholder="Buscar en lo que dijo " + p["name"])}
<section><h2 class="sect">Apariciones</h2>
{"".join(tl) or '<p class="empty">Todavía no hay apariciones con su voz identificada.</p>'}
</section>
{pend}"""
    return page(root, p["name"], body, desc=f"Lo que ha dicho {p['name']} en público, con la fuente.")


def build_how(ctx, web):
    frag = (web / "como-funciona.html").read_text(encoding="utf-8")
    vps = sorted(ctx["voiceprints"])
    vp_names = ", ".join(esc(ctx["people"][v]["name"]) for v in vps if v in ctx["people"]) or "ninguna"
    contact = (f'<a href="mailto:{esc(CONTACT_EMAIL)}">{esc(CONTACT_EMAIL)}</a>' if CONTACT_EMAIL
               else "la dirección de correo para correcciones (se publicará aquí antes de abrir el archivo al público)")
    rep = {"{{N_ITEMS}}": num_es(len(ctx["items"])), "{{HOURS}}": hours_es(ctx["total_secs"]),
           "{{VOICEPRINTS}}": vp_names, "{{CONTACT}}": contact}
    for k, v in rep.items():
        frag = frag.replace(k, v)
    return page("", "Cómo funciona", frag, "como")


def build_game(ctx):
    body = f"""
<div class="game-page">
<p class="kicker">Juego diario · <span id="g-num">hoy</span></p>
<h1 class="ptitle">¿Quién lo dijo?</h1>
<p class="lede">Cinco frases dichas en público durante la precampaña. Elige quién dijo cada una. Las mismas frases para todos, cada día.</p>
<div id="game" class="game" aria-busy="true">
  <noscript><p class="g-msg">El juego necesita JavaScript.</p></noscript>
</div>
<p class="note g-honest">Frases transcritas automáticamente de apariciones públicas; escucha la fuente para comprobarlas. El resultado y la racha se guardan solo en este navegador.</p>
</div>
<script src="assets/juego.js?v={ASSET_V}" defer></script>"""
    return page("", "¿Quién lo dijo?", body, "juego", desc="Juego diario: 5 frases de los candidatos, ¿quién lo dijo?",
                body_attrs=f' data-share-url="{esc(SHARE_URL)}"')


ASSET_V = "0"
GENERATED = ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=str(ROOT / "data" / "items"))
    ap.add_argument("--people", default=str(ROOT / "config" / "people.json"))
    ap.add_argument("--voiceprints", default=str(ROOT / "voiceprints"))
    ap.add_argument("--out", default=str(ROOT / "site"))
    a = ap.parse_args()
    build(Path(a.items), Path(a.people), Path(a.out), Path(a.voiceprints))


if __name__ == "__main__":
    main()
