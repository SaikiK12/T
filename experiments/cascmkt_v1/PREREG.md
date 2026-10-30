# PREREG: cascmkt_v1 (R253). Buy the market after hours with many liquidation-cascade triggers

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R253
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_cascmkt.py`. It reuses `triggers()` from `scripts/run_oiwick.py` (R252), unchanged, and
  R252's book loop (`slices.run`, `hedge=False`, tier costs and funding).
- **Queue:** M233 (cascade-count market timing)
- **Gate:** 0 (screen).

## What the author has seen
- **R252, discovery 2021-23 (effectively 2022-23, because OI covers 10% of 2021):**
  - 658 long-cascade triggers (hourly OI drop >= 3% plus a lower wick >= 3 ATR).
  - The coin's raw price rose +143 bp over the next 24 h on average; market-adjusted only +23 bp.
  - So the bounce is mostly the whole market's. This idea comes from that post-hoc diagnostic.
- The author has **not** looked at:
  - how many coins trigger in the same hour;
  - the market's return after multi-coin hours;
  - anything in 2024-25 for this trigger.
- **The discovery window is spent for this idea.** The decided read is validation only.

## Rule
- **Trigger:** R252's long-cascade trigger, per eligible coin and hour (`triggers(...) == +1`, masked by eligibility).
- **Cascade hour:** an hour h where at least **K = 3** eligible coins trigger.
- **Position:** long the equal-weight market, w = 1 / (eligible coins) on every eligible coin.
  - It starts at the close of hour h and is held 24 h. A newer cascade hour restarts the 24 h.
  - Gross exposure is 1 while held.
- **Books:** `slices.run(hedge=False)`, with tier costs (1x, 2x, 3x) and funding as in R252.

## Stage (1 trial)
- **Validation 2024-01-01..2025-06-30** is the decided read. Pass if all hold at 1x:
  - mean > 0;
  - NW t (10 lags) >= 2;
  - 2x mean > 0;
  - alpha against the equal-weight market's daily return > 0.
- The bar is t >= 2, not R252's 1.5, because the idea was chosen after seeing 2022-23.
- **Holdout:** not read; it is spent at program level.

## Reported (not decided on)
- Cascade hours per year.
- **The equal-weight market's mean forward return after cascade hours** (1, 4 and 24 h), against the unconditional
  mean over all hours, in both windows.
- Book statistics at 1x/2x/3x (mean, t, gross, cost, exposure, alpha, beta, per year, trimmed mean). Also the same
  on 2022-23, labelled post hoc.
- Cascade-hour counts and the 24 h forward market return for K = 1, 2 and 5 (descriptive).

## Multiplicity
- Trials = 1.
- Program trials before: 9,472,001 (after R252).

## Expectations
- Sell-off rebounds are a known crypto pattern, but they are mixed with continuation in crashes (2022).
- 2024-25 had fewer crashes than 2022, so cascade hours will be rare. Power is low.
- **Most likely:** NULL, with few events.
