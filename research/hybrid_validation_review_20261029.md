# Adversarial review: hybrid portfolios, gates, and validation

**Scope.** Static review of R285 and the existing selection audit/findings as of 2026-10-29. No outcomes were recalculated, no data were pulled, and no frozen lane was edited. This is a design review, not evidence that an ensemble or gate has positive expected PnL.

## Assessment

Combining strategies is economically plausible when their *net, investable* returns have distinct sources of risk and imperfect dependence. That is a reason to test a blend; it is not evidence that selecting low-correlated historical winners creates future alpha. A blend can improve a risk statistic simply by lowering exposure, inherit a parent's market beta, or look diversified because its accounting omits open-position mark-to-market. The decisive claim should be net incremental value versus a preselected parent at a common capital and risk constraint.

The repository already has useful adversarial evidence. R228's selected static flow blend was NULL against X2; R233's regime/MIX design was NULL; R253's three static optimizers were NULL against the incumbent; and R309's fixed carry-plus-spot mix was NULL against carry. These outcomes do not rule out all ensembles. They do show that more sleeves, optimizer names, or regime labels have not yet produced demonstrated incremental value here. R228 also documents substantial overlap among A, B, and X2, so sleeve count and labels are poor substitutes for distinct information.

R285 is a worthwhile frozen prospective question, but its decision is an absolute-book test under a particular archive-volatility normalization. Its frozen decision does not require the composite to beat the best individual family or a capital-matched parent. The reported comparison to the best family is descriptive. Therefore even a R285 pass would establish only that this specified book clears its registered conditions; it would not establish that diversification added value. Keep R285 unchanged. Any incremental-value claim needs a separately frozen comparator design and evidence collected prospectively after that design is fixed.

There is also a material measurement issue in R285's event sleeve: tickets are booked on primary-exit day and days with no exits are zero, while open event positions are not marked to market daily. That series can misstate the sleeve's volatility, covariance, and capital path. The archive correlations are in-sample context from selected parents, not evidence of forward independence. Equal archive risk is not equal capital or margin feasibility; R285 itself flags a large carry notional requirement and a prior liquidation concern. These are interpretation limits, not grounds to alter the frozen specification.

## What the primary literature supports

Bates and Granger's forecast-combination result motivates combining forecasts whose errors differ, but it is a forecast-error result, not a trading-PnL result ([1969 paper](https://doi.org/10.1057/jors.1969.103)). Timmermann's review explains why simple combinations can be robust when estimated error covariances and weights are unstable; this is a caution against fitting many weights, not a finding that equal weights maximize net crypto returns ([2006 chapter](https://doi.org/10.1016/S1574-0706(05)01004-9)).

Markowitz gives the mean-variance framework, whose portfolio weights depend on estimated means and covariances ([1952 paper](https://doi.org/10.1111/j.1540-6261.1952.tb01525.x)). DeMiguel, Garlappi, and Uppal found that a broad set of sample-based optimizers did not consistently beat naive 1/N across the equity datasets they examined; estimation error and turnover matter ([2009 paper](https://doi.org/10.1093/rfs/hhm075)). This supports a frozen, low-parameter blend as a sensible baseline against fitted weights. It does not establish 1/N or archive-vol equalization as optimal for crypto perps, nor remove the selection bias from choosing parent strategies on the same historical record.

For a declared finite search, White's Reality Check tests whether the best searched model beats a benchmark after data snooping ([2000 paper](https://doi.org/10.1111/1468-0262.00152)); Hansen's SPA improves power against irrelevant alternatives while retaining the need to supply the searched family ([2005 paper](https://doi.org/10.1198/073500105000000063)); Romano-Wolf stepdown can support candidate-specific claims while controlling familywise error under dependence ([2005 paper](https://doi.org/10.1111/j.1468-0262.2005.00615.x)). None recovers omitted researcher choices or automatically corrects a later selection among families. The repository's selection audit correctly treats raw trial totals as disclosure, not as a calibrated effective count. PBO/CSCV and the Deflated Sharpe Ratio can be useful selection diagnostics ([Bailey et al.](https://escholarship.org/uc/item/4w1110bb); [Bailey and López de Prado](https://doi.org/10.3905/jpm.2014.40.5.094)); they do not replace an untouched chronological prospective evaluation, especially when market regimes drift.

## Comparison structure for a successor

Before collecting decision-period observations, freeze one candidate blend and one primary benchmark. Define aligned daily net returns on the same UTC calendar and the same account denominator. For parent sleeve $i$, let $r_{i,t}^{net}$ include its existing execution, fee, and funding assumptions. Then define:

\[
r_{mix,t}^{net}=\sum_i w_i r_{i,t}^{net}-c_{rebalance,t}-c_{incremental\ execution,t},\qquad \sum_i w_i=1.
\]

Do not deduct costs already embedded in the parent series twice. Charge any additional turnover, re-hedging, financing, borrowing, or impact introduced by the blend. Freeze the missing-sleeve rule, trade timing, exit/marking convention, and position/cash treatment; do not renormalize weights on days when a sleeve is missing unless that rule was frozen. Include cash as an explicit sleeve whenever capital is left unallocated. For event sleeves, carry daily mark-to-market exposure while a position is open, then reconcile final realized PnL and costs at exit.

Choose the parent benchmark using training data only, before the evaluation period. The primary series is the paired differential

\[
d_t=r_{mix,t}^{net}-r_{parent,t}^{net},\qquad H_0:E[d_t]\leq 0.
\]

The primary decision should ask whether the blend is both net profitable under its frozen cost stress and incrementally better than that parent under a predeclared capital/risk constraint. Report the differential in account return units and a risk-matched comparison; a Sharpe increase caused only by scaling the same parent down is not alpha. Keep the equal-capital blend, every constituent parent, and a passive/cash alternative as fixed secondary controls. If the “best parent” is selected after looking at evaluation data, test the maximum over all parent controls with the same joint procedure rather than treating the chosen parent as fixed.

If using equal-risk weights, label them precisely (for example, “standalone archive-vol scaled”) and freeze the volatility estimates and weights from training/archive data. This does not make future risks equal, make the account feasible, or undo selection upstream. If using ERC, HRP, minimum variance, or learned weights, treat each formula, covariance window, shrinkage setting, update schedule, and constraint set as separate candidate choices from a training-only family. Freeze rebalance frequency and turnover bounds. Do not fit or retune weights on the forward decision sample. Model collateral, liquidation, cross-margin/netting, and open-position marks before calling a normalized return stream an executable account.

For a dynamic gate, define $g_t=f(x_{t-1};\theta)$, where every state input is available at the actual decision time, and freeze $f$, thresholds, warm-up, update schedule, delay, and position transition before the test. Set $r_{on,t}^{net}=r_{parent,t}^{net}$ for the ungated strategy, and compare the gate with that parent on identical capital, timing, and costs:

\[
r_{gate,t}^{net}=g_t r_{on,t}^{net}+(1-g_t)r_{off,t}^{net}-c_{switch,t},
\qquad d_t^{gate}=r_{gate,t}^{net}-r_{parent,t}^{net}.
\]

For a simple on/off overlay, $r_{off}$ must be the specified alternative (usually cash), not a post hoc favorable control. Charge switching, hedge adjustment, and delayed fills. Select thresholds and regimes on training data only. A validation result cannot also choose the gate, and repeated manual intervention ends confirmatory status. R233 shows why a regime narrative or a locally strong segment is insufficient: its registered rule found no gate, and its MIX did not clear its frozen increment bar.

## Dependence and prospective decision rules

Use paired daily differentials and serially robust uncertainty. For a finite set of blend/gate candidates or multiple benchmark claims, resample contiguous time blocks jointly across every candidate and benchmark so common market shocks and cross-strategy dependence remain intact. Center the differential under the null; freeze block length/sensitivity, studentization, bootstrap count and seed, universe/calendar, candidate family, cost tiers, and statistic. Use SPA as the primary family test, Reality Check as a conservative sensitivity, and Romano-Wolf only for predeclared candidate-specific claims. Include all tried thresholds, weights, windows, parent combinations, sample cuts, failed variants, and interim looks in the lineage. Do not use an estimated effective trial count as a substitute for the candidate matrix.

The cleanest confirmation is one terminal evaluation of one frozen candidate against one frozen parent, on data not used to create or select either. If interim decisions are necessary, calibrate the maximum over candidates, comparators, and all looks jointly under a frozen dependence-aware procedure. R285 has two planned looks and an inherited Bonferroni threshold; the audit notes that nominal boundaries have not been calibrated for overlapping/dependent observations. Do not retrofit its boundary or decision. Treat the already examined archive and historical holdouts as hypothesis-generation only; prospective forward observations can test only the frozen question, not a later blend inspired by interim outcomes.

## Recommendation

Retain the existing NULLs and R285 preregistration as written. Read any R285 pass as “the frozen cross-family book cleared its absolute gates,” not “the blend beat its parents” or “equal-risk diversification is proven.” A successor should test one frozen blend or gate against its best training-selected parent with the paired net differential above, common account constraints, daily marking of open risk, and all candidate/look dependence handled in advance. The core acceptance question is whether net incremental value survives costs and the parent comparison in genuinely prospective data.
