# Forecast evaluation: probability skill, ranking and executable returns

This playbook is for the separate question raised by the project’s broad goal: does the model know what is likely to happen to a coin, or does a portfolio sort merely earn a relative return? It supplements the [confidence review](CONFIDENCE_REVIEW.md) and [research frontier](RESEARCH_FRONTIER.md). It does not amend an active preregistration or define a live gate.

## Freeze the question first

Write the forecast target so an outcome can be assigned without discretion. Examples are “MEXC local-mid return for the next 24 hours is positive,” “the coin beats a named crypto benchmark over the next 24 hours,” or “the next-period return is in a specified quantile.” These are different targets. Specify venue, clock, horizon, eligible contracts, handling of contract changes and missing outcomes, and whether a horizon overlaps the next forecast. If using “up,” define whether fees or funding are part of the outcome; usually keep price direction and net-trade profitability as separate targets.

Use the exact frozen forecast probability or score saved at the decision time. Compare against a simple baseline estimated only from data available then, such as a past-only base rate. Include every eligible forecast in coverage accounting. A missing prediction is not silently dropped if the production system would have had to act or abstain.

## Keep three evaluations separate

| Question | Useful evidence | What it cannot establish by itself |
|---|---|---|
| Are probabilities trustworthy? | Brier score or log loss versus a frozen base-rate forecast; reliability diagram with uncertainty; coverage | A positive trading return after fees or a useful portfolio ranking |
| Are coin rankings useful? | Rank information coefficient; prespecified score buckets with future relative returns; monotonicity and coverage | That a forecast such as “70% chance up” is calibrated, or that fills are feasible |
| Can the forecast be monetized? | Frozen portfolio rule, MEXC-local executable prices, fees, spread/impact, funding, turnover, drawdown and capacity | Calibrated coin-level probabilities or persistence into an unobserved regime |

For binary outcomes (y_i\in\{0,1\}) and forecasts (p_i\in[0,1]), the Brier score is the mean ((p_i-y_i)^2); the log loss is the mean negative log probability assigned to the observed outcome. Lower is better. These are proper scores: in expectation, a forecaster minimizes them by reporting its actual probability. Accuracy at a 0.5 cutoff discards confidence information. Gneiting and Raftery provide the general scoring-rule framework ([2007 paper](https://doi.org/10.1198/016214506000001437)); Murphy’s Brier decomposition separates reliability, resolution and outcome uncertainty ([1973 paper](https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2)).

For continuous return distributions, use a proper distributional score such as CRPS, and report quantile scores and interval coverage if the model emits quantiles or intervals. A probability of an up move does not communicate the size of a possible loss. For tail-sensitive claims, predefine a tail score or quantile target rather than choosing one after a stress event. Gneiting and Raftery discuss proper scores for both categorical and continuous forecasts.

## Make the baseline comparison explicit

For every frozen coin, horizon and decision time, compare the forecast against a small ladder: zero-return/no-change; an expanding past-only mean return; an expanding past-only up-rate or majority-sign rule; a simple per-coin lagged-return model; a broad-crypto-market-only forecast; a market-plus-coin-history forecast; and the nominated model. Fit every baseline from information available at that decision time. For market-conditioned forecasts, forecast the market leg as well; using the realized future market return as a control leaks the answer. Report raw returns alongside market-adjusted or beta-matched results so shared movement is not presented as coin-specific skill.

For return forecasts, report out-of-sample (R^2) against both zero return and the recursively estimated mean: (1-\sum_t(y_t-\hat y_t)^2/\sum_t(y_t-b_t)^2), with (b_t) fixed by the named benchmark. Use Clark–West's adjusted one-sided comparison for nested models, retaining raw out-of-sample (R^2) so the realized error change remains visible; use a Diebold–Mariano comparison for nonnested forecasts. For a sign claim, compare hit rate with the forecast's and outcome's past-only sign base rates, not an assumed 50/50 market. The Pesaran–Timmermann test evaluates sign association while accounting for those marginal rates. Report up and down performance separately, plus prespecified large-move results.

Do not make mean directional accuracy the profit gate. Arain and Snudden's daily real-time BTC study (October 2021–February 2024) finds that higher average directional accuracy can still conceal breakdowns during large moves; their results apply to one spot-BTC sample, not this project's altcoin perps. Christoffersen and Diebold also show how volatility dynamics affect direction-of-change forecasting. Freeze the forecast-to-position mapping, then compare net results with cash, buy-and-hold, market-only and beta-matched baselines after fees, spread, impact and funding. Statistical skill and economic value answer different questions.

## Calibration and uncertainty

Plot predicted probability against observed frequency with uncertainty intervals. Dimitriadis, Gneiting and Jordan’s CORP reliability diagrams use isotonic regression and uncertainty quantification; they are a more principled calibration diagnostic than an arbitrary expected-calibration-error binning choice ([PNAS 2021](https://doi.org/10.1073/pnas.2016191118)). Still report score distributions and sample coverage: flexible calibration curves are noisy when there are few independent dates, and a good-looking plot is not a pass criterion by itself.

Crypto panels have dependence in both dimensions: many coins share each day’s shock, and each coin recurs across days. Choose inference before results. Multiway clustering by date and coin is one option when there are enough clusters ([Cameron, Gelbach & Miller 2011](https://doi.org/10.1198/jbes.2010.07136)). A date-block bootstrap should resample whole cross-sections together so common market moves are preserved; block length and statistic need to be fixed in advance ([Politis & Romano 1994](https://doi.org/10.1080/01621459.1994.10476870)). Overlapping target windows increase dependence further. A correction cannot manufacture independent regimes from a short sample.

If several signals, horizons, thresholds, universes or scoring rules were tried, define the complete candidate family and retain null as well as winning outcomes. Stepwise family-wise procedures can address a documented finite family ([Romano & Wolf 2005](https://doi.org/10.1111/j.1468-0262.2005.00615.x)); they cannot correct undocumented experiments, chosen-after-looking horizons or repeated monitoring. Tests for forecast breakdown can guide a prespecified alarm ([Giacomini & Rossi 2009](https://doi.org/10.1111/j.1467-937X.2009.00545.x)), but checking often and retuning after a signal of deterioration creates another selection path. Choose estimation-window length using past-only rolling validation and freeze it ([Pesaran & Timmermann 2007](https://doi.org/10.1016/j.jeconom.2006.03.010)).

## Deterministic toy check (not market evidence)

For outcomes `(1, 0, 1, 0)`, forecasts `(0.9, 0.1, 0.9, 0.1)` and `(0.6, 0.4, 0.6, 0.4)` both have 100% direction accuracy at threshold 0.5. Their Brier scores are 0.01 and 0.16; their log losses are approximately 0.105 and 0.511. Thus hit rate alone cannot distinguish confidence quality. This four-row example uses invented outcomes and proves nothing about this project’s forecasts.

## Application to this repo

The repository’s portfolio evidence is not a calibrated per-coin forecast. If a future, separately preregistered lane evaluates that question, keep its primary target and score distinct from R200’s portfolio gate. Report (1) overall and per-date coverage, (2) score versus a past-only benchmark, (3) calibration with uncertainty, (4) rank performance if ranking is claimed, and (5) a separate executable portfolio result. Fix the universe and categories point-in-time; preserve delisted and unavailable symbols in coverage. A model can be calibrated but economically useless, rank correctly but misstate probabilities, or show paper PnL without reliable individual-coin probabilities.

The repository still has to satisfy its own rules: freeze a new specification before measuring, do not reuse a spent holdout, preserve nulls, and leave active frozen lanes unchanged. This note reports only the synthetic arithmetic above; no market data, project forecast scores, backtests or strategy statistics were run.

## References

- Gneiting & Raftery (2007), [Strictly Proper Scoring Rules, Prediction, and Estimation](https://doi.org/10.1198/016214506000001437).
- Murphy (1973), [A New Vector Partition of the Probability Score](https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2).
- Dimitriadis, Gneiting & Jordan (2021), [Stable Reliability Diagrams for Probabilistic Classifiers](https://doi.org/10.1073/pnas.2016191118).
- Cameron, Gelbach & Miller (2011), [Robust Inference With Multiway Clustering](https://doi.org/10.1198/jbes.2010.07136).
- Politis & Romano (1994), [The Stationary Bootstrap](https://doi.org/10.1080/01621459.1994.10476870).
- Romano & Wolf (2005), [Stepwise Multiple Testing as Formalized Data Snooping](https://doi.org/10.1111/j.1468-0262.2005.00615.x).
- Giacomini & Rossi (2009), [Detecting and Predicting Forecast Breakdowns](https://doi.org/10.1111/j.1467-937X.2009.00545.x).
- Pesaran & Timmermann (2007), [Selection of Estimation Window in the Presence of Breaks](https://doi.org/10.1016/j.jeconom.2006.03.010).
- Hyndman & Athanasopoulos, [Forecasting: Principles and Practice](https://otexts.com/fpp3/) (rolling-origin evaluation).
- Pesaran & Timmermann (1992), [A Simple Nonparametric Test of Predictive Performance](https://doi.org/10.1080/07350015.1992.10509922).
- Christoffersen & Diebold (2006), [Financial Asset Returns, Direction-of-Change Forecasting, and Volatility Dynamics](https://doi.org/10.1287/mnsc.1060.0520).
- Clark & West (2007), [Approximately Normal Tests for Equal Predictive Accuracy in Nested Models](https://doi.org/10.1016/j.jeconom.2006.05.023).
- Yae & Tian (2022), [Out-of-Sample Forecasting of Cryptocurrency Returns: A Comprehensive Comparison of Predictors and Algorithms](https://doi.org/10.1016/j.physa.2022.127379).
- Arain & Snudden (2026), [When Are Statistical Forecast Gains Economically Relevant? Evidence From Bitcoin Returns](https://doi.org/10.1002/for.70077).
