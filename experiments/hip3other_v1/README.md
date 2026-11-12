# hip3other_v1 (R476)

Replication of R475 (M530) on new venues: R475's frozen weekly funding-carry book (short up to 5 US-stock perps with
trailing funding of at least 12%/yr, long the same stocks) run on every HIP-3 deployer other than trade.xyz. That is
Felix, Kinetiq, Dreamcash and mkts in the decision sample A (2026-01-16 .. 07-22; most of them shut down in June
2026), and Paragon and EntropyIO in B (reported).

- `PREREG.md`: frozen question, data, samples and what the author had seen.
- `results/`: written once after the fetch.
- Code: `scripts/run_hip3other.py` (calls `scripts/run_hip3stock.py` unchanged), `scripts/fetch_hip3other.py`,
  `tests/test_hip3other.py`.

Paper only. No order, no money, no key.
