"""Shared DeepSeek client for the analysis layer, with a hard spending cap.

Every call adds its token cost to data/llm_spend.json; once the total passes CAP_USD, ask()
raises BudgetExceeded and the scripts stop. Prices are deliberately pessimistic, so the real
bill stays below the cap.

External speech always goes in the user message as JSON data; the system prompt tells the model
to treat it only as text to analyse. Answers are parsed as JSON and validated by the caller.
"""
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEND = ROOT / "data" / "llm_spend.json"
MODEL = "deepseek-flash"
CAP_USD = float(os.environ.get("LLM_CAP_USD", "9.0"))   # Gerrit: 10 EUR cap for steps 1-3
PRICE_IN, PRICE_OUT = 0.30 / 1e6, 1.20 / 1e6               # USD per token, pessimistic

_lock = threading.Lock()


class BudgetExceeded(Exception):
    pass


def spent():
    with _lock:
        try:
            return json.loads(SPEND.read_text())["usd"]
        except (FileNotFoundError, ValueError, KeyError):
            return 0.0


def _add(usd, tin, tout):
    with _lock:
        try:
            d = json.loads(SPEND.read_text())
        except (FileNotFoundError, ValueError):
            d = {"usd": 0.0, "in": 0, "out": 0, "calls": 0}
        d["usd"] += usd; d["in"] += tin; d["out"] += tout; d["calls"] += 1
        tmp = SPEND.with_suffix(".tmp")
        tmp.write_text(json.dumps(d))
        tmp.replace(SPEND)   # atomic, so a reader never sees a half-written file
        return d["usd"]


def ask(system, data, max_tokens=4000):
    """Send `data` (any JSON-able object) as the user message; return the parsed JSON answer or None."""
    if spent() >= CAP_USD:
        raise BudgetExceeded(f"spent {spent():.2f} >= cap {CAP_USD}")
    body = {"model": MODEL, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(data, ensure_ascii=False)}]}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                                          "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=180))
            u = r.get("usage", {})
            _add(u.get("prompt_tokens", 0) * PRICE_IN + u.get("completion_tokens", 0) * PRICE_OUT,
                 u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
            txt = r["choices"][0]["message"]["content"]
            return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        except Exception as e:
            print(f"llm call failed ({e.__class__.__name__}: {str(e)[:100]})", file=sys.stderr)
            time.sleep(4 * (attempt + 1))
    return None
