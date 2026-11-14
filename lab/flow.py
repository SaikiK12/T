"""Order-flow datasets streamed from the public archive and reduced to hourly bars on the fly (raw files are not kept).

metrics   (5-minute rows, from 2020-09): open interest and its value, top-trader and all-account long/short ratios,
          taker buy/sell volume ratio. Hourly: OI value at the last row of the hour, ratios averaged over the hour.
bookDepth (about every 30 s, from 2023-01): cumulative depth within +-1..5% of mid, as quantity and notional.
          Hourly: mean notional per band over the hour (bid bands b1..b5, ask bands a1..a5).
Rows are keyed by the hour that contains them, like kline open times, so a row is known at that bar's close.

usage: python -m lab.flow metrics|bookDepth [--symbols A,B] [--start 2021-01-01] [--end 2025-12-31]
"""
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from . import data

HOUR = 3_600_000


def _ms(stamp):
    return (pd.to_datetime(stamp, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)


def reduce_metrics(raw):
    df = pd.read_csv(io.BytesIO(raw))
    if df.empty:
        return None
    t = _ms(df["create_time"])
    h = (t // HOUR) * HOUR
    g = pd.DataFrame({"t": h, "oi_value": df["sum_open_interest_value"], "oi": df["sum_open_interest"],
                      "top_ls_count": df["count_toptrader_long_short_ratio"],
                      "top_ls_sum": df["sum_toptrader_long_short_ratio"], "ls_count": df["count_long_short_ratio"],
                      "taker_ls_vol": df["sum_taker_long_short_vol_ratio"]}).groupby("t")
    out = g[["top_ls_count", "top_ls_sum", "ls_count", "taker_ls_vol"]].mean()
    out[["oi_value", "oi"]] = g[["oi_value", "oi"]].last()
    return out.reset_index()


def reduce_book(raw):
    df = pd.read_csv(io.BytesIO(raw))
    if df.empty:
        return None
    df["t"] = (_ms(df["timestamp"]) // HOUR) * HOUR
    w = df.pivot_table(index="t", columns="percentage", values="notional", aggfunc="mean")
    cols = {p: (f"b{-p}" if p < 0 else f"a{p}") for p in w.columns}
    w = w.rename(columns=cols)
    for c in [f"{s}{i}" for s in "ba" for i in range(1, 6)]:
        if c not in w:
            w[c] = np.nan
    return w[[f"{s}{i}" for s in "ba" for i in range(1, 6)]].reset_index()


REDUCERS = {"metrics": reduce_metrics, "bookDepth": reduce_book}


def _one(key, kind):
    try:
        blob = data._get(f"{data.BASE}/{key}")
    except Exception:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            return REDUCERS[kind](z.read(z.namelist()[0]))
    except Exception:
        return None


def needed_days(warmup=35):
    """Per research column, the days it is tradable at some hour, plus `warmup` days before each (for trailing
    features). Fetching only these cuts the order-flow downloads about five-fold."""
    root = data.ROOT / "research"
    meta = json.loads((root / "meta.json").read_text())
    t = np.load(root / "t.npy")
    elig = np.load(root / "elig.npy", mmap_mode="r")
    D = len(t) // 24
    day_any = np.asarray(elig[: D * 24]).reshape(D, 24, -1).any(axis=1)
    c = np.concatenate([np.zeros((1, day_any.shape[1])), np.cumsum(day_any[::-1], axis=0)])[::-1]
    ahead = (c[:D] - c[np.minimum(np.arange(D) + warmup + 1, D)]) > 0      # tradable within the next `warmup` days
    days = pd.to_datetime(t[::24][:D], unit="ms", utc=True).strftime("%Y-%m-%d").values
    return {s: set(days[ahead[:, i]]) for i, s in enumerate(meta["symbols"])}


def build(kind, symbols, start="2020-01-01", end=data.END, workers=48, root=None, log=print, days=None):
    """`days`: optional {symbol: set of 'YYYY-MM-DD'} to fetch; other days are skipped."""
    out = Path(root or data.ROOT) / f"{kind}_1h"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    mpath = out / "manifest.json"
    if mpath.exists():
        manifest = json.loads(mpath.read_text())["symbols"]
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        for i, s in enumerate(symbols, 1):
            if s in manifest or (out / f"{s}.parquet").exists():
                continue
            stamped = [(k, data._DATE.search(k)) for k in data.list_zips(f"{data.UM}/daily/{kind}/{s}/")]
            stamped = [(k, m.group(1) + m.group(2)) for k, m in stamped if m and m.group(2)]   # skip odd names
            keys = [k for k, d in stamped if start <= d <= end and (days is None or d in days.get(s, ()))]
            parts = [p for p in ex.map(lambda k: _one(k, kind), keys) if p is not None]
            if not parts:
                continue
            df = pd.concat(parts, ignore_index=True).drop_duplicates("t", keep="last").sort_values("t")
            df.to_parquet(out / f"{s}.parquet", index=False)
            manifest[s] = {"rows": len(df), "files": len(keys), "used": len(parts),
                           "first": int(df["t"].iloc[0]), "last": int(df["t"].iloc[-1])}
            log(f"{time.strftime('%H:%M:%S')} {kind} {i}/{len(symbols)} {s}: {len(parts)}/{len(keys)} days, "
                f"{(time.time() - t0) / 60:.1f} min")
            if i % 20 == 0:
                mpath.write_text(json.dumps({"kind": kind, "start": start, "end": end, "symbols": manifest}, indent=1))
    mpath.write_text(json.dumps({"kind": kind, "start": start, "end": end, "symbols": manifest}, indent=1))
    log(f"{kind}: {len(manifest)} symbols done")
    return manifest


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=REDUCERS)
    ap.add_argument("--symbols")
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default=data.END)
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--all-days", action="store_true", help="fetch every day, not only tradable days plus warm-up")
    a = ap.parse_args()
    if a.symbols:
        syms = a.symbols.split(",")
    else:
        syms = json.loads((data.ROOT / "research" / "meta.json").read_text())["symbols"]
    build(a.kind, syms, a.start, a.end, a.workers, days=None if a.all_days else needed_days())
