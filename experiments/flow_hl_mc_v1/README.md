# flow_hl_mc_v1 (R458): R448's books at measured Hyperliquid costs

Would a real account trading R448's crypto flow books on Hyperliquid's main dex pay what R448's paper charges? This
lane recomputes R448's positions unchanged and replaces each trade's assumed tier cost (6-20 bp by Binance rank) with
Hyperliquid's tier-0 taker fee (4.5 bp) plus the slippage of a $1k market order in the hourly main-dex book snapshots
of `claude/xyz-books-data` (`main/books/`).

- Rule and decisions: [PREREG](PREREG.md) (frozen `f938cec8…`).
- Runner: `scripts/run_flow_hl_mc.py`, weekly in `.github/workflows/claude-xperp-reads.yml`; output in
  `results/forward/`.
- Zero trials: it can only add a failure to R448, never a pass.
