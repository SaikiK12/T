# hip3carry_fwd (R479)

Forward paper lane for M530 and M531, earned by R475, R476 and R477. R475's weekly funding-carry rule is run forward
from 2026-11-16 on two books:
- S: short the US-stock perps of every HIP-3 dex (xyz, Paragon, EntropyIO, ...) and hold the stock;
- T: short R477's xyz index, ETF and metal perps and hold their USD UCITS twins on the LSE.

Each decides on its carry (funding + 85% of dividends − costs − the 13-week bill) at assumed and measured costs; the
total, price included, must stay positive.

- `PREREG.md`: frozen rule, reads, power and what the author had seen.
- `results/futility/` and `results/final/`: written once by `.github/workflows/claude-hip3carry.yml` on or after
  2027-02-13 and 2027-05-15. Each read fetches its own data (manifest copied into the results).
- Code: `scripts/run_hip3carry.py`, `scripts/fetch_hip3carry.py`, `tests/test_hip3carry.py`.
- Measured costs: the hourly book snapshots on `claude/xyz-books-data` (`books/` for xyz, `hip3/` for Paragon and
  EntropyIO from 2026-11-12).

Paper only. No order, no money, no key.
