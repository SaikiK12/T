"""Read of xfund_bfx_fwd (R524), as its PREREG decides.

- **Series.** R512's (measured book costs plus taker fees: Binance 5 bp, Bitfinex 6.5 bp; 21 bp for a leg with no
  record), through R520's read.
- **Looks at 90 and 180 scored days, on fund_book** (funding net of measured costs; the price legs hedge the same
  coin):
  - PASS if NW t (lag 5) of fund_book >= 2.5 and the cumulative net_book > 0;
  - FAIL if the mean fund_book <= 0, or if the cumulative net_book falls below -3% (kill switch);
  - otherwise CONTINUE after look 1, and FAIL at look 2.
- **Calibration** (R507's 2025-26 days): power 0.77 at 90 days and 1.0 at 180, size 0.0 on the demeaned series.

usage: python scripts/read_xfund_bfx_fwd.py   (prints JSON; writes nothing)
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402
from scripts import read_xfund_dhl_fwd as r520  # noqa: E402  (R512's series with Deribit's fee table)

LANE = ROOT / "experiments" / "xfund_bfx_fwd"
r520.r512.FEE_BP.setdefault("binance", 5.0)
r520.r512.FEE_BP.setdefault("bitfinex", 6.5)
LOOK1, LOOK2, T_MIN, NW_LAG, KILL = 90, 180, 2.5, 5, -0.03


def decide(fund, net):
    fund, net = np.asarray(fund, float)[:LOOK2], np.asarray(net, float)[:LOOK2]
    n = len(fund)
    hit = np.flatnonzero(np.cumsum(net) < KILL)
    for look in (LOOK1, LOOK2):
        if n < look:
            break
        if len(hit) and hit[0] < look:
            return f"FAIL (kill switch, day {int(hit[0]) + 1})"
        f, x = fund[:look], net[:look]
        if newey_west_t(f, NW_LAG)[2] >= T_MIN and x.sum() > 0:
            return f"PASS (look at {look})"
        if f.mean() <= 0:
            return f"FAIL (look at {look}: mean <= 0)"
        if look == LOOK2:
            return "FAIL (look at 180)"
    if len(hit):
        return f"FAIL (kill switch, day {int(hit[0]) + 1})"
    return "RUNNING" if n < LOOK1 else "CONTINUE (after look 1)"


def main():
    s = r520.r512.series(LANE, "A")
    rep = r520.r512.read(s)
    rep.pop("verdict", None)
    rep["verdict"] = decide(s.fund_book.to_numpy(float), s.net_book.to_numpy(float)) if len(s) else "RUNNING"
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
