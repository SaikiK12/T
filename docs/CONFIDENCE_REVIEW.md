# Confidence review: what the market-prediction project can claim

Review of the R212 repository snapshot dated 2026-10-19. This is an independent research-design review. It does not change frozen specifications, recalculate returns, or re-audit the forward-data implementation underway elsewhere.

## Decision

The project has found promising cross-sectional signals, especially top traders positioned against their own crowd, but it has not yet established a reliable, executable edge. R198’s registered primary book did not meet its holdout rule, the R200 forward test is only at an early checkpoint, and the evidence is mainly Binance-specific while the stated project goal is primarily MEXC altcoins. Keep the work in paper mode. Treat any later real-money decision as an owner decision after a fresh, venue-matched paper result and practical risk checks.

The current evidence supports a narrower statement than “predict the market on whatever coin”: some frozen ranks distinguish average future returns across a changing set of liquid Binance contracts. It does not show that every coin’s return can be forecast reliably, or that the same signal is profitable after execution on another exchange.

## Evidence ledger

| Result | What the snapshot reports | What it supports | What it does not establish |
|---|---|---|---|
| R197, in-sample flow book | +42.6% annualized net at 1x costs, Newey–West t 3.25; +26.9% at 2x and +11.3% at 3x | A coherent portfolio candidate worth monitoring | Independent confirmation: the cells came from a large atlas search and the book design followed earlier attempts |
| R198, registered holdout primary | +103.8% over 457 days (+82.9% annualized), t 1.22 versus the preregistered t >= 2 rule; 47% maximum drawdown and 1.93 gross exposure | Positive realized holdout PnL with substantial uncertainty | A confirmed result. The preregistered primary verdict is NOT CONFIRMED; the holdout is spent |
| R198, top-vs-crowd alone | +89.3% over the holdout, t 2.72, 16% maximum drawdown, 0.64 gross exposure | The clearest component to motivate a future test | A confirmatory pass: it was reported as a secondary result, after candidate selection, not the registered primary decision |
| R200, live paper books A and B | At the 2026-10-19 snapshot, 18 scored days; reported returns are positive but the frozen decision is at 90 days, 2026-12-29 at the earliest | A useful prospective test has started | A conclusion from 18 days. Its preregistration itself expects 90 days may still be inconclusive |

For R198, the combined portfolio’s return stays positive at higher modeled costs, but its statistical uncertainty remains the deciding issue. The secondary top-vs-crowd number is attractive, yet choosing it after seeing the same holdout would spend that holdout twice. It should be treated as a hypothesis for a later frozen test, not retroactively promoted.

The R200 ticket count also needs careful interpretation. The frozen gate checks mean, hit rate, worst day and a Newey–West t statistic; the shared gate can report entry-day clusters when supplied, but does not gate on them. Ninety daily tickets from 72-hour overlapping positions are not automatically ninety independent opportunities. Its 30- and 60-day checkpoints should remain operational monitoring only; do not retune or declare a pass there.

## What the project has done well

- It freezes a research question before measuring it, records experiment counts, and treats null results as results.
- The historical universe includes delisted contracts, reducing survivor-only backtest bias.
- R198 used a one-shot holdout with a written decision rule and explicitly marked the primary result not confirmed.
- Cost sensitivity, placebo/full-pipeline null work, and live/archive parity checks are part of the process.
- It distinguishes predictive cells from a tradable portfolio and reports failure of many ideas to survive costs.
- The repository contains no order path or credentials, and its rules reserve any future order for the owner.

Those are strong research habits. They reduce common sources of self-deception, but they cannot turn an inconclusive holdout into confirmation or establish fills on a different venue.

## Main confidence gaps

### 1. Selection remains material

R198’s own preregistration says the signal cells came from a 338,240-cell atlas and two book designs. The current registry reports 9,471,705 program trials, mostly context-atlas cells. Those cells are highly correlated, so 9.47 million is not a count of independent experiments and should not be fed mechanically into a Bonferroni correction. It is still evidence that the research process has had many chances to find attractive patterns. Count research decisions as well as script-level cells: chosen signal definitions, portfolios, horizons, hedges, samples, and follow-up questions all matter.

The right response is not to pick a universal t-statistic from an equity paper. Use the registry and full-pipeline nulls to describe the search, keep exploratory results labeled, and make the next untouched forward period the confirmatory test. Harvey, Liu and Zhu explain why the usual t > 2 convention can be too permissive after factor mining; their estimated higher hurdle is specific to their equity-factor setting, not a universal crypto rule. Sullivan, Timmermann and White show how to evaluate a full universe of technical rules for data-snooping rather than report only its winner. Deflated Sharpe and probability-of-backtest-overfitting diagnostics can add context, but cannot replace a frozen prospective test.

### 2. The target market is not settled

FOUNDATION says the goal is mainly MEXC altcoin perpetuals. The discovery book, holdout and R200 paper test use Binance USD-M returns. R200 also includes Binance TradFi perpetuals in its live universe. A feature computed from Binance may conceivably predict MEXC returns, but this repository has not demonstrated that transfer. If Binance is now the actual target, update the charter in a future change; if MEXC remains the target, measure fills, fees, funding, listings, symbol mappings, and liquidity on MEXC.

The moving top-50 universe is broad across time, but it is not a promise about “whatever coin.” The evidence applies to contracts that meet the frozen eligibility and history rules. Newly listed, thin, delisted, or unsupported coins may behave differently. Publish coverage and performance by predeclared liquidity and age groups, and do not generalize to a coin group that was not tested.

### 3. A portfolio return is not yet a coin forecast

The book ranks and shorts selected coins relative to a universe hedge. That can be a useful portfolio strategy even if it cannot predict an individual coin’s direction. To support the broader prediction claim, a separate preregistration should define what each coin-level forecast means, evaluate calibration and rank monotonicity on unseen periods, report coverage, and cluster uncertainty by date and coin. Keep this diagnostic distinct from the existing R200 pass rule.

### 4. Risk and execution are not fully represented by a positive backtest

The R198 primary had 47% maximum drawdown and nearly 2x gross exposure; its universe hedge is an equal-weight basket whose internal rebalancing is idealized. The findings explicitly lack borrow, margin and forced-liquidation modeling. A nominally market-neutral return series can still be hard to finance and can suffer severe short squeezes. The top-vs-crowd secondary looks smoother, but its 16% drawdown does not erase its selection problem.

The 1x/2x/3x fee matrix is a useful stress check, not a fill model. A live paper result should use the intended venue’s fee tier, bid/ask, realistic signal-to-entry delay, funding, rejected or partial fills, and capacity at the planned order size. Report gross and net exposure, turnover, liquidity consumed, drawdown and the result under conservative execution assumptions.

### 5. The current sample is short for the decision being asked

R200’s own frozen expectations say that a Sharpe near 1 over 90 days often produces a t-statistic around 0.5–1, and that the result may be “not decided.” Do not weaken the threshold if that happens. If it remains promising, freeze an extension under a new registry ID and keep accumulating genuinely forward observations. Do not reopen R198 or reuse the post-2026-10-01 Binance outcomes already seen to choose a replacement strategy.

## Recommended next research lane

After leaving R200’s frozen books and Claude’s active pipeline audit untouched, the most valuable independent angle is a target-venue transfer and factor-attribution lane. The Foundation currently points to MEXC, so this proposal assumes MEXC remains the intended execution venue. If that assumption is wrong, document the target before freezing anything.

1. **Register first.** Create a new lane with one primary portfolio hypothesis, a fixed symbol-eligibility rule, signal source, clock, entry delay, holding rule, position sizing, benchmark, and cost model. Do not edit R200 or use the R198 holdout again. Start the MEXC prospective sample only after the new specification is frozen; do not backfill dates whose Binance outcomes have already been read as evidence for this signal.
2. **Test transport, not a new optimized signal.** Keep the selected signal definition fixed and ask whether it yields net returns on MEXC-tradable crypto perps. Restrict to the preregistered common support of signal availability and MEXC contracts; explicitly log missing symbols and hours. Use MEXC prices and funding for outcomes and a feasible MEXC hedge with its own costs.
3. **Measure incremental return.** Alongside the one primary net portfolio result, report prespecified market, size, and momentum factor exposure; also report basis, liquidity, volatility and funding exposure as diagnostics. Do not select factor definitions or hedge weights after seeing the outcome. Liu, Tsyvinski and Wu find market, size and momentum factors account for many cryptocurrency cross-sectional strategies. Chi and coauthors find cryptocurrency futures results sensitive to signal and holding period, with basis more persistent than momentum in their sample; their data cover 12 large OKEx contracts through March 2021, so this is a benchmark design lesson, not evidence that this strategy transfers.
4. **Answer the coin-level question separately.** Before opening results, define fixed forecast buckets and report whether future MEXC returns change monotonically across them, by the preregistered coin groups, with uncertainty clustered by date and coin. This determines whether the project predicts across coins or only earns a pooled portfolio return.
5. **Plan the decision rule for dependence and multiplicity.** Preserve R200’s frozen designation of book A as primary and book B as the second trial; do not promote B after seeing it do better. For the new lane, define the final date, inference method, serial/cross-sectional dependence treatment, and what happens at any monitoring points. Do not declare a pass from whichever checkpoint happens to look best.
6. **Keep the capital gate separate from the statistics gate.** A statistically positive paper result is not enough by itself. Before any owner-placed small stake, require plausible execution costs, acceptable drawdown and margin stress, a meaningful number of independent market regimes, and no unmodeled short/borrow failure. The existing gate is a necessary project rule, not proof that its risk limits fit the owner’s capital.

This lane will not make the result independent of the original signal discovery; it will answer the more practical unresolved question of whether the selected Binance-derived signal survives on the intended trading venue. A new signal discovered from the same history would need its own untouched forward confirmation.

## Reading list for the next review

- Campbell Harvey, Yan Liu and Heqing Zhu, [“. . . and the Cross-Section of Expected Returns”](https://www.nber.org/papers/w20592), for multiple testing and factor-discovery thresholds. Apply the lesson about selection, not their numeric threshold as a crypto cutoff.
- Ryan Sullivan, Allan Timmermann and Halbert White, [“Data-Snooping, Technical Trading Rule Performance, and the Bootstrap”](https://doi.org/10.1111/0022-1082.00163), for evaluating the rule-search process instead of only its best result.
- David Bailey et al., [“The Probability of Backtest Overfitting”](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253), and David Bailey and Marcos López de Prado, [“The Deflated Sharpe Ratio”](https://doi.org/10.3905/jpm.2014.40.5.094), as selection-bias diagnostics for a finite historical strategy set.
- Marcos López de Prado, [Advances in Financial Machine Learning](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/advances-in-financial-machine-learning-978-1-119-48208-6), especially its treatment of backtest overfitting and purged validation.
- Yukun Liu, Aleh Tsyvinski and Xi Wu, [“Common Risk Factors in Cryptocurrency”](https://doi.org/10.1111/jofi.13119), for market/size/momentum controls in cross-sectional crypto returns.
- Yeguang Chi et al., [“An Empirical Investigation on Risk Factors in Cryptocurrency Futures”](https://doi.org/10.1002/fut.22425), for futures basis, holding-period sensitivity, and factor attribution.

No new market data, return statistic, backtest, or test suite was run for this review. All project figures above are quoted from the repository snapshot and should be rechecked if the branch advances before this note is merged.
