# Forecast confidence and sizing are different questions

Reviewed 2026-10-19 from the R217/R225/R227 code and specifications. Static audit only: no forecasts or market returns were recalculated, and no frozen lane was changed.

## Name the object correctly

The project currently has four distinct objects that should not be conflated:

- **R227 forecast score:** a single pinned-model point forecast used to rank coins and score return error. With `sample_count=1`, it is not a probability distribution; path spread cannot be used as confidence.
- **R217 X2 agreement weight:** related flow cells agree, so a coin receives more slices. The cells share inputs and the weight is not a calibrated chance of success.
- **R217/R225 volatility multiplier:** exposure responds to past portfolio volatility. This is a risk overlay, not directional skill or model confidence.
- **Portfolio net return:** a result after the specified venue, cost and funding assumptions. It does not establish the calibration of each coin forecast or achievable fills.

Keep probability skill, ranking skill, trading return, and risk control as separate claims. A calibrated up probability can still be unprofitable after costs; a useful rank can be poorly calibrated; a lower drawdown can simply reflect lower average exposure.

## R217 and R225 sizing limitations

R217's R1 is $m_d=\mathrm{clip}(\sigma_{expanding}/\sigma_{EWMA},0,2)$, computed from past daily book net returns. The target is the expanding sample volatility, so it moves with the sample, and the 2x cap permits leverage above the base book. R217 reports mean multiplier but does not compare R1 with a constant multiplier at the same average gross exposure. Its lower drawdown cannot be attributed to better timing without that control.

R217's R2 code is not the half-Kelly rule described in `docs/SIZING_EVIDENCE.md`. It calculates $k=(\mu/\sigma^2)\max(0,1-1/t^2)$, then divides by the historical median positive $k$ and clips to 0–2; there is no 0.5 fractional-Kelly factor. Its $t=\mu/(\sigma/\sqrt{180})$ also treats 180 daily observations as independent despite overlapping 72-hour sleeves. This makes R2 a relative, path-dependent sizing heuristic, not an interpretable Kelly fraction.

R225 correctly labels its decision as risk-only, but its current calculation scales daily net PnL and estimates resizing cost with $|\Delta m|\times$ mean gross exposure $\times 8$ bp. A later lane should reprice position changes by symbol and hedge. Its decision takes the first 365 on-time rows without proving 365 consecutive dates; late/backfilled or missing dates must not silently count as a continuous live record. Leave the frozen R217/R225 rules unchanged.

## Better next tests

### Probability calibration

After R227's model artifact, vintage, and runner blockers are resolved, a separate, unfrozen calibration proposal can map its frozen 24-hour log-return score $s$ to $p(\mathrm{up})=1/(1+e^{-(a+bs)})$. Fit the two coefficients on an earlier historical segment and freeze them; use a later historical segment only as an exploratory diagnostic. The decisive sample must be prospective and collected after the model, target, baseline, and calibration map are frozen.

Define the binary target exactly as whether the same venue's next 24-hour close-to-close return is positive. Compare daily equal-weight cross-sectional Brier loss with a past-only per-coin up-rate baseline; treat the UTC date, not each coin-row, as the inference unit. Let $\Delta_t=\text{baseline Brier}_t-\text{model Brier}_t$, so positive values favor calibration. One proposed pass rule is a one-sided 95% lower confidence bound for mean $\Delta_t$ above zero at a single final look after 365 complete prospective dates. Predeclare a date-block bootstrap or HAC sensitivity and a minimum coverage gate. Report log loss, CORP reliability with uncertainty, calibration slope/intercept, and forecast coverage as diagnostics. Missing eligible forecasts remain visible in coverage and cannot be silently dropped. This test would establish probability skill only; it would not establish a trading edge or MEXC transfer.

### Risk forecast before a new multiplier

Test the volatility premise directly before trying another multiplier grid. On one frozen unit-size book, calculate daily realized variance $RV_t=\sum_{h=1}^{24}r_{t,h}^2$. Compare a past-only 30-day-half-life EWMA variance forecast with a past-only expanding-mean variance baseline using QLIKE, $L(RV,\hat v)=\log(\hat v)+RV/\hat v$. Use one final score comparison after 365 complete prospective dates and a predeclared dependence-aware interval. Passing this test supports variance forecasting, not directional alpha.

Only a later risk-only application should use $m_t=\min(1,\sigma_0/\sqrt{\hat v_t})$, with $\sigma_0$ fixed in the training period so the overlay cannot increase base exposure. Compare with 1x and a constant multiplier fixed from training data or a predeclared exposure target; matching on realized prospective exposure would be an ex-post descriptive comparison, not confirmatory evidence. Compute scaled position-level costs and preserve 1x/2x/3x reporting. A leverage cap is not a maximum-loss guarantee; account limits, execution, and liquidation remain separate gates.

## References

- The repository's [forecast evaluation playbook](FORECAST_EVALUATION_PLAYBOOK.md) covers proper scores, baselines, CORP reliability diagrams, coverage, and date-block inference.
- Baker and McHale, [Optimal Betting Under Parameter Uncertainty](https://doi.org/10.1287/deca.2013.0271).
- MacLean, Thorp and Ziemba, [Long-term capital growth: the good and bad properties of Kelly and fractional Kelly](https://doi.org/10.1080/14697688.2010.506108).
- Busseti, Ryu and Boyd, [Risk-Constrained Kelly Gambling](https://doi.org/10.3905/joi.2016.25.3.118).
- Moreira and Muir, [Volatility-Managed Portfolios](https://doi.org/10.1111/jofi.12513); Cederburg et al., [On the performance of volatility-managed portfolios](https://doi.org/10.1016/j.jfineco.2020.04.015).
- Lo, [The Statistics of Sharpe Ratios](https://doi.org/10.2469/faj.v58.n4.2453).

No R228 is registered or frozen by this memo. Any measurement needs its own complete preregistration, including the model/data vintage and unresolved timing and funding checks.
