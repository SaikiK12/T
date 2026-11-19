# Risk / portfolio construction / sizing: reading notes (2026-11-19)

Scope legend: READ = text read in the stated part; NOT READ = not opened.

1. Palomar, Portfolio Optimization: Theory and Application (CUP 2025). Author-hosted PDF: https://portfoliooptimizationbook.com/book/portfolio-optimization-book.pdf (608 pp).
   READ: TOC; sec 7.3.1 Kelly criterion portfolio (eq 7.13, mean-variance Taylor approx eq 7.15-7.16); sec 10.5 drawdown portfolios (opening only, p.280-281); sec 11.2-11.3 risk contributions via Euler theorem (eq 11.1).
   NOT READ: ch 10.1-10.4 detail, ch 11.4-11.8, ch 14 (robust, resampling), ch 3.6 shrinkage.
   Key: Kelly portfolio = max E log(1+w'r) s.t. 1'w=1, w>=0 (convex); 2nd-order approx E log(1+w'r) ~ w'mu - 1/2 w'Sigma w.
   Risk parity: RC_i = w_i dF/dw_i for positively homogeneous risk F (vol, VaR, CVaR), sum RC_i = F(w).
   Lab use: Kelly-with-constraints template; ERC across books.

2. Busseti, Ryu, Boyd, Risk-Constrained Kelly Gambling, arXiv:1603.06183 (28 pp). https://arxiv.org/abs/1603.06183 (pdf https://arxiv.org/pdf/1603.06183)
   READ: abstract; sec 1-2 (Kelly); sec 4 (drawdown bound, full derivation); sec 5 (RCK problem, eq 7), 5.1 (lambda = log beta / log alpha, eq 8: P(Wmin<alpha) < alpha^lambda), 5.2 (light/heavy risk aversion; light limit: constraint ~ (lambda/2) var(log) <= E log), 5.3 two-outcome case.
   NOT READ: sec 6 (Markowitz link), numerical experiments, appendix proofs (only skimmed).
   Key: convex constraint E[(r'b)^(-lambda)] <= 1 implies drawdown probability < alpha^lambda. Beats fractional Kelly at equal drawdown risk (paper's claim, simulations only).

3. Boyd et al., Multi-Period Trading via Convex Optimization, F&T Optimization 2017, arXiv:1705.00109 (77 pp). https://arxiv.org/abs/1705.00109
   READ: TOC; sec 4.3 forecast-error risk (pp.30-33): worst-case return term rho'|x-w^b| (eq 4.6); covariance uncertainty |Delta_ij| <= kappa sqrt(S_ii S_jj) gives psi = (x-w)'S(x-w) + kappa (sigma'|x-w|)^2 (eq 4.8). Suggests kappa = 0.02-0.05.
   NOT READ: sec 2 (costs, self-financing), sec 5 (multi-period), 6-7 examples.

4. Thorp, The Kelly Criterion in Blackjack, Sports Betting and the Stock Market (1997 paper, author-hosted at sites.oxy.edu/lengyel/M330/thorp/ch3.pdf). Scanned PDF; read visually.
   READ: ch 3 section (a) pp.7-9 of ch3 (fraction bet f, Brownian-motion approximation P(sup ...) formula (3.1); m = p ln(1+f)+q ln(1-f), s^2 = pq[ln((1+f)/(1-f))]^2; example C=2, n=1e4, p=.51, f=.0117 -> P=.9142; f=.02 -> P=.9214). NOT READ: ch 1-2, 4-10, appendices.
   Note: example figures are as printed in that text; the example probability lines are printed as "P(.)" in the scan, read as in the scan.

5. Roncalli, Introduction to Risk Parity and Budgeting (Chapman & Hall 2013). Only the SOLUTIONS book is at MPRA: https://mpra.ub.uni-muenchen.de/47679/1/MPRA_paper_47679.pdf (152 pp). The main text was NOT obtained (author page riskparitybook.html not checked for free download).
   READ (solutions book): sec 2.3 ERC portfolio (RC_i = x_i (Sigma x)_i / sigma(x); ERC = equal RC); sec 3.9 Frazzini-Pedersen model (margin constraint m_j x_j' P_t <= W_j in the Lagrangian; equilibrium with leverage constraints).
   NOT READ: sec 1.x, 2.4 CF-VaR, 2.6-2.9, 3.x others.

6. Asness, Frazzini, Pedersen, Leverage Aversion and Risk Parity, FAJ 68(1) 2012. AQR-hosted PDF: https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/Leverage-Aversion-and-Risk-Parity.pdf (14 pp)
   READ: abstract, intro, data/construction (RP weights = inverse of trailing 3-year monthly vol, rescaled to match benchmark vol; monthly rebalance).
   NOT READ: theoretical model details, robustness tables.
   Key claim: safer assets have higher risk-adjusted returns under leverage aversion; RP levers the risk-balanced portfolio.

7. Moreira & Muir, Volatility Managed Portfolios, NBER WP 22208 (April 2016). https://www.nber.org/system/files/working_papers/w22208/w22208.pdf (57 pp)
   READ: intro, sec 2.1-2.2 (f^sigma_{t+1} = (c / sigma_hat_t^2) f_{t+1}, sigma_hat^2 = previous month realized variance from daily returns; c set so managed vol = buy-and-hold vol).
   Glanced: Table 1 (managed factor alphas), sec 3 utility claims (text says ~65% lifetime utility gain for mean-variance investor trading market only). NOT verified line by line.

8. Rockafellar & Uryasev, Optimization of Conditional Value-at-Risk (1999 preprint). https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf (26 pp)
   READ: abstract, intro, sec 2 definitions (eq 1 Psi(x,alpha); eq 2 VaR alpha_beta(x)=min{alpha: Psi>=beta}; CVaR phi_beta(x) = conditional mean of losses above VaR).
   NOT READ: the minimization formula and LP reformulation in sec 3-4 (described in intro only).

9. Harvey, Hoyle, Korgaonkar, Rattray, Sargaison, Van Hemert, The Impact of Volatility Targeting, JPM 45(1) 2018. Duke author-hosted: https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf (21 pp)
   READ: abstract, intro, parts of equity section (gross/net Sharpe table notes; unscaled equity Sharpe 0.40 in the text excerpt read), bond section pointer.
   NOT READ: most tables, transaction-cost assumptions in full.
   Key claim (abstract): Sharpe ratios higher with vol scaling for risk assets (equities, credit) and for balanced/risk-parity portfolios; scaling reduces the left tail.

10. Ledoit & Wolf, Honey, I Shrunk the Sample Covariance Matrix, UPF WP 2003 (JPM 2004 published version may differ). https://econ-papers.upf.edu/papers/691.pdf (21 pp)
    READ: abstract, intro, sec 3.2 constant-correlation target; sec 3 + App B: kappa_hat = (pi_hat - rho_hat)/gamma_hat; delta_hat = max(0, min(kappa_hat/T, 1)) (eq 5).
    Key: shrink sample covariance toward structured target; claim: lower tracking error, higher realized IR on stock data.

11. Taleb, Statistical Consequences of Fat Tails (3rd ed. compilation), arXiv:2001.10488 (523 pp). https://arxiv.org/abs/2001.10488
    READ: glossary secs 2.2.5 (law of medium numbers / preasymptotics) and 2.2.6 (kappa metric, eq 2.3-2.4: convergence rate of the mean absolute deviation of partial sums, 0 for Gaussian, 1 for Cauchy).
    NOT READ: main technical chapters. Polemical tone; treat as diagnostic, not as settled method.

Downloaded but out of domain / not read: cond-mat/0307332 (Bouchaud et al, market response; not used).
Attempted, not usable: DeMiguel, Garlappi, Uppal (faculty.london.edu URL returned an HTML page, not a PDF; not read). Boyd & Vandenberghe cvxbook (stanford.edu/web.stanford.edu: TLS/proxy failure; not obtained). Thorp chapters 1-2,4-10 exist at same host (not read).

Found but NOT fetched for legal reasons or failure:
- Lopez de Prado HRP (SSRN blocked to curl; a third-party smallake.kr copy exists, not used because provenance unverified).
- Chekhlov-Uryasev-Zabarankin 2005 IJTAF (no free full text found). A 2003 draft at cis.upenn.edu course site exists; not read (provenance uncertain).
- McNeil 1999 EVT lecture notes (not found on ETH host; ETH papers page reachable: people.math.ethz.ch/~embrecht/papers.html; not checked).
- Embrechts, Resnick, Samorodnitsky 1999 EVT (CAS-hosted; not read).
- Grossman-Zhou 1993, Cvitanic-Karatzas 1995 (no free copy located).
- Meucci, Risk and Asset Allocation (no free copy located).
- Schmidli ruin-theory lecture notes (host unreachable from sandbox).
