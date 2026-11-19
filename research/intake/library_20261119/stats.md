# Stats / econometrics / inference book notes (legal free sources only)

Working folders: pdfs in `.../books/stats/pdfs/`, extracted text in `.../books/stats/txt/`, HTML in `.../books/stats/html/`.
Nothing was written in /home/user/T.

## Read (20 items)

### 1. Ramdas & Wang, Hypothesis Testing with E-values (arXiv:2410.23614 v6, 264 pp; FnT 2025)
- Legal: arXiv author PDF (also CMU author drafts).
- Read: TOC; 1.5 betting interpretation; 7.3-7.4 test supermartingales, Ville's inequality; 9.1 compound e-values and e-BH (Def 9.1, Ex 9.3, Prop 9.12).
- Key formulas:
  - Ville: P(exists t: M_t >= 1/alpha) <= alpha for any e-process M (eq 7.4a).
  - Compound e-values: sum_k E_P[E_k] <= K for all P (Def 9.1).
  - e-BH: reject H_k iff e_k >= t_alpha, with t_alpha = inf{t : t R(t) >= K/alpha}; equivalently at rank k the cut is K/(alpha k). FDR control holds under arbitrary dependence.
- Lab use: sequential, anytime-valid stopping for forward paper P&L; e-BH across many funding-carry lanes/tickets instead of BH on p-values.
- Note: 1.5 says p-values reciprocated are not e-values (double dipping).

### 2. Lattimore & Szepesvari, Bandit Algorithms (597 pp)
- Legal: author-hosted PDF (tor-lattimore.com).
- Read: TOC; 6.1 explore-then-commit; 7.1 optimism principle; Thm 7.1 (UCB); 16.1 asymptotic lower bound (Thm 16.2 framing).
- Key:
  - ETC (Thm 6.1): R_n <= m sum_i Delta_i + (n - mk) sum_i Delta_i exp(-m Delta_i^2 / 4).
  - UCB with delta = 1/n^2 (Thm 7.1): R_n <= 3 sum_i Delta_i + sum_{i: Delta_i>0} 16 log(n)/Delta_i.
  - Consistent policies: liminf R_n / log n >= sum_i Delta_i / d_inf (Lai-Robbins type).
- Lab use: a multi-venue/multi-coin allocation problem (which carry to run with limited capital/compute) as a bandit; exploration cost in a capacity-limited book.

### 3. Gelman, Carlin, Stern, Dunson, Vehtari, Rubin, BDA3 (677 pp)
- Legal: authors' site PDF, "electronic edition for non-commercial purposes only" (stated in the PDF footer).
- Read: 6.3 posterior predictive checking (p(y_rep|y) = integral p(y_rep|w)p(w|y)dw; test quantity T(y,w)); 7.2 information criteria and CV (lppd, overestimate of out-of-sample accuracy; LOO-CV cost); 11.4 convergence (discard first half as warm-up; compare between/within chain variance until they match).
- Lab use: posterior predictive checks on the backtest P&L model (does it reproduce max drawdown, sign runs?); LOO/WAIC to compare funding-model variants; R-hat-style checks if the lab fits Bayesian models.

### 4. Shalizi, Advanced Data Analysis from an Elementary Point of View (905 pp draft)
- Legal: author's CMU draft PDF.
- Read: TOC (chs 3, 6, 23 structure); 23.5 bootstrapping time series (body text read).
- Key: simple resampling destroys dependence; block bootstrap with block length k ~ n^(1/3) (Kunsch 1989); circular, block-of-blocks, stationary bootstrap (geometric block length, mean k); sieve bootstrap (model-based compromise).
- Lab use: CI for Sharpe/mean funding P&L from daily autocorrelated series; choose block length by checking how the CI width moves with k.

### 5. MacKay, Information Theory, Inference and Learning Algorithms (640 pp)
- Legal: author-hosted (inference.org.uk). Text says on-screen viewing permitted, printing not permitted.
- Read: 28.1 Occam's razor (body): posterior odds P(H1|D)/P(H2|D) = [P(H1)/P(H2)] x [P(D|H1)/P(D|H2)].
- Key: evidence (marginal likelihood) automatically penalises flexibility (Figure 28.3 intuition).
- Lab use: compare model complexity for a carry signal (threshold/lookback choices) with marginal likelihood or Bayes factor instead of in-sample p-values.

### 6. Grinstead & Snell, Introduction to Probability (518 pp)
- Legal: Dartmouth-hosted PDF (author-posted; I did not verify the licence text inside the file).
- Read: 12.2 gambler's ruin (body); 12.3 arcsine laws (body).
- Key: with p (win), q = 1-p: q_{k+1} - q_k = (q/p)^k (q_1 - q_0) (eq 12.7); time spent in the lead follows the arcsine density f(x) = 1/(pi sqrt(x(1-x))).
- Lab use: how long a strategy's cumulative P&L stays on one side of zero under a null; a sanity check for "streak" arguments on live paper P&L (sign-persistence null).

### 7. Kroese, Botev, Taimre, Vaisman, Data Science and Machine Learning, 1st ed (DSML, 2019; updated PDF 22 Aug 2024)
- Legal: author page (UQ) states the 1st-edition PDF is free for educational or self-study use with acknowledgment. Second edition is paid (CRC), not used.
- Read: 3.3.2 bootstrap method (body); 3.4.4 noisy optimization (body).
- Key: bootstrap percentile and normal CIs (iid assumption); noisy optimisation via stochastic approximation with central differences (eq 3.28) and common random numbers to lower variance of the difference.
- Lab use: when tuning carry thresholds on noisy backtests, use common random numbers across parameter settings; treat the backtest objective as noisy.

### 8. Petropoulos et al., Forecasting: Theory and Practice (arXiv:2012.03854 v4, multi-author review, large)
- Legal: arXiv PDF.
- Read: 2.12.1 benchmarking principles (body); 2.12.2 point, interval and pHDR error measures (body, opening).
- Key: compare to random walk plus ARIMA, ETS, Theta; use several metrics (point, interval, probabilistic); test significance; beware publication bias; VaR backtests for quantile forecasts.
- Lab use: a benchmark protocol for any forecast in the lab (naive random-walk baseline on funding and basis).

### 9. Hyndman & Athanasopoulos, Forecasting: Principles and Practice, 3rd ed (online, OTexts)
- Legal: free online at otexts.com/fpp3 (print sold).
- Read: chapter 5 "The forecaster's toolbox" (fetched full chapter text via curl, sections 5.5 incl. prediction intervals, bootstrap residuals, time-series CV on rolling origin).
- Key: 95% PI ŷ_{T+h|T} +/- 1.96 sigma_h; sigma_h grows with h; multi-step intervals assume uncorrelated residuals; bootstrap residual intervals assume only uncorrelated, constant-variance residuals; time-series CV uses only past observations per test point.
- Lab use: honest forecast intervals for funding rates; rolling-origin evaluation for any predictor.

### 10. Durrett, Probability: Theory and Examples, v5 (Jan 2019, 490 pp)
- Legal: author's PDF (Duke), author-hosted.
- Read: TOC (sections 1-4 headings); 2.5.1 rates of convergence (Thm 2.5.11, body).
- Key: S_n/n^(1/2) (log n)^(1/2+eps) -> 0 a.s. for iid mean-zero finite variance; LIL gives sqrt(2 sigma^2 log log n) scale (remark).
- Lab use: limits of P&L scale and "how big can noise get" statements.
- Partial: did not read the martingale or Poisson chapters.

### 11. Vershynin, High-Dimensional Probability, 2nd ed draft (341 pp)
- Legal: author draft PDF (UC Irvine) at HDP-2.pdf (the first-edition link says "update your link").
- Read: 2.2 Hoeffding (Thm 2.2.1, body); 2.9 Bernstein for subexponentials (Thm 2.9.1 statement and proof start).
- Key: P(sum a_i X_i >= t) <= exp(-t^2 / (2 ||a||^2)) for Rademacher; Bernstein gives a variance-plus-range term.
- Lab use: finite-sample tail bounds for a returns mean; Bernstein is the right tool for fat-ish returns with bounded range.
- Partial: did not read beyond section 2.9 and the high-dimensional chapters.

### 12. Johnson, Ott, Dogucu, Bayes Rules! An Introduction to Applied Bayesian Modeling (online)
- Legal: free online at bayesrulesbook.com (licence text not verified in this run).
- Read: chapter 6 TOC and the diagnostics passage (trace plots, parallel chains, neff ratio, autocorrelation, R-hat); chapter 16 "hierarchical models without predictors" (shrinkage passage).
- Key: R-hat, effective sample size and ACF checks alongside trace plots; partial pooling shrinks group means toward the overall mean.
- Lab use: partial pooling across venues or coins (shrink noisy per-coin funding edge toward the pooled mean) instead of picking the best coin.
- Partial: did not read chapter 6 narrative text in full; read diagnostics summary only.

### 13. Cunningham, Causal Inference: The Remix (online draft, 2nd ed, "work in progress")
- Legal: free online at mixtape.scunning.com (author-hosted).
- Read: chapter 9 "Difference-in-Differences Fundamentals" (eqs 9.9-9.10 and the non-parallel-trends bias text).
- Key: DiD = ATT + (non-parallel trends bias) (eq 9.10); identification needs parallel trends.
- Lab use: an event study on a venue policy change (e.g. fee or funding-cap change) as a natural experiment; check parallel pre-trends first.

### 14. James, Witten, Hastie, Tibshirani, An Introduction to Statistical Learning with Applications in R, 1st ed (7th printing PDF)
- Legal: statlearning.com "Download the PDFs here" link (author/publisher-authorised free PDF of the book). The file I fetched is the 1st-edition printing (no multiple-testing chapter; the 2nd edition is a different file).
- Read: 5.2 The Bootstrap (body, portfolio allocation example).
- Key: alpha = (sigma_Y^2 - sigma_XY) / (sigma_X^2 + sigma_Y^2 - 2 sigma_XY) (eq 5.6); estimate it on past returns and use the bootstrap to get its sampling spread.
- Lab use: the sampling error of any capital-split or sizing weight across two strategies.

### 15. Gelman, Hill, Vehtari, Regression and Other Stories (546 pp)
- Legal: author-hosted PDF (users.aalto.fi/~ave/ROS.pdf, linked from the authors' ROS-Examples page). The PDF says "free to view and download for personal use only; not for re-distribution."
- Read: 4.4-4.5 (body) on statistical significance pitfalls.
- Key: significance is not practical importance; non-significant is not zero; significant vs non-significant is not itself significant (estimates 25 +/- 10 and 10 +/- 10 example, difference 15 +/- 14); forking paths and researcher degrees of freedom.
- Lab use: a checklist for promoting a carry variant: report effect size and CI, count the search space explicitly, and show the difference between variants, not just which one is "significant".

### 16. Ly, Boehm, Grunwald, Ramdas, van Ravenzwaaij, A Tutorial on Safe Anytime-Valid Inference (45 pp)
- Legal: CWI repository PDF (ir.cwi.nl/pub/35995).
- Read: abstract and introduction (pp 1-3) only.
- Key: classical p-value tests become invalid under peeking; e-value based anytime-valid tests and confidence sequences keep type I error under optional stopping and continuation; the 'optional continuation' idea.
- Lab use: explicit stopping rule for a forward paper trial: stop early at a predefined e-value threshold, or continue, without losing error control.
- Partial: did not read the design sections (2-3) or the safestats examples.

### 17. Hernan & Robins, Causal Inference: What If (365 pp)
- Legal: free download from the authors' page (miguelhernan.org, file hernanrobins_WhatIf_19aug26.pdf) which states the book is free.
- Read: 3.3 Positivity (body).
- Key: positivity: Pr[A=a | L=l] > 0 for every level l present in the population of interest; identification needs exchangeability, positivity and consistency; standardised means are undefined when positivity fails.
- Lab use: positivity = a cell with zero support (for example a venue/coin/period with no data on one side) should block an estimate, not be silently extrapolated.
- Partial: did not read the IP-weighting or g-methods chapters.

### 18. Murphy, Probabilistic Machine Learning: An Introduction (book 1, online, 860 pp; April 2025 online version)
- Legal: MIT Press open-access PDF on the author's GitHub release, licence CC-BY-NC-ND (in the PDF).
- Read: 5.2.2 Bayesian model selection (body); 5.2.4 connection between cross-validation and marginal likelihood (body, start).
- Key: p(m|D) proportional to p(D|m)p(m); p(D|m) = integral p(D|theta,m)p(theta|m)dtheta; sequential prediction form; LOO-CV approximates the marginal likelihood under a plug-in approximation.
- Lab use: choose a model's complexity by evidence, with LOO-CV as a cross-check.

### 19. Davidson & MacKinnon, Econometric Theory and Methods (2021 short draft, 195 pp; NOT the full 2004 book)
- Legal: author-hosted PDF (McGill, e662/Ectsbook.pdf).
- Read: TOC; chapter 7 section 7.5 "The Golden Rules of Bootstrapping" (body).
- Key: Golden Rule 1: for a bootstrap test, the bootstrap DGP must satisfy the null (else the test can lose all power); Golden Rule 2: unless the statistic is pivotal, the bootstrap DGP should be the best estimate of the true DGP under the null; bootstrap p-value uses B draws with p-hat* = (1/B) sum I(tau_b* > tau_hat).
- Lab use: when a backtest bootstrap resamples P&L under the null of zero edge, the resampled series must have zero mean and the same dependence.
- Caveat: the full 2004 text was not reachable with a legal copy in this run; the 2021 draft is a different, shorter book.

### 20. Downey, Think Stats, 2nd ed (264 pp; CC licence stated in the text: CC BY-NC-SA 4.0)
- Legal: free online at greenteapress.com.
- Read: TOC; 9.2 HypothesisTest (body, class structure and PValue); 9.9 errors (body); 9.10 power by simulation (body).
- Key: permutation-based p-value; false-positive rate = alpha by construction; power estimated by simulating under an assumed effect.
- Lab use: a simple permutation/power simulator for "how many forward trades to detect a given edge at 80% power".
- Note: an elementary text; mainly for implementation.

## Found but not read legally (titles only, reasons in brackets)
- Hastie, Tibshirani, Friedman, The Elements of Statistical Learning (free author PDF exists; stanford host gave a TLS certificate failure in this session, so not read).
- Hastie, Tibshirani, Wainwright, Statistical Learning with Sparsity (free author PDF exists; same Stanford host problem, not read).
- Bruce Hansen, Econometrics (2022) and Probability and Statistics for Economists (paid; only code/data free).
- Shumway & Stoffer, Time Series Analysis and Its Applications, 4th ed (paid Springer; the older free drafts were not verified).
- Efron & Hastie, Computer Age Statistical Inference (only Cambridge excerpt/frontmatter free).
- Wasserman, All of Statistics (author page has errata; a free full PDF not verified).
- Blitzstein & Hwang, Introduction to Probability (free web copy linked to a Google Drive file of unknown provenance; not used).
- Hampel, Ronchetti, Rousseeuw, Stahel, Robust Statistics (paid); Huber & Ronchetti, Robust Statistics (paid).
- Politis & McElroy, Time Series: A First Course with Bootstrap Starter (paid).
- Think Bayes 2 (download did not return a valid PDF).
- Davidson & MacKinnon full 2004 ETM (only the 2021 draft is free; not the 2004 text).

## Not gone through (scope left)
- OpenIntro Statistics (free; landing page only, PDF link not located).
- Lahiri, Resampling Methods for Dependent Data (not checked for a free copy).
- Online FDR / e-value papers (Xu & Ramdas 2024; arXiv 2601.20386; 2603.24792) are papers, not books; left for the methods queue.
