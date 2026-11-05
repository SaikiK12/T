# Confidence-scaled sizing: what the evidence supports (2026-10-19)

Written by a research subagent and filed by the lab. Sources were read at abstract or summary level unless noted.
Nothing here was run.

**Bottom line:**
- No peer-reviewed out-of-sample study shows that scaling exposure by a model's own confidence adds value.
- Shrunk Kelly is theory and is supported.
- Volatility scaling and drawdown scaling mostly cut tail risk; they rarely raise Sharpe.
- Meta-labeling has vendor-grade evidence only.

So every "confidence multiplier" rule must beat a volatility-target control and a constant multiplier at the same
average exposure.

| # | Idea | Sources (grade) | Failure mode | Past-only rule for a book's daily net r |
|---|---|---|---|---|
| 1 | Kelly shrunk for estimation error | Baker & McHale, *Decision Analysis* 10(3) (2013), doi:10.1287/deca.2013.0271; Chopra & Ziemba, *JPM* 19(2) (1993); MacLean, Thorp & Ziemba, *Quant. Finance* 10(7) (2010) (B) | A 90-day t is near 1, so plug-in Kelly levers noise | m = clip(0.5 x (mu/sigma^2) x max(0, 1 - 1/t^2), 0, 1.5), using a 180-day trailing mean and variance through t-1 |
| 2 | Volatility targeting (control) | Moreira & Muir, *JF* 72(4) (2017); Cederburg et al., *JFE* 138 (2020): fails out of sample in 103 strategies; Harvey et al., *JPM* 45(1) (2018): cuts tails; Barroso & Detzel, *JFE* 140 (2021): costs remove the gain (B) | The window is a hidden trial | m = clip(sigma* / sigma_hat, 0, 1.5), with sigma_hat an EWMA (30-day half-life) through t-1 and sigma* from a burn-in year |
| 3 | Meta-labeling | López de Prado, *AFML* (2018) (C); one vendor test (D) | Accuracy gains reflect class balance; leakage without purging | m = clip(2p - 1, 0, 1), p from a monthly-refit logistic model on lagged features |
| 4 | Conviction (score) weights vs equal weights | Grinold & Kahn (C); DeMiguel, Garlappi & Uppal, *RFS* 22 (2009): 1/N hard to beat (B) | Concentrates in extreme, illiquid coins; turnover | w = clip(z, -2, 2) normalised, vs equal-weight extremes at the same gross |
| 5 | Signal agreement | Timmermann (2006) (C); Smith & Wallis, *OBES* 71 (2009); Rapach, Strauss & Zhou, *RFS* 23 (2010) (B) | Signals sharing inputs agree by construction | m = clip(A / median_365(A), 0.5, 1.5), A = share of components agreeing |
| 6 | Own-performance scaling | Moskowitz, Ooi & Pedersen, *JFE* 104 (2012); Ehsani & Linnainmaa, *JF* 77 (2022) (B); Grossman & Zhou (1993, theory) | Buys after noise gains, sells after noise losses | m = 1.5 if the trailing 60-day sum > 0, else 0.5 |
| 7 | Regime cut | Daniel & Moskowitz, *JFE* 122 (2016); Barroso & Santa-Clara, *JFE* 116 (2015); Stivers & Sun, *JFQA* 45 (2010) (B) | Few crash episodes, so low power | m = 0.5 if the 30-day cross-sectional dispersion is in its top tercile and the alt index's 90-day return < 0, else 1 |

## Ranked to pre-register
1. Shrunk half-Kelly.
2. The volatility target, which is the control every other rule must beat.
3. Own-performance scaling.
4. The dispersion regime cut.
5. Score weighting.

Not recommended yet: meta-labeling and agreement.

## Protocol
- Freeze all rules and parameters before any statistic.
- Compare each rule with the volatility-target control and with a constant multiplier at matched average |m|.
- Charge cost on |dm| x gross exposure on top of the book's own costs, and report 1x/2x/3x.
- Take burn-in statistics only from data before the test window.

The subagent advised against the lab's earlier example `m = clip(trailing 90-day t / 2, 0.5, 2)`: a 90-day t is
usually below 1, so the rule would sit at its floor and lever only noise streaks.

## Addendum 2026-11-05: untested forms and one per-candle formula

Written by Claude after the owner asked for the multiple to be set on every candle. Nothing below is a result on a
book; the two numeric checks are a simulation and a descriptive BTC risk measure.

**What the lab has tested (daily, on book nets):**
- volatility target: R217, and R225 forward;
- a relative Kelly heuristic (R217 R2; not the clean form, see `CONFIDENCE_AND_SIZING_AUDIT.md`);
- own-performance and agreement scaling: R217;
- dispersion regime cut: R260;
- convex grid and equal risk: R228, R253;
- confidence-sized carry: R281;
- static leverage and liquidation: R280;
- volatility gating of carry: R382.

**Not tested yet:**
1. Clean shrunk Kelly with the factor below, on candles rather than days.
2. Gârleanu-Pedersen partial trading toward an aim that discounts fast-decaying signals.
3. A no-trade band for proportional (fee and half-spread) costs.
4. The Grossman-Zhou drawdown cushion.
5. A per-candle leverage cap from the conditional liquidation tail.
6. A HAR forecast with funding inputs (M455).
7. Risk-constrained Kelly (Busseti, Ryu and Boyd 2016).
8. Meta-labeling, which stays not recommended.

**Shrinkage factor (derived here).**
- **Setup:** let the true per-candle mean be mu, the variance s^2, and the estimate mu_hat ~ N(mu, s^2/n), so
  t = mu sqrt(n)/s.
- **Expected growth:** with f = c mu_hat/s^2, the expected out-of-sample log growth is
  c mu^2/s^2 - c^2 (mu^2 + s^2/n)/(2 s^2).
- **Optimum:** this is maximised at c* = t^2/(t^2 + 1).
- **Full Kelly (c = 1):** it grows at (t^2 - 1)/(2n), which is negative whenever t < 1.
- **Estimator:** E[t_hat^2] = t^2 + 1, so a plug-in estimator of c* is c = max(0, 1 - 1/t_hat^2), the positive-part
  James-Stein form. Use the deflated, out-of-sample t of the model that produces mu_hat.
- **Check:** simulated exact log growth (4,000 estimates x 2,000 days) gives c* = 0.20, 0.50, 0.75 and 0.85 at
  t = 0.5, 1, 2 and 3. Theory gives 0.20, 0.50, 0.80 and 0.90; the grid step is 0.05. At t = 1, full Kelly
  loses 0.8 bp a day while c* earns 9.9 bp. This explains why R217's Kelly-type scaling hurt.

**Gârleanu-Pedersen (JF 2013, Propositions 2 to 4, read from the NBER w15205 text).**
- **Trade rule:** x_t = x_{t-1} + (a/lambda)(aim_t - x_{t-1}), with
  a = [-(gamma(1-rho) + lambda rho) + sqrt((gamma(1-rho) + lambda rho)^2 + 4 gamma lambda (1-rho)^2)] / (2(1-rho)).
- **Aim:** aim_t = (gamma Sigma)^-1 B (f_t^k / (1 + phi_k a/gamma))_k, where phi_k is signal k's per-period decay.
- **Cost model:** it assumes quadratic (impact) costs, Lambda = lambda Sigma. Proportional fees instead give a no-trade
  band whose width scales with the cube root of the fee. A candle-level rule needs both.

**Grossman-Zhou (Math. Finance 1993).** To lose at most 1 - alpha of the running peak M_t, hold the risky
position in proportion to the cushion W_t - alpha M_t. Under log utility, the proportion is the Kelly fraction.

**Per-candle liquidation cap (descriptive, BTCUSDT 1h, 2025-11 to 2026-10, short leg, 24 h hold).**
- **Tail size:** the 24 h max adverse move over the past-only EWMA sigma x sqrt(24) has q99 = 3.55 and q99.9 = 7.89.
- **Cap:** with maintenance margin 0.5%, L_t = 1/(mm + k sigma_hat_t sqrt(24)) has a median of 5.6 (p5 3.9, p95 7.7).
- **Static cap:** an unconditional q99.9 move of 11.2% gives L = 8.6.
- **Reading:** the conditional cap is not looser than the static one. Jumps out of calm hours make the standardised tail
  heavy, so a cap scaled by volatility must keep a tail term for calm hours.

**Combined rule proposed for one pre-registered lane (gate 0 on held carry data, M476).**
- **Position:** x_t = clip(x_{t-1} + (a/lambda)(aim_t - x_{t-1}), 0, L_t), and it moves only when |aim_t - x_{t-1}|
  exceeds the band.
- **Aim:** aim_t = max(0, 1 - 1/t_hat^2) x mu_hat_t / (sigma_hat_t^2 (1 + phi a/gamma)) x (1 - alpha M_t/W_t).
- **Inputs:** mu_hat_t and t_hat use past candles only. sigma_hat_t comes from the variance forecast. The cap L_t is
  above.
- **Controls:** it must beat a constant multiplier at matched mean exposure and the volatility-target control.
- **Costs:** |dx| is charged at the measured book cost, with 1x/2x/3x reported.
- **Sources:**
  - Gârleanu & Pedersen, [NBER w15205](https://www.nber.org/papers/w15205);
  - Grossman & Zhou, [Math. Finance 3(3)](https://ideas.repec.org/a/bla/mathfi/v3y1993i3p241-276.html);
  - [Kelly with a stop-loss rule, arXiv 1311.2550](https://arxiv.org/pdf/1311.2550);
  - Grobys et al. on volatility management and crypto momentum crashes ([Springer](https://link.springer.com/10.1007/s10203-026-00589-2)).
