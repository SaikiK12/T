"""Recorder for trade.xyz's other futures-referenced perps, COPPER and HO (DIESEL), and the contracts they reference.
No lane yet: it keeps the option of a frozen forward lane for M532 on these markets (for example after R480's
futility read on 2027-05-15). Yahoo drops a futures contract's history at expiry and Hyperliquid keeps only the latest
5,000 1-hour candles, so a lane registered later needs these recordings. Nobody reads the values before such a lane is
frozen. Stdlib only (the runner's python3).

Why these contracts (xyz's Roll Schedules page, https://docs.trade.xyz/llms-full.txt, read 2026-11-12):
- COPPER (COMEX HG) references a bimonthly cycle. At the start of each calendar month it references
  Jan-Feb H, Mar-Apr K, May-Jun N, Jul-Aug U, Sep-Nov Z, Dec H (next year).
  - It rolls on business days 5-9 of Feb, Apr, Jun, Aug and Nov (Z6 to H7 in November 2026).
  - Kept: the contract referenced at the start of the month and the next two in the cycle.
- HO (ULSD, "DIESEL") was listed on 2026-10-01. xyz's table for it is garbled.
  - Kept: the next four calendar months (m+1..m+4), which covers both readings (next month as for CL, or the one after
    as for Brent).

<out>/yahoo/<SYM>.csv          open_ms, open, high, low, close, volume  (complete 60-minute bars, e.g. HGH27.CMX)
<out>/xyz/<NAME>_1h.csv        open_ms, open, high, low, close, volume  (complete 1-hour candles of xyz:<NAME>)
<out>/xyz/<NAME>_funding.csv   time, fundingRate, premium              (hourly funding prints)

The network and file helpers are R480's (scripts/record_futroll.py, pinned in R480's PREREG; imported, never edited).

usage: python3 scripts/record_cuho.py --out .cuho-data [--now 2026-11-12T20:00:00Z]
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record_futroll as rec  # noqa: E402

COPPER_AT_START = {1: "H", 2: "H", 3: "K", 4: "K", 5: "N", 6: "N", 7: "U", 8: "U", 9: "Z", 10: "Z", 11: "Z", 12: "H"}
COPPER_CYCLE = "HKNUZ"
PERPS = ("COPPER", "HO")


def copper(now):
    """HG contracts (Yahoo, COMEX): the one xyz references at the start of `now`'s month and the next two."""
    code = COPPER_AT_START[now.month]
    year = now.year + (1 if now.month == 12 else 0)
    i = COPPER_CYCLE.index(code)
    out = []
    for k in range(3):
        j = i + k
        out.append(f"HG{COPPER_CYCLE[j % 5]}{(year + j // 5) % 100:02d}.CMX")
    return out


def heating_oil(now):
    """HO contracts (Yahoo, NYMEX) for the next four calendar months."""
    out = []
    for k in range(1, 5):
        m = now.month - 1 + k
        y, mo = now.year + m // 12, m % 12
        out.append(f"HO{rec.CODES[mo]}{y % 100:02d}.NYM")
    return out


def record(out, now):
    out = Path(out)
    now_ms = int(now.timestamp() * 1000)
    fail = 0
    for sym in copper(now) + heating_oil(now):
        try:
            rows = rec.yahoo_bars(sym, now_ms)
            added = rec.merge(out / "yahoo" / f"{sym}.csv", rows, "open_ms", rec.BAR_COLS) if rows else 0
            print(f"{sym}: {len(rows)} bars, {added} new", flush=True)
        except Exception as e:  # noqa: BLE001  (one symbol's failure must not stop the rest)
            print(f"{sym}: FAILED {type(e).__name__}: {e}", flush=True)
            fail = 1
        time.sleep(2)
    start = now_ms - rec.VENUE_DAYS * 24 * rec.H
    for name in PERPS:
        coin = f"xyz:{name}"
        try:
            c = rec.venue_candles(coin, start, now_ms)
            a = rec.merge(out / "xyz" / f"{name}_1h.csv", c, "open_ms", rec.BAR_COLS)
            time.sleep(1.5)
            fr = rec.venue_funding(coin, start, now_ms)
            b = rec.merge(out / "xyz" / f"{name}_funding.csv", fr, "time", rec.FUND_COLS)
            print(f"{coin}: {len(c)} candles ({a} new), {len(fr)} funding ({b} new)", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{coin}: FAILED {type(e).__name__}: {e}", flush=True)
            fail = 1
        time.sleep(1.5)
    return fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--now", default=None, help="UTC time, e.g. 2026-11-12T20:00:00Z (default: now)")
    a = ap.parse_args()
    now = (datetime.strptime(a.now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if a.now
           else datetime.now(timezone.utc))
    sys.exit(record(a.out, now))


if __name__ == "__main__":
    main()
