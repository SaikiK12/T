"""Combined fast read of two independent design-gap forward lanes (R523), as experiments/gap_combo_fast/PREREG.md
decides: R509 (Kraken + Hyperliquid) and R520 (Deribit + Hyperliquid), equal weight on common scored days.

Per lane:
- R509 comes from R510's `series` (fund_book = funding - measured cost / 40, and net_book);
- R520 comes from R512's `series` with Deribit's fee (through R520's read).
The combined day is the mean of the two lanes on days both scored.

Looks: 20 and 30 common scored days.
- PASS if NW t (lag 5) of the combined fund_book >= 3.0 and the combined cumulative net_book > 0.
- FAIL if the mean combined fund_book <= 0, or if either lane's cumulative net_book falls below -3%.
- Otherwise NOT YET at look 1 and NO EARLY PASS at look 2. The lanes' own reads then decide.

usage: python scripts/read_combined_gap_fast.py   (prints JSON; writes nothing)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402
from scripts import read_xfund_dhl_fwd as r520  # noqa: E402  (R520's read: Deribit fee)
from scripts import read_xfund_eea_fast as r510  # noqa: E402  (R510's read of R509)

LOOKS = (20, 30)
T_MIN, NW_LAG, KILL = 3.0, 5, -0.03


def combine(a, b):
    """Common scored days of two lanes: day, fund_book, net_book (means), and each lane's net_book."""
    cols = ["day", "fund_book", "net_book"]
    if a.empty or b.empty:
        return pd.DataFrame(columns=cols + ["net_a", "net_b"])
    m = a[cols].merge(b[cols], on="day", suffixes=("_a", "_b")).sort_values("day", ignore_index=True)
    return pd.DataFrame({"day": m.day, "fund_book": (m.fund_book_a + m.fund_book_b) / 2,
                         "net_book": (m.net_book_a + m.net_book_b) / 2, "net_a": m.net_book_a, "net_b": m.net_book_b})


def decide(c):
    n = len(c)
    if n and ((c.net_a.cumsum() < KILL).any() or (c.net_b.cumsum() < KILL).any()):
        return None, "FAIL (a lane's kill switch)"
    done = [k for k in LOOKS if n >= k]
    if not done:
        return None, "RUNNING"
    for k in done:
        f, x = c.fund_book.to_numpy(float)[:k], c.net_book.to_numpy(float)[:k]
        if newey_west_t(f, NW_LAG)[2] >= T_MIN and x.sum() > 0:
            return k, "PASS"
        if f.mean() <= 0:
            return k, "FAIL"
    return done[-1], "NOT YET" if done[-1] == LOOKS[0] else "NO EARLY PASS"


def main():
    c = combine(r510.series(), r520.r512.series(r520.LANE, "A"))
    look, verdict = decide(c)
    print(json.dumps({"common_scored_days": int(len(c)), "look": look, "verdict": verdict}, indent=1))


if __name__ == "__main__":
    main()
