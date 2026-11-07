# PREREG: posimpulse_v1 (R234). Does the change in top-vs-crowd positioning predict returns beyond its level?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R234
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_posimpulse.py`, `lab/screen.py` (the standard spread screen), `lab/flowfeat.load`
- **Queue:** M001 in `registry/methods.csv` (NEXT_SEARCH_SPACE's first-ranked item)
- **Gate:** this is a gate-0 screen (`docs/GATES.md`). A pass makes it a candidate for a frozen forward lane; it is not
  evidence by itself.

## Why
The lab's strongest lead is the *level* of top_vs_crowd = log(top_ls_sum) - log(ls_count): coins where top traders
lean against the crowd (R197, R211). A level can sit unchanged for weeks. The *impulse* is the change: top traders
turning against the crowd now. If the edge is a crowding unwind, a fresh divergence should carry information the level
does not.

## What the author has seen
- Every result of the top_vs_crowd level: atlas R185, flow books R196-R198, R211, R213-R218, R228, R233, and forward
  replays.
- No statistic of the change in top_vs_crowd over any horizon has been computed. The atlas has `top_vs_crowd` level
  views only (`lab/flowfeat.specs`).

## Features (per coin and hour t, from `metrics` at t, as R211)
- `tvc[t] = log(top_ls_sum[t]) - log(ls_count[t])`.
- **imp24** = `tvc[t] - tvc[t-24]`.
- **imp72** = `tvc[t] - tvc[t-72]`.
- NaN when either end is missing.

## Books (lab/screen.py, unchanged)
- For each feature, xs8 bins among eligible coins (`features.bins_xs(x, elig, 8)`, top 50).
- **H** opens long 72 h slices in bin 7 and short slices in bin 0.
- **L** is the opposite.
- Size 1 / (72 x K), with K = mean slices opened per hour over discovery. Universe hedge, tier costs, funding.
- Four books: imp24/H, imp24/L, imp72/H, imp72/L.

**Reference: the level book.** top_vs_crowd level, xs8 bin 0 short alone, the same construction (R211's reference).
Its daily nets are the regressor for the residual.

## Stages (lab.screen.default_rule)
1. **Discovery** 2021-01-01..2023-12-31. A book passes if all three hold:
   - 1x NW t (lag 10) >= 2;
   - 2x mean > 0;
   - the residual against the level book has NW t >= 2.
2. **Validation** 2024-01-01..2025-06-30, for discovery passers only. A book passes if all three hold:
   - 1x mean > 0;
   - t >= 1.5;
   - residual mean > 0.
3. **Holdout:** **not read.** The holdout is spent at program level (`docs/GATES.md`, 2026-10-20).
   - A validation passer becomes a candidate for a forward paper lane under a new id, decided on strict on-time days
     only.
   - Forward data is available: R200 journals the live top-trader and account ratios hourly.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean bp/day, NW t, Sharpe, max drawdown, gross and cost;
  - correlation, beta and residual against the level book;
  - per-year means.
- Trimmed mean at 1x: the 10 best and 10 worst days removed.
- Coverage: the share of eligible coin-hours with a finite feature, by year. Positioning data covers about 10-13% of
  coin-hours in 2021-22 and about 99% from 2023 (CRITIQUE item 10). So discovery is mostly 2023, and per-year numbers
  show it.

## Multiplicity
- Trials = 4.
- Program trials before: 9,471,893 (after R233).

## Expectations
- **Most likely NULL.** The level already captures slow divergence. A 24 h change is noisier, and its bins turn over
  faster, which costs more.
- **Best chance: imp72/H.** Its short leg (bin 0) holds coins where top traders newly turned short against the crowd.
  That is the side the level book profits from.
