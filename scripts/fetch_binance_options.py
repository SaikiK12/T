"""Binance European options history from data.binance.vision (docs/AUCTION_AND_FLOW.md): the only free archive of
option positioning the lab has found, for gamma, delta, vanna and charm exposure (M300 and the owner's term list).

- EOHSummary: one row per option and hour with OHLC, volume, best bid and ask, implied vols, mark price, the greeks
  (delta, gamma, vega, theta) and open interest. Published for BTC, ETH, BNB, XRP and DOGE from 2023-05-18 to
  2023-10-23 only. One parquet per underlying in data/binance_options/eoh/, t = the hour's start in epoch ms. The row
  is a snapshot at the hour's end: lab.exposure's Black-76 greeks match the published ones best with T measured from
  t + 1 h (median relative error 0.06% on BTC, checked 2026-10-21), so a row is known at t + 1 h. The underlying
  price is openinterest_usdt / openinterest_contracts.
- BVOLIndex: Binance's BTC and ETH implied-volatility index, one value a second, from 2023-06-20 (to 2026-10-20 when
  fetched; 26 days missing). Kept as the last value of each minute in data/binance_options/bvol/.
Raw zips are cached under data/raw/ and checked against the published SHA-256 (lab.data.fetch, strict). Resumable;
a symbol whose parquet exists is skipped. Data collection only.

usage: python scripts/fetch_binance_options.py [--workers 8]
"""
import argparse
import io
import json
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "binance_options"
EOH = "data/option/daily/EOHSummary/"
BVOL = "data/option/daily/BVOLIndex/"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        return pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))


def eoh_frame(df):
    """Hourly option rows: t from date and hour, expiry and strike split out of the instrument name."""
    df = df.copy()
    df["t"] = (pd.to_datetime(df["date"].astype(str) + " " + df["hour"].astype(str).str.zfill(2) + ":00", utc=True)
               .dt.tz_localize(None).astype("datetime64[ms]").astype("int64"))
    exp, strike = df["strike"].astype(str).str.split("-", n=1, expand=True).T.values
    df["expiry"] = pd.to_datetime(exp, format="%y%m%d").astype("datetime64[ms]").astype("int64") + 8 * 3_600_000
    df["strike"] = pd.to_numeric(strike)
    num = ["open", "high", "low", "close", "volume_contracts", "volume_usdt", "best_bid_price", "best_ask_price",
           "best_bid_qty", "best_ask_qty", "best_buy_iv", "best_sell_iv", "mark_price", "mark_iv", "delta", "gamma",
           "vega", "theta", "openinterest_contracts", "openinterest_usdt"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    keep = ["t", "symbol", "underlying", "type", "expiry", "strike"] + num
    return df[keep]


def bvol_frame(df):
    """Per-second index values to the last value of each minute, t = the minute's start in epoch ms."""
    df = df[["calc_time", "index_value"]].copy()
    df["t"] = df["calc_time"] // 60_000 * 60_000
    return df.groupby("t", as_index=False)["index_value"].last().rename(columns={"index_value": "bvol"})


def one(kind, sym, workers):
    sub, build = (EOH, eoh_frame) if kind == "eoh" else (BVOL, bvol_frame)
    path = OUT / kind / f"{sym}.parquet"
    if path.exists():
        return kind, sym, "skip", None
    keys = data.list_zips(f"{sub}{sym}/")
    with ThreadPoolExecutor(workers) as ex:
        files = list(ex.map(lambda k: data.fetch(k, strict=True), keys))
    frames = [build(read_zip(f)) for f in files if f is not None]
    df = pd.concat(frames, ignore_index=True).sort_values("t").drop_duplicates()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)
    return kind, sym, len(df), {"files": len(keys), "first_t": int(df.t.min()), "last_t": int(df.t.max()),
                                "rows": len(df), "keys": keys}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    jobs = [("eoh", p.rstrip("/").rsplit("/", 1)[1]) for p in data._list(EOH)[1]]
    jobs += [("bvol", p.rstrip("/").rsplit("/", 1)[1]) for p in data._list(BVOL)[1]]
    prov_path = OUT / "provenance.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else {}
    for kind, sym in jobs:
        kind, sym, n, info = one(kind, sym, a.workers)
        log(f"{kind} {sym}: {n}")
        if info:
            prov[f"{kind}/{sym}"] = {k: v for k, v in info.items() if k != "keys"} | {
                "source": f"{data.BASE}/{EOH if kind == 'eoh' else BVOL}{sym}/", "fetched_utc":
                time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), "checksums": "published SHA-256, strict"}
            prov_path.write_text(json.dumps(prov, indent=1))


if __name__ == "__main__":
    main()
