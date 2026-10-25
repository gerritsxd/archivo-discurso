"""Build the archive database (SQLite + full-text search) from data/items/*.json.

    python3 src/build_db.py [--items data/items] [--db data/archivo.db]

Rebuilds into a temp file and swaps it in, so the API never reads a half-built database.
The daily game picks (table `daily`) are carried over from the old database, so a day's
puzzle never changes once someone has played it.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marks import time_at  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = """
CREATE TABLE items (
  id TEXT PRIMARY KEY, date TEXT, outlet TEXT, title TEXT, url TEXT, kind TEXT,
  language TEXT, duration_s REAL, processed_at TEXT, reviewed INTEGER, json TEXT
);
CREATE TABLE speakers (
  item_id TEXT, label TEXT, person TEXT, name TEXT, decision TEXT, reason TEXT, talk_s REAL,
  PRIMARY KEY (item_id, label)
);
CREATE TABLE turns (
  id INTEGER PRIMARY KEY, item_id TEXT, idx INTEGER, start REAL, end REAL,
  label TEXT, person TEXT, name TEXT, text TEXT, marks TEXT
);
CREATE INDEX turns_item ON turns(item_id, idx);
CREATE INDEX turns_person ON turns(person);
CREATE VIRTUAL TABLE turns_fts USING fts5(
  text, content='turns', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE quotes (
  id INTEGER PRIMARY KEY, item_id TEXT, turn_id INTEGER, person TEXT, start REAL,
  text TEXT, words INTEGER, score INTEGER
);
CREATE INDEX quotes_person ON quotes(person);
CREATE TABLE daily (date TEXT, n INTEGER, quote_id INTEGER, person TEXT, text TEXT,
  item_id TEXT, start REAL, PRIMARY KEY (date, n));
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""

SENT = re.compile(r"(?<=[.?!…])\s+")


def quote_candidates(turn, people):
    """Citable pieces of an identified candidate turn for the game: 1–3 whole sentences,
    15–45 words, that don't give the answer away (no own name or party)."""
    p = people.get(turn["person"], {})
    # own name or party gives the answer away ("Podemos" only as the party, not the verb:
    # case-sensitive, so "podemos" in the middle of a sentence stays allowed)
    names = [w for w in p.get("match", []) + [p.get("role", "")] if w]
    give_away = re.compile(r"(" + "|".join(map(re.escape, names)) + r")") if names else None
    sents = [s.strip() for s in SENT.split(turn["text"]) if s.strip()]
    offsets, pos = [], 0  # character offset of each sentence: its second comes from the word marks
    for s in sents:
        pos = turn["text"].find(s, pos)
        offsets.append(max(pos, 0))
        pos = max(pos, 0) + len(s)
    out, i = [], 0
    while i < len(sents):
        step = 1
        for span in (1, 2, 3):
            if i + span > len(sents):
                break
            chunk = " ".join(sents[i:i + span])
            n = len(chunk.split())
            if n > 60:
                break
            if n >= 12 and chunk[:1].isupper():
                if not (give_away and give_away.search(chunk)):
                    out.append((round(time_at(turn.get("marks"), offsets[i], turn["start"]), 1), chunk, n))
                step = span
                break
        i += step
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=str(ROOT / "data" / "items"))
    ap.add_argument("--db", default=str(ROOT / "data" / "archivo.db"))
    args = ap.parse_args()
    people = json.loads((ROOT / "config" / "people.json").read_text(encoding="utf-8"))

    tmp = args.db + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.executescript(SCHEMA)

    n_items = n_turns = n_quotes = 0
    for f in sorted(Path(args.items).glob("*.json")):
        it = json.loads(f.read_text(encoding="utf-8"))
        db.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            it["id"], it.get("date"), it.get("outlet"), it.get("title"), it.get("url"),
            it.get("kind"), it.get("language"), it.get("duration_s"),
            it.get("pipeline", {}).get("processed_at"), int(it.get("pipeline", {}).get("reviewed", False)),
            json.dumps(it, ensure_ascii=False)))
        matched = set()
        for lab, s in it.get("speakers", {}).items():
            db.execute("INSERT INTO speakers VALUES (?,?,?,?,?,?,?)", (
                it["id"], lab, s.get("person"), s.get("name"), s.get("decision"), s.get("reason"), s.get("talk_s")))
            if s.get("decision") == "match" and s.get("person") in people \
                    and people[s["person"]].get("kind") == "candidate":
                matched.add(lab)
        for idx, t in enumerate(it.get("turns", [])):
            cur = db.execute("INSERT INTO turns (item_id, idx, start, end, label, person, name, text, marks) "
                             "VALUES (?,?,?,?,?,?,?,?,?)", (
                                 it["id"], idx, t["start"], t["end"], t["label"],
                                 t.get("person") if t["label"] in matched else None, t.get("name"), t["text"],
                                 json.dumps(t.get("marks") or [])))
            n_turns += 1
            if t["label"] in matched:
                for start, text, words in quote_candidates(t, people):
                    db.execute("INSERT INTO quotes (item_id, turn_id, person, start, text, words) "
                               "VALUES (?,?,?,?,?,?)", (it["id"], cur.lastrowid, t["person"], start, text, words))
                    n_quotes += 1
        n_items += 1
    # every turn is indexed (interviewers and unidentified speakers too): the API searches candidates
    # by default and everything with ?all=1
    db.execute("INSERT INTO turns_fts(rowid, text) SELECT id, text FROM turns")

    # content scores from score_quotes.py (cached by text), so a rebuild keeps them
    cache_f = Path(args.db).parent / "quote_scores.json"
    if cache_f.exists():
        import hashlib
        cache = json.loads(cache_f.read_text(encoding="utf-8"))
        rows = db.execute("SELECT id, text FROM quotes").fetchall()
        db.executemany("UPDATE quotes SET score=? WHERE id=?", [
            (cache.get(hashlib.sha1(t.encode("utf-8")).hexdigest()[:16]), qid) for qid, t in rows])

    # keep the game days already played
    if os.path.exists(args.db):
        old = sqlite3.connect(args.db)
        try:
            rows = old.execute("SELECT date, n, quote_id, person, text, item_id, start FROM daily").fetchall()
            db.executemany("INSERT INTO daily VALUES (?,?,?,?,?,?,?)", rows)
        except sqlite3.Error:
            pass
        old.close()

    from datetime import datetime, timezone
    db.execute("INSERT INTO meta VALUES ('built_at', ?)", (datetime.now(timezone.utc).isoformat(timespec="seconds"),))
    db.commit()
    db.close()
    os.replace(tmp, args.db)
    print(f"{n_items} items, {n_turns} turns, {n_quotes} game quotes -> {args.db}")


if __name__ == "__main__":
    sys.exit(main())
