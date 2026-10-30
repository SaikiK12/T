# PREREG: xsbattery_v1 (R238). Eight untested cross-sectional features as one-week spread books

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R238
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_xsbattery.py`, `lab/screen.py`, `lab/flowfeat.load`
- **Queue:** M034 (weekly momentum and reversal), M180 (daily MAX, IVOL, skew), M182 (52-week high), M171 (funding
  slope), M178 (OHLC spread proxy)
- **Gate:** 0 (screen). This is the owner's brute-force pass: several features in one frozen family, every book
  counted.

## What the author has seen
- R222: 168 h MAX, low beta, residual momentum and premium net of funding. All NULL.
- R226: quote volume. R236: Amihud (discovery pass, validation fail). R234: positioning impulse.
- No statistic of any feature below in this universe at a one-week hold. The atlas (R185) has ret, donch, rsi and
  related views at horizons up to 72 h only.

## Features (per coin and hour t; known at the close of t)
| Name | Definition | Queue |
|---|---|---|
| mom7 | log(c_t / c_{t-168}) | M034 |
| rev28 | log(c_t / c_{t-672}) | M034 |
| maxd | max over the last 720 h of the 24 h log return | M180 |
| ivol | std over 720 h of r_i - r_mkt, where r_mkt is the equal-weight mean of eligible coins' hourly returns | M180 |
| skew | rolling skewness of hourly returns over 720 h | M180 |
| hi52 | log(c_t) - log(max c over the last 8,760 h); needs a full year | M182 |
| fslope | mean daily funding over 7 days minus over 30 days. Each settlement's rate is placed at its hour, 0 between settlements, NaN before the first record | M171 |
| arspread | Abdi-Ranaldo: sqrt(max(mean over 720 h of 4 (log c_{t-1} - eta_{t-1})(log c_{t-1} - eta_t), 0)), with eta = (log high + log low) / 2 | M178 |

Rolling windows need complete data (`min_periods` = window).

## Books (lab/screen.py, hold 168 h)
- For each feature, xs8 bins among eligible coins.
- **H** opens long one-week slices in bin 7 and short slices in bin 0. **L** is the reverse.
- Size 1 / (168 x K). Universe hedge, tier costs, funding.
- 8 features x 2 = **16 books** (trials).

## Stages (as R236)
1. **Discovery** 2021-01-01..2023-12-31. Pass if both hold:
   - 1x NW t (lag 10) >= 2;
   - 2x mean > 0.
2. **Validation** 2024-01-01..2025-06-30, for discovery passers only. Pass if the 1x mean is > 0 with t >= 1.5.
3. **Holdout:** not read. A validation passer becomes a candidate for a forward paper lane under a new id.

**Multiplicity note.** With 16 books and a one-sided 2.3% tail at t 2, about 0.4 false discovery passes are expected
under the null. That is before accounting for H and L being mirror images; at most one of each pair can pass. The
validation stage is the filter.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean, NW t, Sharpe, max drawdown, gross and cost;
  - per year;
  - trimmed mean.
- Coverage of each feature over eligible coin-hours.
- The correlation matrix of the H books' discovery daily nets, to show which features are the same bet.

## Multiplicity
- Trials = 16.
- Program trials before: 9,471,905 (after R237).

## Expectations
- **Literature:**
  - weekly momentum in large coins and reversal in small ones (Ficura 2023);
  - MAX signs conflict;
  - low IVOL and negative skew earn in equities.
- **Lab priors:**
  - R222 found nothing at 168 h for MAX or momentum;
  - R236 found that small and illiquid coins earned in 2021-23 and lost in 2024-25.
- **Most likely:**
  - one or two discovery passes from the features tied to size (ivol, arspread, hi52), which then fail validation, as
    R236 did;
  - NULL overall.
