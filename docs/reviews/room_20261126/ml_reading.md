# ML to select positions in a cross-venue funding carry book: reading notes

Date: 2026-11-25. Role: research reader, room of 2026-11-26. Scope: read only, one file written.

## What was read in full, and what was not

| Source | Status | Link |
|---|---|---|
| Bailey, Borwein, López de Prado, Zhu, "The Probability of Backtest Overfitting" (2015 rev., J. Comp. Finance 20(4), 2017) | Read in full (text extracted from the author-hosted eScholarship PDF, CC BY-NC) | https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf (also https://papers.ssrn.com/abstract=2326253) |
| Bailey and López de Prado, "The Deflated Sharpe Ratio" (JPM 40(5), 2014) | Read the main text and the trial-count sections; appendix A.1 not checked line by line | https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf (SSRN abstract 2460551) |
| López de Prado, "The 10 Reasons Most Machine Learning Funds Fail" (2018) | Read in full (author-distributed copy hosted by GARP) | https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf |
| Hudson & Thames, triple-barrier and meta-labeling explainer | Read in full (web page, not a paper) | https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy/ |
| Hudson & Thames meta-labeling repo (cites the four JFDS papers) | Read the README-level content only | https://github.com/hudson-and-thames/meta-labeling |
| Securities.io, BTC funding-rate forecasting with DAR models (Jan 2024 to Mar 2025) | Read the summary; a practitioner write-up, not peer-reviewed | https://www.securities.io/bitcoin-funding-rates-forecasting-trading-costs/ |

Not obtained, so nothing below is quoted from them:
- Joubert (2022), "Meta-Labeling: Theory and Framework" (JFDS 4(3)). No arXiv or author copy was found. The only content I have is the repo's one-line summary.
- Meyer, Barziy, Joubert (2023), "Meta-Labeling: Calibration and Position Sizing" (JFDS 5(2)). Only its title and abstract summary are on the repo page.
- Joubert et al. (2024), "The Three Types of Backtests" (SSRN 4897573). The SSRN page returned HTTP 403. Only a search summary was read: it covers walk-forward, resampling and Monte Carlo, and has no performance metrics.
- López de Prado, *Advances in Financial Machine Learning* (2018), chapters 3, 4 and 7. No legal free copy was found. The purging and embargo procedure below comes from the 10-reasons paper, which restates it.
- "10 Reasons" on SSRN (3104816): HTTP 403. The GARP copy was used instead.
- Any arXiv paper that applies ML to predict perpetual funding rates. I did not find one (see section 5).

## 1. Labels for a carry trade: fixed horizon vs triple barrier, and what meta-labeling adds

**Fixed horizon is the default in the literature, and the 10-reasons paper calls it a problem.** Its words: "virtually all ML papers label observations using the fixed-time horizon method" (10-reasons, Pitfall 5, https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf). Its three objections, quoted: the same threshold "is applied regardless of the observed volatility"; the label set has "The large majority of labels will be 0"; and "it is simply unrealistic to build a strategy that profits from positions that would have been stopped-out by the fund, exchange (margin call) or investor."

**Triple barrier labels the exit that a real position would meet.** The 10-reasons paper: "If the upper horizontal barrier is touched first, we label the observation as a 1. If the lower horizontal barrier is touched first, we label the observation as a -1. If the vertical barrier is touched first, we have two choices: The sign of the return, or a 0." The Hudson & Thames page gives the same rule in its words: "Should the path of a stock reach the upper barrier before the vertical then a value of 1 is returned" (https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy/).

**Meta-labeling is a second model on top of a primary rule.** 10-reasons: "the role of the secondary ML algorithm is to determine whether a positive from the primary (side decision) model is true or false. It is not its purpose to come up with a betting opportunity." Its sizing role: "ML will not decide the side of your bet, only the size." The repo summary of Joubert (2022) says the layer helps to "size positions, filter out false-positive signals" (https://github.com/hudson-and-thames/meta-labeling).

**Relevance to the carry book.** The side is already fixed by the rule: long the cheaper-to-pay venue, short the richer one. So the ML model should only decide whether to take the entry or how big to size it, which is the meta-labeling case. The 10-reasons paper gives the reason it is safer: "the effects of overfitting are limited when you apply meta-labeling" (same source).

**Caveat from the Hudson & Thames test.** Their results are accuracy and precision on price-based primary rules, not carry. Mean reversion on Bollinger bands, validation: "The accuracy jumps from 20% to 77%." Out of sample: "The precision jumps from 0.17 to 0.20 and the accuracy from 17% to 63%." Trend following, out of sample: "The precision increases from 0.48 to 0.54 and the accuracy from 48% to 55%." The same page says the trend result "doesn't out perform on all the metrics however it does outperform on a risk adjusted basis." Accuracy gains of this size are not evidence for a carry book; only net money is.

## 2. Purged k-fold and embargo: procedure and why overlap leaks

**Why k-fold leaks.** 10-reasons, Pitfall 8: "Consider a serially correlated feature X that is associated with labels Y that are formed on overlapping data: (1) Because of the serial correlation, X_t ≈ X_{t+1}; (2) because labels are derived from overlapping data points, Y_t ≈ Y_{t+1}." The result: a classifier "is more likely to achieve Y_{t+1} = E[Y_{t+1}] even if X is an irrelevant feature. In the presence of irrelevant features, leakage leads to false discoveries."

**Purging, the exact procedure.** Each label Y_j is a function of the bars in [t_{j,0}, t_{j,1}]. Remove from training every label i whose span overlaps a test label's span. The paper gives three overlap conditions: "(1) t_{j,0} ≤ t_{i,0} ≤ t_{j,1}; (2) t_{j,0} ≤ t_{i,1} ≤ t_{j,1}; (3) t_{i,0} ≤ t_{j,0} ≤ t_{j,1} ≤ t_{i,1}." Its words: "eliminate from the training set all observations whose labels overlapped in time with those labels included in the testing set. I call this process purging."

**Embargo, the exact procedure.** Training labels that end before the test start need no removal, because they "contain information that was available at the testing time." Only training labels that start just after the test are dropped: "eliminate from the training set observations that immediately follow an observation in the testing set." The paper sets the width as "A small value h ≈ .01T, where T is the number of bars, often suffices to prevent all leakage." For a carry label that runs until the spread exits, h should be at least the longest label span, not 1% of the sample; the 1% rule is the paper's, and I would not copy it for a 14-day trailing feature with multi-day exits.

**Overlap weights.** Labels that share bars carry less information. The 10-reasons paper defines uniqueness: "The uniqueness of a label i at time t is u_{t,i} = 1_{t,i} / c_t", where c_t counts the labels live at t. Sample weights from the average uniqueness reduce the effective sample size. For this book, count the live entries per day, not per row.

**Walk-forward and its limits.** The paper's view: "History is a filtration; hence, using trailing data guarantees that the testing set is out-of-sample (no leakage), as long as purging has been properly implemented." Its three disadvantages: "a single scenario is tested (the historical path)", "WF is not necessarily representative of future performance", and high variance. Its fix is combinatorial purged CV, which builds many backtest paths from the same groups (10-reasons, Solution 9).

**Practical rule for this lab.** Use purged walk-forward with the embargo set to the maximum label span, and report the path count alongside the one walk-forward path.

## 3. Trials, and which correction to report

**The number of trials must be reported.** DSR paper: "the most important piece of information missing from virtually all backtests published in academic journals and investment offerings is the number of trials attempted. Without this information, it is impossible to assess the relevance of a backtest." Its abstract: "The Deflated Sharpe Ratio (DSR) corrects for two leading sources of performance inflation: Selection bias under multiple testing and non-Normally distributed returns."

**The expected maximum under noise.** From the 10-reasons paper: E[max of I standard normals] ≈ (1 − γ) Z^{-1}[1 − 1/I] + γ Z^{-1}[1 − 1/(I e)], with γ ≈ 0.5772 (Euler's constant), and it grows with I. Its warning: "Even though the true Sharpe ratio is zero, we expect to find one strategy with a Sharpe ratio of E[max]". The DSR paper states the same with an explicit N: "its expected maximum is greater than zero, even if the true SR is zero."

**DSR inputs.** The DSR "deflates SR by taking into consideration five additional variables": non-normality (skew and kurtosis), sample length T, the variance of the Sharpe ratios tried, and N, the number of independent trials. N is the hard part for this lab. Count every configuration tried, including dropped thresholds, venue sets, and features, not only the ones that reached the report.

**PBO, from Bailey et al.** The rule: "The probability that the model configuration selected as optimal IS will underperform the median of the N model configurations OOS." Its procedure is CSCV: "we partition M across rows, into an even number S of disjoint submatrices", then "we form all combinations C_S of M_s, taken in groups of size S/2." For S = 16 this is "12, 780 combinations." The paper's decision rule: "a customary approach would be to reject models for which PBO is estimated to be greater than 0.05." It also needs N large: "N >> 10 is required" for granularity. Its demo: a seasonal strategy with IS SR between 1 and 2.2 had "the PBO is as high as 55%." That number is the paper's own example, not a carry result.

**Warning in the same paper.** "Any counter-overfitting technique used to select an optimal strategy will result in overfitting." So PBO and DSR are checks on a chosen book, not tools to pick one.

**What to report.** The count of configurations, the DSR of the chosen book with that N, PBO by CSCV over the same configurations, and the cost multiples (1x, 2x, 3x). The 10-reasons paper says a WF backtest needs "to control for the number of trials (I)... Without this information, it is not possible to determine the Family-Wise Error Rate (FWER), False Discovery Rate (FDR), Probability of Backtest Overfitting (PBO) or similar."

## 4. Features that predicted funding persistence, with reported skill

**Direct evidence is thin.** The only quantitative result I read on funding-rate prediction is the Securities.io study. Its models are double autoregressive (DAR), not ML. Setup: data "from January 11, 2024, through March 17, 2025, with observations every eight hours"; out-of-sample "The final 384 observations, covering November 10, 2024, onward." Its benchmark is "assume the next funding rate equals the latest observed rate." Features: none listed in the text; the models use "persistence in funding rates and changes in their volatility."

Reported directional accuracy, DAR vs persistence benchmark on the 384-observation test (the article gives ranges by estimation method, and I could not read the benchmark's figure):
- Binance: "48.70% to 60.16%".
- Bybit: "49.48% to 62.5%".

Backtest with modelled fees, annualized: "6.258% vs. 4.258%" (DAR vs benchmark), with 8 vs 15 trades. Without fees: "10.122% vs. 16.652%" with 59 vs 78 trades. So the DAR model beat the naive benchmark only after fees, and only with far fewer trades. The article's own line: "The best model for predicting a number may differ from the best model for deciding whether to commit capital."

**Interpretation for us.** The useful features are the lagged funding level and its recent change (the persistence the DAR captures), and the volatility of funding. A directional accuracy near 50% on persistence means that the signal is mostly the carry level, which the frozen rule already uses. The ML gain has to come from something beyond these.

**Not evidence.** arXiv 2610.01115 (Certified Alpha Capacity, https://arxiv.org/abs/2610.01115) is theory: its abstract talks of "Statistical validation takes time, and alpha can decay before the evidence justifies deployment." It has no funding-rate data in the abstract. The arXiv 1912.03270 paper (BitMEX, GARCH) is statistical, not ML, and I did not read it in full.

## 5. Search log, for the next reader

- arXiv full-text search for funding-rate ML returned no paper with an out-of-sample ML result on perpetual funding rates. Two queries were run, plus a search for the 2024-2025 window.
- The next search: "funding rate forecasting XGBoost LightGBM" and "perpetual funding persistence logistic" on arXiv, and the SSRN listing for Joubert's 2022 paper with an author copy.
- Open question for the room: whether any funding-rate ML paper reports N (trials). I did not find one that does.

## 6. Design recommendation for this lab

1. **Primary rule, frozen.** Keep the trailing 14-day spread rule (enter above 5%/yr, exit below 2.5%/yr). The ML layer only filters or sizes its entries, so the frozen rule is the baseline in every test.
2. **Label, triple-barrier style.** For each rule-entry day, label 1 if net carry (funding received minus paid, minus fees, minus the basis move) over the position's life is positive at 2x costs; label 0 otherwise. Barriers: the rule's own exit (spread below 2.5%) as the horizontal, a basis or margin stop as the second, and a fixed maximum hold as the vertical.
3. **Overlap.** Entries overlap, so weight each label by its average uniqueness and count live entries per day.
4. **Features, five at most.** Current spread, 14-day spread change, funding-rate volatility over 14 days, the basis between the two venues, and a venue-liquidity or open-interest proxy. No feature the rule already uses without a test that it adds.
5. **Model, simple.** Logistic regression with L2 penalty first. Gradient boosting only if the logistic model beats the frozen rule, with depth 2 and fewer than 50 trees.
6. **Validation.** Purged walk-forward. Embargo equals the maximum label span, not 1% of the sample. Training window expanding, refit weekly, scoring only the next week.
7. **Comparison.** Paired, on the same entry days: the meta-filtered book against the frozen rule, net of costs at 1x, 2x and 3x, with a cash benchmark.
8. **Trial count.** Log every configuration (thresholds, features, model, embargo, venue set) in a file before the run. N is the length of that file.
9. **Correction.** Report DSR of the chosen book's out-of-sample net return with that N, and PBO by CSCV over the same configurations. A PBO above 0.05 blocks the claim, following the paper's own rule.
10. **Forecast before the freeze.** Write P(PASS) in `registry/forecasts.csv`. The base rate for ML-selected books that survive confirmation is low in this lab (CLAUDE.md, outside carry: 0% in several families), so the prior should be below 0.2 unless a named piece of evidence lifts it.
11. **The one number that decides.** The DSR of the meta-filtered book's out-of-sample net carry minus the frozen rule's, paired by entry day, at 2x costs, with N as in step 8. Pass if it is at or above 0.95 and PBO is below 0.05. Otherwise the ML layer is not used, and the frozen rule stays.

## Weakest links

- Two of the core meta-labeling papers (Joubert 2022, Meyer et al. 2023) were not read in full. The design above relies on the 10-reasons paper and the Hudson & Thames summary, not on their equations.
- The only funding-rate result read is a practitioner write-up with a DAR model; its fee and trade-count figures come from the article's own backtest, which I did not re-run.
- The DSR figures are from the paper's text, not a recomputation. The expected-maximum formula is quoted from the 10-reasons restatement.
- Nothing here measures how the carry book's decay or venue capacity interacts with a filter; that needs the lab's own data.
