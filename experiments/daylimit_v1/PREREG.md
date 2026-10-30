# PREREG: daylimit_v1 (R208), do daily loss and profit limits improve a book?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R208
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_daylimit.py`, `lab/slices.py`
- **Source claim:** `docs/CLAIMS.md` C17 (Krechendo course, prop-firm daily limits; grade D).

## What the author had seen
The two books' daily results: flow72 combined (R197 in-sample +42.6%/yr, t 3.25; R198 holdout +104% over 457 days)
and top_vs_crowd alone (R197 +69.3%/yr; R198 book B). Never their hourly path within a day, never any stop rule on
them. Theory (optional stopping): with independent hourly results a stop cannot raise the mean, only reshape the
distribution; it can help only if intraday results are autocorrelated.

## Books
As R197 (universe hedge, tier costs, funding), with positions summed over the cells before costs:
- **F:** flow72 combined: top_vs_crowd, taker[24], taker[4] xs8 bin 0, short 72 h slices, unit 1/(72 x K), K from
  2021-2023 as R197.
- **T:** top_vs_crowd alone, its own K.

## Overlay
Day = 00:00-23:00 UTC rows. Day-to-date PnL after row t = the sum of the overlaid book's hourly net over the day's
rows up to t (ret[t] is known at the close of row t + 1). When it is <= -x or >= +y, every position and the hedge
are set to 0 from row t + 1 to the day's last row, and the book's positions resume at the next day's 00:00 row.
Closing and reopening pay the tier costs (computed exactly by `slices.run` on the masked positions; the trigger uses
the masked book's own PnL, solved by iteration to a fixed point).
- Grid: x in {0.5%, 1%, 2%} with y in {1%, 2%, 4%} (9), loss-only x (3), profit-only y (3): 15 per book.
- **Primary: book F, x = 1%, y = 2%.**

## Windows and decision
- In-sample: 2021-01-01..2025-06-30. Second window: 2025-07-01..2026-09-30 (the books' holdout is spent, but no
  overlay has been computed on it).
- Statistic: the paired daily difference d = overlay net - unfiltered net, at 1x.
- **IMPROVES** if the primary's d has a positive in-sample mean with NW t (lag 10) >= 2 **and** a positive mean on the
  second window. Otherwise NULL.

## Reported (not decided on)
All 30 overlays: mean, Sharpe, max drawdown, worst day, 1st percentile day, share of days stopped; 2x and 3x costs;
the hourly autocorrelation of the books' net (lags 1-6), which says whether a stop could help at all.

## Multiplicity
Trials = 30. Program trials before: 9,471,653.

## Expectations
NULL for the mean (optional stopping); loss limits cut the worst days and add costs; profit limits cut the best days.
Any "improvement" in Sharpe from a stop should come with a lower mean.
