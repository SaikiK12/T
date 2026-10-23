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
