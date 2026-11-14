# FINDINGS: daylimit_v1 (R208), do daily loss and profit limits improve a book?

**Verdict: NULL, and harmful.** Closing the flow books for the rest of the day after a daily loss or gain costs a round
trip on the whole book each time it fires, and the books' hourly results have no autocorrelation for a stop to use
(lags 1-6: -0.002 to +0.013). The primary (book F, stop at -1% or +2%) loses 22.5 bp a day against the unfiltered book
in-sample (t -8.3) and 57 bp a day on 2025-07..2026-09.

- **Registry row:** R208 (trials: 30)
- **Reproduce:** prereg sha 5c1cdac7; `python scripts/run_daylimit.py` (about 1 minute).
- **Source claim:** `docs/CLAIMS.md` C17 (course material and prop-firm rules; grade D).

## Numbers (1x costs; d = overlay minus unfiltered, bp per day, NW t lag 10)
Book F, flow72 combined (unfiltered: +12.1 bp/day in-sample, Sharpe 1.59, max DD 26%; +23.1 bp/day on the second
window, Sharpe 1.07, max DD 47%):

| stop | days stopped in / 2nd | net bp/day in-sample | d in-sample (t) | net bp/day 2nd | d 2nd (t) | max DD in-sample |
|---|---|---|---|---|---|---|
| **-1% / +2% (primary)** | **36% / 86%** | **-10.4** | **-22.5 (-8.3)** | **-34.0** | **-57.1 (-3.7)** | **186%** |
| -2% / +4% | 11% / 53% | +5.9 | -6.2 (-4.3) | +1.7 | -21.4 (-1.7) | 29% |
| -2% only | 9% / 35% | +6.7 | -5.4 (-4.6) | +18.6 | -4.5 (-0.5) | 29% |
| +4% only | 2.5% / 19% | +11.3 | -0.8 (-1.0) | +2.5 | -20.6 (-2.4) | 27% |
| -0.5% / +1% (tightest) | 63% / 99% | -29.2 | -41.3 (-10.4) | -48.4 | -71.5 (-4.3) | 481% |

Book T, top_vs_crowd alone (unfiltered +19.0 bp/day in-sample, +75.6 on the second window): every one of the 15
overlays has a negative d in both windows (in-sample -14 to -58 bp/day, t -4.0 to -7.6; second window -41 to -136).
The least bad, +4% only, keeps +4.7 bp/day in-sample and +34.3 on the second window.

All 30 overlays: d < 0 in-sample; 30 of 30 also d < 0 on the second window. Totals are sums of daily returns at the
book's unit size (not compounded), so a "drawdown" above 100% is possible.

## Cost sensitivity
The primary's d: -22.5 / -48.6 / -80.0 bp/day at 1x / 2x / 3x in-sample and -57.1 / -107.0 / -155.6 on the second
window. Read linearly, about 26 bp/day in-sample (50 on the second window) of the 1x loss is the cost of closing and
reopening; the rest is +3.6 bp/day in-sample and -7.2 on the second window: no reliable effect before costs either.
The unfiltered book F: +12.1 / +8.2 / +4.4 bp/day in-sample at 1x / 2x / 3x.

## Reading
- Optional stopping holds here: the books' hourly net is serially uncorrelated, so stopping after a bad or good start
  to the day does not change what the rest of the day earns, and each stop pays about 0.3-0.5% of capital in round-trip
  costs (gross exposure about 1.3 short plus the hedge).
- Stops fire far more on the second window (86% of days for the primary) because the book's daily volatility roughly
  tripled (Sharpe 1.07 at twice the mean). A fixed percentage limit is a volatility bet.
- For prop accounts (R202): a firm's daily loss limit is better met by **sizing** the book so a limit-sized day is
  rare than by an intraday kill switch, which here converts a positive book into a negative one.
- Read against 9,471,683 program trials (after this lane).

## Implementation note
The PREREG describes solving the trigger "by iteration to a fixed point". The first run's iteration did not converge
in 20 rounds (a change on one day moves the next day's reopening cost, so changes propagate one day per round). The
script computes the same fixed point exactly, day by day. It checks one overlay per book against the full engine
(`slices.run` on the masked positions); the check passed for both books. The rule is unchanged.

## What this does not show
Stops on fast books or single trades (here: slow, diversified books only); volatility-scaled limits; stops that
reduce size rather than close everything.
