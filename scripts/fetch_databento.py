"""Bounded Databento historical pulls (CME Globex futures ticks) into data/databento/<name>/.

The owner's API key lives only in /root/.config/databento/env (chmod 600, outside the repo): never in a repo file, a log,
a manifest or an argument. Every pull first asks metadata.get_cost (free) and refuses when the price is above --max-usd, so
a typo in a date range cannot spend more than the cap. Output is CSV compressed with zstd, one file per request, and a
manifest row (request, price quoted, bytes, sha256, UTC fetch time) appended to <out>/manifest.csv. Paper research only;
this places no order.

usage:
  python scripts/fetch_databento.py cost --symbols CL.c.0 --schema mbp-1 --start 2026-10-28T14:25:00Z --end 2026-10-28T14:45:00Z
  python scripts/fetch_databento.py get  --symbols CL.c.0 --schema mbp-1 --start ... --end ... --out data/databento/eia_probe \
         [--max-usd 0.05]
"""
import argparse
import csv
import datetime as dt
import hashlib
import os
import sys
import threading
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = Path(os.environ.get("DATABENTO_ENV", "/root/.config/databento/env"))
BASE = "https://hist.databento.com/v0"
_LOCK = threading.Lock()
MANIFEST_COLS = ["file", "dataset", "symbols", "stype_in", "schema", "start", "end", "quoted_usd", "bytes", "sha256",
                 "fetched_utc"]


def read_key(path=KEY_FILE):
    """The key from the env file; a clear error (never the key) when it is missing."""
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith("DATABENTO_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return key
    except OSError:
        pass
    raise SystemExit(f"no DATABENTO_API_KEY in {path}")


def params(a):
    return {"dataset": a.dataset, "symbols": a.symbols, "stype_in": a.stype_in, "schema": a.schema, "start": a.start,
            "end": a.end}


def quote(p, key, session=requests):
    r = session.get(f"{BASE}/metadata.get_cost", params=p, auth=(key, ""), timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"get_cost failed: http {r.status_code} {r.text[:200]}")
    return float(r.text)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(p, key, out, max_usd, session=requests):
    """Quote, refuse above the cap, download to out, append the manifest. Returns (path, quoted_usd)."""
    usd = quote(p, key, session)
    if usd > max_usd:
        raise SystemExit(f"refused: quoted ${usd:.4f} is above --max-usd ${max_usd:.4f}")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    stem = "_".join([p["dataset"], p["symbols"].replace(",", "+"), p["schema"], p["start"], p["end"]]).replace(":", "")
    path = out / f"{stem}.csv.zst"
    if path.exists():
        raise SystemExit(f"{path} exists; nothing overwritten")
    body = dict(p, stype_out="instrument_id", encoding="csv", compression="zstd", map_symbols="true",
                pretty_px="true", pretty_ts="true")
    tmp = path.with_suffix(".tmp")
    with session.post(f"{BASE}/timeseries.get_range", data=body, auth=(key, ""), stream=True, timeout=300) as r:
        if r.status_code != 200:
            raise SystemExit(f"get_range failed: http {r.status_code} {r.text[:200]}")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.rename(path)
    with _LOCK:
        new = not (out / "manifest.csv").exists()
        with open(out / "manifest.csv", "a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(MANIFEST_COLS)
            w.writerow([path.name, p["dataset"], p["symbols"], p["stype_in"], p["schema"], p["start"], p["end"],
                        f"{usd:.6f}", path.stat().st_size, sha256(path),
                        dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")])
    return path, usd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("cost", "get"))
    ap.add_argument("--dataset", default="GLBX.MDP3")
    ap.add_argument("--symbols", required=True)
    ap.add_argument("--stype-in", dest="stype_in", default="continuous")
    ap.add_argument("--schema", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(ROOT / "data" / "databento" / "adhoc"))
    ap.add_argument("--max-usd", type=float, default=0.05)
    a = ap.parse_args(argv)
    key = read_key()
    p = params(a)
    if a.cmd == "cost":
        print(f"${quote(p, key):.6f}")
        return 0
    path, usd = fetch(p, key, a.out, a.max_usd)
    print(f"{path} {path.stat().st_size} bytes, quoted ${usd:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
