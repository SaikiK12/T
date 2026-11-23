"""Combined fast read of the three floorless venues' design-gap forward lanes (R527), as
experiments/gap_combo3_fast/PREREG.md decides: R509 (Kraken + Hyperliquid), R520 (Deribit + Hyperliquid) and R524
(Bitfinex + Binance), equal weight on days all three scored.

Per lane:
- R509 comes from R510's `series` (fund_book = funding - measured cost / 40, and net_book);
- R520 comes from R512's `series` with Deribit's fee, through R520's read;
- R524 comes from R512's `series` with Binance's and Bitfinex's fees, through R524's read.

Looks: 20 and 30 common scored days.
- PASS if NW t (lag 5) of the combined fund_book >= 3.0 and the combined cumulative net_book > 0.
- FAIL if the mean combined fund_book <= 0, or if any lane's cumulative net_book falls below -3%.
- Otherwise NOT YET at look 1 and NO EARLY PASS at look 2. The lanes' own reads then decide.

usage: python scripts/read_combined_gap3_fast.py   (prints JSON; writes nothing)
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402
from scripts import read_xfund_bfx_fwd as r524  # noqa: E402  (R524's read: Binance and Bitfinex fees)
from scripts import read_xfund_dhl_fwd as r520  # noqa: E402  (R520's read: Deribit fee)
from scripts import read_xfund_eea_fast as r510  # noqa: E402  (R510's read of R509)

LOOKS = (20, 30)
T_MIN, NW_LAG, KILL = 3.0, 5, -0.03
NAMES = ("kraken", "deribit", "bitfinex")


def combine(*lanes):
    """Days every lane scored: day, fund_book and net_book (equal-weight means), and each lane's net_book."""
    cols = ["day", "fund_book", "net_book"]
    out = ["day", "fund_book", "net_book"] + [f"net_{n}" for n in NAMES[:len(lanes)]]
    if any(x.empty for x in lanes):
        return pd.DataFrame(columns=out)
    m = None
    for n, x in zip(NAMES, lanes):
        y = x[cols].rename(columns={"fund_book": f"fund_{n}", "net_book": f"net_{n}"})
        m = y if m is None else m.merge(y, on="day")
    m = m.sort_values("day", ignore_index=True)
    k = len(lanes)
    m["fund_book"] = sum(m[f"fund_{n}"] for n in NAMES[:k]) / k
    m["net_book"] = sum(m[f"net_{n}"] for n in NAMES[:k]) / k
    return m[out]


def decide(c):
    n = len(c)
    nets = [x for x in c.columns if x.startswith("net_") and x != "net_book"]
    if n and any((c[x].astype(float).cumsum() < KILL).any() for x in nets):
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


def lanes():
    return (r510.series(), r520.r512.series(r520.LANE, "A"), r524.r520.r512.series(r524.LANE, "A"))


def main():
    c = combine(*lanes())
    look, verdict = decide(c)
    print(json.dumps({"common_scored_days": int(len(c)), "look": look, "verdict": verdict}, indent=1))


if __name__ == "__main__":
    main()
