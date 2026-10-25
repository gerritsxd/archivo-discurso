"""Local dev server: serves site/ and forwards /api/ to the JSON API (src/api.py).

    py -3.13 -I web/dev_server.py [--port 8765] [--api http://127.0.0.1:8431] [--root site]

Mirrors production, where nginx serves the static site and proxies api/ under the
same sub-path. Development only; binds to 127.0.0.1. Standard library only.
"""
import argparse
import functools
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    api = "http://127.0.0.1:8431"

    def _is_api(self):
        return self.path.startswith("/api/") or self.path.startswith("/discurso/api/")

    def _proxy(self, method):
        body = None
        if method == "POST":
            n = min(int(self.headers.get("Content-Length") or 0), 64 * 1024)
            body = self.rfile.read(n)
        path = self.path[len("/discurso"):] if self.path.startswith("/discurso/") else self.path
        req = urllib.request.Request(self.api + path, data=body, method=method,
                                     headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                code, data, ctype = r.status, r.read(), r.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as e:
            code, data, ctype = e.code, e.read(), e.headers.get("Content-Type", "application/json")
        except (urllib.error.URLError, OSError):
            code, data, ctype = 502, b'{"error":"api unreachable"}', "application/json"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self._is_api():
            return self._proxy("GET")
        return super().do_GET()

    def do_POST(self):
        if self._is_api():
            return self._proxy("POST")
        self.send_error(405)

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--api", default="http://127.0.0.1:8431")
    ap.add_argument("--root", default=str(ROOT / "site"))
    a = ap.parse_args()
    Handler.api = a.api.rstrip("/")
    handler = functools.partial(Handler, directory=a.root)
    print(f"http://127.0.0.1:{a.port}/  (api -> {Handler.api})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), handler).serve_forever()


if __name__ == "__main__":
    main()
