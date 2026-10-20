# PREREG: volrisk_v1 (R241). Short-volatility timing on SVXY, and R239's VIX reversal on unseen years

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R241
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_volrisk.py`, which imports the loaders, `vixrev`, `etf_row` and `decide` from
  `scripts/run_fxindex.py` unchanged. Data: Yahoo daily via `lab/markets.py`, cached 2026-10-20. The runner records
  each file's sha256.
- **Queue:** M224 (SVXY in contango), M214 (VIX term-structure carry with a VIX filter), M226 (VIXREV-QQQ on
  2013-2026). M197 (VIX spike reversion on the index) is the same idea as M218/M226.
- **Gate:** 0, with the holdout read once in the same run for validation passers (as R235 and R239).

## What the author has seen
- R239: the VRP measure (VIX² minus next-month realised variance) was positive on 82-85% of days in every window, with
  t 2.55 / 5.71 / 1.11 by window. VIXREV-QQQ had alpha +2.94 bp/day, t 1.94 in 2001-2012 and was not run later.
- Data structure only: SVXY starts 2011-10-04, ^VIX3M 2006-07-17, ^VIX and QQQ 2000.
- Not computed by this lab: any SVXY return, any statistic of VIX vs VIX3M, any QQQ or VIX statistic after 2012.
- Known from public history (not from this data): SVXY lost about 80-90% on 2018-02-05 and moved from -1x to -0.5x
  VIX-futures exposure on 2018-02-28. The 2020 crash was a second large loss. Both lie in the windows below, and that
  is intended.

## Rules
**1. SVXY-CONTANGO (M224).** Each day d, the signal is long if the ^VIX close of d-1 is below the ^VIX3M close of
d-1, otherwise flat. The VIX closes are stamped 16:15 New York, after SVXY's 16:00 close, so the position changes at
the open of d and is held until the open of the next change.
- Daily return on day d: `s_{d-2} x overnight_d + s_{d-1} x intraday_d`, where `overnight_d = adj_open_d /
  adjclose_{d-1} - 1` and `intraday_d = adjclose_d / adj_open_d - 1`. Adjusted open = `open x adjclose / close`.
- Costs: 3 bp one-way at 1x per position change, charged on the day of the change. SVXY's quoted spread is wider than
  SPY's.

**2. SVXY-CALM (M214).** The same as rule 1, but long only if the VIX close of d-1 is also below the median of the
VIX closes over the 252 trading days ending at d-1. The M214 note's hard loss limit is left out: R208 found stops
harmful, and a stop is a second rule.

**3. VIXREV-QQQ (M226).** Exactly R239's rule:
- a trigger on day d when QQQ's close-to-close return is below -1% and the ^VIX close of d-1 is above 25;
- long from the adjusted open of d+1 to the close of d+5, with a new trigger extending the exit;
- costs 1 bp one-way.

Three trials.

## Tests and stages
- **SVXY rules** are judged on PnL: the mean daily net with NW t at lag 10. Reported, not tested: the alpha against
  buy-and-hold SVXY and the beta to SPY.
  - **Discovery 2011-10-05..2016-12-31:** pass if the 1x t >= 2 and the 2x mean > 0.
  - **Validation 2017-01-01..2019-12-31:** pass if the 1x mean > 0 with t >= 1.5.
  - **Holdout 2020-01-01..2026-10-19:** read once, for validation passers. Pass if the 1x mean > 0 with t >= 2.
- **VIXREV-QQQ** is judged as in R239, on its alpha against buy-and-hold QQQ. Its 2001-2012 discovery is seen and
  failed (t 1.94), so the test starts here.
  - **Validation 2013-01-01..2019-12-31:** pass if the 1x alpha > 0 with t >= 1.5 and the 2x alpha > 0.
  - **Holdout 2020-01-01..2026-10-19:** read once, if validation passes. Pass if the 1x alpha > 0 with t >= 2.
- A holdout pass is gate-1 archive evidence (`docs/GATES.md`). It then needs a forward paper lane under a new id. A
  short-volatility book also needs a gate-3 account-risk review, whatever its t.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean net bp/day, annual return and volatility, Sharpe, max drawdown;
  - share of days invested;
  - beta to SPY (SVXY rules), alpha and beta against buy-and-hold (all rules);
  - trimmed mean (10 best and 10 worst days removed).
- Per-year means.
- Buy-and-hold SVXY for comparison.
- The worst single day and the worst 5-day loss of each SVXY rule.
- VIXREV-QQQ: triggers per window.

## Multiplicity
- Trials = 3.
- Program trials before: 9,471,930 (after R240).
- VIXREV-QQQ was chosen as the best of R239's six rules on 2001-2012, so this test inherits a best-of-6 selection.

## Expectations
- **SVXY-CONTANGO:**
  - Contango holds on most days, so the rule is invested about 80-85% of the time.
  - In 2011-2016 SVXY rose strongly, so a discovery pass is likely.
  - Validation contains February 2018. Whether the one-day signal was flat before 2018-02-05 decides that window, and
    the author does not know.
  - Most likely: discovery pass; validation decided by one day.
- **SVXY-CALM** is invested less, so it is likely to be safer and weaker.
- **VIXREV-QQQ:** 2013-2019 had few days with VIX above 25 (late 2015, early and late 2018), so the test is thin.
  Most likely NULL for lack of triggers.
