# R253 optimizer_v1: three static risk allocations over the existing flow sleeves

- **Registry id:** R253
- Canonical method: M027. Owner: Codex, single writer on `codex/static-optimizer-study`.
- Prepared 2026-10-20. Freeze and commit this spec, runner and tests before computing study outcomes.
- Runner: `scripts/run_optimizer.py`.
- Runner SHA-256: `3323df8a7eb3bbb75811654f1c13d943fb71fa20e0b568e9dc558e6cb12884cc`

## Question and received scope

Do minimum variance, equal risk contribution or hierarchical risk parity improve the existing A/B/X2 allocation
beyond the R228 incumbent, after matching discovery risk and accounting for the original books' trading costs?
This is a finite allocation study, not a new signal search. R228 tested 30 endpoints/pairwise mixtures; R233 tested
fixed regime mixtures. Neither fitted these three risk allocators. No rolling refit, online weighting, new sleeve,
short allocation, leverage or covariance-estimator grid is included. M026 online learners remain open.

The owner expanded the objective to net PnL across spot, perpetuals, forex, indices and prop challenges. That scope
does not make every market one dataset: this study uses the archived Binance crypto-perpetual flow sleeves only.

Primary references and exact reading extent are in `SOURCES.json`: Maillard/Roncalli/Teiletche's primary abstract
for equal risk contributions; Lopez de Prado's author publication entry/primary abstract for HRP; the inspected
PyPortfolioOpt primary implementation for clustering/bisection. The original full papers were not reread; the ERC
author PDF returned HTTP 503. The precise executable definitions below are this study's fixed implementation.

## Prior information and inputs

The investigator and lab have previously computed and seen these dates and books. R217/R228/R233 summaries and
R228's selected weights have informed the design. The known R228 incumbent is **0 A / 0.3 B / 0.7 X2**. Its validation
Sharpe improvement was only about 0.007 over its endpoint control. No fitted optimizer weight or new outcome has
been computed for this lane before its freeze/commit. ALL windows are spent, exploratory gate 0. There is no fresh
holdout claim and no CONFIRMED verdict available.

Reuse `experiments/sizing_v1/results/daily.npz`, keys `A_C0`, `B_C0`, `X2`, exactly 2,099 finite daily returns per
source, 2021-01-01 through 2026-09-30. Dates come from the pinned source script. No network or new market download.
The archived NPZ SHA-256 is `3ea686670c35c9946a560cc29cd1087b79cbeef40a78208840ab3b3e86aa0ec5`.
`scripts/run_allocation.py` already verifies R217/R228 frozen specs, NPZ, summary CSV and original sizing runner
digests, shapes, finite values, split counts, exact 1x summary agreement and nonnegative linear cost decrements.
Call its guards before parsing outcomes; the new runner also verifies its own digest and its hard-coded
DEPENDENCIES (allocation runner, weekly-rotation inference helper, lab stats and prereg). Hash changes stop the run.
Inherited raw-return missing-data/fill assumptions cannot be repaired from daily sleeve summaries.

Windows: discovery rows [0,1095), validation [1095,1642), descriptive known holdout [1642,2099).
Only discovery may determine covariance, allocation weights, selected method or risk scales. Known holdout is
reported after selection and never decides or rescues the verdict.

## Exactly three allocators

Use the unbiased discovery sample covariance of the three saved 1x net streams, in A/B/X2 order. Require finite
symmetric 3x3 covariance, nonzero scale and smallest eigenvalue > trace(covariance) x 1e-12. Normalize by trace
for numerical work. No shrinkage, diagonal loading, removed sleeve or alternate window after failure. This shared
positive-definite input contract is a study restriction, not a claim that HRP generally requires invertibility.

1. **min_variance:** minimize w'Cov w subject to w >= 0 and sum(w)=1. Enumerate the seven nonempty simplex faces
   in ascending face size/lexicographic index order. On each face solve Cov_active v=1 and normalize; discard a
   face if any normalized weight < -1e-12, otherwise clip tiny negatives to zero and renormalize. Select the
   strictly smallest variance; exact ties retain the first enumerated face.
2. **equal_risk:** solve the positive convex objective .5 x'Cov x - sum(log(x))/3 by cyclic coordinate descent in
   A/B/X2 order. Start x_i=1/sqrt(Cov_ii). Holding other coordinates fixed, set
   x_i=(sqrt(c_i^2+4 Cov_ii/3)-c_i)/(2 Cov_ii), c_i=sum_{j != i} Cov_ij x_j. Normalize w=x/sum(x).
   Stop when every variance contribution w_i(Cov w)_i / (w'Cov w) differs from 1/3 by <=1e-10, within 10,000
   sweeps. Failure is INCONCLUSIVE; no tuned retries.
3. **hrp:** correlation distance sqrt((1-corr_ij)/2), with correlation clipped to [-1,1]. Three-asset single
   linkage merges the smallest-distance pair first; ties use the lexicographically first pair. Canonical leaf order
   is outsider, smaller pair index, larger pair index. Recursively bisect that order at floor(length/2). Cluster
   risk is its covariance variance using normalized inverse-diagonal weights. Allocate between children in inverse
   proportion to their cluster variances. Recurse to leaves and normalize. No linkage/order search.

All weights must be finite, nonnegative, sum to one and remain constant in every window. Select the highest
discovery 1x population-standard-deviation Sharpe among the three; exact ties use the order above. Tabulate all
three regardless of selection. Controls: fixed R228 incumbent, equal one-third allocation and each single sleeve.

## Account model and costs

As R228, linear segregated sleeves at fixed reference notional: daily 1x PnL is sum(w_j net_j). There is no
cross-sleeve netting refund, NAV rebalancing or learned day-to-day switching. A, B and X2 overlap; three allocators
are not three independent sources of alpha. No capacity, minimum contract size or MEXC fee/fill assertion follows.

At 1x report daily mean, sqrt365 population Sharpe, NW(10) t, additive drawdown including initial zero equity and
weighted gross exposure. At 2x/3x, report EXACT SPLIT MEANS by weighting the original corresponding CSV means.
Their daily paths, Sharpe, drawdown, t statistics and intervals are unavailable and remain NA. Do not subtract an
average fee from every date or fabricate a stressed path.

For each optimizer/control pair, let s_c and s_b be discovery daily sample standard deviations of candidate and
incumbent. Freeze candidate_scale=min(1,s_b/s_c), incumbent_scale=min(1,s_c/s_b). Their remaining capital earns
zero. This matches discovery risk with neither side levered. Report pairwise scaled results in every window at
1x and scaled exact means at 2x/3x. Also retain full-size tables and endpoint/equal-weight controls.

## Single validation decision and uncertainty

Build the three columns of validation 1x candidate-minus-incumbent daily PnL at their respective frozen risk
scales. Reuse the pinned R230 circular moving-block helper: common sampled dates for all columns, 5,000 draws,
primary block 30 days, seed 20261020253 + block length; lengths 10/60 are nondecisive sensitivities. Center each
column and use its fixed original Bartlett NW(10) mean standard error. The maximum centered t across the three
columns gives the family-max diagnostic p=(1+exceedances)/(5000+1). The selected paired mean has an ordinary
percentile 95% interval. Undefined required metrics/standard errors are INCONCLUSIVE; no column/day/replicate
may be dropped. This diagnostic is approximate and conditional on spent dates; it does not correct the lab's
earlier searches, the published incumbent selection or nonstationarity.

The discovery-selected allocator passes only if ALL hold on validation:
- 1x Sharpe gain over its scaled incumbent >=0.15;
- risk-matched 1x mean gain >0;
- candidate mean >0 at 2x original costs;
- candidate additive drawdown <= its scaled incumbent's;
- primary paired mean 95% lower bound >0;
- primary three-method family-max p <=0.05.

All pass => PARTIAL exploratory candidate for a separately frozen prospective study; otherwise NULL. There is no
validation-best substitution. A required contract/metric failure gives INCONCLUSIVE, not a disguised null or pass.
Multiplicity: **3 new method trials**, not seven internal solver faces or resample counts. No wider grid after run.

## Artifacts and stopping

Write metrics.csv (all methods/controls, all windows/cost means), risk_matched.csv, fixed selection/weights and
covariance, bootstrap summaries, verdict, input/code/spec/software manifest and deterministic gzip daily paths for
only the selected risk-matched pair. `--out` supports a fresh directory; refuse a nonempty one. Provenance/hash
failures abort before any output directory or verdict is written. After those guards, retain data/calculation
failures as INCONCLUSIVE and preserve old artifacts. Append one completion row through lab.registry, preserving the old journal.
Reconcile M027 exact scope in the canonical CSV/room; do not introduce another queue or panel. Frozen older files
and forward lanes remain intact. No orders, credentials, large data/model download, PR merge or live-money action.
