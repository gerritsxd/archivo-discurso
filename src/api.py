"""Read-only JSON API over data/archivo.db, for the website and the daily game.

    python3 src/api.py [--port 8431] [--db data/archivo.db]

Served behind nginx at https://gerritsxd.com/discurso/api/ . Standard library only.

GET  /api/stats
GET  /api/search?q=...&person=feijoo&from=2026-10-01&to=2026-10-31&limit=20&offset=0
GET  /api/item/<id>
GET  /api/daily[?date=YYYY-MM-DD]       today's 5 quotes (no answers)
POST /api/guess {"date": "...", "n": 0, "guess": "abascal"}   -> answer + source
POST /api/ask {"q": "..."}             answer from the archive's quotes only (DeepSeek, daily cap; src/ask.py)
GET  /api/claims?person=&type=promesa|dato|ataque|postura&topic=&insult=1&target=&q=&limit=&offset=
GET  /api/contradictions[?person=]      possible contradictions (both quotes + sources)
GET  /api/analysis                      counts per candidate: types, topics, attack targets, insults
GET  /api/attacks                       who attacks whom: counts per candidate x target group
GET  /api/tone                          tone per candidate (-2..2, weighted by seconds), emotions, share on rivals
"""
import argparse
import json
import os
import sys
import random
import re
import sqlite3
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))  # -I leaves the script dir off sys.path
from marks import time_at  # noqa: E402
MADRID = ZoneInfo("Europe/Madrid")
ROUNDS = 5
LAUNCH = "2026-10-25"  # puzzle no. 1
DB_PATH = ROOT / "data" / "archivo.db"
LOCK = threading.Lock()  # daily picks are written once; serialise that write


FOLD = str.maketrans("áéíóúüàèìòùïçñÁÉÍÓÚÜÀÈÌÒÙÏÇÑ", "aeiouuaeiouicnaeiouuaeiouicn")


def fold(s):
    """Lower-case without accents, same length as the input (so positions map back)."""
    return s.translate(FOLD).lower()


def people():
    return json.loads((ROOT / "config" / "people.json").read_text(encoding="utf-8"))


def connect(ro=False):
    """Read-only unless the request must write (only the daily game's picks are ever written)."""
    db = sqlite3.connect(f"file:{DB_PATH}?mode={'ro' if ro else 'rw'}", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def source_link(url, start):
    """Link to the original at the right moment, where the platform supports it."""
    s = int(start or 0)
    if not url:
        return None
    if "youtube.com/watch" in url:
        return f"{url}&t={s}s"
    if "youtu.be/" in url:
        return f"{url}?t={s}"
    if re.search(r"\.(mp3|m4a|aac|ogg)(\?|$)", url) or "/play.mp3" in url:
        return f"{url.split('#')[0]}#t={s}"
    return url  # e.g. RTVE Play: the page shows the minute separately


def candidates():
    return sorted(({"id": k, "name": v["name"], "role": v.get("role", "")}
                   for k, v in people().items() if v.get("kind") == "candidate"),
                  key=lambda c: c["name"].split()[-1])  # alphabetical by surname: no party order


def today():
    return datetime.now(MADRID).date().isoformat()


def daily_rows(db, date):
    rows = db.execute("SELECT * FROM daily WHERE date=? ORDER BY n", (date,)).fetchall()
    if rows:
        return rows
    with LOCK:
        rows = db.execute("SELECT * FROM daily WHERE date=? ORDER BY n", (date,)).fetchall()
        if rows:
            return rows
        used = {r[0] for r in db.execute("SELECT quote_id FROM daily")}
        pool = {}
        # only sentences rated as having content (score_quotes.py); 3s only if nothing better
        # per person, only their best-rated tier (5 if they have unused 5s, else 4, else 3)
        for q in db.execute("SELECT id, person, text, item_id, start, score FROM quotes WHERE score >= 3"):
            if q["id"] not in used:
                pool.setdefault(q["person"], []).append(q)
        for p in pool:
            best = max(q["score"] for q in pool[p])
            pool[p] = [q for q in pool[p] if q["score"] == best]
        rng = random.Random(f"quienlodijo-{date}")
        persons = sorted(pool)
        rng.shuffle(persons)
        # 5 different people when possible; otherwise fill from whoever has quotes left
        order = persons[:ROUNDS]
        while len(order) < ROUNDS and persons:
            order.append(rng.choice(persons))
        picks = []
        for p in order:
            if not pool.get(p):
                continue
            q = pool[p].pop(rng.randrange(len(pool[p])))
            picks.append(q)
        for n, q in enumerate(picks):
            db.execute("INSERT INTO daily VALUES (?,?,?,?,?,?,?)",
                       (date, n, q["id"], q["person"], q["text"], q["item_id"], q["start"]))
        db.commit()
        return db.execute("SELECT * FROM daily WHERE date=? ORDER BY n", (date,)).fetchall()


class Handler(BaseHTTPRequestHandler):
    server_version = "archivo-discurso"

    def send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if code != 200 or "guess" in self.path else "public, max-age=60")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # no IPs in logs
        pass

    def do_GET(self):
        u = urlparse(self.path)
        path = re.sub(r"^/discurso", "", u.path).rstrip("/")
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            with connect(ro=path != "/api/daily") as db:
                if path == "/api/stats":
                    return self.send(self.stats(db))
                if path == "/api/search":
                    return self.send(self.search(db, q))
                if path.startswith("/api/item/"):
                    row = db.execute("SELECT json FROM items WHERE id=?", (path.split("/")[-1],)).fetchone()
                    return self.send(json.loads(row["json"]) if row else {"error": "not found"}, 200 if row else 404)
                if path == "/api/claims":
                    return self.send(self.claims(db, q))
                if path == "/api/contradictions":
                    return self.send(self.contradictions(db, q))
                if path == "/api/attacks":
                    return self.send(self.attacks(db))
                if path == "/api/tone":
                    return self.send(self.tone(db))
                if path == "/api/analysis":
                    return self.send(self.analysis(db))
                if path == "/api/daily":
                    return self.send(self.daily(db, q.get("date") or today()))
        except sqlite3.Error as e:
            return self.send({"error": "database", "detail": str(e)[:200]}, 503)
        self.send({"error": "not found"}, 404)

    def do_POST(self):
        path = re.sub(r"^/discurso", "", urlparse(self.path).path).rstrip("/")
        if path == "/api/ask":
            return self.ask()
        if path != "/api/guess":
            return self.send({"error": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
            date, rnd, guess = str(body["date"]), int(body["n"]), str(body["guess"])
        except (ValueError, KeyError, json.JSONDecodeError):
            return self.send({"error": "bad request"}, 400)
        if date > today():
            return self.send({"error": "future"}, 400)
        with connect(ro=True) as db:
            row = db.execute("SELECT d.*, i.outlet, i.title, i.url, i.date AS item_date FROM daily d "
                             "JOIN items i ON i.id = d.item_id WHERE d.date=? AND d.n=?", (date, rnd)).fetchone()
        if not row:
            return self.send({"error": "not found"}, 404)
        ppl = people()
        p = ppl.get(row["person"], {})
        self.send({
            "correct": guess == row["person"],
            "answer": {"id": row["person"], "name": p.get("name"), "role": p.get("role")},
            "source": {"item_id": row["item_id"], "outlet": row["outlet"], "title": row["title"],
                       "date": row["item_date"], "start": row["start"],
                       "link": source_link(row["url"], row["start"])},
        })

    def ask(self):
        if not os.environ.get("DEEPSEEK_API_KEY"):
            return self.send({"error": "Las preguntas no están disponibles ahora mismo."}, 503)
        try:
            n = int(self.headers.get("Content-Length", 0))
            q = str(json.loads(self.rfile.read(min(n, 4096)) or b"{}")["q"])
        except (ValueError, KeyError, json.JSONDecodeError):
            return self.send({"error": "bad request"}, 400)
        import ask  # imported lazily: the rest of the API works without a key
        ppl = {k: v for k, v in people().items() if v.get("kind") == "candidate"}
        with connect(ro=True) as db:
            res, code = ask.answer(db, q, ppl, source_link)
        self.send(res, code)

    def stats(self, db):
        per = {}
        for r in db.execute("SELECT person, COUNT(DISTINCT item_id) items, SUM(end-start) secs, COUNT(*) turns "
                            "FROM turns WHERE person IS NOT NULL GROUP BY person"):
            per[r["person"]] = {"items": r["items"], "minutes": round((r["secs"] or 0) / 60, 1), "turns": r["turns"]}
        tot = db.execute("SELECT COUNT(*) n, SUM(duration_s) s FROM items").fetchone()
        built = db.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        return {"items": tot["n"], "hours": round((tot["s"] or 0) / 3600, 1),
                "quotes": db.execute("SELECT COUNT(*) FROM turns WHERE person IS NOT NULL").fetchone()[0],
                "per_person": per, "candidates": candidates(), "updated": built["value"] if built else None}

    CLAIM_SQL = ("SELECT c.*, i.date, i.outlet, i.title, i.url FROM claims c JOIN items i ON i.id = c.item_id")

    def claim_json(self, r):
        return {"id": r["id"], "item_id": r["item_id"], "person": r["person"], "type": r["type"],
                "topic": r["topic"], "target": r["target"], "insult": bool(r["insult"]),
                "insult_words": r["insult_words"] if "insult_words" in r.keys() else "", "summary": r["summary"],
                "quote": r["quote"], "entities": json.loads(r["entities"] or "[]"), "date": r["date"],
                "outlet": r["outlet"], "title": r["title"], "start": r["start"],
                "link": source_link(r["url"], r["start"])}

    def claims(self, db, q):
        limit = max(1, min(int(q.get("limit", 50)), 200))
        offset = max(0, int(q.get("offset", 0)))
        where, args = ["1=1"], []
        for f, col in (("person", "c.person"), ("type", "c.type"), ("topic", "c.topic")):
            if q.get(f):
                where.append(f"{col} = ?"); args.append(q[f])
        if q.get("insult") == "1":
            where.append("c.insult = 1")
        if q.get("target"):
            where.append("c.target LIKE ?"); args.append(f"%{q['target']}%")
        if q.get("grp"):
            where.append("c.id IN (SELECT claim_id FROM claim_targets WHERE grp = ?)"); args.append(q["grp"])
        if q.get("q"):
            where.append("(c.quote LIKE ? OR c.summary LIKE ?)"); args += [f"%{q['q']}%"] * 2
        sql = self.CLAIM_SQL + " WHERE " + " AND ".join(where)
        total = db.execute(f"SELECT COUNT(*) FROM ({sql})", args).fetchone()[0]
        rows = db.execute(sql + " ORDER BY i.date DESC, c.start LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        return {"total": total, "results": [self.claim_json(r) for r in rows]}

    def contradictions(self, db, q):
        sql, args = "SELECT * FROM contradictions", []
        if q.get("person"):
            sql += " WHERE person = ?"; args.append(q["person"])
        out = []
        for x in db.execute(sql + " ORDER BY person, topic", args).fetchall():
            a = db.execute(self.CLAIM_SQL + " WHERE c.id=?", (x["claim_a"],)).fetchone()
            b = db.execute(self.CLAIM_SQL + " WHERE c.id=?", (x["claim_b"],)).fetchone()
            if a and b:
                out.append({"person": x["person"], "topic": x["topic"], "kind": x["kind"], "explanation": x["explanation"],
                            "a": self.claim_json(a), "b": self.claim_json(b)})
        return {"total": len(out), "results": out}

    def attacks(self, db):
        cells, totals, detail = {}, {}, {}
        for r in db.execute("SELECT c.person, ct.grp, COUNT(DISTINCT c.id) n FROM claim_targets ct "
                            "JOIN claims c ON c.id = ct.claim_id GROUP BY c.person, ct.grp"):
            cells.setdefault(r["person"], {})[r["grp"]] = r["n"]
        for r in db.execute("SELECT person, COUNT(*) n FROM claims WHERE type='ataque' GROUP BY person"):
            totals[r["person"]] = r["n"]
        for r in db.execute("SELECT c.person, ct.grp, ct.target, COUNT(DISTINCT c.id) n FROM claim_targets ct "
                            "JOIN claims c ON c.id = ct.claim_id GROUP BY c.person, ct.grp, ct.target ORDER BY n DESC"):
            detail.setdefault(r["person"], {}).setdefault(r["grp"], {})[r["target"]] = r["n"]
        return {"cells": cells, "attacks": totals, "detail": detail, "candidates": candidates()}

    def tone(self, db):
        per = {}
        for r in db.execute("SELECT person, SUM(seconds) s, SUM(tone*seconds)/SUM(seconds) t, "
                            "SUM(rivals*seconds)/SUM(seconds) rv, COUNT(*) n FROM tone GROUP BY person"):
            per[r["person"]] = {"seconds": round(r["s"]), "tone": round(r["t"], 2), "rivals": round(r["rv"]),
                                "chunks": r["n"], "emotions": {}, "by_date": {}}
        for r in db.execute("SELECT person, emotions, seconds FROM tone"):
            e = per[r["person"]]["emotions"]
            for x in json.loads(r["emotions"]):
                e[x] = e.get(x, 0) + r["seconds"]
        for p in per.values():
            tot = sum(p["emotions"].values()) or 1
            p["emotions"] = dict(sorted(((k, round(100 * v / tot)) for k, v in p["emotions"].items()),
                                        key=lambda kv: -kv[1]))
        for r in db.execute("SELECT person, date, SUM(tone*seconds)/SUM(seconds) t, SUM(seconds) s FROM tone "
                            "GROUP BY person, date ORDER BY date"):
            per[r["person"]]["by_date"][r["date"]] = {"tone": round(r["t"], 2), "seconds": round(r["s"])}
        return {"per_person": per, "candidates": candidates()}

    def analysis(self, db):
        per = {}
        for r in db.execute("SELECT person, type, COUNT(*) n FROM claims GROUP BY person, type"):
            per.setdefault(r["person"], {"types": {}, "topics": {}, "targets": {}, "insults": 0})["types"][r["type"]] = r["n"]
        for r in db.execute("SELECT person, topic, COUNT(*) n FROM claims GROUP BY person, topic"):
            per[r["person"]]["topics"][r["topic"]] = r["n"]
        for r in db.execute("SELECT person, target, COUNT(*) n FROM claims WHERE type='ataque' AND target != '' "
                            "GROUP BY person, target ORDER BY n DESC"):
            t = per[r["person"]]["targets"]
            if len(t) < 8:
                t[r["target"]] = r["n"]
        for r in db.execute("SELECT person, COUNT(*) n FROM claims WHERE insult=1 GROUP BY person"):
            per[r["person"]]["insults"] = r["n"]
        n_contra = db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
        return {"per_person": per, "contradictions": n_contra, "candidates": candidates()}

    def search(self, db, q):
        text = (q.get("q") or "").strip()[:200]
        limit = max(1, min(int(q.get("limit", 20)), 50))
        offset = max(0, int(q.get("offset", 0)))
        where, args = ([] if q.get("all") == "1" else ["t.person IS NOT NULL"]), []
        if text:
            # quote every term so user input can't use FTS operators; "…" keeps phrases
            phrases = re.findall(r'"([^"]+)"', text)
            rest = re.sub(r'"[^"]+"', " ", text)
            terms = ['"' + p.replace('"', "") + '"' for p in phrases] + \
                    ['"' + w.replace('"', "") + '"' for w in rest.split() if w]
            terms = terms[:10]   # bounded query cost
            where.append("t.id IN (SELECT rowid FROM turns_fts WHERE turns_fts MATCH ?)")
            args.append(" ".join(terms))
        if q.get("person"):
            where.append("t.person = ?"); args.append(q["person"])
        if q.get("from"):
            where.append("i.date >= ?"); args.append(q["from"])
        if q.get("to"):
            where.append("i.date <= ?"); args.append(q["to"])
        sql = " FROM turns t JOIN items i ON i.id = t.item_id WHERE " + (" AND ".join(where) or "1=1")
        total = db.execute("SELECT COUNT(*)" + sql, args).fetchone()[0]
        hit = [p for p in re.findall(r'"([^"]+)"', text)] + re.sub(r'"[^"]+"', " ", text).split()
        rows = db.execute("SELECT t.*, i.date, i.outlet, i.title, i.url" + sql +
                          " ORDER BY i.date DESC, t.start LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        return {"total": total, "results": [{
            "item_id": r["item_id"], "person": r["person"], "name": r["name"], "date": r["date"],
            "outlet": r["outlet"], "title": r["title"], "start": self.hit_time(r, hit), "text": r["text"],
            "link": source_link(r["url"], self.hit_time(r, hit)), "context": self.before(db, r)} for r in rows]}

    @staticmethod
    def hit_time(r, terms):
        """Second at which the first searched word is said (word marks), else the turn start."""
        if not terms:
            return r["start"]
        folded = fold(r["text"])
        # the whole query first, then the longest words ("autónomos" before "que")
        pos = -1
        for t in [" ".join(terms)] + sorted(terms, key=len, reverse=True):
            pos = folded.find(fold(t))
            if pos >= 0:
                break
        if pos < 0:
            return r["start"]
        try:
            mk = json.loads(r["marks"] or "[]")
        except (IndexError, KeyError, ValueError):
            return r["start"]
        return max(0, time_at(mk, pos, r["start"]) - 1)

    def before(self, db, r):
        """The turn just before a quote (usually the interviewer's question), for context.
        Shown under that speaker's own label, never under the candidate's name."""
        rows = db.execute("SELECT name, person, text FROM turns WHERE item_id=? AND idx BETWEEN ? AND ? "
                          "ORDER BY idx DESC", (r["item_id"], r["idx"] - 3, r["idx"] - 1)).fetchall()
        # walk back over the other speaker's short fragments ("Pues ya está.") to a real question
        name, parts = None, []
        for p in rows:
            if p["person"] == r["person"] or (name and p["name"] != name):
                break
            name = p["name"]
            parts.insert(0, p["text"])
            if len(" ".join(parts).split()) >= 25:
                break
        text = " ".join(parts).strip()
        # < 10 words is usually a diarization slip inside the candidate's own speech
        # ("Ni ha habido tanto miedo en los"), not someone else talking
        if not text or not 10 <= len(text.split()) <= 250:
            return None
        # Only in a real dialogue (interview, press conference: the candidate answers several
        # times). In a rally the turn before is the previous speaker's speech, which would read
        # as a fake question.
        n = db.execute("SELECT COUNT(*) FROM turns WHERE item_id=? AND person=? AND length(text) > 60",
                       (r["item_id"], r["person"])).fetchone()[0]
        if n < 3:
            return None
        # keep the end: the question, without trailing "Gracias."
        text = re.sub(r"\s*(muchas\s+)?gracias[.!]?$", "", text, flags=re.I)
        q = text.rfind("?")
        if q >= 0 and len(text) - q < 120:
            text = text[:q + 1]
        starts = [m.end() for m in re.finditer(r"[.!?…]\s+", text[:max(0, len(text) - 1)])]
        keep = [s for s in starts if len(text) - s <= 320]
        text = text[keep[0]:] if keep else ("… " + text[-320:].split(" ", 1)[-1] if len(text) > 320 else text)
        return {"name": name, "text": text.strip()}

    def daily(self, db, date):
        if date > today() or date < LAUNCH:
            return {"error": "no puzzle for this date", "date": date}
        rows = daily_rows(db, date)
        number = (datetime.fromisoformat(date) - datetime.fromisoformat(LAUNCH)).days + 1
        return {"date": date, "number": number, "candidates": candidates(),
                "rounds": [{"n": r["n"], "text": r["text"]} for r in rows]}


def main():
    global DB_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8431)
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()
    DB_PATH = Path(args.db)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
