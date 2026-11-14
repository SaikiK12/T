# flow_hlstock_mc_v1 (R453): R451's books at measured xyz costs

Would a real account trading R451's flow books on Hyperliquid's xyz markets pay what R451's paper charges? This lane
recomputes R451's positions unchanged and replaces each trade's assumed cost with xyz's actual fee (HIP-3 growth mode)
plus the slippage of a $1k market order in the hourly book snapshots of `claude/xyz-books-data`.

- Rule and decisions: [PREREG](PREREG.md) (frozen `26a0ed2d…`).
- Runner: `scripts/run_flow_hlstock_mc.py`, weekly in `.github/workflows/claude-xperp-reads.yml`; output in
  `results/forward/`.
- Zero trials: it can only add a failure to R451, never a pass.
