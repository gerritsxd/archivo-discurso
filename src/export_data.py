"""Public data dump: the whole database, unfiltered, for anyone to download and check.

Runs on the VPS after the analysis passes. Writes to OUT (served at /discurso/datos/):
  archivo.sqlite.gz    every table: items, speakers, every turn (journalists and unidentified
                       speakers included), game quotes, claims, attack targets, contradictions,
                       attribution checks, tone. Today's and future game answers are removed.
  items.tar.gz         one JSON per appearance (the pipeline's own output)
  claims.csv           the statements table as CSV, with source links
  review/              the human review files (rejected contradictions, attribution review)
  LEEME.txt            what each table and column means
The dump is built from a copy (sqlite backup API), so the live database is never exposed or locked.

    python3 -I src/export_data.py [--out /var/www/gerritsxd/discurso-datos]
"""
import argparse
import csv
import gzip
import json
import shutil
import sqlite3
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api import source_link  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "archivo.db"

LEEME = """Archivo del discurso político — datos completos
================================================
Fuente: https://gerritsxd.com/discurso/  ·  Código: https://github.com/gerritsxd/archivo-discurso
Licencia de los datos: CC BY 4.0 (cita «Archivo del discurso político»). Generado: {when}.

Todo es automático y sin revisión humana salvo donde se indica. Las transcripciones salen de
Whisper large-v3; quién habla, de pyannote + huellas de voz; el análisis, de DeepSeek.
Se publican TODAS las intervenciones, también las de periodistas y hablantes sin identificar.

archivo.sqlite.gz (SQLite 3; descomprimir y abrir con cualquier cliente SQLite)
  items        una fila por aparición: id, fecha, medio, título, url, tipo, duración, json completo
  speakers     cada hablante de cada aparición: persona asignada (o vacío), decisión de la huella
               de voz (match / unknown / ambiguous / too_short) y su similitud
  turns        cada intervención: hablante, persona (solo si es candidato identificado), texto,
               inicio y fin en segundos, marks = [[posición del carácter, segundo], ...] para
               enlazar cualquier frase al segundo exacto
  quotes       frases candidatas del juego diario, con su puntuación de contenido (1-5)
  daily        frases del juego de días pasados
  claims       afirmaciones de candidatos: tipo (promesa, dato, ataque, postura), tema, objetivo,
               insulto (0/1) y palabras despectivas, resumen, cita literal (comprobada palabra por
               palabra contra la transcripción), segundo
  claim_targets  destinatarios normalizados de cada ataque (target) y su grupo (grp)
  contradictions posibles contradicciones publicadas (un par por asunto); las rechazadas por
               revisión humana están en review/contradictions_review.json
  attribution_checks  aviso automático de si el contenido encaja con el hablante (ok / dudoso)
  tone         tono de cada fragmento de ~2 min (-2..2), emociones, % dedicado a rivales

claims.csv   la tabla claims con fecha, medio y enlace a la fuente en el segundo de la cita
items.tar.gz un JSON por aparición, tal como lo produce la cadena (incluye todas las intervenciones)
review/      revisiones humanas: contradicciones rechazadas y la muestra de atribución revisada
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/var/www/gerritsxd/discurso-datos")
    out = Path(ap.parse_args().out)
    tmp = out.with_name(out.name + ".new")
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "review").mkdir(parents=True)

    copy = tmp / "archivo.sqlite"
    src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    dst = sqlite3.connect(copy)
    src.backup(dst)
    src.close()
    today = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    dst.execute("DELETE FROM daily WHERE date >= ?", (today,))   # don't give away today's game
    dst.commit()

    with open(tmp / "claims.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "fecha", "candidato", "tipo", "tema", "objetivo", "insulto", "palabras_despectivas",
                    "resumen", "cita", "segundo", "medio", "titulo", "enlace", "aparicion"])
        cols = [r[1] for r in dst.execute("PRAGMA table_info(claims)")]
        iw = "c.insult_words" if "insult_words" in cols else "''"
        for r in dst.execute(f"""SELECT c.id, i.date, c.person, c.type, c.topic, c.target, c.insult, {iw}, c.summary,
                c.quote, c.start, i.outlet, i.title, i.url, c.item_id FROM claims c JOIN items i ON i.id = c.item_id
                ORDER BY i.date, c.item_id, c.start"""):
            w.writerow(list(r[:13]) + [source_link(r[13], r[10]), r[14]])
    dst.execute("VACUUM")
    dst.close()
    with open(copy, "rb") as fi, gzip.open(str(copy) + ".gz", "wb", compresslevel=9) as fo:
        shutil.copyfileobj(fi, fo)
    copy.unlink()

    with tarfile.open(tmp / "items.tar.gz", "w:gz") as t:
        excl = ROOT / "config" / "exclude.txt"
        skip = {l.split("#")[0].strip() for l in excl.read_text(encoding="utf-8").splitlines()} if excl.exists() else set()
        for p in sorted((ROOT / "data" / "items").glob("*.json")):
            if p.stem not in skip:   # duplicates and wrong fetches stay out of the dump too
                t.add(p, arcname=f"items/{p.name}")
    for name in ("config/contradictions_review.json", "eval/attribution_review.jsonl", "eval/attribution_sample.jsonl",
                 "eval/ATTRIBUTION.md"):
        p = ROOT / name
        if p.exists():
            shutil.copy(p, tmp / "review" / p.name)
    (tmp / "LEEME.txt").write_text(LEEME.format(when=datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M")),
                                   encoding="utf-8")
    sizes = {p.name: p.stat().st_size for p in tmp.iterdir() if p.is_file()}
    (tmp / "index.json").write_text(json.dumps({"generated": today, "files": sizes}, indent=1), encoding="utf-8")
    old = out.with_name(out.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    if out.exists():
        out.rename(old)
    tmp.rename(out)
    shutil.rmtree(old, ignore_errors=True)
    print("data dump:", {k: f"{v / 1e6:.1f} MB" for k, v in sizes.items()})


if __name__ == "__main__":
    main()
