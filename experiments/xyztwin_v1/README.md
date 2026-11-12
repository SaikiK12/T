# xyztwin_v1 (R477)

Gate-0 test of M531: R475's frozen weekly funding-carry rule on 13 trade.xyz index, ETF and metal perps (SMH, URNM,
EWY, KR200, EWJ, JP225, NIFTY, SP500, XYZ100, XLE, GOLD, SILVER, TLT). Each short is hedged with a USD UCITS ETF or ETC
twin on the London Stock Exchange that a French retail account can hold, marked at 16:00 UTC. Decided against the
13-week T-bill on sample A (2026-01-16 .. 07-22); B is reported.

- `PREREG.md`: frozen pairs, changes from R475, power, risks.
- `results/`: written once after the fetch.
- Code: `scripts/run_xyztwin.py` (wraps `scripts/run_hip3stock.py`), `scripts/fetch_xyztwin.py`,
  `tests/test_xyztwin.py`.

Paper only. No order, no money, no key.
