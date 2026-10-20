"""Hourly snapshot of every MEXC perpetual: the displayed funding rate with its next settlement time, cycle and caps
(funding_rate), and the ticker (last, bid/ask, index and fair price, 24 h volume, holdVol = open interest in
contracts). Two public requests per run. MEXC publishes no history of the displayed (next) rate or of open interest,
so this is the only way to get them (M172 next-funding revision; MEXC_EDGES rule 4).

One file per UTC hour, data/recorders/mexc_ticker/<YYYY-MM-DD>/<HH>.parquet (gitignored); a second run in the same
hour writes nothing. recv_ms is this recorder's receipt time. Data collection only.

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


def snapshot(get=mexc.get, now_ms=None):
    """One frame, a row per symbol: funding fields prefixed f_, ticker fields prefixed t_."""
    recv = now_ms or int(time.time() * 1000)
    fund = pd.DataFrame(get("funding_rate"))
    tick = pd.DataFrame(get("ticker"))
    fund = fund[["symbol", *[c for c in FUNDING if c in fund]]].rename(columns={c: f"f_{c}" for c in FUNDING})
    tick = tick[["symbol", *[c for c in TICKER if c in tick]]].rename(columns={c: f"t_{c}" for c in TICKER})
    df = fund.merge(tick, on="symbol", how="outer")
    df.insert(0, "recv_ms", recv)
    return df


def record(get=mexc.get, now_ms=None, out=OUT):
    now_ms = now_ms or int(time.time() * 1000)
    stamp = pd.Timestamp(now_ms, unit="ms", tz="UTC")
    path = Path(out) / stamp.strftime("%Y-%m-%d") / f"{stamp:%H}.parquet"
    if path.exists():
        return path, 0
    df = snapshot(get, now_ms)
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
