# FINDINGS: chartxm_v1 (R247). R243's seven chart rules on daily forex and world equity indices

**Verdict: NULL.** None of the 14 books passed discovery (2001-2012). Validation and the holdout were not read.
- On indices, the oscillator fades and the trend rules were mildly positive. The best was CCI, alpha +1.5 bp/day,
  t 1.50.
- On forex, nothing was positive beyond t 1.
- **Pivot breakouts lost in both groups:** alpha t -2.49 in forex and **-4.16 on indices**. R243 found the same on
  crypto 4 h and daily bars.

- **Registry row:** R247 (trials 14). Program trials after it: 9,471,979.
- **Gate:** 0.
- **Reproduce:** prereg sha 9c0a3cbb, frozen in commit b1da463 before the run. Run `python scripts/run_chartxm.py`
  (seconds).
- **Origin:** queue M210 (forex and index leg), M200, M202, M203.

## A bug, fixed after the first run (disclosed)
- **The bug:** the first run started each book at the day of its *largest* total position (`argmax` of the position
  sum) instead of its first nonzero position, as the PREREG says. The PREREG text governs.
- **What it changed:** 5 of the 7 FX books lost early years from discovery. STOCH/FX started only in 2009 and showed
  alpha +1.40, t 1.98, a near miss. BOLL/IDX started in 2006.
- **The fix:** a one-line change to the first nonzero position, then a rerun.
  - STOCH/FX over its full window is +0.25, t 0.57.
  - No verdict changed: nothing passed in either run.
- **Records:** the first run is kept in `run_firstpass_startbug.log` and `results/books_firstpass_startbug.csv`. The
  tables below are the corrected run.

## Numbers (discovery; 1x; alpha against the group's equal-weight buy-and-hold)

| Book | Net bp/day | Gross / cost | Turnover /yr | Beta | Alpha bp/day (t) | Alpha at 2x / 3x | Long share | Days |
|---|---|---|---|---|---|---|---|---|
| SUPERTREND_RSI/FX | -1.01 | -0.87 / 0.15 | 37 | -0.34 | -0.92 (-1.38) | -1.07 / -1.21 | 52% | 3,125 |
| MACD/FX | -0.39 | -0.23 / 0.16 | 40 | -0.18 | -0.34 (-0.50) | -0.50 / -0.66 | 51% | 3,125 |
| STOCH/FX (fade) | +0.29 | +0.45 / 0.16 | 41 | +0.16 | +0.25 (0.57) | +0.09 / -0.08 | 44% | 3,125 |
| CCI/FX (fade) | -0.88 | -0.69 / 0.19 | 48 | +0.22 | -0.94 (-1.89) | -1.13 / -1.32 | 47% | 3,125 |
| BOLL/FX (fade) | +0.23 | +0.35 / 0.12 | 29 | +0.08 | +0.21 (0.96) | +0.09 / -0.02 | 47% | 3,125 |
| ICHIMOKU/FX | -0.21 | -0.12 / 0.10 | 25 | -0.28 | -0.14 (-0.22) | -0.24 / -0.34 | 53% | 3,125 |
| PIVOT_BREAK/FX | -1.34 | -0.64 / 0.70 | 177 | -0.11 | -1.31 (**-2.49**) | -2.01 / -2.71 | 52% | 3,125 |
| SUPERTREND_RSI/IDX | +0.65 | +0.78 / 0.14 | 35 | -0.33 | +1.14 (0.80) | +1.00 / +0.86 | 59% | 3,123 |
| MACD/IDX | +0.37 | +0.52 / 0.15 | 39 | -0.20 | +0.67 (0.43) | +0.51 / +0.36 | 51% | 3,123 |
| STOCH/IDX (fade) | +1.28 | +1.44 / 0.16 | 41 | +0.13 | +1.08 (1.03) | +0.92 / +0.75 | 34% | 3,123 |
| CCI/IDX (fade) | **+1.83** | +2.04 / 0.20 | 51 | +0.23 | **+1.49 (1.50)** | +1.29 / +1.08 | 41% | 3,123 |
| BOLL/IDX (fade) | +0.86 | +0.97 / 0.11 | 28 | +0.12 | +0.68 (1.36) | +0.57 / +0.46 | 54% | 3,123 |
| ICHIMOKU/IDX | +0.99 | +1.07 / 0.08 | 21 | -0.34 | +1.50 (1.10) | +1.42 / +1.34 | 63% | 3,123 |
| PIVOT_BREAK/IDX | -3.98 | -3.22 / 0.76 | 193 | -0.12 | -3.81 (**-4.16**) | -4.57 / -5.34 | 53% | 3,123 |

FX days start in 2001 because USDJPY and EURGBP start in 2000; most other pairs join in 2003-04, and AUDUSD in 2006-05.

Alpha per year at 1x (bp/day):

| Book | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PIVOT_BREAK/IDX | +0.1 | -7.2 | -2.7 | -1.3 | -0.7 | -4.2 | -5.0 | -17.0 | -2.5 | -2.7 | -1.6 | -0.9 |
| PIVOT_BREAK/FX | -4.3 | +0.2 | +0.4 | -2.5 | +1.1 | -0.7 | -3.8 | -4.7 | +0.8 | -0.3 | -0.0 | -1.8 |
| CCI/IDX | -1.6 | +6.0 | +0.5 | -0.7 | -1.6 | -0.0 | +2.3 | +11.8 | -1.5 | -1.0 | +3.9 | -0.2 |
| STOCH/IDX | -1.0 | +1.9 | +1.5 | -0.1 | -1.2 | -0.3 | +1.8 | +7.7 | -0.6 | -0.5 | +3.6 | +0.1 |

## Cost sensitivity
- 1 bp one-way at 1x. Every rule except the pivot breaks trades 20-50 times its book per year, so costs are 0.1-0.2
  bp/day and no sign changes at 3x.
- The pivot books turn over 177-193 times a year (0.7-0.8 bp/day at 1x). Their loss is mostly gross.
- **The index fades' alphas are 1-3 bp/day in a world of 0.2 bp/day costs.** Retail CFD spreads on world indices
  (often 1-2 points, i.e. 0.5-1 bp) would cost about 2-5x this model's 1x.

## Reading
- **Daily chart rules on forex carried nothing in 2001-12.** That covers trend (Supertrend, MACD, Ichimoku), fades
  and breaks, consistent with R239's weak spot momentum.
- **On equity indices, the signs follow daily mean reversion.**
  - Fades of extremes (CCI, Stochastic, Bollinger) are positive, with t 1.0-1.5. 2008 is the largest year in each.
  - A close beyond the prior day's R1/S1 reverses: PIVOT_BREAK/IDX alpha -3.81 bp/day, t -4.16, negative in 11 of 12
    years.
- **Pivot breaks lose in three markets.**
  - Crypto (R243): 4 h net -10.3 bp/day, t -1.91; 1 d -14.5, t -1.99.
  - Forex daily: alpha t -2.49. Indices daily: alpha t -4.16.
  - So the mirror, fading a close beyond R1/S1, would have earned before costs in every market in discovery. That is a
    post-hoc reading of a losing book, not a tested rule. It is queued as M231, whose first fair read is the 2013-19
    validation decade.
- **Trend on indices** (Supertrend, Ichimoku) has positive alpha, because the books carry a negative beta (-0.33)
  and so hedge the market. It is not significant.

## New queue row
- **M231: floor-pivot fade on daily indices and forex** (mirror of PIVOT_BREAK).
  - Short a close above the prior day's R1, long a close below S1, held a day.
  - Frozen on this lane's discovery reading. Validation 2013-19 is its first unseen window, then the 2020-26 holdout,
    read once.
  - Variants: crypto 4 h, and a band of 0.1-1 ATR beyond the level (M203).

## Not checked
- FX rollover (carry), index dividends and financing.
- Next-open execution instead of the close.
- Commodities and bonds: Yahoo's continuous futures are not back-adjusted, so roll gaps would contaminate the returns.
- Other parameters of the seven rules (R243's were kept frozen).
- Intraday bars for forex and indices (Dukascopy phase 2 needs the owner's yes).
- Validation and the holdout.
