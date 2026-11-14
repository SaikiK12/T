# FINDINGS: ctxslice_v1 (R201), replicated context edges as one slice book

**Verdict: NULL.** Stage 1 (in-sample, selection-biased) failed its gate: the full book of 547 replicated excess
context pairs loses at 1x costs. The holdout was not read.

- **Registry row:** R201 (trials: 1)
- **Reproduce:** prereg sha 4d2261c5; cells sha ed59ae0c; `python scripts/run_ctxslice.py list|insample`.

## Stage 1 numbers (2021-01-01..2025-06-30, 1,642 days, M = 396 coin-states per hour)
| book | hedge | cost | per year | Sharpe | NW t | max DD | gross bp/day | cost bp/day | turnover/day |
|---|---|---|---|---|---|---|---|---|---|
| all 547 (primary) | universe | 1x | -32.2% | -0.83 | -1.97 | 180% | 19.3 | 20.1 | 2.79 |
| all | universe | 2x | -139.6% | | -8.0 | | | 40.2 | |
| all | universe | 3x | -246.9% | | -13.1 | | | 60.3 | |
| all | top 10 / BTC / none | 1x | -31% / -26% / -3% | | -1.7 / -1.3 / -0.1 | | | | |
| atlas_ctx cells (315) | universe | 1x | +33.9% | 1.43 | 3.17 | 27% | 18.1 | 7.8 | 1.09 |
| atlas_mtf cells (232) | universe | 1x | -75.7% | -2.85 | -6.35 | 346% | 1.2 | 14.1 | 1.95 |
| horizons 1-4 h (249) | universe | 1x | -82.5% | -2.75 | -6.39 | 376% | 1.7 | 16.3 | 2.26 |
| horizons 12-24 h (289) | universe | 1x | +39.4% | 1.78 | 3.85 | 21% | 17.6 | 5.6 | 0.78 |
| horizon 72 h (9) | universe | 1x | +0.6% | 1.22 | 3.20 | 0.8% | -0.1 | 0.04 | 0.01 |

Primary by year: 2021 -22%, 2022 -13%, 2023 -64%, 2024 -53%, 2025H1 +7%. (Sub-books share the size normalizer M of the
full book, so their exposures are fractions of 1.)

## Reading
- The fast cells (1-4 h, mostly atlas_mtf) earn almost nothing gross per day once held as slices (1-2 bp against
  14-16 bp of costs): their day-weighted atlas edges of 23-35 bp per state-hour do not survive turnover. Same lesson as
  flow72_v1 and maker_v1.
- The slow cells (12-24 h, mostly atlas_ctx) pay: +39%/yr in-sample, t 3.85, max DD 21%, cost 5.6 bp/day against
  17.6 bp/day gross. These numbers are selection-biased (the cells were picked on these years) and were looked at
  among five sub-books, so they are a lead, not evidence.

## Cost sensitivity
In the table: the primary is negative at 1x, 2x and 3x.

## Next
ctxslice_v2: the 12-24 h sub-book as a new lane, chosen on this in-sample table, with a one-shot holdout (unread for
these cells).
