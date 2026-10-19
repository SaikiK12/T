# Research frontier: questions the current evidence has not settled

Reviewed 2026-10-19. This supplement prioritizes independent literature and execution questions that are easy to miss when reading only the lab's own strategy results. It is a source review and a proposed test design, not a new preregistration or a market result. The repo's frozen lanes and live forward journals remain authoritative.

## The main distinction to preserve

Four claims are often collapsed into “the model predicts the market”:

1. A feature is associated with later returns.
2. A forecast ranks or assigns probabilities to individual coins correctly.
3. A portfolio formed from those forecasts earns positive returns after executable costs.
4. The signal, fills, and risk controls transfer to the venue and size the owner intends to trade.

Evidence for one does not establish the next. The project’s strongest tests are portfolio tests. If the goal includes confidence about a particular coin, add a separate forecast evaluation: specify the target in advance (for example, the next 24-hour MEXC return relative to the crypto-perp universe), report rank information coefficient and fixed probability buckets, and score probabilities with Brier or log score against a simple base-rate forecast. Use reliability plots and report coverage, including missing or newly listed contracts. Proper scores reward honest probability forecasts; a profitable long/short sort alone does not show that “70% likely” means 70%. Gneiting and Raftery’s treatment of proper scoring rules is a sound starting point ([paper](https://doi.org/10.1198/016214506000001437)).

## Underexplored empirical findings

### Crypto alpha can hide in the least tradable coins

Cakici, Shahzad, Będowska-Sójka and Zaremba’s cross-sectional ML study finds that much of the apparent predictability comes from simple characteristics, including price, past alpha, momentum and illiquidity. Reported alphas concentrate in small, volatile, hard-to-trade coins and depend on extreme returns there ([2024 paper](https://doi.org/10.1016/j.irfa.2024.103244)). This is a warning about where the result comes from, not proof that the lab’s signal has the same problem.

Zaremba and coauthors study more than 3,600 cryptoassets from 2015 to 2021 and find that short-horizon reversal and momentum vary with liquidity: the most liquid, largest coins show daily momentum where the broader cross-section tends toward reversal ([2021 paper](https://doi.org/10.1016/j.irfa.2021.101908)). This makes a single pooled coefficient a weak description of a strategy whose eligible universe, depth, and contract availability change over time.

**Project consequence:** extend liquidity analysis from historical volume buckets to *executable capacity*. Report returns and coverage by predeclared coin-age and liquidity groups, then price fixed target notionals against MEXC depth. Preserve delisted and ineligible names in coverage accounting. Historical studies above mostly use spot universes and cannot establish MEXC-perpetual fills.

### “Order flow” is not one portable feature

Anastasopoulos and coauthors study daily data for 84 coins from January 2018 through June 2022 and construct signed order flow from 11 fiat-currency markets. Their work finds predictive information in global order flow and evaluates out-of-sample forecasting portfolios ([2026 Journal of Financial Markets paper](https://doi.org/10.1016/j.finmar.2026.101047)). Their feature is transaction flow across international spot markets. It is not Binance’s top-trader position ratio, account ratio, or their difference; it cannot validate those particular positioning features.

Makarov and Schoar document persistent cross-exchange price gaps and decompose Bitcoin exchange flow into common and venue-specific components. Their results show that exchange segmentation matters for both price formation and arbitrage ([2020 Journal of Financial Economics paper](https://doi.org/10.1016/j.jfineco.2019.07.001)). That supports treating Binance-signal-to-MEXC-return transport as a hypothesis. It does not imply that a Bitcoin result generalizes to altcoins or that a Binance signal predicts MEXC fills.

**Project consequence:** always label signal venue, mark/return venue, and execution venue separately. A Binance-derived signal evaluated on MEXC prices is a transfer test; a MEXC-native signal is a different feature experiment. Do not merge them into one claim. Existing cross-venue positioning tests on Gate/OKX are useful but do not settle the intended MEXC execution question.

### Perpetual execution assumptions need a 2026 refresh

MEXC’s official fee notice lists API futures maker/taker rates of 0.06%/0.08% per filled side effective June 1, 2026. A taker entry and exit therefore costs 16 bp before spread, slippage, or funding. Rejected and partial orders are a separate execution risk because they can leave intended exposure unmatched. The notice’s worked example still quotes the prior 0.04%/0.06% schedule, so treat the page as internally inconsistent and confirm the owner’s actual rate through the account-specific fee endpoint before freezing costs ([fee notice](https://www.mexc.com/announcements/article/updates-to-api-futures-trading-fees-jun-1-2026-17827791535742), [Get Fee Details](https://www.mexc.com/api-docs/futures/account-and-trading-endpoints/get-fee-details)).

MEXC says its futures API connects to live trading and has no API sandbox ([official API FAQ](https://www.mexc.co/mexc-api)). Public order-book shadow fills can estimate spread, depth, and latency exposure, but cannot establish actual API fill parity. A future paper-to-live decision also needs point-in-time contract eligibility and sizing (`contractSize`, quantity step, tick, limits, pause/listing state), actual settlement timestamps and funding cashflows, partial/unfilled handling, and fair-price margin/liquidation stress. The venue’s contract and funding endpoints expose fields that should drive that ledger ([contract metadata](https://www.mexc.com/api-docs/futures/market-endpoints/get-contract-info), [funding history](https://www.mexc.com/api-docs/futures/market-endpoints/get-funding-rate-history), [risk limits](https://www.mexc.com/api-docs/futures/account-and-trading-endpoints/get-risk-limits)).

These details materially change the interpretation of the current cost matrix: a modeled 6 bp one-way taker cost is below the listed 8 bp API taker fee, before execution impact. The table rate is not the account’s guaranteed final rate, and the source/example conflict is a reason to verify, not choose whichever value favors the backtest.

## Methods and book notes for Claude

These are applied reading notes, not substitutes for the books. The takeaways below are paraphrased from the works and publisher descriptions; crypto-specific claims still require crypto data.

- **Marcos López de Prado, _Advances in Financial Machine Learning_**, especially chapter 7 on purging/embargo and chapter 12.4 on combinatorial purged cross-validation ([publisher contents](https://www.wiley.com/en-gb/advances-in-financial-machine-learning-p-9781119482086)). Purging removes labels whose outcome windows overlap a validation sample; embargo adds a time gap to limit leakage around a split. Useful when training or selecting among overlapping 72-hour trades. Combinatorial splits can describe sensitivity to path choices, but are not the same as a clean forward deployment period, and a PBO estimate is not the probability a strategy will make money next year.
- **Larry Harris, _Trading and Exchanges: Market Microstructure for Practitioners_**, with its dedicated chapter on liquidity and transaction-cost measurement ([Oxford chapter 21](https://academic.oup.com/book/52292/chapter-abstract/421090015)). The practical lesson is to treat execution cost as a market-structure outcome: urgency, order type, depth, spread, and adverse selection all matter. A passive quote can save fees and still lose through missed fills or selection into trades that move against it. Use the book to frame cost measurement; use MEXC’s current contract rules and prospective book data for actual values.
- **Rishi Narang, _Inside the Black Box_, 3rd edition**, separates alpha, risk, transaction-cost, portfolio-construction, and execution models ([Wiley, 3rd edition](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/finance-investments-13fi/investments-securities-13fi3/inside-the-black-box-978-1-119-93189-8)). For this project, a good signal is only one component: sizing, hedge quality, funding, and fills can reverse the net result. Review those components as a linked system rather than interpreting strategy Sharpe as a property of the feature alone.
- **Ernest Chan, _Algorithmic Trading: Winning Strategies and Their Rationale_** ([Wiley](https://www.wiley.com/en-us/algorithmic-trading-winning-strategies-and-their-rationale-p-9781118460146)). The useful habit is to connect each strategy hypothesis to its rationale, implementation, and code. For crypto, reuse the workflow, not old asset-specific parameter values or thresholds.

For the lab’s large and dependent search, White’s Reality Check tests the *best candidate from a declared search family* against a benchmark while accounting for data reuse ([2000 paper](https://doi.org/10.1111/1468-0262.00152)); Hansen’s SPA is a related family-wise predictive-ability test ([2005 paper](https://doi.org/10.1198/073500105000000063)). These are more relevant to correlated candidate searches than treating millions of atlas cells as independent trials. They require a defensible candidate family and dependence-aware resampling. Keep PBO/DSR as diagnostics and the chronological forward result as the decisive deployment evidence; none can recover undocumented analyst choices.

## Proposed next test, not yet frozen

Do not modify R198 or R200. After the active forward decision and audit are complete, a new lane can ask one question: **does one already nominated signal, with its formula and timing held fixed, produce a positive net portfolio on a prospectively observed MEXC USDT-margined crypto-perpetual universe?** Freeze the signal, venue map, eligibility and delisting rules, target size, order type, decision-to-submit delay, funding accounting, benchmark, final date, inference procedure, and rejection/no-fill rules before collecting or opening outcomes. Exclude TradFi contracts from a crypto-only target.

Record public MEXC book snapshots/deltas, signal timestamp, modeled arrival, quote age, fills (if separately authorized later), fees, funding events, cancellations, and skipped names. A shadow fill remains a simulation. Report gross and net PnL, turnover, maximum drawdown, capacity/slippage at fixed notionals, 1x/2x/3x cost stress, and the predeclared factor exposures. If the project also wants “confidence on any coin,” register a separate coin-level forecast target and calibration score; do not promote that diagnostic into the portfolio gate after seeing results.

## What was and was not tested here

The local checkout contains no raw market-data archive, so no new historical return statistic or backtest was calculated. The available Python suite was attempted earlier: 61 tests passed and 12 errored because this environment lacks `numba` and `pyarrow`. That is an environment-limited code check, not evidence for or against an edge. No package was installed, no market data was downloaded, and no frozen specification or journal was changed.

Focused supplements in this review: [recent cross-sectional factor evidence](CRYPTO_CROSS_SECTION_EVIDENCE.md), a [coin-level forecast scorecard and baseline horse race](FORECAST_EVALUATION_PLAYBOOK.md), [market direction and regime](MARKET_DIRECTION_AND_REGIME.md), [feature vintage integrity](FEATURE_VINTAGE_INTEGRITY.md), [contract lifecycle integrity](CONTRACT_LIFECYCLE_INTEGRITY.md), an [implementation integrity review](IMPLEMENTATION_INTEGRITY_REVIEW.md), [perpetual carry accounting](PERP_CARRY_ACCOUNTING.md), and [execution/capacity/liquidation constraints](PERP_EXECUTION_AND_RISK.md). The new notes separate broad-market direction from relative ranking, distinguish revised data from values actually knowable at the time, and treat token lineage and exchange contracts as different objects. Together they distinguish published studies, preprints, official venue mechanics, code review and synthetic-only checks.
