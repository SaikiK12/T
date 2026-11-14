# R257 mixed_signals_v1: regime-conditioned combinations of distinct executable targets

Finite specification committed before the first outcome calculation. Canonical method M234; round R257.

- **Registry id:** R257
- Owner: Codex, single writer on `codex/mixed-signal-study`.
- Runner: `scripts/run_mixed_signals.py`.
- Runner SHA-256: `d312aa6b1493682cba196dd6ed7065f73dfbd3d00e50b963909eb8152a96d29f`

## Question, source scope and previous information

Does combining time-series channel trend, cross-sectional relative-strength continuation and short-horizon
cross-sectional reversal according to a predetermined BTC price regime improve validation PnL/risk after the
actual trades and costs of the combined target are simulated?

This mixes desired instrument positions before execution. It does not average separately measured strategy
Sharpe ratios, add equity curves without accounting for trades, or assume the component signals are independent.
All components use prices; distinct rule types do not establish distinct information or independent alpha.

Borrow the exact component definitions and data/accounting infrastructure from the pinned R229 and R230 code and
frozen specifications. R229's source is Zarattini, Pagani and Barbon, *Catching Crypto Trends*, cover dated 2025-04-09,
[primary author-hosted PDF](https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf),
whose received-byte SHA-256 and adaptations are in `experiments/slow_trend_v1/PREREG.md`.
R230 cites Liu, Tsyvinski and Wu's [author-hosted April 2019 manuscript](https://economics.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
for cross-sectional momentum, and White's [primary manuscript](https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/White.pdf)
for accounting for a searched family. Those received references motivate components/diagnostics; the original full
papers are not newly re-read for this draft. The regime thresholds, 7-day reversal, proportions and state-dependent
combinations below are this study's explicit research choices, not claims attributed to those papers.

R229 tested the two standalone trend variants; R230 tested weekly momentum/reversal rotation and a BTC gate; R231
tested partial execution of the unchanged trend target; R232 tested equal-weight cadence. This new finite family
instead conditions a target-level mixture on three fixed regime definitions and daily executes the combined
holdings. The overlapping components and earlier results are disclosed, not independent rediscoveries.

The investigator/lab has previously seen these assets, windows and related study results. ALL splits are spent,
exploratory gate 0, including `known_holdout`. No archive result can confirm an edge, authorize a live bot, or prove
transfer to MEXC perpetuals. A pass can only motivate a separately frozen prospective study.

## Fixed inputs and checks before outcomes

Reuse ONLY R229's already cached 414 Binance SPOT daily ZIPs, January 2021 through September 2026:
BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, in that fixed order. Exactly 2,099 finite positive closes per
symbol, 2021-01-01 through 2026-09-30. This is a fixed six-survivor universe, not point-in-time altcoin coverage.
No new download, alternate coin, interpolation, missing-value repair, contract, funding series or model is allowed.

Before opening any price value, verify this lane's frozen spec and exact runner digest, its Registry id against
the code's ROUND_ID/seed, and every hard-coded DEPENDENCIES digest. The pinned R230 guard also verifies its own
frozen spec/runner and pinned dependencies. R229's `load_prices` then verifies its frozen spec/code, locked data
manifest, archive bytes/publisher checksums, documented timestamp units and complete fixed calendar.
Missing or changed data/dependencies stop this evaluation; do not silently choose another cache revision.

`--raw-dir` defaults to the existing `/workspace/quant-small-data/slow_trend_v1/raw`. `--out` must name a new path;
an existing directory or symlink is refused. Provenance/hash/registration failures stop before market reads and
before output creation. Subsequent data, numerical or required-metric failures are recorded INCONCLUSIVE in the
new result directory. Retain the partial artifacts and failure; no truncated window or dropped family member.

## Exactly 36 candidates and four controls

Enumerate the Cartesian product in this order; exact selection ties retain the first enumerated item:

1. BTC regime: `btc_ret28`, `btc_ret56`, `btc_sma200`.
2. Bull trend proportion p: 0.25, 0.50, 0.75.
3. Bear template: `cash`, `trend`, `half_trend_reversal`, `reversal`.

Each regime is known at close t:
- `btc_ret28`: bull iff BTC close[t] > close[t-28], available from t=28.
- `btc_ret56`: bull iff BTC close[t] > close[t-56], available from t=56.
- `btc_sma200`: bull iff BTC close[t] > mean(close[t-199:t+1]), available from t=199.

Equality is not bull. Before the regime has enough history, that candidate's target is all cash, rather than
assuming an observable bear state. No future close, realized volatility or later regime label enters the rule.

Fixed components at close t:
- **T, trend:** R229 **`trend_plain` only**: the nine binary long/cash close-channel components for horizons
  5/10/20/30/60/90/150/250/360, stateful trailing midpoint stops exactly as R229, averaged and divided by six.
  The `trend_vol` variant and any new volatility overlay are excluded from this finite family.
- **M, momentum:** rank each coin's close[t]/close[t-28]-1 descending; target one third in each top-three coin.
- **R, reversal:** rank the negative 7-day return descending; target one third in each bottom-three coin.

Ranking ties preserve the fixed symbol order. M/R are cash before their respective histories are available.
In a known bull state, target = p*T + (1-p)*M. In a known nonbull state, target is respectively 0, T, 0.5*T+0.5*R,
or R according to the bear template. All weights are nonnegative, sum <=1 and are desired POST-COST NAV fractions.
Cash earns zero. There is no shorting, borrowing, leverage, additional window, p value, filter or stop search.

Controls, in exact tie order: **trend**, **momentum28**, **reversal7**, **passive**. The first three use the same
unchanged T/M/R definitions and daily rebalance. Passive is constant equal-six weights, rebalanced before return
dates labeled the first UTC day of a month, otherwise keeping units. All controls share initialization, execution,
source universe, terminal exits and costs. Cash is a template, not an additional selectable control.

## Execution, full costs and windows

Use the pinned R230 exact self-financing `account`, alpha=1. Each daily candidate and each active component control
rebalances before every scored return. Row i executes at close C[i-1] using only target[i-2] and earns the move to
C[i]: a full daily bar separates the signal close from the modeled execution boundary. The passive target is known
ahead of time; its constant target can use the same index. No same-bar fill shortcut or OHLC touch fill is added.

Before each rebalance mark existing units at C[i-1]. Solve
`NAV_after + c*sum(abs(desired_weight_j*NAV_after-current_dollars_j)) = NAV_before`
with R230's 55-step bisection, then update actual units/cash. Combine targets before this execution: fees arise
from the net change in the combined instrument holdings, not summed standalone sleeve trades. Track actual
drifted holdings; do not approximate turnover with yesterday's desired weight differences.

Rerun complete accounts at one-way costs 12/24/36 bp (1x/2x/3x): the inherited modeled 10 bp fee +2 bp slippage at
1x. These are frozen assumptions, not current account-specific schedules, recorded fills or capacity estimates.
Each account starts units0/cash1 at EACH split, including forced initialization off the passive cadence, and
liquidates every remaining unit at the split's final close with exit costs charged to that final return.
Unlike R253's summary-only stress data, all daily paths and statistics here are simulated independently at all
three costs. Never multiply a saved net return or subtract a mean cost to manufacture another cost tier.

Discovery: 2022-01-01..2023-12-31, 730 returns. Validation: 2024-01-01..2025-06-30, 547 returns.
Descriptive `known_holdout`: 2025-07-01..2026-09-30, 457 returns. 2021 warms indicators and is not scored.
Indicators can use earlier closes across split boundaries; positions, cash and NAV restart for each account.

## Discovery-only selection and capital scaling

Compute unscaled discovery 1x and 2x paths for all 36 candidates and four controls. Select ONE candidate with
highest unscaled discovery 2x net Sharpe, and separately ONE control with highest unscaled discovery 2x Sharpe.
Sharpe uses population SD and sqrt365. Use their declared orders to break exact ties. No performance threshold
filters an alternative, and validation/known_holdout cannot choose or replace either winner.

For every candidate j, using only its unscaled discovery 1x net sample SD s_j and the selected control's unscaled
discovery 1x SD s_c, fix candidate_scale[j]=min(1,s_c/s_j) and control_scale[j]=min(1,s_j/s_c). Zero/nonfinite
selection risk or score makes the evaluation INCONCLUSIVE; do not remove the offending candidate or control.

Rerun EACH candidate and its separately risk-scaled selected control for every split and cost tier. Apply each
capital scale to desired target weights inside the self-financing engine, with the residual in cash. Neither side
leverages. This targets equal discovery risk; execution costs/drift mean actual scaled volatility can differ.
Record observed volatility and exposure. Also tabulate full-size standalone controls for context.

## Uncertainty and the one fixed decision

Build all 36 columns of validation 1x daily differences, candidate_j minus its selected-control account at that
pair's frozen scales. Use the pinned R230 `bootstrap_family` helper with 5,000 common circular moving-block draws,
primary block 30 and fixed seed **20261020257+block**. Blocks 10/60 are nondecisive sensitivities. ROUND_ID and seed
must be updated together before freeze if the provisional registry id changes; neither may change after outcomes.

Center each column, resample synchronized dates, keep each original Bartlett NW(10) mean SE fixed, and compare
the maximum centered bootstrap t across all 36 columns with the discovery-selected candidate's observed t.
Family-max p=(1+exceedances)/5001. The selected paired mean receives an ordinary percentile 95% interval.
Required undefined means/Sharpes/drawdowns/standard errors are INCONCLUSIVE; no day, column or replicate is dropped.
This is a conditional diagnostic on spent dates, not a proven correction for the lab's prior searches, control
selection, nonstationarity or survivor selection.

The discovery-selected candidate passes only if all five hold on validation:
1. 1x Sharpe >= its matched selected control's Sharpe +0.15;
2. candidate mean daily net >0 at 2x costs;
3. 1x compound max drawdown, including initial NAV1, <= matched selected control's;
4. primary selected paired-mean 95% lower endpoint >0;
5. primary 36-family max-statistic p <=0.05.

All pass => PARTIAL exploratory candidate for a separately frozen prospective study. Otherwise NULL. There is no
CONFIRMED verdict. Other candidates, sensitivity blocks, positive gross numbers or known_holdout cannot rescue a
failure. Count **36 candidate trials** once; controls and bootstrap draws are comparisons/computation, not extra
independent discoveries. No wider grid, replacement component or retuned rule after the first market run.

## Compact artifacts, provenance and stopping

Save all unscaled discovery 2x candidate/control selection scores; grid_metrics.csv for all 36 matched pairs and
standalone_controls.csv for all four full-size controls at every split/cost; fixed choice/scales; bootstrap
summaries; verdict; and a source/code/spec/software manifest with output hashes. Summaries include mean, sqrt365
volatility/Sharpe, NW(10)t, compound drawdown, dollar costs, turnover, exposure and final NAV.

Only the selected candidate/matched-control full daily account paths are stored, across every split/cost, in
deterministic `selected_daily.csv.gz`: net, gross, fee fraction/dollars, turnover, exposure, NAV, ending cash and
held units. Held units describe exposure during the return, before a possible terminal liquidation; ending cash
already includes that exit. Do not duplicate the input price cache or store all candidate tensors.

The manifest hashes all result bytes except itself; the anticipated verdict bytes are hashed before the verdict
is written last. A data/numerical failure retains an INCONCLUSIVE verdict and any partial artifacts. If a write
failure already created a partial verdict, preserve it and write `inconclusive.json`; that failure takes precedence.
A fresh-directory repeat must reproduce output bytes; retain both rather than overwriting. Parent completes the
append-only registry record and canonical-queue reconciliation after review/run. This draft writes neither queue
nor journal. No frozen older file, forward lane, account, secret, trade, money movement or PR merge is part of it.
