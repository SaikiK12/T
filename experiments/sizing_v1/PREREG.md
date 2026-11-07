# PREREG: sizing_v1 (R217), does sizing up when confidence is high beat a constant size?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R217
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_sizing.py`, `lab/slices.py`
- **Sources:** the owner's request (raise the multiplier when confidence is high, across strategies);
  `docs/SIZING_EVIDENCE.md` (shrunk Kelly, volatility targeting, own-performance and regime scaling; no out-of-sample
  support for confidence scaling, so a constant multiplier is the control).

## What the author had seen
All daily results of books A (three flow cells) and B (top_vs_crowd) at zero and one-hour delay, all universes, all
windows (R198, R213, R216), including the holdout. No book has ever been run with a time-varying or
agreement-weighted size. Every multiplier rule below was written before computing any of them.

## Books (one-hour delay as R213 d = 1; crypto contracts only as R216; 72 h slices; unit 1 / (72 x 9.316); universe hedge;
tier costs; funding)
- **A:** slices of top_vs_crowd, taker[24], taker[4] (xs8 bin 0, short), summed: a coin flagged by k cells holds k
  slices (linear agreement).
- **B:** top_vs_crowd alone.

## Time-series multipliers (m_d for every hour of day d, from the book's own constant-size daily net through day d - 1)
- **C0** (control): m = 1.
- **R1 volatility target:** sigma_hat = EWMA std (half-life 30 days) of the daily net through d - 1, sigma_star = std of
  all daily nets through d - 1; m = clip(sigma_star / sigma_hat, 0, 2); m = 1 before 90 days of history.
- **R2 shrunk Kelly:** over the trailing 180 days, mu, sigma, t = mu / (sigma / sqrt(180)); k = (mu / sigma^2) x max(0,
  1 - 1 / t^2) if mu > 0 else 0; m = clip(k / median of the positive k values through d - 1, 0, 2); m = 1 until 30
  positive k values exist.
- **R3 own performance:** m = 1.5 if the trailing 60-day sum of daily net is positive, else 0.5; m = 1 before 60 days.
- **R4 regime cut:** m = 0.5 when both hold, else 1:
  - the 30-day median of the daily cross-sectional std of eligible crypto coins' returns (through d - 1) is at or above
    the 2/3 quantile of its own history (at least 365 days);
  - the equal-weight index of eligible crypto coins returned less than 0 over the trailing 90 days.

Position changes from m are charged at tier cost: the scaled positions run through `slices.run`.

## Cross-sectional multipliers (within book A: more agreeing cells, more size)
- **X1 cap:** a coin flagged by any of the three cells holds one slice (no agreement scaling).
- **X2 square:** a coin flagged by k cells holds k^2 slices.
- X1 and X2 are rescaled so their mean gross exposure on 2021-01..2023-12 equals A's.

## Windows and decision
- Discovery 2021-01-01..2023-12-31, validation 2024-01-01..2025-06-30. The holdout 2025-07-01..2026-09-30 is reported;
  its constant-size outcome is known, so it decides nothing.
- A rule **passes** if, at 1x, its annualized Sharpe exceeds the matching control's (C0 for R1-R4, book A for X1/X2) by
  0.3 or more in **both** discovery and validation, and its validation mean is positive. A pass becomes a forward
  overlay on R215 under a new id; nothing here is confirmed.

## Reported
Per rule, book, window and 1x/2x/3x: mean bp/day, NW t (lag 10), Sharpe, max DD, mean |m| (or mean gross exposure),
mean / mean |m|.

## Multiplicity
Trials = 10 (R1-R4 on A and B, X1, X2). Program trials before: 9,471,718.

## Expectations
Following the literature: R1 lowers drawdown with a similar Sharpe; R2 and R3 add noise on a book whose daily
autocorrelation is near zero; R4 has few episodes; X2 adds turnover and concentration. Guess: no rule passes.
