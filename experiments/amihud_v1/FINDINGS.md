# FINDINGS: amihud_v1 (R236). Amihud illiquidity as a one-week spread book

**Verdict: NULL.** illiq/H passed discovery and then lost in validation. The holdout was not read.

- **Registry row:** R236 (trials 2). Program trials after it: 9,471,903.
- **Gate:** 0.
- **Reproduce:** prereg sha 40e7252d, frozen in commit 3261d04 before the run. Run `python scripts/run_amihud.py`
  (about 2 minutes).
- **Origin:** queue M002.
- **Feature coverage:** finite for 93% of eligible coin-hours in 2021-2025H1. It needs 720 complete hours.

## Numbers (1x / 2x / 3x; K 11.8 slices per hour; 168 h hold)

| Book | Window | Net bp/day | NW t (1x) | Residual vs qv_lvl, bp/day (t) | Corr with qv_lvl | Trimmed (1x) | Gross / cost (1x) |
|---|---|---|---|---|---|---|---|
| illiq/H | discovery | +11.9 / +11.1 / +10.3 | **2.28** | +9.5 (2.02) | -0.52 | +10.0 | 12.7 / 0.8 |
| illiq/H | validation | -9.2 / -10.0 / -10.8 | -1.07 | +1.9 (0.24) | -0.53 | -12.1 | -8.4 / 0.8 |
| illiq/L | discovery | -13.4 / -14.2 / -15.0 | -2.58 | -11.0 (-2.36) | +0.52 | -11.6 | -12.7 / 0.8 |

- H longs the most illiquid coins and shorts the most liquid.
- Per year for illiq/H at 1x: 2021 +19.5, 2022 +6.7, 2023 +9.4, 2024 -4.2, 2025H1 -19.4 bp/day.

## Cost sensitivity
A one-week hold costs 0.8 bp/day at 1x, so the verdict does not depend on cost. The validation loss is gross.

## Reading
- **The illiquidity premium was there in 2021-2023 and reversed in 2024-25.** All three discovery years were positive,
  and both validation years negative.
  - This matches the 2024-25 market: large caps (BTC, ETF-driven names) led, and small alts lagged.
  - It is the same reversal the lab saw in other small-coin longs.
- **Most of the book is inverse volume.** Its correlation with the long-high-volume book is -0.52.
  - Against that book, the residual stayed positive in validation (+1.9 bp/day), but with t 0.24.
  - The validation loss is the volume-size part, not the price-impact part. Seen after the run; a description only.
- **Drawdown:** the 1x book's drawdown reached 32% in discovery and 82% in validation (sums of daily returns at unit
  size). An illiquid long book is a squeeze and liquidity-crash exposure.

## Not checked
- Other lookbacks (7 or 90 days) and holds.
- One-sided books.
- The residual (Amihud orthogonal to volume) as its own book.
- The holdout.
