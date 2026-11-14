# Adaptive selection and concept drift: when a signal stops working

Reviewed 2026-10-19. The project has a planned policy layer in `lab/policy.py` that
chooses among already measured return streams using trailing performance, shrinkage,
rebalance intervals and a turnover-matched random policy. This note supplies the
research discipline for that layer. It does not turn an adaptive policy into a new
confirmation of the underlying signals.

## Three different things can change

1. **The market distribution can move.** Volatility, liquidity, correlations,
   funding and the eligible universe can change while the signal-to-return relation
   stays similar.
2. **The signal can lose conditional predictive value.** The same feature can have a
   smaller or reversed relation to the target after a regime or participant change.
3. **The implementation can deteriorate.** A stable gross relation can stop paying
   after fees, spread, partial fills, latency, funding or a contract change.

A detector trained on feature distributions cannot establish a change in forecast
skill. A detector trained on realized losses is delayed by the outcome horizon and is
itself a forecast-selection rule. Track these streams separately and do not call a
covariate alarm evidence that the portfolio edge has disappeared.

## What the methods literature supports

Gama and coauthors classify concept drift as abrupt, gradual, recurring or
incremental and emphasize that a detector must be paired with an adaptation rule
([survey, 2014](https://doi.org/10.1145/2523813)). The taxonomy is useful for naming a
failure mode; it does not select a detector or show that financial returns have a
stable, observable drift process. ADWIN-style detectors compare recent and older
windows while adapting their width ([Bifet & Gavaldà, 2007](https://doi.org/10.1137/1.9781611972771.42)).
Their concentration assumptions are strained by autocorrelation, volatility
clustering and overlapping crypto labels. If used here, the window rule and alarm
threshold must be frozen before the scored period, and alarms should be based only on
information that would have arrived by the decision time.

Giacomini and White's conditional predictive-ability framework evaluates whether a
forecast is useful conditional on the information set used for selection
([2006](https://doi.org/10.1111/j.1468-0262.2006.00718.x)). This is closer to the
project's question than comparing a model selected after the full sample. It still
requires a predeclared loss, an estimation window and a serial-dependence treatment.
White's Reality Check and Hansen's SPA address the best result from a searched family;
they do not make an unrecorded sequence of adaptive choices independent.

Online portfolio-selection surveys show why transaction costs matter: a rule that
switches toward a recent winner can give up its advantage in turnover even when the
selection statistic is directionally right ([Li & Hoi, 2014](https://doi.org/10.1145/2512962)).
These algorithms provide comparison ideas, not evidence that they work on crypto
perpetuals. The project must price every rebalance, preserve exposure constraints and
compare against a turnover-matched no-skill policy.

Rolling-origin evaluation is the natural clock for an adaptive strategy: each refit
uses only data before the next forecast block ([Tashman, 2000](https://doi.org/10.1016/S0169-2070(00)00065-0)).
Window length should be selected by past-only validation rather than chosen from the
full sample; predictive relationships can change as the window changes
([Pesaran & Timmermann, 2007](https://doi.org/10.1016/j.jeconom.2006.03.010)). Dynamic
model averaging and online expert weighting are comparison families, but their
guarantees concern forecast loss or regret against a benchmark, not positive net
returns after crypto fees ([Koop & Korobilis, 2012](https://doi.org/10.1111/j.1468-2354.2012.00704.x);
[Freund & Schapire, 1997](https://doi.org/10.1006/jcss.1997.1504)).

Recent crypto factor work also points in this direction. Wang and Pang's October
2026 preprint reports that the selected cross-sectional signals vary across rolling
windows and that full-sample StepM selects none at its stated threshold
([preprint](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7556359)). It is a
preprint with different data and an accessible abstract that does not settle later
persistence. It supports testing temporal stability, not choosing a rolling winner
from the current project.

## Proposed `adaptive_selection_v1` lane

Open a new immutable lane after the active forward books are decided. Do not alter
R198 or R200 and do not use their observed holdout or forward outcomes to choose the
policy parameters.

**Candidate set.** Freeze a finite matrix of previously defined, net-of-cost daily
strategy streams. Include the fixed equal-weight reference book, the candidate
selection pool and a turnover-matched random policy. Do not add a new signal after the
adaptive lane starts. Keep the candidate definitions, missing-data rule, eligibility
and costs identical across policies.

**Information clock.** At a rebalance date, use only returns whose full outcome window
has ended. A 72-hour slice cannot be scored as a one-day observation when only its
first day is known. Save the candidate scores and selected set before the forward
segment is evaluated. If a data revision changes an old score, retain the value that
was available at the original selection time.

**Nested choice.** Use an inner, past-only validation period to choose one lookback,
rebalance interval, number of names, shrinkage rule and switching-cost assumption.
Lock those choices for the next outer evaluation block. If the lane compares several
adaptive families, use synchronized date-block resamples and a family-wise procedure;
do not report the best window as if it had been specified in advance.

**Primary comparison.** Predeclare one net daily loss differential between the
adaptive policy and the fixed reference book. Report the mean, a date-block or HAC
interval, turnover, gross and net exposure, maximum drawdown, worst day and coverage.
Use the same selected dates and cost multiplier for both policies. Repeat the final
summary at 1x, 2x and 3x costs, but do not select the multiplier after seeing the
result.

**Drift alarms.** Keep feature-distribution alarms, forecast-loss alarms and
execution-cost alarms in separate columns. An alarm can reduce size or abstain only
under a predeclared rule. If the policy is allowed to stop after a loss streak, charge
the opportunity cost of the stopped periods and compare it with a no-stop policy. A
post-hoc stop that removes the losing dates is a new strategy, not risk management
for the old one.

**Meta-labeling.** A secondary model may filter or size a frozen primary direction
signal, but triple-barrier labeling is only a target definition. Freeze the barrier,
vertical horizon, costs, funding and delay; train only after each label's full outcome
has matured; purge overlapping events and embargo at least the maximum label horizon;
and use nested chronological validation for the filter threshold and model size. A
2026 futures meta-labeling preprint found near-chance AUC and no paired-bootstrap
interval excluding zero across five contracts, while a 2025 Binance BTC/ETH study
using triple-barrier labels reports after-cost results on two highly liquid assets.
These are design references, not evidence for an altcoin-perpetual improvement
([meta-labeling study](https://doi.org/10.2139/ssrn.7356724);
[crypto triple-barrier study](https://doi.org/10.1186/s40854-025-00866-w)).

**Dependence.** Use the same contiguous date blocks for every candidate and policy.
Set the minimum block length at the largest mechanical target/holding overlap, then
run a sensitivity with longer blocks for persistent regimes. Shared market shocks
mean that coin rows cannot be resampled independently. The effective sample size of
the selected policy is the number of date blocks carrying independent information,
not the number of coin selections.

## A small arithmetic warning

Suppose two hypothetical strategies each earn 1 basis point per day in the half of a
100-day sample when they are active and lose 1 basis point in the other half. An
oracle that switches exactly once earns 100 basis points gross. If the switch costs
15 basis points, it earns 85 basis points net; a policy that switches ten times pays
150 basis points and loses 50 basis points even with the same gross selection skill.
The numbers are invented and do not describe this project. They show why a recent-
winner rule needs an explicit turnover baseline.

## What would count as evidence

An adaptive policy is useful only if its frozen, past-only choices improve the primary
net differential against the fixed reference and matched-random policy on a genuinely
forward block, with the result surviving the declared cost stress and dependence
treatment. A positive result would support a conditional policy for that candidate
pool; it would not prove that any individual signal predicts every coin. A null result
would be useful evidence that recent performance is not a reliable selection guide.

No market data, project returns or new test statistics were run for this note. It is a
method and preregistration guide; `lab/policy.py` remains unchanged.

## Sources

- Gama, Žliobaitė, Bifet, Pechenizkiy and Bouchachia, ["A survey on concept drift adaptation"](https://doi.org/10.1145/2523813), *ACM Computing Surveys* (2014).
- Bifet and Gavaldà, ["Learning from time-changing data with adaptive windowing"](https://doi.org/10.1137/1.9781611972771.42), *SDM* (2007).
- Tashman, ["Out-of-sample tests of forecasting accuracy"](https://doi.org/10.1016/S0169-2070(00)00065-0), *International Journal of Forecasting* (2000); Pesaran and Timmermann, ["Selection of estimation window in forecasting"](https://doi.org/10.1016/j.jeconom.2006.03.010), *Journal of Econometrics* (2007).
- Giacomini and White, ["Tests of Conditional Predictive Ability"](https://doi.org/10.1111/j.1468-0262.2006.00718.x), *Econometrica* (2006).
- Koop and Korobilis, ["Forecasting inflation using dynamic model averaging"](https://doi.org/10.1111/j.1468-2354.2012.00704.x), *International Economic Review* (2012); Freund and Schapire, ["A decision-theoretic generalization of on-line learning"](https://doi.org/10.1006/jcss.1997.1504), *Journal of Computer and System Sciences* (1997).
- Li and Hoi, ["Online portfolio selection: A survey"](https://doi.org/10.1145/2512962), *ACM Computing Surveys* (2014).
- White, ["A reality check for data snooping"](https://doi.org/10.1111/1468-0262.00152), *Econometrica* (2000); Hansen, ["A test for superior predictive ability"](https://doi.org/10.1198/073500105000000063), *Journal of Business & Economic Statistics* (2005).
- ["Evaluating Interpretable Meta-Labeling for Intraday Futures Trend Following"](https://doi.org/10.2139/ssrn.7356724), SSRN preprint (2026); Grądzki, Wójcik and Lessmann, ["Algorithmic crypto trading using information-driven bars, triple barrier labeling and deep learning"](https://doi.org/10.1186/s40854-025-00866-w), *Journal of Asset Management* (2025).
- Wang and Pang, ["Predictability on the Move: The Cryptocurrency Cross-Section"](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7556359), SSRN preprint (October 2026).
