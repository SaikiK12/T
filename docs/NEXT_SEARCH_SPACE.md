# Next research priorities (refreshed after R226)

**Historical proposal, not the live queue.** The ranking and open/tested labels below belong to the stated review
date. Reconcile a candidate with [methods.csv](../registry/methods.csv), [rounds.csv](../registry/rounds.csv) and the
linked frozen lane evidence before doing work. Preserve the distinctions here; do not repeat the old priority list.

Reviewed 2026-10-19. This is a planning memo, not a preregistration or new market result. Every measurement still needs a frozen lane, an exact trial count, and a clean statement of which dates and outcomes researchers have already seen.

## What R226 actually tested

R226 (`experiments/tradesize_v1/FINDINGS.md`) registered six discovery books: three unsigned 24-hour activity/size features, each sorted in both directions, as a 72-hour top-versus-bottom spread. It found no book that passed discovery. The count-surge book was nearly the quote-volume book (`corr=0.99`); its residual was `+0.3 bp/day`. Mean print size against its own 30-day mean had a `-0.5 bp/day` residual. No validation or holdout was run because nothing passed discovery.

That is a useful null, but it is narrower than the old Block C proposal. R226 did **not** run its 6-hour or 72-hour feature windows, other bins, or other holding horizons. Do not describe all of Block C as tested. Also do not repeat the six registered variants. The remaining unsigned variants are low priority: they mostly extend a feature that did not add information to quote volume, and finishing the old grid is not itself a research rationale. Aggressor-signed flow is a distinct hypothesis, not a result of R226.

The raw registry total after R226 is 9,471,756. Most of that is highly correlated context-atlas cells, so it is not a count of independent experiments. Registry rows also mix attempted trials, filtered cells, and planned counts; the total is not a complete ledger of researcher choices or a calibrated effective trial count. See `docs/SELECTION_AND_TRIAL_ACCOUNTING_AUDIT.md`. It is still evidence of extensive researcher degrees of freedom. The former 93k-cell proposal is a rough legacy grammar, **not** a justified next run or a multiplicity denominator. Avoid brute-forcing it. State the economic mechanism, primary outcome, number of candidates, date windows already viewed, and stop rule before each small family is measured. Use family-level dependence-aware inference only when a family search is genuinely specified; reserve confirmation for outcomes collected after the frozen decision.

## Evidence already spent or weakly understood

| Area | Current evidence | Consequence |
|---|---|---|
| Price, oscillators and structure | R185: raw reversal is present; excess is weak and below costs. Later atlas combinations also failed net out of sample. | Do not relabel indicator combinations as new hypotheses without a distinct mechanism and incremental baseline. |
| Flow levels and 72-hour books | R196–R198 found an in-sample flow result; its holdout did not confirm the primary combination. The strongest top-versus-crowd component was chosen after seeing prior results. | Treat archival follow-ups as exploratory; use a frozen prospective test for any further claim. |
| Positioning levels and their components | R185, R211–R212 and R216 test levels/decompositions; the added account-headcount component did not validate. | A change/impulse question remains distinct; it must beat the already-seen level book and use valid timestamps. |
| Trade count / unsigned mean print size | R226's six discovery variants were null or added nothing beyond quote volume. | Close the tested cells. Do not claim capacity was tested; signal activity and order capacity are different. |
| Cross-venue positioning, funding and liquidation ideas | Existing cross-venue studies, carry variants and liquidation-fade tests already cover several common stories; see `docs/MAP.md`, `docs/CLAIMS.md` and `docs/EDGE_SCOREBOARD.md`. | Read each claim's kill criteria before reopening it. A new venue or renamed feature is not automatically independent evidence. |

The old calendar holdout (2025-07 through 2026-09) has been examined by multiple project families and has informed later choices. It is not a fresh program-wide holdout. Label any new archive result exploratory, even when a particular feature was not previously run, and do not use it as the decisive confirmation of a selected follow-up.

## Ranked queue

### 1. Positioning impulse, conditional on timestamp integrity

**Question:** does a change in top-trader positioning relative to the crowd add value beyond the known positioning level?

The code defines `top_vs_crowd = log(top_ls_sum) - log(ls_count)` (`lab/flowfeat.py`). One compact candidate is its 24-hour change at a fixed UTC daily cut: long the cross-sectional top quintile of the change, short the bottom quintile, equal-weight, hold 72 hours, and use the repo's dollar-neutral universe convention. Compare it with the frozen level-based 72-hour flow book and the fixed price/taker controls. The primary claim should be incremental net value, not that the level book itself has been rediscovered. Do not search accelerations, multiple changes, bins, horizons and cutoffs in the same lane.

Archived Binance position-ratio coverage is poor in 2021–2022 and exceeds 99% only from 2023 onward (`docs/MAP.md`; `docs/POSITIONING_AND_ORDERFLOW_VALIDITY.md`). Treat 2023–2025H1 as a limited exploratory screen. Verify endpoint interval labels, completeness and availability time before calculating changes; do not forward-fill stale or missing ratios. The CFTC literature supports studying changes in positioning, but its weekly, delayed institutional categories do not validate Binance ratios or MEXC altcoin returns. A positive archival screen still needs a fresh prospective signal/return test. Report 1x/2x/3x costs; reject if it fails validation, adds no net value over the fixed level book, or depends on incomplete/stale inputs.

### 2. Aggressor-signed trade flow, after data feasibility

R226 used unsigned count and size; neither identifies which side initiated trades. One normalized signed-flow measure could be `(aggressor_buy_notional - aggressor_sell_notional) / total_notional`, but the source's side semantics must be validated against its documentation and prints before calling it signed flow. Test one definition, one fixed horizon and one fixed portfolio against quote-volume and existing flow controls. Avoid a many-horizon/bins sweep.

Historical Binance aggregate-trade data would be a large download and needs the owner's explicit approval under `AGENTS.md`; no download is authorized by this planning memo. A prospective event capture must preserve source venue, exchange timestamp, local receipt time, sequence gaps and the actual executable arrival delay. A short event-level markout is useful for price-formation research but may be too fast for a manual strategy; a favorable markout is not by itself a tradable portfolio edge. Treat older dates as exploratory and require net incremental value at frozen 1x/2x/3x costs on new data.

One operationally precise version of the existing C11 idea is signed order imbalance during the first 10 seconds after :15, :30 and :45 quarter-hour boundaries, with one 12-hour outcome. This is already in the claim ledger, not a newly discovered edge. The roughly 0.5 bp opening-return result is from a separate out-of-sample exercise; the 4–12h order-imbalance regressions and the 16.9 bp decomposed public-signal component use the paper's full sample and are not out-of-sample trading results. A :15/:30/:45-only test is a narrower follow-up because the main specification includes :00. See `docs/QUARTER_HOUR_AGGRESSOR_FLOW_PROPOSAL.md` for details, source-side semantics, and the data-feasibility gate. No historical tape download is authorized.

### 3. Size-aware MEXC shadow-cost calibration for an unchanged paper book

This does not search for alpha; it checks whether the lab's assumed costs erase or exaggerate an existing paper result. R224 currently has only two snapshots per coin, while its $10k median displayed-book estimate is about 9.6 bp API one-way versus an assumed 8 bp tier (`experiments/mexc_costs/journal/status.json`). That is not an execution-time or fill study. Capture timestamped MEXC depth around the frozen R215-A paper position changes, at a predeclared account notional, and compare side-specific book-walk cost plus the verified fee with the current tier estimate. Keep fees, spread/impact, funding, rejected/partial exposure and turnover separate. Report 1x/2x/3x and fixed-notional capacity. Call it a shadow cost estimate, not an executed fill; no orders are needed.

The public depth stream is useful for prospective book reconstruction, but displayed liquidity can disappear and local arrival latency matters. Do not install a general backtesting/execution framework to solve missing historical order-book data: the repo already has registered research and event-capture scaffolding, and the missing history cannot be reconstructed after the fact. See `docs/PERP_EXECUTION_AND_RISK.md` and `docs/RESEARCH_FRONTIER.md`.

### 4. MEXC next-funding-rate revision and exact carry ledger

R190–R191 already test trailing settled funding, R223 rejects a simple extreme-negative-settlement capture, and R220's replay is approximately flat. Do not repeat a funding-level or cross-venue funding-spread sweep. The open question is narrower: does the displayed next rate, or its within-cycle revision, forecast the next settled rate better than a no-change forecast? First score that forecast prospectively. Only if it adds information should a separately frozen portfolio test compare expected carry with realized spot-perpetual basis changes, exact settlement cashflows, fees and contract units. MEXC's current rate and `nextFundingTime` need timestamped capture; public historical depth and account fee details have separate limitations. See `docs/PERP_CARRY_ACCOUNTING.md` and `docs/MEXC_EDGES.md`.

### 5. New data feasibility: exchange-wallet netflow

Observed net deposits/withdrawals to identified exchange wallets are distinct from token unlock schedules, active-address counts and funding. They may represent changes in immediately saleable supply, but point-in-time wallet labels, token migrations, chain reorgs, provider revisions and coverage can easily create lookahead. Begin with a source and coverage audit only. No direction or return test should be chosen from the already-seen R181 unlock result. If labels cannot be frozen as they were known at each date, stop this axis.

### Separate risk and forecast-confidence work

Volatility forecasting is risk management, not a directional alpha claim. `docs/VOLATILITY_AND_TAIL_RISK_FORECASTS.md` already sketches an honest persistence/EWMA/HAR/GARCH horse race with QLIKE. Run that only as a separate, preregistered question. `docs/CONFIDENCE_AND_SIZING_AUDIT.md` documents why R217/R225 multipliers are risk overlays, why X2 is not calibrated confidence, and how to isolate the sizing premise in a later test. Likewise, a profitable rank portfolio does not make its per-coin probabilities calibrated. `docs/FORECAST_EVALUATION_PLAYBOOK.md` describes proper-score tests against a base rate and market-only forecast; a single generated path or path spread must not be treated as confidence.

## Selection and confirmation rules for the next lane

- Pick one mechanism, one primary feature definition, one horizon, one matched baseline and one primary estimand. A limited diagnostic set may be reported, but it cannot be searched for a better story after outcomes are read.
- Record parent rounds, the observation that triggered the follow-up, trial-count definition, prior date-window exposure and exploratory/confirmatory status. Raw trial totals describe search history; they are not automatically the number of independent tests and should not be fed blindly into Bonferroni.
- For a finite searched family, retain every attempted candidate and test the maximum statistic on common time blocks. The selection audit documents the minimum append-only ledger and the limits of raw `program_trials()` totals. Do not retroactively calibrate R221 or reopen a spent holdout.
- Use historical dates only as an exploratory filter when prior research has touched that calendar. A fresh confirmation starts after the specification is frozen, records on-time data append-only, forbids performance peeking and has one final decision.
- A claim needs valid point-in-time coverage, exact contract identity and lifecycle treatment, a sensible baseline, costs/funding, and positive net evidence at 1x and 2x with 3x reported. For the intended venue, a Binance signal tested on MEXC prices is transfer evidence; it is not evidence of MEXC fills.
- Do not progress to real money based on an edge statistic alone. The existing `go_real()` threshold does not gate dependence-aware sample size, drawdown, leverage, execution capacity, margin/liquidation or a maximum account-loss budget; see `docs/CAPITAL_GATE_REVIEW.md`, `docs/CONFIDENCE_REVIEW.md` and `docs/PERP_EXECUTION_AND_RISK.md`. Statistical evidence, execution evidence and owner-set capital limits are separate gates.
- Before using any cache, also satisfy the source-hash, expected-shard, interior-gap and exact-funding-event controls in `docs/DATA_PROVENANCE_AUDIT.md`; a processed-file hash by itself does not prove complete source coverage.

No new data were downloaded and no return statistic was computed for this update. Candidate counts, windows, cost rules and decision thresholds in any row above remain unregistered until an owner-approved preregistration is frozen.
