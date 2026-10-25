"""Record the audio of a live stream (open HLS / icecast) for N minutes into data/raw/<id>/.

Writes audio.aac (original codec, no re-encode), audio.wav (16 kHz mono, what process.py reads)
and meta.json in the shape fetch.py writes. If the stream drops, ffmpeg is restarted until the
deadline; the parts are concatenated (ADTS AAC can be joined with a plain byte copy).
Only for openly accessible streams: no DRM, geo-block, login or bot-check circumvention.
Never YouTube. Does not use the GPU. Run process.py afterwards (see m3/DEBATE_RECORDER.md).

Usage:
    python src\record_live.py URL --minutes 180 --id 2026-11-16-debate-sanchez-feijoo \
        --title "Debate cara a cara Sanchez-Feijoo" --outlet "RTVE La 1 (simulcast)" \
        [--person "Pedro Sanchez; Alberto Nunez Feijoo"] [--kind debate] [--start "2026-11-16 21:50"] [--raw-dir DIR]
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--minutes", type=float, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--outlet", default="")
    ap.add_argument("--person", default="")
    ap.add_argument("--kind", default="debate")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--language", default="es")
    ap.add_argument("--start", help="local 'YYYY-MM-DD HH:MM': wait until then before recording")
    ap.add_argument("--audio-map", default="0:a:0", help="ffmpeg -map for the audio track (HLS: first = Castellano)")
    ap.add_argument("--raw-dir", default=str(ROOT / "data" / "raw"))
    a = ap.parse_args()

    d = Path(a.raw_dir) / a.id
    d.mkdir(parents=True, exist_ok=True)
    if (d / "audio.wav").exists():
        sys.exit(f"{d}/audio.wav exists; refusing to overwrite")
    if a.start:
        wait = (datetime.strptime(a.start, "%Y-%m-%d %H:%M") - datetime.now()).total_seconds()
        if wait > 0:
            print(f"waiting {wait/60:.1f} min until {a.start}", flush=True)
            time.sleep(wait)

    ff = ffmpeg()
    t0 = time.time()
    deadline = t0 + a.minutes * 60
    parts, fails = [], 0
    while time.time() < deadline - 2 and fails < 30:
        part = d / f"part{len(parts):03d}.aac"
        left = deadline - time.time()
        cmd = [ff, "-hide_banner", "-loglevel", "warning", "-y",
               "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10",
               "-i", a.url, "-t", f"{left:.0f}", "-vn", "-map", a.audio_map, "-c:a", "copy", str(part)]
        print(f"{datetime.now():%H:%M:%S} recording part {len(parts)} ({left/60:.1f} min left)", flush=True)
        r = subprocess.run(cmd)
        if part.exists() and part.stat().st_size > 10_000:
            parts.append(part)
            fails = 0 if r.returncode == 0 else fails
        else:
            fails += 1
        if time.time() < deadline - 2:
            time.sleep(5)  # stream dropped: pause, retry
    if not parts:
        sys.exit("nothing recorded (stream unreachable, geo-blocked or protected?)")

    out = d / "audio.aac"
    with open(out, "wb") as o:
        for p in parts:
            with open(p, "rb") as f:
                shutil.copyfileobj(f, o)
            p.unlink()
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", str(out), "-ac", "1", "-ar", "16000", str(d / "audio.wav")], check=True)
    dur = time.time() - t0
    meta = {
        "date": a.date, "person": a.person, "kind": a.kind, "outlet": a.outlet, "title": a.title,
        "url": a.url, "tier": "1", "duration_min": f"{dur/60:.1f}", "has_text": "no",
        "notes": "live recording (record_live.py)", "file": "audio",
        "id": a.id, "fetch_kind": "live", "language": a.language, "source_file": out.name,
        "sha256": sha256(out), "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok {a.id}: {dur/60:.1f} min, {out.stat().st_size/dur*8/1000:.0f} kb/s, {len(parts)} part(s)")


if __name__ == "__main__":
    main()
