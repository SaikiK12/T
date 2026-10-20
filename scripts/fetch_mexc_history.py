"""Download MEXC public history for every crypto USDT perpetual listed today: hourly contract klines, hourly index
klines and settled funding, from 2025-04-01 (funding history starts 2025-04-27 on every contract) to the last closed
hour. Writes data/mexc_hist/ only (the forward lanes' caches under data/mexc/ are left alone). Resume requires a
matching request receipt and unchanged files. Legacy/partial/stale caches are preserved and rejected; use a fresh
--out directory to collect a new snapshot. Receipts prove retrieved bytes, not exchange-history completeness.

usage: python scripts/fetch_mexc_history.py --out data/mexc_hist_new --end 2026-10-20T18:00:00Z [--workers 4]
Pin --end when resuming across clock hours. Without it, end is the start of the current UTC hour.
"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, mexc, panel  # noqa: E402

OUT = data.ROOT / "mexc_hist"
START = panel.ms("2025-04-01")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closed_hour_end(now_ms):
    """Exclusive bar-open bound: at 12:34, include the complete 11:00 bar."""
    return int(now_ms) // mexc.HOUR * mexc.HOUR


def one(sym, end, out=None):
    out = Path(out) if out is not None else OUT
    paths = {k: out / k / f"{sym}.parquet" for k in ("klines_1h", "index_price_1h", "funding")}
    receipt = out / "receipts" / f"{sym}.json"
    request = {"schema": 1, "symbol": sym, "start": START, "end_exclusive": end}
    try:
        if receipt.exists():
            saved = json.loads(receipt.read_text())
            if not isinstance(saved, dict):
                raise ValueError("receipt must be a JSON object")
            if saved.get("request") != request:
                return sym, "error cached request differs; use a fresh --out directory"
            for k, path in paths.items():
                if not path.is_file() or sha256(path) != saved["files"][k]["sha256"]:
                    return sym, "error cached bytes differ from receipt; cache preserved"
            return sym, "skip verified request and hashes (coverage not certified)"
        if any(p.exists() for p in paths.values()):
            return sym, "error legacy/partial cache has no receipt; use a fresh --out directory"
        got = {"klines_1h": mexc.fetch_klines(sym, START, end),
               "index_price_1h": mexc.fetch_klines(sym, START, end, kind="index_price"),
               "funding": mexc.funding_history(sym, START, end)}
        for k, df in got.items():
            if "t" not in df or df.t.isna().any() or df.t.duplicated().any():
                raise ValueError(f"{k}: missing/duplicate timestamp")
            if not df.t.is_monotonic_increasing or not ((df.t >= START) & (df.t < end)).all():
                raise ValueError(f"{k}: timestamps outside requested range or unordered")
        files = {}
        for k, df in got.items():
            paths[k].parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation: never replace existing research inputs, including an interrupted write.
            with paths[k].open("xb") as f:
                df.to_parquet(f, index=False)
            files[k] = {"sha256": sha256(paths[k]), "rows": len(df),
                        "min_t": int(df.t.min()) if len(df) else None,
                        "max_t": int(df.t.max()) if len(df) else None}
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with receipt.open("x") as f:
            json.dump({"request": request, "files": files, "retrieved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "collector_sha256": sha256(Path(__file__)), "coverage_certified": False}, f, indent=2)
    except (mexc.MexcError, OSError, ValueError, KeyError, TypeError) as e:
        return sym, f"error {e}"
    return sym, f"{len(got['klines_1h'])} bars, {len(got['funding'])} settlements"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=OUT, help="snapshot directory; existing unverified bytes are never overwritten")
    ap.add_argument("--end", help="exclusive UTC hour, e.g. 2026-10-20T18:00:00Z; pin for reproducible resume")
    a = ap.parse_args()
    if a.workers < 1:
        ap.error("--workers must be positive")
    latest = closed_hour_end(time.time() * 1000)
    end = latest
    if a.end:
        try:
            timestamp = pd.Timestamp(a.end)
            if timestamp.tzinfo is None:
                raise ValueError("timezone required")
            if timestamp.value % (mexc.HOUR * 1_000_000):
                raise ValueError("end must align exactly to an hour")
            end = int(timestamp.timestamp() * 1000)
            if end % mexc.HOUR or not START < end <= latest:
                raise ValueError("end must be a closed hour after START and no later than the current UTC hour")
        except (ValueError, TypeError, OverflowError) as e:
            ap.error(f"invalid --end: {e}")
    table = mexc.contracts(refresh=True)
    crypto = table[table.type == 1]
    a.out.mkdir(parents=True, exist_ok=True)
    run = a.out / "runs" / str(time.time_ns())
    run.mkdir(parents=True)
    (run / "contracts.json").write_text(crypto.to_json(orient="records"))
    log(f"{len(crypto)} crypto contracts; history {pd.Timestamp(START, unit='ms')} .. {pd.Timestamp(end, unit='ms')}")
    errors, outcomes = [], {}
    with ThreadPoolExecutor(a.workers) as ex:
        for i, (sym, msg) in enumerate(ex.map(lambda s: one(s, end, a.out), sorted(crypto.symbol)), 1):
            outcomes[sym] = msg
            if msg.startswith("error"):
                errors.append(sym)
            if i % 25 == 0 or msg.startswith("error"):
                log(f"{i}/{len(crypto)} {sym}: {msg}")
    (run / "manifest.json").write_text(json.dumps({"start": START, "end_exclusive": end, "contracts": len(crypto),
        "errors": errors, "outcomes": outcomes, "coverage_certified": False,
        "collector_sha256": sha256(Path(__file__)), "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=2))
    log(f"done; {len(errors)} errors: {errors[:20]}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
