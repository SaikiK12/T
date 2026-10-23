# PREREG: atlas_ctx (R192), context lifts: when does a known signal get stronger?

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R192
- **Owner (single writer):** the session that froze it
- **Code:** `lab/atlas.py` (`run`, `lift_stats`), `scripts/run_context_atlas.py`, `scripts/build_extra_views.py ctx`

## What the author had seen
atlas_v1 discovery and validation on main+clock (mean reversion in price views replicates at about 48%, against 9% for
placebo picks; groupings by session, tier and BTC regime gave many conditional cells, half of which replicated); the two
merge lanes (no robust net edge; per-trade edges well below costs); the per-trade diagnostic that an isolated oversold
coin keeps falling more often than a coin oversold together with the whole market (the motivation for the crowding
context). For the crowding views only their bucket counts were printed (no return was touched). No flow statistic has
been computed yet.

## Question
The atlas found signals with a gross edge but mostly under their round-trip cost. A signal does not have to be traded
at every hour: it can be traded only in the contexts where it is stronger. Which contexts (time of day and market opens,
calendar days, BTC trend and volatility, dispersion and breadth, a market-wide flush or melt-up, the symbol's own open
interest, positioning, taker flow and order book) amplify, damp or reverse which signal, and do those lifts hold on
later data? Which (signal, context) pairs have a gross edge above their round-trip cost?

## Data, universe and periods
As atlas_v1: hourly Binance USD-M perps, tradable = top 50 by trailing 30-day quote volume. Discovery 2021-01-01 to
2023-12-31 (six half-year eras); validation 2024-01-01 to 2025-06-30. Holdout (from 2025-07-01) not read.

## Signals (the base cells)
The views of the main tensor (`features.default_specs()`) that are not time-only (about 256), every bin, horizons
h in {1, 4, 12, 24, 72} hours, measures raw (long the cell) and excess (long the cell, short the universe), defined as
in atlas_v1.

## Contexts (each one is a separate pass with its codes as the groups)
- **clock** (6): us_clock, eu_clock, cme_clock, us_day, expiry_clock, us_dst (lab/sessions.py, decision time).
- **crowd** (10): share of tradable symbols in the lowest (z below -1.5) or highest (z above +1.5) trailing-720h z bucket
  of ret[1], ret[3], ret[6], ret[24] and ema_ratio[8] at that hour, in buckets with edges 2%, 5%, 10%, 20%, 35%.
- **market** (25): the time-only main views btc_ret (9), disp (9), breadth (6) and funding_clock.
- **flow** (37): the views of `flowfeat.specs()` for the same symbol (open interest change and OI/price quadrant, crowd
  and top-trader long/short, top vs crowd, taker ratio, OI turnover, book imbalance, depth). Cells without flow data are
  left out of these passes, so their base is the flow-covered subset. Skipped if the flow tensor is not built.

## Statistic
For a cell (view, bin, h, measure) and context code k, per day: the mean forward return of the cell's observations
inside k and outside k. Reported (`atlas.lift_stats`): the cell's base mean, the conditional mean and NW t inside k, and
the **lift** = mean and NW t (lag ceil(h/24) + 2) of the daily difference inside minus outside (days with both), the
number of eras where the lift keeps its sign, the share of the cell's observations in k, the round-trip cost and
cond edge/cost = |conditional mean| / round-trip cost. "Amplifies" = the lift has the sign of the base mean.

## Placebo and threshold
- One placebo pass per context: returns circularly shifted inside the period by 24k + 12 hours (k uniform in
  [120, 975], seeded by the context name), which breaks both the signal and the context links to returns.
- Threshold tau for (family, measure, h) on |lift t|: the smallest value on a 0.25 grid from 2 to 10 with estimated FDR
  (placebo count / real count over all contexts of the family, same filters) <= 0.10 and at least 5 real cells. The same
  procedure on |cond t| gives tau_cond.
- Filters for both counts: base support >= 1% of its view's cells, share >= 2%, lift days >= 100.

## Findings
- **Confident lift (CL)**: |lift t| >= tau and the lift sign in >= 4 of the eras it has.
- **Confident conditional edge (CCE)**: a CL that amplifies, with |cond t| >= tau_cond and cond edge/cost >= 1, i.e. a
  context where the signal's gross edge exceeds its round-trip cost.

## Validation (once, after the discovery lists are written and hashed)
The CL list (real and placebo) is frozen. The same passes run on validation with real returns. A CL replicates when its
validation lift has the same sign and |lift t| >= 2; a CCE replicates when it also has validation cond edge/cost >= 1 with
the same sign of the conditional mean. Baseline: the placebo CLs measured on the same validation data.

## Decision
- A family is **SIGNAL** when at least 20 of its CLs replicate and its replication rate is >= 25% and >= 2x the baseline.
- The lane is CONFIRMED (in-sample, gross) when at least one family is SIGNAL; otherwise NULL.
- Reported regardless: per family and horizon the CL counts against placebo, replication rates, the amplifiers vs
  dampeners, and the replicated CCE list with validation edge/cost at 1x, 2x and 3x cost.

## Multiplicity
Trials = the number of real discovery lift cells that pass the filters, logged to the registry.

## Stop rules
- Any failing unit test stops the run before results are read.
- No re-run of discovery with other thresholds or contexts after seeing results; a change is a new lane.

## Expectations (written before running)
Mean reversion in price views will be amplified when the whole market flushes (the crowding contexts) and damped when a
coin falls alone. US hours will amplify short-horizon effects. Flow contexts (open interest falling with price,
positioning extremes) will amplify reversal. Most CCEs will be short horizons in rare contexts; few will replicate with
edge/cost >= 1, since replication rates in atlas_v1 were about half.
