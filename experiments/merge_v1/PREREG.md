# PREREG: merge_v1 (R186), merging many signals into one forecast

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R186
- **Owner (single writer):** the session that froze it
- **Code:** `lab/merge.py`, `lab/atlas.py`, `scripts/run_merge.py`
- **What the author had seen when freezing:** the atlas_v1 (R185) discovery log's summary lines (per-horizon thresholds
  and the count of confident edges, 896 real vs 86 and 49 placebo in one grouping). No cell-level atlas result, no
  merge result. Nothing below was chosen from atlas results.

## Question
Single signals with real gross edge are usually too small to pay their own trading costs. If each month we re-learn
which signals currently work (using past data only), add the strongest ones into a single forecast per symbol and hour,
and trade only where that forecast exceeds the round-trip cost, does it earn after costs out of sample? How does the
result change with the number of signals merged (the "merge curve"), and what fee level would it survive (break-even)?

## Data
Same universe, data and cost model as atlas_v1 (top 50 by trailing 30-day volume, 499 columns, one-way cost 6/8/12/20
bp by liquidity rank, funding included). Test span 2022-01-01 to 2025-06-30 (42 monthly refits). The holdout from
2025-07-01 is not read.

## Procedure (fixed)
- Refit on the first day of each month. Training window: the 365 days ending 72 hours before the refit (embargo = the
  longest horizon), forward returns cut at the window end. Nothing after the embargo enters the model.
- In the window, for every cell (view, bin) of the main and clock tensors: mean forward return at horizons 4, 24 and 72
  hours, raw and excess (as in atlas_v1), Newey-West t with lag ceil(h/24) + 2. Usable cells: support >= 1% of the
  view's cells, data on >= 60% of the window's days, the same sign in both halves of the window; excess excludes
  time-only views. Cells with |t| >= 2 are ranked by |t|.
- Forecast with N cells (N in 1, 3, 10, 30, 100, 200, the top N by |t|): f = beta_N x (sum of the means of the cells
  whose condition holds at that hour and symbol). beta_N = least-squares slope through the origin of the realized forward
  return on that sum over the training window.
- Trading, hourly, on eligible symbols: enter long if f > k_in x round-trip cost of that symbol, short if f < -k_in x
  cost (k_in in 0, 0.5, 1, 1.5, 2); exit when the forecast in the held direction is <= 0, after a minimum hold of 4 hours.
  Excess forecasts trade a long-short book (longs and shorts each half of capital, each side divided by
  max(count, 5)); raw forecasts trade one directional pool divided by max(count, 10). Positions leave when the symbol
  stops being eligible. Costs on every weight change.
- Cost accounting multiplier cmult in 0, 0.25, 0.5, 1, 2 (0 = gross; 0.5 roughly a low-fee taker venue; 1 = the tier
  model). The thresholds stay at 1x cost, so the strategy is the same and only the bill changes. A second variant scales
  the thresholds with the fee (k_in x cmult, cmult in 0.25 and 0.5): what a lower-fee trader would run.
- Runs: M1 = main + clock tensors (primary). M1s = M1 with a 180-day training window (sensitivity). M2 = main + clock +
  flow (order flow; metrics from 2021, book depth from 2023 for 30 symbols), secondary. Each run also has a placebo:
  the full procedure on returns circularly shifted by 24k + 12 hours inside [2021-01-01, 2025-07-01), seeded by the tag.

## Primary configuration and decision
Primary: M1, excess, h = 24, N = 30, k_in = 1, fixed thresholds, cmult = 1.
- **GROSS EDGE OOS** if the primary at cmult 0 has Newey-West t (lag 5, daily) >= 3.
- **NET PASS** if the primary at cmult 1 has t >= 2, a positive sum in at least 3 of the 4 calendar periods (2022, 2023,
  2024, 2025H1), and its placebo at cmult 1 has t < 1.
- Otherwise NET FAIL, with the break-even cmult reported (linear interpolation of annual net over cmult).
Reported for all configurations: annual net, gross, cost, Sharpe, t, max drawdown, turnover, positions, per-year net,
the merge curve over N, break-even fee, and the Deflated Sharpe of the best configuration at cmult 1 against all
configurations tried. Selected cells per refit are saved: the record of what worked when.

## Multiplicity
Trials = number of trading configurations evaluated, real runs only (each run: 3 horizons x 2 measures x 6 N x 5 k_in x
5 cmult, plus the fee-aware variants). The internal cell selection repeats every month and is part of the procedure, not
counted separately; the placebo is the check that the procedure itself does not invent profit.

## Stop rules
- Any failing unit test or look-ahead canary stops the run.
- No change of the primary after seeing results; a changed idea is a new lane.
- No holdout read; a holdout test of a frozen configuration is a separately registered lane.

## Expectations (written before running)
Gross OOS edge is likely positive for the merged forecast; net at 1x tier costs is uncertain and probably weak or
negative for small N and short horizons, better for larger N, longer horizons and higher thresholds. The placebo should
show gross near zero and net negative by about the costs.
