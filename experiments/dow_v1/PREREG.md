# PREREG: dow_v1 (R254). Day-of-week effects on the S&P 500, world indices, the US dollar, BTC and crypto

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R254
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_dow.py`. It reuses, unchanged:
  - `etf()`, `fx_returns()`, `etf_row()`, `COST` and `WINDOWS` from `scripts/run_fxindex.py` (R239);
  - `bars()` and `GROUPS` from `scripts/run_chartxm.py` (R247);
  - the crypto universe and `slices.run`, as in R252.
- **Queue:** M219 (calendar effects; the day-of-week part, which is untested)
- **Gate:** 0 (screen).

## What the author has seen
- **R239:** Halloween on SPY (alpha t 1.32, discovery fail) and pre-holiday on SPY.
- The lab has computed no weekday statistic.
- **Literature:**
  - The weekend/Monday effect was negative Monday returns in US stocks before the 1990s, and has mostly faded since.
  - Crypto studies report weekday patterns that do not replicate across samples.

## Markets (5) and weekdays
- **SPY:** daily total return (`etf("SPY").r`). Weekdays Mon-Fri.
- **IDX:** the equal-weight mean of the daily close-to-close returns of R247's 10 indices, on each index's own
  calendar. A date's mean is over the indices that traded that date. Weekdays Mon-Fri.
- **USD:** minus the mean of the 7 G10 currencies' daily returns against the dollar (`fx_returns()`). Weekdays Mon-Fri.
  - Saturday and Sunday rows, if any, are dropped from all Yahoo series, and the count is reported.
- **BTC:** the BTCUSDT perp, hourly `u.ret`. A UTC day d means the bars opening 00:00-23:00 UTC on d. Weekdays Mon-Sun.
- **CRYPTO:** the equal-weight top-50 eligible perps, same timing. Weekdays Mon-Sun.

Trials = 5 + 5 + 5 + 7 + 7 = 29 weekday books (one selected per market).

## Book for weekday d and sign s
- **Yahoo markets:** hold s x the market over day d only, entering at the previous close and exiting at d's close.
  - Net = s x r_d - 2 x 1 bp x cmult on each traded day; 0 on other days.
- **Crypto:** `slices.run(hedge=False)` with tier costs and funding.
  - Position s / (eligible coins) on each eligible coin for CRYPTO, or s on BTC, on every hourly row whose earned bar
    opens in UTC weekday d.
- **Alpha:** net regressed on the market's own daily return over all days of the window (lstsq, as `etf_row`).
  - Alpha is the intercept's mean (bp/day), with NW t (10 lags).
  - So alpha measures day d's excess over the market's average day, not market exposure.
  - For crypto the daily reference is the market's (EW, or BTC's) return summed in the same 24-row day blocks as the
    book's nets.

## Selection (per market, in discovery only)
- For each weekday d, take the s = +1 book at 1x.
- Pick the d with the largest |alpha t|, and set s = the sign of that alpha.
- The selected (d, s) is then frozen for later windows.

## Stages (per market, on the selected book)
| Stage | Yahoo window | Crypto window | Pass if |
|---|---|---|---|
| 1. Discovery | 2001-01-01..2012-12-31 | 2021-01-01..2023-12-31 | alpha t >= 2; 2x alpha > 0; 1x net > 0 |
| 2. Validation | 2013-01-01..2019-12-31 | 2024-01-01..2025-06-30 | alpha > 0 and alpha t >= 1.5 |
| 3. Holdout | 2020-01-01..2026-10-19, read once for validation passers | not read (spent at program level) | alpha > 0 and alpha t >= 2 |

## Reported (not decided on)
- **Discovery, per market and weekday:** n days, mean day-d return (bp), alpha (bp/day of book) and alpha t, at
  s = +1. This is the selection table.
- **Validation, the same table for every weekday.** Descriptive only; the verdict uses the selected book alone.
- **Selected books at 1x/2x/3x:** net mean, NW t, alpha, alpha t, beta, cost, alpha per year.

## Multiplicity
- Trials = 29.
- Program trials before: 9,472,002 (after R253).

## Expectations
- **Yahoo:** US and world index weekday effects have mostly vanished since 2000. An index book may pass discovery on
  2001-12 crash days and then fail.
- **USD:** no known weekday effect.
- **Crypto:** three years give about 156 of each weekday, so a weekday alpha needs about 20+ bp per day to reach t 2.
  Weekend days have lower volume, and Monday has been reported as strong in some samples.
- **Most likely:** NULL in all five.
