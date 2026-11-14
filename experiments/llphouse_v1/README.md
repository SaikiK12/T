# llphouse_v1 (R484)

M536, gate 0 on history. Lighter's LLP takes the house side of liquidations, so its day return is roughly the crowd's
P&L on Lighter turned around. When LLP has an extreme day (below the 10th or above the 90th percentile of its previous
90 days), does following (book F) or reversing (book R) BTC's same-day move over the next UTC day pay its costs on
Hyperliquid's BTC perp? ETH and LIT are reported.

- `PREREG.md`: frozen question, rule, costs, window, decision and what was seen before the freeze.
- `raw/`: Hyperliquid BTC and ETH daily candles and hourly funding, fetched once after the freeze by
  `scripts/fetch_llphouse.py`, byte-exact with `manifest.json` (sha256 per body).
- `results/`: written once by `scripts/run_llphouse.py` (`events.csv`, `report.json`).
- Tests: `tests/test_run_llphouse.py`.

Paper only. No order, no money, no key.
