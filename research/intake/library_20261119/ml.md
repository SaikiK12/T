# ML and quant strategy research: reading notes (readers' digest, domain 5)

Downloads are in `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/books/ml/pdfs/`. Text extracts sit beside them as `.txt`.
Scope column = what was actually read. "Skimmed" means headings and selected passages only.

## Sources read

| # | Source | Legal URL used | Scope actually read | Key idea |
|---|---|---|---|---|
| 1 | Gu, Kelly, Xiu, "Empirical Asset Pricing via ML" (RFS 2020; NBER w25398) | https://dachxiu.chicagobooth.edu/download/ML.pdf ; https://www.nber.org/system/files/working_papers/w25398/w25398.pdf | Abstract, intro results, sample and validation design (sec 1.1), predictor ranking text, Sharpe results | Trees and NNs beat linear models through nonlinear predictor interactions; price trend, liquidity and volatility dominate. Strong for equities 1957-2016 |
| 2 | Kelly & Xiu, "Financial Machine Learning" (NBER w31502, 2023) | https://www.nber.org/system/files/working_papers/w31502/w31502.pdf | Abstract, sec 2.2 (bigger is better), sec 3.2 (experimental design), sec 5.6 (trading costs and RL) | Complexity is a virtue under shrinkage; embargo between train and validation for serial correlation |
| 3 | Chen, Pelger, Zhu, "Deep Learning in Asset Pricing" (arXiv 1904.00745) | https://arxiv.org/pdf/1904.00745 | Abstract, sample (1967-2016), train/validation/test split, tuning by validation Sharpe | No-arbitrage GAN-style SDF estimator, OOS Sharpe 2.6 vs 1.7 (paper's own numbers, gross) |
| 4 | Freyberger, Neuhierl, Weber, "Dissecting Characteristics Nonparametrically" (NBER w23227) | https://www.nber.org/system/files/working_papers/w23227/w23227.pdf | Abstract, main findings lines | Adaptive group LASSO finds the characteristics with independent information; many known predictors are redundant |
| 5 | Feng, Giglio, Xiu, "Taming the Factor Zoo" (NBER w25481) | https://www.nber.org/system/files/working_papers/w25481/w25481.pdf | Abstract, intro | Double-selection LASSO tests whether a new factor adds beyond a big set; plain LASSO selection is unstable |
| 6 | Hou, Xue, Zhang, "Replicating Anomalies" (NBER w23394) | https://www.nber.org/system/files/working_papers/w23394/w23394.pdf | Abstract, sec 1-2 replication design, liquidity-category result | With NYSE breakpoints and VW returns, 64% of 447 anomalies are insignificant; 93% of liquidity variables fail |
| 7 | Harvey & Liu, "Evaluating Trading Strategies" (JPM 2014) | https://people.duke.edu/~charvey/Research/Published_Papers/P116_Evaluating_trading_strategies.pdf | Full paper (11 pp): multiple-testing sections (Bonferroni, Holm, BHY), Sharpe haircut section | Adjust Sharpe ratios for the number of tried strategies; Holm/BHY beat Bonferroni |
| 8 | Arnott, Harvey, Markowitz, "A Backtesting Protocol in the Era of ML" (JFDS 2019) | https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf | Seven-point protocol headings and checklists (text is font-encoded; decoded by hand) | Economic hypothesis before testing, count every trial, treat "out of sample" as not truly out of sample |
| 9 | Bailey, Borwein, López de Prado, Zhu, "Probability of Backtest Overfitting" | https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf | Abstract, framework, CSCV procedure (sec 2.2), features and limitations pointers | CSCV: split into S blocks, all train/test combinations; S=16 gives 12,780 splits; PBO = share where the IS-best is below median OOS |
| 10 | Bailey & López de Prado, "The Deflated Sharpe Ratio" (JPM 2014) | https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf | Intro and DSR construction (skew, kurtosis, length, N trials) | DSR = PSR with a threshold equal to the expected maximum Sharpe over N independent trials |
| 11 | Moskowitz, Ooi, Pedersen, "Time Series Momentum" (JFE 2012) | https://pages.stern.nyu.edu/~lpederse/papers/TimeSeriesMomentum.pdf | Abstract, sec 2.4 ex-ante vol estimate, position sizing (40% vol target) | Sign of 12-month excess return, scaled by ex-ante vol, across 58 futures; diversified Sharpe > 1 (post-1985) |
| 12 | Lim, Zohren, Roberts, "Enhancing TSMOM with Deep Neural Networks" (arXiv 1904.04912) | https://arxiv.org/pdf/1904.04912 | Abstract, method, out-of-sample protocol, transaction cost section | Sharpe-loss-trained LSTM inside a vol-scaled TSMOM; 88 futures 1995-2015; recalibrated every 5 years; turnover regularizer |
| 13 | Krauss, Do, Huck, "DNN, GBT, RF: Statistical arbitrage on the S&P 500" (FAU DP 03/2016; EJOR 2017 is paywalled) | https://www.iwf.rw.fau.de/files/2016/03/03-2016.pdf | Abstract, main results and cost discussion | Daily ranking by predicted outperformance; ensemble 0.45%/day gross, 0.25%/day after costs; returns decline after 2001 |
| 14 | Gort et al., "DRL for crypto trading: practical approach to address backtest overfitting" (arXiv 2209.05559) | https://arxiv.org/pdf/2209.05559 | Abstract, walk-forward and k-fold critique, hypothesis test (eq. 7), fee assumption (0.3%) | Frames overfitting as a hypothesis test on agents; test window is only about 7 weeks (05/01-06/27/2022) |
| 15 | Hambly, Xu, Yang, "Recent Advances in RL in Finance" (arXiv 2112.04553) | https://arxiv.org/pdf/2112.04553 | Abstract, intro, table of contents, sec 4.2-4.3 excerpts (execution, portfolio) | RL survey; Sharpe is the preferred reward over total profit; several works cite transfer learning to limit overfitting |
| 16 | Sezer, Gudelek, Ozbayoglu, "Financial TS forecasting with DL: systematic review 2005-2019" (arXiv 1911.13288) | https://arxiv.org/pdf/1911.13288 | Conclusions and publication-count summaries only | Counts show about 3 crypto papers before 2020; reported metrics are not comparable across studies |
| 17 | Fang et al., "Cryptocurrency Trading: A Comprehensive Survey" (arXiv 2003.11352) | https://arxiv.org/pdf/2003.11352 | Table of contents, sec 7.2 (ML) opening, scattered reported accuracies | Reported crypto ML accuracies (e.g., SVM 62.3%) are single-study, unreplicated |
| 18 | Sutton & Barto, RL: An Introduction (2nd ed., 2020) | http://incompleteideas.net/book/RLbook2020.pdf | Sec 1.4 (limits), sec 11.3 (deadly triad), sec 13 intro (policy approximation) | Off-policy learning + bootstrapping + function approximation can diverge; policy gradient is a more stable choice for trading agents |
| 19 | Goodfellow, Bengio, Courville, Deep Learning, ch. 5 (ML basics) | https://www.deeplearningbook.org/contents/ml.html | Sec 5.2.1 (no free lunch), 5.3 (hyperparameters and validation sets), 5.4 (estimators, bias and variance) | Validation set built from training data only; test set never used for choices |
| 20 | Hastie, Tibshirani, Friedman, ESL (2nd ed.) | https://hastie.su.domains/ElemStatLearn/ (PDF via the author's linked Drive copy) | Sec 7.10.2 "The wrong and right way to do cross-validation" | Screening predictors on the full sample before CV inflates CV accuracy from 50% to about 97% (ESL example: 50 samples, 5000 noise predictors, CV error 3%) |
| 21 | James, Witten, Hastie, Tibshirani, ISLR (1st ed., 7th printing) | https://www.statlearning.com/s/ISLR-Seventh-Printing.pdf | Sec 5.1.1-5.1.4 (validation set, LOOCV, k-fold, bias-variance of CV) | Basic CV mechanics; k=5 or 10 trades bias for variance |
| 22 | Murphy, Probabilistic ML: An Introduction (book 1) | https://github.com/probml/pml-book/releases/latest/download/book1.pdf (CC BY-NC-ND) | Sec 4.5.4-4.5.5 (CV, one-standard-error rule), Bayesian model selection passage, Figure 3.2 (spurious time-series correlation) | The one-standard-error rule picks the simplest model within noise of the best CV score |
| 23 | Shalev-Shwartz & Ben-David, Understanding ML (2014) | https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/understanding-machine-learning-theory-algorithms.pdf | Sec 11.2 (hold-out, validation, k-fold, train/val/test); exercise on k-fold failure | Hold-out bound depends only on validation size; k-fold can fail (exercise 11.1, constant predictor) |
| 24 | Jansen, Machine Learning for Trading, 3rd ed. (code repo) | https://raw.githubusercontent.com/stefan-jansen/machine-learning-for-trading/main/README.md | README only (chapter map, DSR, Reality Check, walk-forward discipline) | Useful pointers; notebooks not opened |

## Downloaded but not read (do not count)
- Bishop, PRML (Microsoft Research PDF) in `pdfs/bishop_prml.pdf`.
- Harvey 2016 "Practical applications of backtesting" (Duke) in `pdfs/harvey_2016_practical.pdf`.

## Not legally readable or not checked
- Harvey & Liu, "Backtesting" (JPM 2015): SSRN returned 403 to this environment; no author copy found in search.
- Avellaneda & Lee, "Statistical Arbitrage in the US Equities Market": only student-hosted copies found, hosting status unclear, not read.
- Krauss, Do, Huck: EJOR version paywalled; working-paper version read (table above).
- Jegadeesh & Titman (1993), Lopez de Prado (book), Dixon et al. (book), Chan, Jansen book: not checked or not free.
- An arXiv result labelled 2411.06380 was a control-theory paper unrelated to finance; discarded.

## Evidence notes
- GKX and Freyberger et al. report economic gains; the sample is equities, 1957-2016 or later. I found no net-of-cost headline in GKX main text (inferred from absence of cost tables).
- DMN (Lim et al.): main numbers are before costs; they report the strategy profitable up to about 2-3 bps, not at 10 bps.
- Gort et al.: 7-week OOS test only; weak.
- Krauss et al.: after costs the ensemble is 0.25%/day; returns decay after 2001 (their claim).
- Fang et al.: most reported crypto ML accuracies are single-paper, not replicated.
