# FINDINGS: listings_holdout (R189)

**Verdict: NOT CONFIRMED.** On the untouched holdout the new-listing fade weakened and the squeezes got far larger;
shorting new listings lost money.

- **Registry row:** R189 (trials: 1 primary, 3 descriptive)
- **Reproduce:** prereg sha 7f6bf50e; `python scripts/run_listings_holdout.py` (run once, 2026-10-18).

## Numbers (listings 2025-07-01 to 2026-08-31 with >= 10 M USDT 24 h volume at entry: 206)
| hold | mean net short | clustered t | median excess | share negative | largest squeeze |
|---|---|---|---|---|---|
| 7 days (primary) | -2.6% | -0.78 | -3.8% | 55% | +178% |
| 14 days | -6.0% | -0.96 | -2.5% | 54% | +444% |
| 30 days | -12.7% | -1.67 | -2.1% | 53% | +710% |

Hedged book (primary): -52% net over the window, max drawdown 78%. The fixed 30% stop: -0.9% per event (t -0.44),
70 stops hit.

## Reading
The typical listing still drifted down (median negative), but half as much as in 2021-2025H1, while the right tail grew
several-fold. A pattern with the same sign in five straight years failed in the next fifteen months: the regime risk
the program is built around. No forward tickets.

## What this does not show
Whether a different structure (options-like payoff, much smaller size, or entry later) would work; any such idea is new
and needs its own lane and fresh data (forward only, since the holdout is now spent for listing events).
