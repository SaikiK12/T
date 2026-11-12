# hip3stock_v1 (R475)

Gate-0 test of M530: each week, short the trade.xyz US-stock perps whose trailing 28-day funding is highest (at
least 12%/yr, up to 5 names) and hold the same stocks at a broker. The prices cancel; the book keeps the funding the
perp longs pay and the dividends. Decided against the 13-week T-bill on sample A (2026-01-16 .. 07-22); B is
reported.

- `PREREG.md`: frozen rule, samples, power, risks.
- `results/`: `summary.json` and the daily, weekly and trade files of each variant, written once after the fetch.
- Code: `scripts/run_hip3stock.py`, `scripts/fetch_hip3stock.py`, `tests/test_hip3stock.py`.

Paper only. No order, no money, no key.
