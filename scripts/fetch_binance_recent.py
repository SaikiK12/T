"""Binance USD-M hourly klines past the archive's end (lab.data.END, 2026-09-30) for named perps.

Built by lab.data.build from the same data.binance.vision monthly and daily files as the archive, each checked
against its published SHA-256 (strict), into data/binance_recent/klines_1h/<SYMBOL>.parquet with the archive's schema
and every bar from the symbol's first month to --end. The archive in data/klines_1h is left as it is. Funding is
published monthly only, so the current month has none here.

First use: reserved batch 1 prices R265's post_archive unlock events (days after 2026-09-30), whose prices the
archive does not hold. Data collection only: nothing here computes a return.

usage: python scripts/fetch_binance_recent.py --end 2026-10-20 --symbols BTCUSDT ETHUSDT
       python scripts/fetch_binance_recent.py --end 2026-10-20 --unlock-post-archive
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "binance_recent"
EVENTS = ROOT / "experiments" / "unlocks_v1" / "events.csv"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def post_archive_perps():
    """The Binance perps of R265's post_archive unlock events, plus BTCUSDT (the runner's market reference)."""
    ev = pd.read_csv(EVENTS)
    return sorted(set(ev.perp[(ev.window == "post_archive") & (ev.venue == "binance")]) | {"BTCUSDT"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", required=True, help="last day to include (YYYY-MM-DD)")
    ap.add_argument("--symbols", nargs="*", default=[])
    ap.add_argument("--unlock-post-archive", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    syms = sorted(set(a.symbols) | (set(post_archive_perps()) if a.unlock_post_archive else set()))
    if not syms:
        raise SystemExit("no symbols")
    log(f"{len(syms)} symbols through {a.end}: {' '.join(syms)}")
    data.build("klines", "1h", symbols=syms, workers=a.workers, strict=True, end=a.end, root=OUT, log=log)


if __name__ == "__main__":
    main()
