# PREREG: chartxm_v1 (R247). R243's seven chart rules on daily forex and world equity indices

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R247
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_chartxm.py`. It reuses `states()` from `scripts/run_chartist.py` (R243, frozen) unchanged, and
  the window and decision rules of R239 (`scripts/run_fxindex.py`).
- **Queue:** M210 (chartist brute force, its forex/index leg), M200, M202, M203 (non-crypto leg)
- **Gate:** 0 (screen).

## What the author has seen
- **R243 (crypto, 2021-23):**
  - The fades lost.
  - Daily Supertrend+RSI was the best at +11.3 bp/day, t 1.23. Ichimoku on 4 h was +6.1, t 0.79.
- **R239:**
  - G10 spot momentum (63-day, monthly rebalanced) got t 1.20 in 2006-12.
  - Dollar trend got nothing.
  - Yahoo FX has four spike-and-reversal bad prints in 2008-09.
- **R241/R242:** trend and volatility rules on SPY/QQQ.
- **Not computed on these series:** any of the seven rules below, by anyone in this lab.

## Data (Yahoo daily via `lab/markets`, cached)
- **FX group (11 pairs, spot):** EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF, EURGBP, EURJPY, GBPJPY,
  AUDJPY. Long means long the base currency.
  - USDMXN, USDZAR and USDTRY are left out, because spot returns ignore their large interest carry.
- **IDX group (10 price indices):** ^GSPC, ^NDX, ^DJI, ^RUT, ^GDAXI, ^FTSE, ^N225, ^HSI, ^STOXX50E, ^AXJO.
- **Bars:** each series is on its own exchange calendar and time zone.
  - Rows with a non-positive open, high, low or close are dropped.
  - Bars after 2026-10-19 are dropped.
  - No other cleaning, and the bad prints stay in. The count of daily moves above 8% per FX pair is reported.

## Rules (`run_chartist.states`, daily bars, the parameters frozen in R243)
SUPERTREND_RSI, MACD, STOCH (fade), CCI (fade), BOLL (fade), ICHIMOKU, PIVOT_BREAK. PIVOT_BREAK's levels come from the
previous bar's high, low and close. Each rule gives every asset a state s in {-1, 0, +1} at each close.

## Books (14 trials = 7 rules x 2 groups)
- **Calendar:** the union of the group's trading days. An asset's state carries over its holidays. Its return is 0 on
  its holidays, and its next bar's close-to-close return includes the move over the holiday.
- **Weights:** w_i,d = s_i,d / N_d, where N_d is the number of the group's assets with a defined state that day.
  - Set at the close of day d, earning day d+1's close-to-close return.
  - Executed at the close (FX at Yahoo's daily snapshot); no next-open delay.
- **Cost:** 1 bp one-way per unit of weight change at 1x (FX majors, index futures or CFDs). Reported at 2x and 3x.
- **Not modelled:** FX rollover, index dividends and financing.
- **Benchmark:** the group's equal-weight buy-and-hold of the assets with data.
- **Test statistic:** the alpha of the 1x net against that benchmark, by in-window OLS (`etf_row` style), with
  Newey-West t at lag 10.
- A book's days start at its first nonzero position.

## Stages (as R239)
1. **Discovery 2001-01-01..2012-12-31** (FX effectively from 2004, when Yahoo's pairs start). Pass if all hold:
   - test t >= 2;
   - 2x test mean > 0;
   - 1x net mean > 0.
2. **Validation 2013-01-01..2019-12-31**, for discovery passers. Pass if the test mean > 0 with t >= 1.5.
3. **Holdout 2020-01-01..2026-10-19**, read once, for validation passers only. Pass if the test mean > 0 with t >= 2.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - net, gross, cost, turnover;
  - Sharpe, max drawdown, beta;
  - alpha and t, trimmed alpha, per year;
  - long and short shares.

## Multiplicity
- Trials = 14.
- Program trials before: 9,471,965 (after R246).

## Expectations
- **Trend rules** (Supertrend+RSI, MACD, Ichimoku) on FX: the managed-futures literature (Moskowitz-Ooi-Pedersen 2012;
  Hurst-Ooi-Pedersen 2017) has FX trend positive before 2012 and weak after.
- **Equity indices:** short-horizon trend is weak, with a reversal tilt in daily data. Fades of extremes (Bollinger,
  CCI) have some support (Connors-style index mean reversion).
- **Most likely:** at most one or two discovery passes, none surviving the validation decade. NULL overall.
