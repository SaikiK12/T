"""Hourly snapshot of every MEXC perpetual: the displayed funding rate with its next settlement time, cycle and caps
(funding_rate), and the ticker (last, bid/ask, index and fair price, 24 h volume, holdVol = open interest in
contracts). Two public requests per run. MEXC publishes no history of the displayed (next) rate or of open interest,
so this is the only way to get them (M172 next-funding revision; MEXC_EDGES rule 4).

One file per UTC hour, data/recorders/mexc_ticker/<YYYY-MM-DD>/<HH>.parquet (gitignored); a second run in the same
hour writes nothing. New rows retain request start and response-completion times;
recv_ms is the upper bound after both responses. Older files' recv_ms was the
request start, so it must not be used as a receipt bound. Data collection only.

usage: python scripts/record_mexc_ticker.py
"""
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, mexc  # noqa: E402

OUT = data.ROOT / "recorders" / "mexc_ticker"
TICKER = ("lastPrice", "bid1", "ask1", "indexPrice", "fairPrice", "volume24", "amount24", "holdVol", "timestamp")
FUNDING = ("fundingRate", "maxFundingRate", "minFundingRate", "collectCycle", "nextSettleTime", "timestamp")


def wall_ms():
    return time.time_ns() // 1_000_000


def snapshot(get=mexc.get, now_ms=None, *, clock_ms=wall_ms):
    """Capture completion bounds for the two responses, using the local wall clock."""
    start = clock_ms() if now_ms is None else now_ms
    fund_rows = get("funding_rate")
    fund_recv = clock_ms()
    tick_rows = get("ticker")
    tick_recv = clock_ms()
    if not start <= fund_recv <= tick_recv:
        raise ValueError("Local wall clock moved backwards during snapshot")
    fund = pd.DataFrame(fund_rows)
    tick = pd.DataFrame(tick_rows)
    fund = fund[["symbol", *[c for c in FUNDING if c in fund]]].rename(columns={c: f"f_{c}" for c in FUNDING})
    tick = tick[["symbol", *[c for c in TICKER if c in tick]]].rename(columns={c: f"t_{c}" for c in TICKER})
    df = fund.merge(tick, on="symbol", how="outer")
    df.insert(0, "request_start_ms", start)
    df.insert(1, "funding_recv_ms", fund_recv)
    df.insert(2, "ticker_recv_ms", tick_recv)
    df.insert(3, "recv_ms", tick_recv)
    return df


def record(get=mexc.get, now_ms=None, out=OUT, *, clock_ms=wall_ms):
    now_ms = clock_ms() if now_ms is None else now_ms
    stamp = pd.Timestamp(now_ms, unit="ms", tz="UTC")
    path = Path(out) / stamp.strftime("%Y-%m-%d") / f"{stamp:%H}.parquet"
    if path.exists():
        return path, 0
    df = snapshot(get, now_ms, clock_ms=clock_ms)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)
    return path, len(df)


def main():
    path, n = record()
    print(time.strftime("%H:%M:%S"), f"mexc ticker: {n} rows -> {path}" if n else f"mexc ticker: hour already recorded ({path})")


if __name__ == "__main__":
    main()
