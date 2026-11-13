# linstart_v1 (R485)

M538, gate 0 on history. Short a token's OKX USDT swap from the 1Dutc close of D-7 to the close of D+14, where D is
the day an insiders or privateSale linear-vesting stream starts and raises the weekly unlock rate by at least 0.25% of
max supply (DefiLlama emissions snapshot 2026-11-13). LIT's own start on 2026-12-29 is a forward instance.

- `PREREG.md`: frozen question, event rule, trade, gates, deviations from M538 (OKX instead of Binance) and what was
  seen before the freeze.
- `events.csv`, `symbol_map.csv`: built by `scripts/linstart_events.py` from the snapshot and the OKX bodies below,
  frozen before any price; the runner rebuilds them byte for byte.
- `okx_instruments_swap.json`, `okx_tickers_swap.json`: OKX swap list and last prices (ticker check only).
- `raw/`: OKX daily candles and funding history, fetched once after the freeze by `scripts/fetch_linstart.py`, with
  `manifest.json` (sha256 per body).
- `results/`: written once by `scripts/run_linstart.py` (`verdict.json`, `events_priced.csv`, `null_means.csv`).
- Tests: `tests/test_linstart_events.py`, `tests/test_run_linstart.py`.

Paper only. No order, no money, no key.
