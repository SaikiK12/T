# Market direction and regime: a separate forecast question

Reviewed 2026-10-19. The project's R200 portfolio is cross-sectional: it asks whether selected coins outperform other eligible coins. That can succeed while the broad crypto market falls, and it does not establish that any individual coin will rise. A second, market-direction model would need a separate target, benchmark, evaluation and prospective test.

## Shared movement changes the question

The IMF's 2023 crypto-cycle paper estimates that a common crypto factor explains around 80% of crypto price variation in its sample. This motivates separating a broad crypto move from coin-specific return. It does not mean 80% of a particular project's PnL is a market beta, nor does it establish a tradable forecast ([IMF Working Paper 23/163](https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834)).

Evidence about macro exposure is mixed across horizons and methods. A New York Fed intraday event study finds Bitcoin is orthogonal to monetary-policy and macroeconomic news ([Staff Report 1052](https://www.newyorkfed.org/research/staff_reports/sr1052)). A Chicago Fed working paper finds Bitcoin's equity exposure increased substantially and became positive around 2020 ([Working Paper 2026-16](https://www.chicagofed.org/publications/working-papers/2026/2026-16)). These results can coexist: an asset may share broad risk-on variation with equities while showing little response to specific news over the narrow event window. Neither result is a directional forecast.

Yae and Tian's daily out-of-sample comparison for BTC, ETH and XRP reports that only changes in stock-market stochastic correlation meaningfully predicted returns among the tested predictors; the reported out-of-sample R² values reach 2.69%, 1.71% and 2.12%, respectively. The sample is three assets and daily horizons, so it is a candidate hypothesis, not evidence for hourly altcoin perpetuals or MEXC execution ([2022 paper](https://doi.org/10.1016/j.physa.2022.127379)).

## Keep three targets distinct

| Claim | Example target | What it answers |
|---|---|---|
| Broad market direction | Return of a named point-in-time crypto-perpetual index over the next 24 hours | Is the market forecast above a past-only no-change or drift baseline? |
| Coin-specific direction | Coin return minus a fixed-weight or beta-estimated market return | Does the coin move beyond common crypto exposure? |
| Tradable portfolio outcome | MEXC-local account return after actual fees, funding, spreads and execution rules | Could the forecast produce net results at declared size? |

Freeze index membership, weights, rebalancing clock and missing/delisted-contract treatment before evaluating the first target. For the second, estimate hedge betas recursively using information available at each decision; do not subtract realized future market returns from the target. For the third, use a separate executable ledger and preserve the market forecast as an input rather than silently changing the portfolio's objective.

Report raw coin return, market return, market-adjusted return and forecast-market correlation together. Compare each forecast with zero/no-change, past-only drift and a market-only model; evaluate out of sample by date blocks and disclose both rising and falling regimes. A strong cross-sectional sort during a bull market does not answer the broad-direction question. A high market correlation does not mean the market's direction was forecast.

## Macro features need vintage-aware timestamps

Macro releases often arrive on schedules while historical series are later revised. FRED's documentation distinguishes today's revised observations from real-time periods; ALFRED provides historical vintages. The release-date endpoint also cautions that a source's release date is not necessarily when an observation became available through FRED/ALFRED ([FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [FRED release dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html)). The BLS CPI calendar lists release dates and times (the current schedule lists 08:30 AM; the BLS calendar specifies Eastern time). For a 24/7 crypto test, retain the actual release and first-receipt timestamps with a timezone, not only the reference month or calendar date ([CPI release schedule](https://www.bls.gov/schedule/news_release/cpi.htm), [BLS 2026 calendar](https://www.bls.gov/schedule/2026/)). A date label alone can shift a signal by hours or use a later correction.

For each macro input, store observation period, source release time and timezone, first vendor/API receipt time, vintage or revision identifier, retrieval timestamp, and the value used. Keep stale values explicit between scheduled releases. See [feature vintage integrity](FEATURE_VINTAGE_INTEGRITY.md) for the as-of rule and a separate treatment of on-chain revisions.

## Sources and boundary

- IMF (2023), [The Crypto Cycle and US Monetary Policy](https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834).
- Benigno & Rosa (2023), [The Bitcoin–Macro Disconnect](https://www.newyorkfed.org/research/staff_reports/sr1052), New York Fed Staff Report 1052.
- Drexler, Guettler & Sun (2026), [Crypto Is Coming of Age: The Case of Bitcoin’s Rising Beta](https://www.chicagofed.org/publications/working-papers/2026/2026-16), Chicago Fed Working Paper 2026-16.
- Yae & Tian (2022), [Out-of-Sample Forecasting of Cryptocurrency Returns: A Comprehensive Comparison of Predictors and Algorithms](https://doi.org/10.1016/j.physa.2022.127379).
- Federal Reserve Bank of St. Louis, [real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and [release dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html).
- U.S. Bureau of Labor Statistics, [CPI release schedule](https://www.bls.gov/schedule/news_release/cpi.htm) and [2026 release calendar](https://www.bls.gov/schedule/2026/).

This is a synthesis of published or working-paper evidence and a proposed evaluation design. No macro series, market data or returns were downloaded for this note, and it does not report a project forecast or a tradable edge.
