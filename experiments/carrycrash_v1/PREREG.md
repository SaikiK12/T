# PREREG: carrycrash_v1 (R207), does high market-wide carry predict BTC crashes?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R207
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_carrycrash.py`, `lab/carry.trailing_apr`, `lab/engine.forward_returns`
- **Source claim:** `docs/CLAIMS.md` C08 (Schmeling, Schrimpf, Todorov 2023, BIS WP 1087; grade B).

## What the author had seen
carry_v1 (R190) and carry_holdout (R191): hedged funding carry earns, regime-bound, compressed since 2024. Those lanes
measured carry *returns*, never market carry against later BTC returns. The author knows BTC's broad history (the
May 2021 and 2022 crashes, the 2024-2025 rallies). No statistic of this lane has been computed.

## Signal
- Panel as carry_v1: every column with prices, trailing 30-day liquidity rank, eligible = top 50, tier costs.
- Market carry M_d on day d = the median over eligible coins at the 00:00 UTC row of `trailing_apr(fund_event, 72)`
  (settled funding over the last 72 h, annualized), NaN coins ignored.
- Threshold thr_d = the 90th percentile of M over days d-365..d-1 (at least 180 days of M, else no signal).
- S_d = M_d > thr_d.

## Overlay (primary)
Short BTCUSDT perp, weight 1, held at every hour row from day d's 00:00 row through 7 x 24 rows after the last
signal day (signals extend the hold; they do not stack). Position chosen at the close of row t earns ret[t] (close to
close, funding included: a short receives positive funding). Cost: BTC's tier cost times |change of weight|.
Daily net = sum of 24 rows. Days without a position count as 0.

## Windows and decision
- In-sample: 2021-01-01..2025-06-30. Holdout (this lane's, unspent): 2025-07-01..2026-09-30.
- **CONFIRMED** if the in-sample daily net at 1x has a positive mean with NW t (lag 10) >= 2 **and** the holdout mean
  at 1x is positive. Otherwise NULL. Both windows are computed in the same run.

## Reported (not decided on)
- 2x and 3x costs; per year; days in position; number of episodes (signal runs separated by more than 7 days).
- Crash frequency: P(the minimum BTC close over the next 30 days is <= -20% below day d's close) on signal days vs
  all days; the same for -10%.
- Variants: top quintile (q80) instead of decile; 30-day hold instead of 7.

## Multiplicity
Trials = 4 (decile/quintile x 7/30-day hold). Program trials before: 9,471,649 (after R205's 3 and R206's 4).

## Expectations
Few independent crashes (perhaps 5-8), so almost no power; a short BTC overlay paid funding in bull markets but lost
on the rallies. Guess: NULL, in-sample t between -1 and 1.
