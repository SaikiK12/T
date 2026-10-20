# R230: finite weekly spot rotation search

- **Registry id:** R230
- Prepared 2026-10-20. Freeze before computing any new grid outcome. R229 and the wider project have already examined these dates; ALL splits are exploratory. No historical result can authorize live trading.
- Runner: `scripts/run_weekly_rotation.py`.
- Runner SHA-256: 9084d30faa615d8e02a0b482f60d774537adc868c90cd13f95f23486cda7e8c3

## Question, sources and exact scope

Can train-selected weekly relative-strength/contrarian rotation improve validation returns and drawdown over the same six-coin passive market exposure after costs, with symmetric discovery-only risk scaling and a family-aware uncertainty diagnostic?

Primary sources checked before freeze: Liu, Tsyvinski and Wu, [author-hosted April 2019 manuscript](https://economics.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf), related to [Journal of Finance 2022](https://doi.org/10.1111/jofi.13119); White, [Econometrica 2000](https://doi.org/10.1111/1468-0262.00152) ([public manuscript](https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/White.pdf)). The former studies weekly cross-sectional portfolios and reports momentum, including at four weeks; it does not establish a universal four-week reversal. The latter motivates accounting for the full searched family. Our implementation below is an explicit approximation, not a complete replication of either paper or a proof of family-wise error control.

R222 instead used a 150-day formation window skipping the most recent 30 days. R229 is a stateful per-coin Donchian ensemble. Neither implements this weekly rank family. This is a long-only, six-survivor spot adaptation; it is NOT the full point-in-time 50-coin long/short C14 portfolio. The extra 56-day window, reversed sign, gate, concentration and partial adjustment are disclosed research choices, counted within the grid rather than attributed to the paper.

## Inputs and stopping

Reuse ONLY R229's existing 414 Binance spot daily archives, six fixed symbols in order BTCUSDT/ETHUSDT/SOLUSDT/XRPUSDT/DOGEUSDT/ADAUSDT, 2021-01-01 through 2026-09-30, 2,099 dates per symbol. No network or new download. Reuse R229's verified complete-calendar reader and its locked publisher-checksummed manifest. The runner pins the exact R229 spec, reader, fetcher and data-manifest hashes in `DEPENDENCIES`; also pins the statistics module. Verify own spec/code and every dependency before loading any price. Registration/dependency mismatches stop before outputs. Subsequent data errors, gaps, nonfinite values or undefined required metrics yield INCONCLUSIVE; no altered universe, interpolation or shortened period.

Score discovery 2022-01-01..2023-12-31 (730 days), validation 2024-01-01..2025-06-30 (547), descriptive known_holdout 2025-07-01..2026-09-30 (457). 2021 is warm-up. Indicators may use earlier closes across split boundaries; each account resets to cash 1. Never select or change a rule from validation or known_holdout. No repeat search after a null in this lane.

## Finite family: exactly 96 candidates

Cartesian product, in this deterministic order:

1. Ranking lookback h in (7,14,28,56) calendar observations.
2. Sign in (+1 momentum, -1 reversal).
3. Number held K in (1,2,3).
4. BTC gate in (off,on).
5. Adjustment fraction alpha in (1.0,0.5).

At close t, rank `sign*(C_j[t]/C_j[t-h]-1)` descending. Ties use the fixed symbol order above, with no jitter. Desired post-cost weights equal 1/K on the first K names, zero elsewhere. The optional gate uses the FIXED 56-day BTC return irrespective of h: allow desired exposure only if `BTC_C[t] > BTC_C[t-56]`; otherwise all desired weights are zero. No signal before its required history. No volatility estimate, funding, dollar-volume sort, shorting, leverage, stops or additional learned filters.

Rebalance on the return dates labeled UTC Monday, plus forced initialization at EACH split's first return even if not Monday. Row i executes at close C[i-1], using desired target[i-2], and earns the move to C[i]. Thus a Monday return's entry is the preceding Sunday close using the Saturday close signal, a full daily bar earlier. On other days hold units unchanged. No weekday tuning. The boundary initialization is explicit and included in costs for every candidate and control.

At rebalance, mark actual holdings at C[i-1]. Define drifted PRE-cost weights `d_j=current_units_j*C_j[i-1]/NAV_before`. Set new POST-cost target weights to `(1-alpha)*d_j + alpha*capital_scale*desired_j[i-2]`. Solve `NAV_after+c*sum(abs(new_weight_j*NAV_after-current_dollars_j))=NAV_before` using 55-step bisection. This is a defined convex adjustment of weights; it is not exactly halving cash orders. In particular alpha=.5 retains half the drifted exposure when the BTC gate turns off instead of instantly going to cash. Initial exposure is partial too. Charge final liquidation in full regardless of alpha.

Use long-only spot units/cash, zero cash yield, no leverage. One-way costs 12/24/36 bp at 1x/2x/3x, identical to R229's assumed fee/slippage model. Rerun each account for each tier, charging actual drifted-weight turnover, forced initialization and final exit. These are modeled close-price trades, not measured fills or capacity estimates.

Passive control: six equal post-cost weights, rebalance on return dates labeled the first of a UTC month plus split initialization, otherwise hold units. The monthly schedule and fixed weights need no signal delay, so a constant target may still use index i-2 without changing its meaning.

## Discovery-only selection and comparison scaling

For each candidate compute its unscaled discovery net path at 1x and 2x. Sole selection score is its UNscaled discovery 2x net population-std Sharpe annualized sqrt365; exact ties use grid order. Lock one winner before scoring future splits. No discovery minimum performance filter, manual winner replacement or validation reranking.

Using unscaled discovery 1x net sample standard deviations s_c and s_p for candidate and full passive, fix `candidate_scale=min(1,s_p/s_c)` and `passive_scale=min(1,s_c/s_p)` separately for EVERY candidate. Neither account uses leverage. Rerun both accounts with those capital scales for ALL splits/cost tiers. Scaling is applied to desired weights in the execution rule; costs and drift are rerun. This targets equal discovery risk approximately: partial-adjustment transitions and costs mean realized scaled risk need not match exactly. Report actual annualized volatility and exposure for each; no validation-risk fit. Selection remains based on the pre-scaling discovery 2x score.

## Paired family uncertainty diagnostic and decision

Use validation 1x paired daily differences between each scaled candidate and its scaled passive control. All 96 columns are retained. Primary circular moving-block bootstrap length30, 5,000 draws, seed20261020230+block; lengths10/60 are nondecisive sensitivities. For each draw sample uniform block starts, wrap within the split, concatenate ceil(n/block) blocks and truncate to n. The same sampled dates are applied to every candidate and paired control. Center each column by its observed mean. Estimate each original column's mean SE with the repository's Bartlett NW(10) definition, and keep that original SE fixed during resampling. Record maximum over96 of resampled centered mean/SE. The family diagnostic p is `(1+count(maximum>=selected_observed_mean/SE))/(5000+1)`. The selected paired mean's ordinary 95% percentile interval is resampled centered selected means plus its original mean. This approximates a least-favorable max-statistic check; it does not correct for earlier project searches, prior date reuse, nonstationarity or survivor selection, and finite-sample validity is not established.

The sole outcome is PARTIAL exploratory evidence only if the discovery-selected candidate has ALL five: validation1x Sharpe >= its scaled passive +0.15; validation2x mean net >0; validation1x compound drawdown <= scaled passive; primary selected paired-mean95% lower endpoint >0; primary96-member family diagnostic p<=.05. Otherwise NULL. The 95 alternatives, sensitivities and known_holdout cannot rescue failure. No CONFIRMED verdict is available. A passed exploratory screen would require a separately frozen future paper test; no bot deployment.

## Outputs and provenance

Save raw discovery2x selection scores; all96 scaled candidates and matched controls' metrics at each split/tier (1,728 accounts); selected/control full daily account paths (including units, costs and exposure); paired differences; all candidate/control daily net panels and15,000 bootstrap maximum statistics in numeric compressed NPZ (`allow_pickle=False` on reading); deterministic verdict. Metrics include mean, annualized arithmetic return/volatility/Sharpe, NW(10)t, compound maxDD including initial cash1, costs, turnover, mean exposure and endingNAV. The NPZ has split/tier-specific day-by-candidate arrays; column order is the frozen grid.

Output directories must be new; files use exclusive creation and LF CSV. Manifest binds all output bytes, all source/dependency hashes, grid/scales and software versions. A second fresh-directory run must reproduce output hashes; investigate disagreement without overwriting the first run. Record96 candidate trials through the append-only registry, including nulls, after completion. No frozen older specification, finding or journal is edited.
