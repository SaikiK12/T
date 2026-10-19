# Selection and trial-accounting audit

Reviewed 2026-10-19 from the repository at R226/R227. Static review only: no market outcomes were recalculated, no data were downloaded, and frozen lanes were not edited.

## The registry total is not an effective trial count

`registry.program_trials()` is a useful raw bookkeeping sum, but its rows do not all count the same thing. The 9.47 million total is neither 9.47 million independent experiments nor a complete count of every researcher choice. It should not be presented as a calibrated effective sample size or used alone as the exact denominator for a backtest-overfitting correction.

- R192's 8,320,806 figure describes cells that survived filters, while its preregistration's FDR screen uses one deterministic shifted-return placebo per context. It is not a full list of attempted feature-context-horizon tests or a precise candidate-level p-value.
- R195's 643,736 figure is likewise a filtered multi-timeframe cell count.
- R184's `battery_v1` search count was a plan, not a completed result. Its review records inconsistent/stale counts and a holdout-boundary bug; that lane is on hold.
- Later books inherit and recombine prior atlas winners. Those are additional researcher choices, but they are not independent discoveries simply because they receive a new round ID.

The selection path matters: R185's atlas informed R192/R195 and later derived books; R198's registered primary missed its holdout rule, while the better top-versus-crowd result was secondary and selected after earlier results. The historical holdout is spent. New archive variants may be useful for engineering or hypothesis generation, but they cannot provide fresh program-level confirmation.

The Deflated Sharpe Ratio's correlation-based implied-trial calculation is a diagnostic, not a fix for this record. With millions of candidate cells and only a few thousand dates, an average-correlation estimate is unstable and depends on which candidates and return histories are included. If reported, show the raw recorded count and sensitivity assumptions separately; do not call one estimated `N_eff` ground truth.

## How to test a declared family

For a future finite family with benchmark $b_t$ and candidate returns $r_{t,j}$, define paired differentials $d_{t,j}=r_{t,j}-b_t$ before looking at results. The family claim is that at least one candidate has positive expected incremental return. Use Hansen's SPA as the primary family test, White's Reality Check as a conservative sensitivity, and Romano-Wolf stepdown only for candidate-specific claims.

Resample contiguous time blocks jointly across every candidate and benchmark, retaining the full cross-section within each block. Center under the null, studentize using the frozen rule, and compare the observed maximum statistic with the bootstrap distribution of the maximum over all candidates. Freeze the block scheme and length, number of replicates, random seed, family membership, benchmark, candidate-generation rule, and cost assumptions in advance. Candidate matrices must retain failed, null, skipped, and invalid candidates; recording only survivors recreates selection bias.

These historical-family tests describe a completed search. They do not substitute for fresh prospective confirmation. For a forward lane, prefer one primary candidate and one final decision; any additional candidate or interim look belongs in the declared testing family.

## R221 inference limit

R221's Bonferroni correction addresses its three books only if each book/look statistic has a valid null distribution. Its power table assumes independent daily returns, while its 72-hour positions overlap and its test uses Newey-West statistics. The group-sequential boundaries therefore have not been shown to control error at their nominal rate under the observed dependence. Do not revise R221 after observing forward outcomes. In a replacement design, calibrate the maximum over books and looks under a predeclared dependent-data simulation or joint block bootstrap, and validate date uniqueness and continuity before every look.

### Synthetic boundary check

I ran a reproducible, outcome-free null simulation in [`research/r221_sequential_null.py`](../research/r221_sequential_null.py). It reproduces `lab.stats.newey_west_t` (checked against its scalar implementation), uses R221's exact 90/182/365-day boundaries, and generates 100,000 Gaussian paths per case with seed `917221`. The table reports a single-book rate before the separate `total_2x > 0` requirement; it is therefore a boundary-crossing diagnostic, not R221's realized family-wise error or its full pass probability.

| Null process and statistic | Stop at day 90 | Raw day-365 boundary tail | Any efficacy-boundary crossing by day 365, applying day-90 stop |
|---|---:|---:|---:|
| Independent, known variance (normal reference) | 2.31% | 0.831% | 0.839% |
| Independent, estimated variance (NW lag 0) | 2.46% | 0.888% | 0.896% |
| Independent, R221 NW lag 10 | 4.24% | 1.121% | 1.171% |
| AR(1), rho 0.1, NW lag 10 | 4.40% | 1.204% | 1.267% |
| AR(1), rho 0.2, NW lag 10 | 4.58% | 1.199% | 1.259% |
| AR(1), rho 0.3, NW lag 10 | 4.75% | 1.357% | 1.423% |
| Three-day rolling-average shocks (MA(2)), NW lag 10 | 5.07% | 1.421% | 1.518% |

R221 allocates 0.833% to each book. The known-variance reference is close to that allocation; using its finite-sample NW lag-10 statistic instead produces a 1.171% crossing rate even for independent returns, and 1.518% under the stylized three-day-overlap process. Monte Carlo standard errors for these two estimates are 0.034 and 0.039 percentage points. This illustrates finite-sample studentization and dependence sensitivity; it does not establish that the MEXC returns follow any of these distributions. The additional 2x-net hurdle can only remove crossings under the assumed monotone cost tiers, but its reduction was not modeled. The actual R221 error rate therefore remains unknown.

For a future replacement decision, set cutoffs from a frozen null calibration that resamples the three books jointly in contiguous date blocks, preserves their cross-book dependence, applies the same HAC statistic and futility rule, and includes the 2x-net hurdle. Validate the exact daily calendar before any look. Keep R221's frozen thresholds and eventual verdict intact.

## Minimum ledger for future searches

Append an immutable row for every generated candidate, not just each promoted round. At minimum record:

- stable family, parent-round, and candidate IDs; complete formula/configuration; generation and selection timestamps;
- every attempted, failed, skipped, filtered, and retained candidate, with the filter stage and reason;
- data source, vintage, venue, target, universe, dates, coverage, cost model, benchmark, metric, seeds, code/spec/data hashes;
- primary versus diagnostic status, dates/results previously viewed, and whether each sample was used for exploration, validation, or confirmation;
- full candidate outcome-vector hash and the follow-up rationale connecting a result to a new hypothesis.

Historical gaps should be marked unknown or incomplete, not reconstructed as a precise denominator from surviving registry rows. Keep the raw computational count separate from researcher degrees of freedom and from the dependence-aware test performed on a declared family.

## Sources

- White (2000), [A Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152).
- Hansen (2005), [A Test for Superior Predictive Ability](https://doi.org/10.1198/073500105000000063).
- Romano and Wolf (2005), [Stepwise Multiple Testing as Formalized Data Snooping](https://doi.org/10.1111/j.1468-0262.2005.00615.x).
- Bailey et al., [The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253).
- Bailey and López de Prado (2014), [The Deflated Sharpe Ratio](https://doi.org/10.3905/jpm.2014.40.5.094).
- Harvey, Liu and Zhu (2016), [. . . and the Cross-Section of Expected Returns](https://doi.org/10.1093/rfs/hhv059).

These methods require a well-defined candidate family. None can correct decisions and variants that were never recorded.
