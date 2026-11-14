# PREREG: atlas_v1 (R185), the gross-edge atlas

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R185
- **Owner (single writer):** the session that froze it
- **Code:** `lab/atlas.py`, `lab/sessions.py`, `lab/flowfeat.py`, `scripts/run_atlas.py`

## Question
Fees aside, which signals predict crypto perpetual returns with high confidence, broadly across symbols and
consistently across market eras, at which horizon, in which market session, liquidity tier and BTC regime, and how far
is each from paying its own trading cost? Second question: does that map hold up on later data it never saw?
This lane maps gross predictive content. It does not claim tradable profit; the merge lane (R186) asks whether combining
the confident signals pays after costs.

## Data and universe
- As in battery_v1: Binance USD-M perpetuals from data.binance.vision, hourly, point-in-time tradable set = top 50 by
  trailing 30-day quote volume (499 columns ever qualify). Manifests: klines_1h edd4faaa2cc1, premiumIndexKlines_1h
  3345c95cea2c, fundingRate e48e89529786.
- Discovery: rows 2021-01-01 to 2023-12-31 (1095 days, six calendar half-years = eras).
  Validation: 2024-01-01 to 2025-06-30 (three eras). Holdout (from 2025-07-01): not read by this lane.
- Order flow: hourly metrics (open interest, long/short ratios, taker ratio) for the 499 columns on their tradable days
  plus 35 warm-up days; order-book depth bands (bookDepth, from 2023-01) for the 30 symbols most often tradable in
  2023-01..2025-06 (data/book_symbols.txt). Their coverage is reported, not assumed.

## Views (the features, binned)
- main: the 284 views of `features.default_specs()` (data/research/bins.npy).
- clock: 6 market clocks of `lab/sessions.py` at decision time, in exchange local time with daylight saving: us_clock,
  eu_clock, cme_clock, us_day (claims Thursday, payroll Friday, FOMC day, holiday, weekend), expiry_clock, us_dst.
- flow: the 37 views of `flowfeat.specs()` (open-interest change, OI/price quadrant, crowd and top-trader long/short,
  top vs crowd, taker ratio, OI turnover, book imbalance at 1/2/5%, imbalance deviation, depth/volume, book shape).
A cell is (view, bin). Bins are fixed edges or cross-sectional/z buckets as each spec says, never fitted to returns.

## Measures
For each eligible (hour t, symbol s) with a bin, forward return over h in {1, 4, 12, 24, 72} hours = sum of next-bar
returns (funding included, longs pay), NaN if the window would pass the period end.
- **raw**: the forward return itself: a long held h hours, gross. (Directional, includes market moves.)
- **excess**: forward return minus the mean over eligible symbols at t: long the cell, short the universe, gross.
  Not computed for views that put every symbol in the same bin at each hour (time-only views).
Per cell and day: the mean over that day's cells. Per cell: the mean of the daily series, Newey-West t with lag
ceil(h/24) + 2, the same per era, the number of eras with the sign of the full mean, breadth (share of symbols with at
least 100 cells whose own mean has that sign), support (share of the view's cells), round-trip cost (2 x mean one-way
tier cost of 6/8/12/20 bp by liquidity rank) and edge/cost = |mean| / round-trip cost.

## Groupings (each a separate pass; "all" pools the groups)
- session (decision time): asia 00-07 UTC; europe 07 UTC to 08:00 New York; us_open 08:00-12:00 New York (the 08:30
  data releases and the 09:30 open); us_afternoon 13:00-15:00; us_evening after that; weekend (Sat/Sun UTC).
- tier: liquidity rank 1-10, 11-25, 26-50.
- regime: BTC trailing 30-day return up/down x trailing 30-day realized vol above/below its trailing 1-year median.

## Placebo and the confidence threshold
- Per grouping, two placebo passes with returns circularly shifted inside the discovery window by 24k + 12 hours
  (k uniform in [120, 975], seeded by the grouping name), so time-of-day alignment is broken too.
- Threshold tau for (tensor, measure, horizon): the smallest |t| on a 0.25 grid from 2 to 10 whose estimated FDR
  (mean placebo count with |t| >= tau over real count, same filters) is <= 0.10 with at least 5 real cells. Computed in
  the "all" group for confident edges and pooled over a grouping's groups for conditional edges. No tau = nothing
  passes for that (tensor, measure, horizon).
- Cells enter the count only with support >= 1% and >= 200 days with data (>= 100 days for single groups).

## Definitions of findings
- **Confident gross edge (CGE)**: an "all" cell with |t| >= tau, the full-sample sign in >= 5 of 6 eras, breadth >= 0.6.
- **Conditional edge**: a single-group cell with |t| >= its grouping's tau and the same sign in >= 4 of 6 eras.
  Reported with the matching "all" cell, flagged "concentrated" when |group mean| >= 2 x |all mean|.

## Validation (once, after the discovery lists are written and hashed)
The CGE and conditional-edge lists are frozen (sha256 of the CSVs printed). The same code then runs on the validation
period (real returns only). Replication = same sign and |t| >= 2 on validation. Baseline: the cells that pass the same
CGE rule in the placebo passes, measured on the same validation data. Reported: replication rate of CGEs vs that
baseline, per family, per horizon, and the validation edge/cost of the CGEs.

## Multiplicity
Trials = number of distinct (view, bin, horizon, measure, group) cells evaluated in the real discovery passes ("all" counted
once), logged to the registry. The placebo FDR is the guard inside the lane; the program total is read alongside it.

## Stop rules
- If the look-ahead canary or any unit test fails, stop and fix before reading results.
- No re-run of discovery with changed thresholds after seeing results; any change is a new lane.

## Expectations (written before running)
Short-horizon reversal and momentum-type cells, funding/premium, and some calendar cells will likely show gross edges
with t far above the placebo; most ICT detectors will add little beyond what price features already carry. Most gross
edges at h <= 4 will be well under their round-trip cost (edge/cost < 1); that is the gap the merge lane must close.
