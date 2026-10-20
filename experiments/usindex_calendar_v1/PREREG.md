# PREREG: usindex_calendar_v1 (R235). Turn-of-month and overnight drift on SPY and QQQ

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R235
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_usindex_calendar.py`. Data: `lab/markets.py` (Yahoo daily, fetched 2026-10-20). The runner
  records the sha256 of each parquet file it reads.
- **Queue:** M196 (turn-of-month) and M195 (overnight vs intraday) in `registry/methods.csv`; `docs/FOREX_AND_INDICES.md`
  rows 3 and 2.
- **Why now:** the owner widened the objective to any market they can trade, NASDAQ included (2026-10-20). These two
  effects have the most published evidence, cost almost nothing to trade, and need only daily bars.

## What the author has seen
- No return, price path or statistic of any symbol in `data/markets/yahoo/` has been computed by this lab.
- Before freezing, the author checked data structure only:
  - row counts, NaN counts, timestamps;
  - the share of bars whose open equals the previous close, by year. It is 95% for ^GSPC before 2008, so index opens
    are unusable, and 0-4% for SPY and QQQ.
- The author knows the published results:
  - turn-of-month (McConnell-Xu 2008; Etula et al. 2020);
  - overnight drift (Cliff-Cooper-Gulen; Lou-Polk-Skouras 2019).
  Both papers' samples end before 2013, but later work covers parts of 2013-2026. So the windows below are unread *by
  this lab*, not by the field.

## Data
- SPY and QQQ daily bars. Each bar's date is its New York date.
- Adjusted prices: `f = adjclose / close`, adjusted open `= open x f`, adjusted close `= adjclose`. Dividends are
  therefore in the returns.
- Close-to-close return: `r_d = adjclose_d / adjclose_{d-1} - 1`.

## Rules (long or flat, one instrument at a time)
- **TOM** (turn-of-month):
  - Invested on the last trading day of each month and the first three trading days of the next. It earns the
    close-to-close return of those four days.
  - It enters at the close two trading days before month end and exits at the close of the third trading day.
  - The trading calendar is the bars themselves; month ends are known in advance.
- **ON** (overnight): every day, buy at the close and sell at the next open. It earns
  `adj_open_d / adjclose_{d-1} - 1` every trading day.
- **Costs:** 1 bp one-way at 1x (an MOC/MOO order in the most liquid ETFs), charged at entry and exit. That is
  2 bp per month for TOM and 2 bp per day for ON. Results are also reported at 2x and 3x.

Four strategies (trials): TOM-SPY, TOM-QQQ, ON-SPY, ON-QQQ.

## Test: alpha against buy-and-hold of the same ETF
In each window, regress the strategy's daily net return on the ETF's close-to-close return. The **alpha** is the
intercept: the mean of `net - b x r`. Its NW t uses lag 10. For a long/flat rule this asks whether the rule beats the
same market exposure held all the time.

## Windows and stages
1. **Discovery 2000-01-03..2012-12-31.** Pass if both hold:
   - 1x alpha NW t >= 2;
   - 2x alpha mean > 0.
2. **Validation 2013-01-01..2019-12-31**, for discovery passers only. Pass if the 1x alpha is > 0 with t >= 1.5.
3. **Holdout 2020-01-01..2026-10-19**, for validation passers only, read once in the same run. Pass if the 1x alpha is
   > 0 with t >= 2.
   - This window has never been read by this lab. A pass here is the lab's strongest archive evidence (gate 1 in
     `docs/GATES.md`), with the caveat above.
   - A pass then goes to forward paper on daily bars under a new id. Real money only after gates 2-4.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean net bp/day, Sharpe, max drawdown, share of days invested;
  - beta, alpha (bp/day) and its NW t.
- For comparison: buy-and-hold mean, Sharpe and max drawdown.
- Per-year alpha at 1x.
- Trimmed alpha (10 best and 10 worst days removed).
- For ON only: the intraday leg (open to close) mean, as context for the overnight/intraday split.

## Multiplicity
- Trials = 4.
- Program trials before: 9,471,897 (9,471,893 after R233, plus R234's 4).

## Expectations
- **TOM:** a positive alpha in discovery is likely. It is the most replicated calendar effect. Whether it held after
  2012 is the open question. Most likely result: discovery pass, validation weak.
- **ON:** gross overnight returns were positive in published samples. But 2 bp a day is about 5%/yr of cost, close to
  the whole equity premium, and the alpha against buy-and-hold also needs negative intraday returns.
  - Most likely: NULL at 1x.
  - QQQ's overnight share is reported larger than SPY's.
