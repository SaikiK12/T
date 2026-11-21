"""Read of xfund_dhl_fwd (R520), as its PREREG decides.

- **Net.** R512's net_book (`scripts/read_xfund_eea3_fwd.series`: the 1x fill-accounting net with measured book costs
  plus taker fees; 21 bp for a leg with no record), with Deribit's 3.5 bp taker fee added to R512's fee table.
- **Two fixed looks.** At R519's Sharpe ratio (about 0.20 a day), R512's anytime rule would need about 300 days.
  - **Look 1, 90 scored days:** PASS if NW t (lag 10) of net_book >= 2.5 and the cumulative net_book > 0; FAIL if
    the mean net_book <= 0; otherwise continue.
  - **Look 2, 180 scored days:** PASS if NW t >= 2.0; otherwise FAIL.
- **Kill switch:** FAIL at once if the cumulative net_book falls below -3%.
- **Reported, not decided:** R512's anytime e-value and fund_book.

usage: python scripts/read_xfund_dhl_fwd.py   (prints JSON; writes nothing)
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402
from scripts import read_xfund_eea3_fwd as r512  # noqa: E402  (frozen R512 read: series, read)

LANE = ROOT / "experiments" / "xfund_dhl_fwd"
r512.FEE_BP.setdefault("deribit", 3.5)
LOOK1, LOOK2, T1, T2, KILL = 90, 180, 2.5, 2.0, -0.03


def decide(x):
    """Verdict from the scored daily net_book series x (oldest first). A decision at a look is final."""
    x = np.asarray(x, float)[:LOOK2]
    n = len(x)
    cum = np.cumsum(x)

    def killed(upto):
        hit = np.flatnonzero(cum[:upto] < KILL)
        return f"FAIL (kill switch, day {int(hit[0]) + 1})" if len(hit) else None

    if n < LOOK1:
        return killed(n) or "RUNNING"
    if killed(LOOK1):
        return killed(LOOK1)
    y = x[:LOOK1]
    if newey_west_t(y, 10)[2] >= T1 and y.sum() > 0:
        return "PASS (look 1)"
    if y.mean() <= 0:
        return "FAIL (look 1: mean <= 0)"
    if killed(n):
        return killed(n)
    if n < LOOK2:
        return "CONTINUE (after look 1)"
    return "PASS (look 2)" if newey_west_t(x, 10)[2] >= T2 else "FAIL (look 2)"


def main():
    s = r512.series(LANE, "A")
    rep = r512.read(s)
    rep.pop("verdict", None)
    rep["verdict"] = decide(s.net_book.to_numpy(float)) if len(s) else "RUNNING"
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
