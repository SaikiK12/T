# rebalfront_v1 (R472): front-running balanced-fund rebalancing

Gate 0 for M522. The rule is from Harvey, Mazzoleni and Melone (NBER w33554): a simulated 60/40 stock/bond
portfolio's drift predicts the next day's stock-minus-bond return, because balanced funds rebalance.

- **Rebuilt on public ETF closes:** SPY for stocks, IEF for bonds, 2002-2026 from Yahoo, plus FRED's bill rate.
- **R** (2002-09 .. 2023-03-17) is the paper's published span; it checks that our construction reproduces their two
  slopes.
- **U** (2023-03-20 .. 2026-11-11) decides, at trade.xyz's SP500/TLT cost (4.2 bp per unit of position change).
- A PASS earns only a forward paper lane on trade.xyz's SP500 and TLT perps.

Files:
- `PREREG.md`, frozen (`PREREG.sha256`).
- `scripts/fetch_rebalfront.py` (data), `scripts/run_rebalfront.py` (the frozen run), `tests/test_rebalfront.py`.
- `results/` after the run, and `FINDINGS.md` after the read.
