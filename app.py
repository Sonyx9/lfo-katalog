#!/usr/bin/env python3
"""Flask varianta katalogu: servíruje index.html a feed převádí živě (s cache) na JSON.

Spuštění:  pip install -r requirements.txt && python app.py
Feed se stahuje max. jednou za FEED_TTL sekund (výchozí 30 min), jinak se vrací z paměti.
"""
import json, os, threading, time
from flask import Flask, Response, send_from_directory, jsonify

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import build_feed  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent
FEED_TTL = int(os.environ.get("FEED_TTL", "1800"))
app = Flask(__name__, static_folder=None)

_cache = {"json": None, "at": 0.0}
_lock = threading.Lock()


def get_products_json() -> str:
    now = time.time()
    if _cache["json"] and now - _cache["at"] < FEED_TTL:
        return _cache["json"]
    with _lock:
        if _cache["json"] and time.time() - _cache["at"] < FEED_TTL:
            return _cache["json"]
        try:
            build_feed.main()  # zapíše data/products.json
            _cache["json"] = (BASE / "data" / "products.json").read_text(encoding="utf-8")
            _cache["at"] = time.time()
        except Exception as e:  # feed nedostupný -> použij poslední soubor na disku
            app.logger.warning("Feed se nepodařilo stáhnout: %s", e)
            if not _cache["json"]:
                _cache["json"] = (BASE / "data" / "products.json").read_text(encoding="utf-8")
        return _cache["json"]


@app.get("/")
def index():
    return send_from_directory(BASE, "index.html")


@app.get("/data/products.json")
def products():
    return Response(get_products_json(), mimetype="application/json",
                    headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/refresh")
def refresh():
    _cache["at"] = 0.0
    get_products_json()
    return jsonify(ok=True, count=json.loads(_cache["json"])["count"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
