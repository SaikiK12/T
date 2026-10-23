"""Download MEXC public history for its TradFi USDT perpetuals (contract type 2: stocks, indices, commodities, ETFs).

- **Hourly** (`--hourly`), every TradFi contract listed today: contract klines, index-price klines and settled funding
  from 2025-04-01 or listing, through `scripts/fetch_mexc_history.one` (same receipts and never-overwrite rules).
- **Minutes** (`--minutes`), the index, commodity and broad-ETF perps in MINUTE_SYMBOLS (M320/M321):
  - 5-minute contract and index klines from 2025-04-01 or listing;
  - 1-minute contract and index klines for the last 30 days. MEXC serves 1-minute bars for about 30 days only, so
    each run writes a dated snapshot (`klines_1m/<symbol>/<end date>.parquet`); run it at least monthly to keep
    the series unbroken.

Writes data/mexc_tradfi/ only. Receipts prove the retrieved bytes, not exchange-history completeness.

usage: python scripts/fetch_mexc_tradfi.py --hourly --minutes --end 2026-10-22T12:00:00Z [--workers 4]
"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, mexc  # noqa: E402
from scripts import fetch_mexc_history as hist  # noqa: E402

OUT = data.ROOT / "mexc_tradfi"
MINUTE = 60_000
STEP = {"Min1": MINUTE, "Min5": 5 * MINUTE}
PAGE = 2000                                     # bars per request
MIN1_DAYS = 30
MINUTE_SYMBOLS = ("NAS100_USDT", "SPX500_USDT", "US30_USDT", "JP225_USDT", "HK50_USDT", "KOSPI_USDT", "SPY_USDT",
                  "QQQSTOCK_USDT", "IWM_USDT", "GLD_USDT", "TLT_USDT", "UVXY_USDT", "SMH_USDT", "USOIL_USDT",
                  "UKOIL_USDT", "NGAS_USDT")
COLS = ["t", "open", "high", "low", "close", "vol", "amount"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tradfi(table):
    """The TradFi (type 2) USDT perpetuals in a `mexc.contracts()` table, sorted."""
    return sorted(table.symbol[table.type == 2])


def bars(symbol, start, end, interval, kind=""):
    """Bars of `interval` with open time in [start, end) (ms), paged PAGE bars at a time: DataFrame t, open, high, low,
    close, vol, amount. kind "index_price" gives the index price."""
    step, out, s = STEP[interval], [], start
    while s < end:
        e = min(end, s + PAGE * step)
        d = mexc.get(f"kline/{kind + '/' if kind else ''}{symbol}", {"interval": interval, "start": s // 1000,
                                                                     "end": (e - step) // 1000})
        if d and d.get("time"):
            out.append(pd.DataFrame({"t": np.asarray(d["time"], np.int64) * 1000,
                                     **{k: np.asarray(d.get(k, [np.nan] * len(d["time"])), np.float64)
                                        for k in COLS[1:]}}))
        s = e
    if not out:
        return pd.DataFrame(columns=COLS)
    df = pd.concat(out).drop_duplicates("t", keep="last").sort_values("t")
    return df[(df.t >= start) & (df.t < end)].reset_index(drop=True)


def write_new(path, df):
    """Exclusive creation: never replace a file that exists. Returns its receipt entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        df.to_parquet(f, index=False)
    return {"sha256": sha256(path), "rows": len(df), "min_t": int(df.t.min()) if len(df) else None,
            "max_t": int(df.t.max()) if len(df) else None}


def minutes(sym, end, out=None):
    """5-minute history from hist.START and a dated 1-minute snapshot of the last MIN1_DAYS days, for one symbol."""
    out = Path(out) if out is not None else OUT
    day = pd.Timestamp(end, unit="ms").strftime("%Y-%m-%d")
    jobs = {"klines_5m": ("Min5", "", hist.START, out / "klines_5m" / f"{sym}.parquet"),
            "index_price_5m": ("Min5", "index_price", hist.START, out / "index_price_5m" / f"{sym}.parquet"),
            "klines_1m": ("Min1", "", end - MIN1_DAYS * 86_400_000, out / "klines_1m" / sym / f"{day}.parquet"),
            "index_price_1m": ("Min1", "index_price", end - MIN1_DAYS * 86_400_000,
                               out / "index_price_1m" / sym / f"{day}.parquet")}
    receipt = out / "receipts_minutes" / f"{sym}_{day}.json"
    try:
        if receipt.exists():
            return sym, "skip receipt exists"
        files = {}
        for k, (iv, kind, start, path) in jobs.items():
            if k.endswith("5m") and path.exists():
                files[k] = {"skipped": "5-minute history already held; refetch into a fresh --out"}
                continue
            df = bars(sym, start, end, iv, kind)
            if df.t.duplicated().any() or not df.t.is_monotonic_increasing:
                raise ValueError(f"{k}: duplicate or unordered timestamps")
            files[k] = write_new(path, df)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with receipt.open("x") as f:
            json.dump({"request": {"symbol": sym, "end_exclusive": end, "min1_days": MIN1_DAYS, "start_5m": hist.START},
                       "files": files, "retrieved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "collector_sha256": sha256(Path(__file__)), "coverage_certified": False}, f, indent=2)
    except (mexc.MexcError, OSError, ValueError, KeyError, TypeError) as e:
        return sym, f"error {e}"
    return sym, ", ".join(f"{k} {v.get('rows', 0)}" for k, v in files.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hourly", action="store_true", help="hourly klines, index and funding for every TradFi perp")
    ap.add_argument("--minutes", action="store_true", help="5- and 1-minute klines for MINUTE_SYMBOLS")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--end", help="exclusive UTC hour, e.g. 2026-10-22T12:00:00Z")
    a = ap.parse_args()
    if not (a.hourly or a.minutes):
        ap.error("pass --hourly and/or --minutes")
    end = hist.closed_hour_end(time.time() * 1000)
    if a.end:
        ts = pd.Timestamp(a.end)
        if ts.tzinfo is None or ts.value % (mexc.HOUR * 1_000_000) or int(ts.timestamp() * 1000) > end:
            ap.error("--end must be a closed UTC hour with a timezone, not in the future")
        end = int(ts.timestamp() * 1000)
    table = mexc.contracts(refresh=True)
    syms = tradfi(table)
    a.out.mkdir(parents=True, exist_ok=True)
    run = a.out / "runs" / str(time.time_ns())
    run.mkdir(parents=True)
    (run / "contracts.json").write_text(table[table.type == 2].to_json(orient="records"))
    outcomes, errors = {}, []
    jobs = []
    if a.hourly:
        jobs.append(("hourly", syms, lambda s: hist.one(s, end, a.out)))
    if a.minutes:
        jobs.append(("minutes", [s for s in MINUTE_SYMBOLS if s in set(syms)], lambda s: minutes(s, end, a.out)))
    for name, todo, fn in jobs:
        log(f"{name}: {len(todo)} contracts to {pd.Timestamp(end, unit='ms')}")
        with ThreadPoolExecutor(a.workers) as ex:
            for i, (sym, msg) in enumerate(ex.map(fn, todo), 1):
                outcomes[f"{name}:{sym}"] = msg
                if msg.startswith("error"):
                    errors.append(f"{name}:{sym}")
                if i % 25 == 0 or msg.startswith("error") or name == "minutes":
                    log(f"{name} {i}/{len(todo)} {sym}: {msg}")
    (run / "manifest.json").write_text(json.dumps({"end_exclusive": end, "tradfi_contracts": len(syms),
        "errors": errors, "outcomes": outcomes, "coverage_certified": False, "collector_sha256": sha256(Path(__file__)),
        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=2))
    log(f"done; {len(errors)} errors: {errors[:20]}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
