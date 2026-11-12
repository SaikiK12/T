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

## Faults and notes
- **2026-11-12, DTB3 from H.15 instead of FRED.**
  - FRED refused the frozen fetch's client: the connection was closed from the cloud container and timed out after
    60 s from a GitHub runner (run 43167744562). curl received the same file, so FRED was screening the client.
  - The client was not altered to get past that, and FRED is no longer contacted.
  - The bill series comes from its primary publisher instead: the Federal Reserve Board's H.15 release archive,
    series RIFSGFSM03_N.B, the same series FRED republishes as DTB3. The wrapper is
    `scripts/fetch_rebalfront_h15.py`; the Yahoo calls and every other step of the frozen fetch are unchanged.
  - The converted file was byte-identical to FRED's CSV on 2026-11-12 (sha256 `f524d676…`).
  - DTB3 enters only the reported equity-only return; the decision (two-leg return) does not use it.
