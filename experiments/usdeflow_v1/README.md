# usdeflow_v1 (R488)

M535, gate 0. Does the weekly log change in USDe circulating supply (DefiLlama id 146; Ethena opens a short perp
hedge on each mint and closes it on redemption) rank-correlate with the next week's change in Hyperliquid's mean
hourly BTC and ETH funding, beyond a circular-shift null? Both coins decide jointly. The six forward carry books'
week-ahead net is reported at 1x/2x/3x as the spread proxy. A predictor test, not a book.

- `PREREG.md`: frozen question, sample, statistic, null, gates, inputs.
- `raw/`: DefiLlama and Hyperliquid bodies fetched once after the freeze by `scripts/fetch_usdeflow.py`, with
  `manifest.json` (sha256).
- `results/`: written by `scripts/run_usdeflow.py` (`weekly.csv`, `report.json`).
- `FINDINGS.md`: rho, circular p, n and halves per coin, the proxy at 1x/2x/3x, read against
  `registry.program_trials()`.
- Prior art: `research/intake/usde_flow_20261113.md` (WS0033-WS0036). Tests: `tests/test_run_usdeflow.py`.

Paper only. No order, no money, no key.
