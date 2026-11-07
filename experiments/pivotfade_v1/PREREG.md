# PREREG: pivotfade_v1 (R248). Fade a close beyond the prior day's floor pivot R1/S1

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R248
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_pivotfade.py`. It reuses, unchanged:
  - `states()`, `resample()` and `prev_day_levels()` from `scripts/run_chartist.py` (R243);
  - `bars()`, `asset_states()`, `book()` and `row()` from `scripts/run_chartxm.py` (R247);
  - the crypto window loop of R243.
- **Queue:** M231 (floor-pivot fade), M203
- **Gate:** 1 for the forex and index books, whose 2020-26 holdout has not been read for this family; 0 for crypto.

## Why this lane exists, and what the author has seen
The rule is the exact mirror of PIVOT_BREAK, which lost in every discovery window it was run on:
- R247 daily indices 2001-12: alpha -3.81 bp/day, t -4.16, negative in 11 of 12 years; FX alpha t -2.49.
- R243 crypto 2021-23: 4 h net -10.3 bp/day, t -1.91; 1 d -14.5, t -1.99.

The rule was chosen by looking at those windows, so **they are spent and are not read again as evidence.** No
statistic of the fade, or of any pivot rule, has been computed on:
- 2013-2026 for forex and indices;
- 2024-2025 for crypto.

## Rule
- P = (H + L + C) / 3 of the previous bar's day; R1 = 2P - L; S1 = 2P - H.
- At each bar's close:
  - close > R1 gives s = -1;
  - close < S1 gives s = +1;
  - otherwise s = 0.
- This is -1 x R243's PIVOT_BREAK state. The state is held until the next bar's close.

## Books (4 trials)
1. **PIVOT_FADE/IDX:** the 10 R247 indices (^GSPC, ^NDX, ^DJI, ^RUT, ^GDAXI, ^FTSE, ^N225, ^HSI, ^STOXX50E,
   ^AXJO), daily bars.
2. **PIVOT_FADE/FX:** the 11 R247 forex pairs, daily bars.
3. **PIVOT_FADE/CRYPTO-4h:** top-50 perps, 4 h bars.
4. **PIVOT_FADE/CRYPTO-1d:** top-50 perps, daily bars.

**Construction, forex and indices.** As R247, with no change:
- union calendar, with the state carried over holidays;
- w = s / N_d, set at the close and earning the next close-to-close return;
- 1 bp one-way per unit of weight change at 1x (2x and 3x reported);
- alpha by OLS against the group's equal-weight buy-and-hold, with NW t at lag 10.

**Construction, crypto.** As R243, with no change:
- position s / (eligible coins) held from the bar's last hourly row to the next bar;
- `slices.run(hedge=False)` with tier costs and funding;
- alpha against the equal-weight market.

## Windows and decisions
- **Forex and indices.** Discovery 2001-12 is spent and not read again.
  1. **Validation 2013-01-01..2019-12-31.** Pass if all hold:
     - 1x alpha > 0 with NW t >= 2;
     - 2x alpha > 0;
     - 1x net mean > 0.
  2. **Holdout 2020-01-01..2026-10-19**, read once, for validation passers only. Pass if the 1x alpha > 0 with t >= 2
     and the 2x alpha > 0.
- **Crypto.** Discovery 2021-23 is spent; the 2025-07 holdout is spent at program level.
  - **Validation 2024-01-01..2025-06-30** only. Pass if all hold:
    - 1x mean > 0 with NW t >= 2;
    - 2x mean > 0;
    - alpha > 0.

## Control (reported, not decided on)
- **REV1D:** for each group and window read, the same book with s = -sign(today's close-to-close return). This is
  generic one-bar reversal, on the same assets, calendar and costs.
- Reported:
  - the control's alpha;
  - the difference PIVOT_FADE minus REV1D in daily 1x alpha series, with its NW t.

  This shows whether the pivot level adds anything to plain reversal.

## Reported (not decided on)
- Per window read, at 1x, 2x and 3x:
  - net, gross, cost, turnover;
  - Sharpe, max drawdown, beta;
  - alpha and t, trimmed alpha, per year;
  - the long and short share.

## Multiplicity
- Trials = 4 (the control is not a trial).
- Program trials before: 9,471,979 (after R247).

## Expectations
- **Forex and indices:** index daily reversal weakened after 2010 in the literature. Most likely the index fade stays
  positive gross, but under t 2 in 2013-19. Forex is near zero.
- **Crypto:** R245 found liquid coins continue at 1 day, so the crypto fade is most likely negative after costs.
- **Most likely:** NULL. The one plausible pass is PIVOT_FADE/IDX.
