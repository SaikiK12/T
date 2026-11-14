# R228 allocation_v1: fixed convex reweighting of existing flow books

Exploratory archive diagnostic, 2026-10-19. Freeze before opening outcome array values. R227 remains reserved for the unfrozen Kronos proposal. No new alpha, fresh holdout, MEXC transfer or execution claim is possible from this study.

## Inputs and exposure already seen

R217's published split summaries, all original book outcomes and its known holdout have informed the project. The investigator has read those summaries and source code, but has not opened the saved daily outcome arrays for this study before freeze. These dates are all spent at program level.

- Books: `A_C0`, `B_C0`, `X2` from `experiments/sizing_v1/results/daily.npz`.
- Archive SHA-256: `3ea686670c35c9946a560cc29cd1087b79cbeef40a78208840ab3b3e86aa0ec5`.
- Summary `experiments/sizing_v1/results/results.csv` SHA-256: `f0c37dcd37b1b850586dbc4da504282b2370d2cb2369d8ab67228709f023a64e`.
- Source `scripts/run_sizing.py` SHA-256: `bd728f138ecc40aaf650c4c2688b22b500b8229fd9f672c2a60e3ae511110c76`.
- Runner: `scripts/run_allocation.py`. Runner SHA-256: `2e0bd37ec44587b3e152418e7925183d688278fbaf0d4550624125b0f3d854f9`.
- Each source outcome has 2,099 finite daily values: 2021-01-01 through 2026-09-30. Dates are reconstructed from the source script, not stored in the NPZ. Discovery `[0:1095]`, validation `[1095:1642]`, descriptive known holdout `[1642:2099]`.

Before any candidate score, verify R217's frozen specification, the three source hashes, array lengths/finiteness and every source/split 1x mean against its archived CSV (absolute tolerance 1e-6 bp/day). Check that each source/split's 1x-to-2x and 2x-to-3x mean decrements agree within 1e-6 bp/day and are nonnegative within tolerance. Fail as INCONCLUSIVE on any mismatch; no repair or alternate source chosen after opening outcomes.

## Exact candidate family and interpretation

Evaluate 30 alternatives: three source-book endpoints and nine interior weights (0.1 through 0.9 in increments of 0.1) for each of the three unordered book pairs. Count all 30 as computational trials, including the three previously evaluated controls; do not call them 30 independent discoveries.

For weights w summing to one, daily 1x PnL is `sum(w_j * net_j)`. The model is segregated sleeves at fixed reference notional, with no cross-book netting or NAV-based rebalancing. A contains B's positioning signal, and X2 reweights the same three cells. This is allocation among overlapping books, not independent-strategy diversification. Do not subtract B's net return from A to manufacture a taker residual or transaction-cost refund.

For each candidate/split report mean bp/day, population-standard-deviation annualized Sharpe (sqrt365, matching the R217 CSV), NW(10) t, additive maximum drawdown including initial zero equity, and linear non-netted gross exposure from the source summaries. Report the three-book correlation matrix by split.

For 2x and 3x costs, compute split MEANS ONLY by linearly combining the corresponding source CSV means. Their daily paths, Sharpe, drawdown, NW statistics and bootstrap intervals are unavailable and must be explicitly NA. Never subtract a split-average cost from each day to fabricate stressed paths. The archive does not establish current capacity or fills.

## Single selection and comparison

Select the highest discovery Sharpe from all 30 alternatives. Separately select the highest discovery Sharpe among the three single-book endpoints as control. Ties use ascending candidate identifier: endpoints `00_A_C0`, `01_B_C0`, `02_X2`, then pairs in source order (A_C0/B_C0, A_C0/X2, B_C0/X2), with the first source's weight ascending 0.1..0.9 and successive numeric prefixes 03..29. Select the first equal maximum. Freeze both choices before using validation to compare them. All candidates may be tabulated afterward, but no validation-best or holdout-best choice is promoted. Undefined discovery Sharpe, risk scale, bootstrap Sharpe or source correlation fails as INCONCLUSIVE; do not drop undefined replicates.

The sole screen is positive if all hold: selected candidate is interior; validation Sharpe exceeds the discovery-selected single-book control by at least 0.15; selected candidate's validation mean is positive at 1x and 2x; and the primary paired bootstrap 95% interval's lower endpoint for validation Sharpe improvement is above zero. Otherwise verdict NULL. Even a positive screen is only PARTIAL exploratory evidence, never CONFIRMED. Report the known holdout regardless, without letting it decide.

Use a paired circular moving-block bootstrap of validation days, resampling the selected candidate and control jointly: 5,000 replicates, primary block length 30 days, seed `20261019228 + block_length`. Concatenate ceil(n/block_length) uniformly sampled blocks, wrap within the split and truncate to n. Interval is the 2.5/97.5 percentile of replicate Sharpe differences. Report 10- and 60-day block sensitivities with the same replicate count; they cannot replace the primary interval. This interval is conditional/descriptive, not a correction for the project's prior selection or already-viewed validation calendar.

Also compare additive drawdown against a constant-scaled control whose scale is discovery std(selected)/std(control), fixed before validation. Report that scale and all three split drawdowns to distinguish attenuation of risk from timing skill. Scaling does not add a new primary hypothesis or let a second rule win.

## Outputs and stop rule

Write input/code/spec hashes and software versions, full candidate table, correlation tables, selected weights/control, bootstrap intervals, risk-matched comparison and deterministic verdict under `experiments/allocation_v1/results/`. For reproduction, `--out` may select a fresh directory; refuse to overwrite an existing nonempty result directory. Bootstrap intervals are stored separately in `bootstrap.json`, not fabricated for individual candidate-table rows. Do not search additional weights, windows, signals, overlays, leverage, thresholds or optimizers after the first run. Register 30 trials and preserve null outcomes. Frozen earlier lanes, their results and journals stay unchanged.
