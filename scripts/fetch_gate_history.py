"""Gate.io's public bulk archive (gateio-public-data on S3, no keys): hourly candles and settled funding for every USDT
perp, delisted ones included, from 2020-01 to the last complete month. Gate lists far more perps than Binance (1,049
live on 2026-10-20), so this is the lab's widest cross-section and a second venue's funding for every Binance coin.

Two steps, both resumable:
1. `fetch`: list each month's keys (S3 ListObjectsV2, paged) and download every file into data/gate_hist/raw/, checking
   each body's MD5 against the S3 ETag. A file already on disk with the right MD5 is skipped.
2. `build`: one parquet per contract and type, routed by the reserved-sample rules (docs/GATES.md):
   - `open/`: contracts whose base has a Binance perp in the archive (data/klines_1h, same name rule as R274's
     `binance_perp`), from 2021-01-01;
   - `reserved/`: everything else, i.e. 2020 rows of every contract and all rows of contracts with no Binance perp.
     Nothing in the lab may read `reserved/` except a frozen batch PREREG that declares RESERVED-GATE-READ.
   The build converts formats only; it computes no statistic.

Raw formats (checked against the live API on 2026-10-20): candlesticks_1h rows are `t,v,c,h,l,o` (t in seconds, v in
contracts); funding_applies rows are `t,r`. Parquet columns: candles t (ms), open, high, low, close, vol_contracts;
funding t (ms), rate. `contracts.csv` lists every contract seen, its route and, for live contracts, its quanto
multiplier (contracts x multiplier = base units). Data collection only.

usage: python scripts/fetch_gate_history.py fetch [--workers 16] [--end 2026-09]
       python scripts/fetch_gate_history.py build
"""
import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402
from scripts.squeeze_events import binance_perp  # noqa: E402  (the name rule that defines the MEXC-only reserve)

BUCKET = "https://gateio-public-data.s3.amazonaws.com"
API = "https://api.gateio.ws/api/v4/futures/usdt/contracts"
OUT = data.ROOT / "gate_hist"
TYPES = ("candlesticks_1h", "funding_applies")
FIRST_MONTH = "2020-01"
OPEN_FROM_MS = 1_609_459_200_000           # 2021-01-01: earlier rows are the reserved 2020 window
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=5):
    delay = 2.0
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lab/1"}), timeout=60) as r:
                return r.read()
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url}: {err}")


def months(first, last):
    return [p.strftime("%Y%m") for p in pd.period_range(first, last, freq="M")]


def listing(prefix):
    """Every (key, size, etag) under a prefix, following continuation tokens."""
    out, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        root = ET.fromstring(get(f"{BUCKET}/?{urllib.parse.urlencode(q)}"))
        for c in root.iter(f"{NS}Contents"):
            out.append((c.find(f"{NS}Key").text, int(c.find(f"{NS}Size").text), c.find(f"{NS}ETag").text.strip('"')))
        if root.findtext(f"{NS}IsTruncated") != "true":
            return out
        token = root.findtext(f"{NS}NextContinuationToken")


def md5_ok(body, etag):
    return "-" in etag or hashlib.md5(body).hexdigest() == etag      # multipart ETags are not MD5s


def fetch_one(item):
    key, size, etag = item
    path = OUT / "raw" / key.split("/", 1)[1]
    if path.exists() and md5_ok(path.read_bytes(), etag):
        return "skip"
    body = get(f"{BUCKET}/{urllib.parse.quote(key)}")
    if len(body) != size or not md5_ok(body, etag):
        raise RuntimeError(f"{key}: size or MD5 differs from the listing")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(body)
    tmp.replace(path)
    return "new"


def fetch(a):
    end = a.end or (pd.Timestamp.now(tz="UTC").to_period("M") - 1).strftime("%Y-%m")
    keys = []
    for m in months(FIRST_MONTH, end):
        for t in TYPES:
            keys += listing(f"futures_usdt/{t}/{m}/")
        log(f"listed {m}: {len(keys)} keys so far")
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    (OUT / "raw" / "listing.json").write_text(json.dumps(
        {"bucket": BUCKET, "listed_at": pd.Timestamp.now(tz="UTC").isoformat(), "end": end,
         "keys": [{"key": k, "size": s, "etag": e} for k, s, e in keys]}, indent=0))
    counts, done = {"new": 0, "skip": 0}, 0
    with ThreadPoolExecutor(a.workers) as ex:
        for status in ex.map(fetch_one, keys):
            counts[status] += 1
            done += 1
            if done % 2000 == 0:
                log(f"{done}/{len(keys)} {counts}")
    log(f"fetch done: {len(keys)} keys {counts}")
    try:
        (OUT / "raw" / "contracts_live.json").write_bytes(get(API))
    except RuntimeError as e:
        log(f"live contract list not saved: {e}")


def parse(path, kind):
    raw = gzip.decompress(path.read_bytes()).decode()
    if kind == "candlesticks_1h":
        df = pd.read_csv(io.StringIO(raw), header=None, names=["t", "vol_contracts", "close", "high", "low", "open"])
        df = df[["t", "open", "high", "low", "close", "vol_contracts"]]
    else:
        df = pd.read_csv(io.StringIO(raw), header=None, names=["t", "rate"])
    df["t"] = (df["t"].astype(float) * 1000).round().astype("int64")
    return df


def route(name, perps):
    """('open', binance perp) when the base has a Binance perp, else ('reserved', '')."""
    base = re.sub(r"_USDT$", "", name)
    hit = binance_perp(base, perps)
    return ("open", hit[0]) if hit else ("reserved", "")


def build(a):
    perps = {p.stem for p in (data.ROOT / "klines_1h").glob("*.parquet")}
    live = {}
    lj = OUT / "raw" / "contracts_live.json"
    if lj.exists():
        live = {c["name"]: c for c in json.loads(lj.read_text())}
    rows = {}
    for kind in TYPES:
        files = {}
        for p in sorted((OUT / "raw" / kind).glob("*/*.csv.gz")):
            files.setdefault(p.name.rsplit("-", 1)[0], []).append(p)
        for name, paths in files.items():
            df = pd.concat([parse(p, kind) for p in paths], ignore_index=True)
            df = df.drop_duplicates("t", keep="last").sort_values("t", ignore_index=True)
            dest, perp = route(name, perps)
            parts = {"reserved": df} if dest == "reserved" else {
                "open": df[df.t >= OPEN_FROM_MS], "reserved": df[df.t < OPEN_FROM_MS]}
            for where, part in parts.items():
                if len(part):
                    out = OUT / where / kind / f"{name}.parquet"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    part.to_parquet(out, index=False)
            r = rows.setdefault(name, {"name": name, "route": dest, "binance_perp": perp,
                                       "quanto_multiplier": live.get(name, {}).get("quanto_multiplier", ""),
                                       "live": name in live})
            r[f"{kind}_months"] = len(paths)
        log(f"built {kind}: {len(files)} contracts")
    pd.DataFrame(sorted(rows.values(), key=lambda r: r["name"])).to_csv(OUT / "contracts.csv", index=False)
    (OUT / "reserved" / "README.md").write_text(
        "Reserved sample (docs/GATES.md). Do not read: only a frozen batch PREREG declaring RESERVED-GATE-READ may.\n")
    n = pd.Series([r["route"] for r in rows.values()]).value_counts().to_dict()
    log(f"contracts: {len(rows)} {n}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--workers", type=int, default=16)
    f.add_argument("--end", help="last month, YYYY-MM (default: last complete month)")
    sub.add_parser("build")
    a = ap.parse_args()
    fetch(a) if a.cmd == "fetch" else build(a)


if __name__ == "__main__":
    main()
