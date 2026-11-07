"""Binance USD-M TradFi perpetuals, 1-minute klines from the public archive (data.binance.vision), every file checked
against its published SHA-256. Crude oil, Brent, natural gas, gold, silver and the QQQ and SPY index/ETF perps trade
24/7 on Binance; the archive holds them from their listing (CL, BZ, NATGAS: 2026-04-01). Used by R368 eventdrift_v1.

Writes data/tradfi_perps/klines_1m/<SYMBOL>.parquet and manifest.json (lab.data.build). Re-running is idempotent: cached
files are re-verified, new days after the last run are fetched when --end moves.

usage: python scripts/fetch_tradfi_perps.py [--end 2026-10-27]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

SYMBOLS = ["CLUSDT", "BZUSDT", "NATGASUSDT", "XAUUSDT", "XAGUSDT", "QQQUSDT", "SPYUSDT"]
OUT = ROOT / "data" / "tradfi_perps"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--end", default="2026-10-27")
    a = ap.parse_args(argv)
    body = data.build("klines", "1m", SYMBOLS, workers=8, strict=True, end=a.end, root=OUT)
    print("manifest sha256", body["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
