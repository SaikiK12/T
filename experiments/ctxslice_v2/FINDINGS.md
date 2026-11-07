# FINDINGS: ctxslice_v2 (R204), slow replicated context pairs, one-shot holdout

**Verdict: NULL.** On the holdout the 12-24 h context book earned -6.5%/yr at 1x (t -0.13). Its gross edge fell from
17.6 bp/day in-sample to 7.0 bp/day, below its 7.9 bp/day of costs. The holdout is spent for these 289 pairs.

- **Registry row:** R204 (trials: 1)
- **Reproduce:** prereg sha 5f19447f; cells sha 517c5fcd; `python scripts/run_ctxslice.py --lane ctxslice_v2
  list|holdout` (M2 = 261.6 coin-states per hour).

## Holdout numbers (2025-07-01..2026-09-30, 457 days)
| book | hedge | cost | per year | Sharpe | NW t | max DD | gross bp/day | cost bp/day | beta BTC |
|---|---|---|---|---|---|---|---|---|---|
| all 289 (primary) | universe | 1x | -6.5% | -0.11 | -0.13 | 57% | 7.0 | 7.9 | -0.17 |
| all | universe | 2x / 3x | -46% / -86% | | -0.89 / -1.66 | | | | |
| all | top 10 / BTC / none | 1x | -16% / -8% / -3% | | -0.30 / -0.14 / -0.06 | | | | |
| atlas_ctx part (236) | universe | 1x | +15.7% | 0.28 | 0.32 | 38% | 12.4 | 6.8 | |
| atlas_mtf part (53) | universe | 1x | -26.5% | -2.44 | -2.31 | 36% | -5.4 | 1.9 | |
| 12 h pairs | universe | 1x | -24.3% | -1.41 | -1.48 | 34% | -1.3 | 4.4 | |
| 24 h pairs | universe | 1x | +11.7% | 0.26 | 0.30 | 32% | 8.3 | 4.6 | |

By month: 9 of 15 positive; swings of -20% to +18%.

## Cost sensitivity
In the table: negative at 1x, 2x and 3x.

## Reading
- In-sample +39%/yr (t 3.85) to holdout -6.5%: the context pairs, picked on 2021-2025H1 from about 9 million cells,
  kept some gross edge (7 bp/day, 40% of in-sample) but not enough to pay a book's costs. The multi-timeframe pairs
  reversed sign.
- This matches the pattern seen across the program: cross-sectional and conditional edges are strongest in 2021-2023,
  weaker in 2024-2025, and smaller again out of sample. The flow book (R198) is the exception that kept its sign.

## Next
Context gating survives only as a lead for the flow book (does top-vs-crowd pay more in some contexts?), not as a
standalone book. The forward test (R200) remains the main line.
