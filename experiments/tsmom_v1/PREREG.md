# PREREG: tsmom_v1 (R237). Cross-asset time-series momentum on equity ETFs, FX, metals and bond futures

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R237
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_tsmom.py`. Data: `lab/markets.py` (Yahoo daily, fetched 2026-10-20). The runner records the
  sha256 of every parquet file it reads.
- **Queue:** M194; `docs/FOREX_AND_INDICES.md` row 1.
- **Gate:** discovery and validation are gate 0. The 2020-2026 window has never been read by this lab, so a pass there
  is gate-1 archive evidence. Published work covers part of that window.

## Why
Time-series momentum has the longest published record of any rule in the queue:
- Moskowitz-Ooi-Pedersen 2012;
- Hurst-Ooi-Pedersen, 1880-2016.

It is critiqued as weak since 2009. The owner asked for forex and index markets, and this is the standard first test
there.

## What the author has seen
- R235: turn-of-month and overnight drift on SPY and QQQ, 2000-2012 only (NULL).
- Structure checks on the Yahoo files: row counts, first and last dates, and open-equals-previous-close shares.
- No other return statistic of any symbol below.

## Universe (23 series, fixed now)
| Class | Series | Notes |
|---|---|---|
| Equity | SPY, QQQ, IWM, DIA | ETFs, dividend-adjusted (`adjclose`) |
| FX | EURUSD=X, GBPUSD=X, USDJPY=X, AUDUSD=X, USDCAD=X, USDCHF=X, NZDUSD=X, EURJPY=X, GBPJPY=X, EURGBP=X, AUDJPY=X, USDMXN=X, USDZAR=X, USDTRY=X | spot only: the interest differential is not in the returns |
| Metals | GC=F, SI=F, HG=F | Yahoo continuous front month, unadjusted; roll gaps stay in |
| Bonds | ZN=F, ZB=F | Yahoo continuous front month, unadjusted; roll gaps stay in |

Excluded before any statistic, because their roll gaps are large in unadjusted continuous series:
- energy and grains: CL=F (negative in 2020-04), NG=F, ZC=F, ZW=F.

Also excluded:
- VIX (not tradable);
- DX-Y.NYB (duplicates FX);
- index levels (no dividends) and index futures (roll gaps), because the ETFs cover them.

## Construction
- **Calendar:** each series on its own local trading dates (`attrs['tz']`). A panel is formed on the union of dates. A
  series' return on a date it did not trade is 0 and it holds no position change.
- **Signal:** at the last union date of each month, using closes through that date:
  - **TS12**: the sign of the trailing 252-trading-day return of the series;
  - **BLEND**: the sign of the average of the signs of the trailing 21-, 63- and 252-day returns, with 0 when they
    cancel.
- **Size:**
  - `w_i = signal_i x min(0.10 / vol_i, 3) / N`, where `vol_i` is the series' trailing 63-day standard deviation x
    sqrt(252), and N is the number of series with a defined signal that month;
  - the 3x cap per series stops tiny-volatility blow-ups.
- **Held** for the next month, from the first union date after the signal date.
- **Daily portfolio return:** `sum_i w_i r_i,d`.
- **Costs** at each rebalance, `c_i x |w_new - w_old|`:
  - 1 bp one-way for equity ETFs, FX majors, metals and bonds;
  - 2 bp for crosses (EURJPY, GBPJPY, EURGBP, AUDJPY);
  - 10 bp for USDMXN, USDZAR and USDTRY;
  - 2x and 3x reported.
- **Not included:**
  - FX carry, futures margin interest or cash yield;
  - the strategy holds its notional in cash at 0%.

Two strategies (trials): TS12 and BLEND.

## Windows and stages
Signals need 252 days of history, so a series enters when it has them.
1. **Discovery 2001-01-01..2012-12-31.** Pass if both hold:
   - 1x mean daily net > 0 with NW t (lag 10) >= 2;
   - 2x mean > 0.
2. **Validation 2013-01-01..2019-12-31**, for discovery passers only. Pass if the 1x mean is > 0 with t >= 1.5.
3. **Holdout 2020-01-01..2026-10-19**, for validation passers only, read once in the same run. Pass if the 1x mean is
   > 0 with t >= 2.
   - A pass goes to forward paper on daily bars under a new id. Real money only after gates 2-4.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean bp/day, annualized return and volatility, Sharpe, max drawdown (sum of daily returns);
  - turnover and cost.
- Beta to SPY and alpha (NW t).
- Per class (equity, FX, metals, bonds) at 1x.
- Per year.
- Trimmed mean (10 best and 10 worst days removed).

## Multiplicity
- Trials = 2.
- Program trials before: 9,471,903 (after R236's 2).

## Expectations
- **Discovery 2001-2012 includes 2008, TSMOM's best year.**
  - Most likely: discovery passes for TS12 (target volatility about 10%/N-diversified, Sharpe about 0.5-0.8 in the
    literature).
  - Validation 2013-2019 is the weak period in published work, so it may fail there.
- **Spot-only FX** removes carry, which matters most for the high-yield pairs.
