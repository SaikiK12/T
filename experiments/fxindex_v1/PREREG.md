# PREREG: fxindex_v1 (R239). Forex and US-index battery: G10 momentum, dollar trend, VIX reversal, calendar, VRP

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R239
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_fxindex.py`. Data: `lab/markets.py` (Yahoo daily, cached 2026-10-20). The runner records the
  sha256 of each parquet file it reads.
- **Queue:** M193 (forex momentum, spot part only), M216 (dollar trend), M218 (index reversal in high VIX), M219
  (calendar effects: Halloween and pre-holiday), M215 (volatility risk premium, measurement).
- **Gate:** 0 (screen), with the holdout read once in the same run for validation passers (as R235).

## What the author has seen
- R235: turn-of-month and overnight on SPY/QQQ. R237: 12-month trend on 23 series, where the 14 FX pairs together
  contributed -0.10 bp/day gross in 2001-2012.
- Before freezing, the author checked data structure only: first and last dates of each file. Most FX pairs start
  2003-09..2003-12 on Yahoo (USDJPY and EURGBP in 2000); ^VIX from 2000; SVXY only from 2011-10 and VXX from 2018,
  so a tradeable short-volatility rule cannot be tested in 2001-2012 and is left out.
- No return or statistic of the rules below has been computed by this lab. The published results are known: FX
  momentum (Menkhoff et al. 2012, mostly with carry), the dollar factor (Lustig et al. 2011), short-term reversal
  after market drops in high volatility (Nagel 2012), the Halloween effect (Bouman-Jacobsen 2002), the pre-holiday
  effect (Ariel 1990), and the variance risk premium (Carr-Wu 2009). Several of these samples end before 2013, so the
  later windows are unread by this lab, not by the field.

## Data
- Each series on its own dates, as R237: the bar's timestamp converted to its exchange time zone and normalised to a
  date. FX bars are stamped at London midnight.
- ETF returns use `adjclose`. Adjusted open = `open x adjclose / close`.
- **G10 currencies vs USD (7):** EUR, GBP, AUD, NZD (from XXXUSD=X) and JPY, CAD, CHF (from USDXXX=X, inverted). The
  daily return of a currency is `px_d / px_{d-1} - 1` for XXXUSD and `px_{d-1} / px_d - 1` for USDXXX.
- **Spot only.** Carry (the interest differential) is not in any FX return here: no free rate series for the other
  six currencies is reachable (FRED is blocked). Before 2009 the AUD/NZD vs JPY/CHF differential was 3-6%/yr, so a
  rule that is long AUD/NZD and short JPY/CHF is understated by this test and the reverse overstated. EM currencies
  are left out because their carry is larger still.

## Rules (seven trials)
1. **FXMOM:** at each month end, rank the 7 currencies by their 63-trading-day return. Long the top 2 and short the
   bottom 2, weight 1/2 each side (gross 2). Held from the next date to the next month end. Costs 1 bp one-way per
   unit of weight change (G10 majors).
2. **DOLLAR:** the equal-weight basket of the 7 currencies vs USD. At each month end, the sign of its 252-day return
   sets the position: long the basket (short USD) if positive, short if negative. Weight 1. Costs 1 bp one-way.
3. **VIXREV-SPY** and 4. **VIXREV-QQQ:** a trigger on day d when the ETF's close-to-close return is below -1% and the
   ^VIX close of day d-1 is above 25 (d-1 so the VIX close, stamped 16:15, is known before the ETF close). Long from
   the adjusted open of d+1 to the close of d+5. A new trigger while long extends the exit to its own d+5. Long or
   flat. Costs 1 bp one-way at each entry and exit.
5. **HALLOWEEN-SPY:** long SPY from the close of the last trading day of October to the close of the last trading day
   of April; flat from May to October. Flat earns 0. Costs 1 bp one-way.
6. **PREHOL-SPY:** long SPY over trading day d (close d-1 to close d) when the next trading day after d is more than
   one weekday away, so d is the last session before an exchange holiday. Weekends do not count as gaps. Exchange
   holidays are published in advance, so the rule has no look-ahead. Two closures were not known in advance and are
   excluded: 2001-09-10 (closed 11-14 September) and 2012-10-26 (Hurricane Sandy, closed 29-30 October). Closures for
   state funerals (2004, 2007, 2018, 2025) were announced days before and count. Costs 1 bp one-way.
7. **VRP (measurement):** each day d, `vrp_d = (VIX_d / 100)^2 x 21 / 252 - sum_{k=1..21} ln(1 + r_{d+k})^2`, with r
   the SPY close-to-close return. It is the implied minus the next 21 days' realised variance. Not a tradeable book
   (options and VIX futures data are paid); it tests whether the premium a short-volatility seller would harvest was
   there. Its NW t uses lag 21 because the windows overlap.

## Tests
- **ETF rules 3-6:** as R235, the alpha against buy-and-hold of the same ETF. Regress the daily net on the ETF's
  close-to-close return; the alpha is the mean of `net - b x r`, with NW t at lag 10.
- **FX rules 1-2:** the raw daily net (long/short, so no market leg to remove), with NW t at lag 10. Beta to SPY is
  reported, not tested.
- **VRP:** the mean of vrp_d in units of annualised variance points, with NW t at lag 21.

## Windows and stages
1. **Discovery 2001-01-01..2012-12-31.** FX rules start when all 7 currencies have their lookback (about 2004-04 for
   FXMOM, 2004-12 for DOLLAR; the runner logs the first date). Pass if both hold:
   - 1x NW t (alpha t for ETF rules) >= 2;
   - 2x mean (alpha mean for ETF rules) > 0. For VRP, the mean > 0.
2. **Validation 2013-01-01..2019-12-31**, for discovery passers only. Pass if the 1x mean (alpha) is > 0 with t >= 1.5.
3. **Holdout 2020-01-01..2026-10-19**, for validation passers only, read once in the same run. Pass if the 1x mean
   (alpha) is > 0 with t >= 2. A pass is gate-1 archive evidence (`docs/GATES.md`), with the caveat above; it then
   needs a forward paper lane under a new id.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x: mean net bp/day, annual return and volatility, Sharpe, max drawdown, gross
  and cost, beta to SPY, share of days invested (ETF rules), turnover (FX rules), trimmed mean (10 best and 10 worst
  days removed).
- Per-year 1x means.
- FX: the count of G10 daily moves above 8% in absolute value (bad-tick check). Nothing is filtered.
- VIXREV: number of triggers per window.

## Multiplicity
- Trials = 7.
- Program trials before: 9,471,921 (9,471,905 after R237, plus R238's 16).

## Expectations
- **FXMOM:** spot-only G10 momentum is weak in the literature after costs. Most likely NULL.
- **DOLLAR:** R237's FX trend was flat. Most likely NULL.
- **VIXREV:** reversal after drops in high volatility is the strongest published idea here, but it has few triggers
  (high-VIX days cluster in 2002, 2008-09, 2010-11), so t is limited. A discovery pass is possible; 2013-2019 had
  few VIX>25 days, so validation will be thin.
- **HALLOWEEN:** a positive alpha in discovery is possible (2001-2012 summers include 2002, 2008 and 2011 drawdowns).
  Validation weak.
- **PREHOL:** about 9 events a year. Most likely NULL in all windows.
- **VRP:** positive in every window is the published fact; the question is only its size and how often it went
  negative (2008, 2020).
