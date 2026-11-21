"""Fast read of R520's journal (R521 xfund_dhl_fast), as experiments/xfund_dhl_fast/PREREG.md decides.

R510's design applied to R520 (Deribit + Hyperliquid). The book's price legs hedge the same coin and add noise, not
return. On R519's history the funding part net of costs had a daily Sharpe ratio of 0.43, against 0.15 for the whole
net. So this read decides on fund_book and keeps the whole net as a guard. R520's own looks are unchanged.

Per scored day of R520's book A (R512's `series`, with Deribit's 3.5 bp fee from R520's read):
- fund_book = funding - measured cost / (2 * 20);
- net_book is R520's decided series.

Looks: 30 and 45 scored days.
- PASS if NW t (lag 5) of fund_book >= 2.5 and the cumulative net_book > 0.
- FAIL if the mean fund_book <= 0, or if R520's kill switch has fired (cumulative net_book < -3%).
- Otherwise NOT YET at look 1, and NO EARLY PASS at look 2 (R520's looks then decide).

usage: python scripts/read_xfund_dhl_fast.py   (prints JSON; writes nothing)
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402
from scripts import read_xfund_dhl_fwd as r520  # noqa: E402  (R520's read: Deribit fee, lane path)

LOOKS = (30, 45)
T_MIN, NW_LAG, KILL = 2.5, 5, -0.03


def decide(fund, net):
    """(look, verdict) from the scored daily fund_book and net_book series (oldest first)."""
    fund, net = np.asarray(fund, float), np.asarray(net, float)
    n = len(fund)
    if n and (np.cumsum(net[:LOOKS[-1]]) < KILL).any():
        return None, "FAIL (R520 kill switch)"
    done = [k for k in LOOKS if n >= k]
    if not done:
        return None, "RUNNING"
    for k in done:
        f, x = fund[:k], net[:k]
        if newey_west_t(f, NW_LAG)[2] >= T_MIN and x.sum() > 0:
            return k, "PASS"
        if f.mean() <= 0:
            return k, "FAIL"
    return done[-1], "NOT YET" if done[-1] == LOOKS[0] else "NO EARLY PASS"


def main():
    s = r520.r512.series(r520.LANE, "A")
    look, verdict = decide(s.fund_book.to_numpy(float), s.net_book.to_numpy(float)) if len(s) else (None, "RUNNING")
    rep = {"scored_days": int(len(s)), "look": look, "verdict": verdict}
    if len(s) >= 3:
        rep["fund_book_nw_t"] = float(newey_west_t(s.fund_book.to_numpy(float), NW_LAG)[2])
        rep["cum_net_book"] = float(s.net_book.sum())
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
