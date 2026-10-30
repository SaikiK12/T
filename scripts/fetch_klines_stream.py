"""Stream Binance USD-M kline archives into one parquet per symbol without keeping the zips (a disk-bounded build).

Same archive keys, checks and parser as `lab.data.build`: every monthly file (daily ones only after the last monthly
month), each checked against its published SHA-256 and parsed by `lab.data.parse`. Unlike `build`, the zips stay in
memory, rows outside [start, end] are dropped before anything is written, only the named columns are kept, and the
parquet is zstd-compressed. Writes <out>/<SYMBOL>.parquet and <out>/manifest.json, which lists every archive key with
its SHA-256 next to each file's rows, first and last bar and digest.

usage: python scripts/fetch_klines_stream.py --symbols BNBUSDT,XRPUSDT --interval 1m --start 2021-01-01 \
           --end 2026-09-30 --out data/klines_1m_tape
"""
import argparse
import hashlib
import io
import json
import sys
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

COLUMNS = ("t", "open", "high", "low", "close", "volume", "count", "taker_buy_volume")


def keys_between(keys, start, end):
    """Archive keys whose month (or day) falls inside [start, end], both 'YYYY-MM-DD'."""
    out = []
    for k in keys:
        m = data._DATE.search(k)
        first = m.group(1) + (m.group(2) or "-01")
        last = m.group(1) + (m.group(2) or "-31")
        if last >= start and first <= end:
            out.append(k)
    return out


def fetch_verified(key, get=data._get, published=data._published_sha256):
    """One archive file's bytes and SHA-256, checked against the published digest; None when the archive lacks it."""
    try:
        blob = get(f"{data.BASE}/{urllib.parse.quote(key)}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    digest = hashlib.sha256(blob).hexdigest()
    if digest != published(key):
        raise data.FetchError(f"{key}: SHA-256 mismatch")
    return blob, digest


def frame(blobs, start, end, columns=COLUMNS):
    """Parsed bars from archive blobs, open times in [start, end] only, one row per open time, sorted."""
    lo = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    hi = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp() * 1000)
    parts = [data.parse(io.BytesIO(b), "klines") for b in blobs]
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(data.KLINE_KEEP))
    df = df[(df["t"] >= lo) & (df["t"] < hi)]
    return df.drop_duplicates("t", keep="last").sort_values("t").reset_index(drop=True)[list(columns)]


def build_symbol(symbol, interval, start, end, out, workers=8, plan=data.plan_files, fetch=fetch_verified, log=print):
    keys = keys_between(plan(symbol, "klines", interval, end=end), start, end)
    with ThreadPoolExecutor(workers) as ex:
        got = list(ex.map(fetch, keys))
    archives = [{"key": k, "sha256": g[1]} for k, g in zip(keys, got) if g is not None]
    df = frame([g[0] for g in got if g is not None], start, end)
    if df.empty:
        log(f"{symbol}: no rows in {start}..{end}")
        return None
    path = Path(out) / f"{symbol}.parquet"
    df.to_parquet(path, index=False, compression="zstd")
    entry = {"rows": len(df), "first": int(df["t"].iloc[0]), "last": int(df["t"].iloc[-1]),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "archives": archives}
    log(f"{symbol}: {len(archives)} archives, {len(df)} bars, {path.stat().st_size / 1e6:.1f} MB")
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--symbols", required=True, help="comma separated")
    ap.add_argument("--interval", default="1m")
    ap.add_argument("--start", required=True, help="first day kept, YYYY-MM-DD")
    ap.add_argument("--end", default=data.END, help="last day kept, YYYY-MM-DD")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for s in a.symbols.split(","):
        entry = build_symbol(s, a.interval, a.start, a.end, out, a.workers)
        if entry:
            manifest[s] = entry
    body = {"kind": "klines", "interval": a.interval, "start": a.start, "end": a.end, "columns": list(COLUMNS),
            "source": f"{data.BASE} USD-M klines (public archive, published SHA-256 checked per file)",
            "symbols": manifest}
    body["sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(body, indent=1, sort_keys=True) + "\n")
    print(f"{len(manifest)} symbols written to {out}, manifest sha {body['sha256'][:12]}")


if __name__ == "__main__":
    main()
