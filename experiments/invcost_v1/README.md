# invcost_v1 (R456): R454's and R455's inventory books at measured costs

R454 (HLP inventory on Hyperliquid) and R455 (LLP inventory on Lighter) charge every trade a flat 9 bp. This lane
recomputes their books unchanged and charges what the venue's book actually cost at the time:
- Hyperliquid's tier-0 taker fee (4.5 bp) plus the slippage of a $1k market order in the nearest hourly snapshot of
  `main/books/`;
- on Lighter, no fee (Standard account) plus the slippage in `lighter/books/`.

It is the owner's "real money must match paper" check for these two lanes, as R453 is for R451. It counts zero
trials: it can only withhold a parent's PASS.

- Rule and decisions: [PREREG](PREREG.md) (frozen `ececc01b…`). Methods M510 and M511.
- Parents: [hlpinv_v1](../hlpinv_v1/README.md) and [llpinv_v1](../llpinv_v1/README.md). The read stops if its
  9 bp recomputation differs from a parent's tickets.
- Runner: `scripts/run_invcost.py`, weekly in `.github/workflows/claude-xperp-reads.yml`. It rewrites
  `results/forward/daily.csv` and `results/forward/report.json`.
- Looks: the cost gap at 90 counted days; at 365, EXECUTABLE AT MEASURED COSTS only if the parent passed.
