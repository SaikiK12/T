# PREREG: listings_holdout (R189), one-shot holdout test of the new-listing fade

Freeze with `lab.prereg.freeze()` before the run. Run once. Never edited afterwards.

- **Registry id:** R189
- **Code:** `lab/events.py`, `scripts/run_listings_holdout.py`
- **Evidence that led here:** listings_v1 (R188). Across all 48 configurations on discovery (2021-2023, 184 listings)
  and validation (2024-2025H1, 227 listings) the excess return of new listings was negative (medians -5% to -21%,
  60-70% negative), but squeezes (+90% to +210%) kept clustered t between about 1 and 3, so R188 was NULL by its rule.
  The configuration below had the strongest combined evidence (discovery t -3.06, validation t -1.52).
- **What has not been read:** any return after 2025-07-01 (the holdout). Only the number of listings in the window
  (353) was counted.

## Test
Listings (first hour with a close) from 2025-07-01 to 2026-08-31; all holding windows end by 2026-09-30.
- **Primary:** short at the close of listing + 24 h, hold 7 days, return minus the equal-weighted top-50 market's
  over the same hours, only listings with trailing 24 h quote volume >= 10 M USDT at entry. Costs one round trip on both
  legs at the tier costs (6/8/12/20 bp one-way by liquidity rank), funding included.
- **Secondary (reported, not decisive):** the same with hold 14 and 30 days; the primary with a fixed stop that closes
  the short when its cumulative excess loss reaches 30% (level fixed here, not tuned).

## Decision
**CONFIRMED** if the primary's mean net short return per event is > 0 with t clustered by listing month >= 2, and the
hedged book (short every event, stake 1/max(open, 10), long the market) has positive net return over the window.
Otherwise **NOT CONFIRMED**. A confirmed result goes to forward paper tickets on new listings before any real money
(`lab.gate.go_real` rules). Either way the result is recorded with the same care.

## Multiplicity
1 primary test (3 secondary, descriptive). Read against the program total.
