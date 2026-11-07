# R229 slow_trend_v1: NULL — the fixed spot trend ensemble misses its validation comparison

Specification frozen 2026-10-19, SHA-256 `ad247ec8676b8ae817fea41a6a6a82303cedf298e49cdaaea35bfd55625f169b`; market run completed 2026-10-20. The runner and fetcher remain the exact code versions pinned before collection. This is an exploratory six-surviving-coin spot adaptation of *Catching Crypto Trends*, not a replication of its rotating universe or a perpetual-futures result.

## Verdict

The primary volatility-scaled trend ensemble earns a positive validation return after doubled costs, but fails three other frozen requirements:

- Validation Sharpe is **1.261**, versus **1.227** for the discovery-risk-matched passive portfolio: improvement **0.034**, below the required 0.15.
- Validation compound drawdown is **9.74%**, worse than the matched passive portfolio's **7.15%**.
- The paired mean improvement is **+0.957 bp/day**, with a 30-day-block 95% interval **[-2.107, +4.656] bp/day**. Its lower endpoint is below zero.

Verdict: **NULL**. The unscaled diagnostic and already-viewed holdout cannot rescue this primary decision. No horizon, stop, universe, cost level or execution delay was changed after opening outcomes.

## What actually ran

The fixed assets are BTC, ETH, SOL, XRP, DOGE and ADA, all Binance spot USDT pairs. The nine close-based Donchian components use 5/10/20/30/60/90/150/250/360 days, with a prior-day trailing stop and reset on reentry. The primary averages their long/cash signals and applies the frozen per-coin 90-day volatility multiplier, capped at one; the diagnostic omits that multiplier. A signal is known a full daily bar before its modeled entry boundary.

The account holds spot units and cash, without leverage, and pays costs on changes from drifted holdings. Desired weights are post-cost weights. Initial entries and final liquidations are charged for every split; the passive benchmark rebalances monthly. Cash yield is zero. All 36 strategy/split/cost accounts were rerun, rather than subtracting average costs from saved returns.

Discovery sets the passive capital fraction to **0.111755**. This scale is fixed before validation; it is not fitted to future volatility. Realized annualized validation volatility is **11.16%** for trend versus **8.62%** for matched passive, so the small higher mean also comes with higher realized risk. The source's 25% per-coin volatility target is not a 25% portfolio-volatility guarantee.

## Primary versus matched passive, 1x costs

| Period | Days | Trend / matched mean bp/day | Trend / matched Sharpe | Trend / matched compound DD |
|---|---:|---:|---:|---:|
| Discovery 2022–2023 | 730 | 2.23 / 0.44 | 1.041 / 0.210 | 5.49% / 11.06% |
| Validation 2024–2025H1 | 547 | 3.85 / 2.90 | 1.261 / 1.227 | 9.74% / 7.15% |
| Known holdout 2025H2–2026Q3 | 457 | -0.51 / -0.38 | -0.254 / -0.199 | 12.71% / 11.78% |

Validation ending NAV from initial cash 1 is 1.22325 for trend and 1.16526 for matched passive. The known-holdout trend NAV is 0.97363. The unscaled trend diagnostic's validation Sharpe is 1.078 and its drawdown 25.65%; it is reported, not promoted.

The primary paired bootstrap uses 5,000 circular 30-day-block replicates. The 10- and 60-day sensitivities, also 5,000 each, give intervals [-1.659,+4.168] and [-1.948,+4.305] bp/day. All include zero. These are conditional historical uncertainty estimates on dates the project has already viewed, not a program-wide multiple-testing correction.

## Complete cost stress for the primary

One-way costs are frozen assumptions of 12/24/36 bp at 1x/2x/3x, covering fee plus assumed slippage. They are not owner-specific fees or measured fills.

| Period | Mean bp/day, 1x / 2x / 3x | Compound DD, 1x / 2x / 3x |
|---|---:|---:|
| Discovery | 2.23 / 2.01 / 1.80 | 5.49% / 5.95% / 6.98% |
| Validation | 3.85 / 3.64 / 3.42 | 9.74% / 10.12% / 10.51% |
| Known holdout | -0.51 / -0.75 / -1.00 | 12.71% / 13.45% / 14.19% |

All benchmark and diagnostic stress paths, turnover, exposure, cost amounts and NAVs are in `results/metrics.csv` and `results/daily.csv`. All 20,808 scored daily account rows are retained.

## Data and provenance

414 monthly daily-candle archives plus publisher checksums were collected from Binance's official public spot archive, totaling **816,137 ZIP bytes**. This stayed below the predeclared 5 MiB budget. All checksums, ZIP CRCs and complete calendars passed: 2,099 days per coin, 12,594 candles in total, including the 2021 indicator warm-up. No gaps were filled. The reader handles the documented January 2025 timestamp change from milliseconds to microseconds.

`DATA.sha256` pins collection manifest `fc90fe4886608cbc090231374bcaf593082d54959bdc25de2ed1566d86fd42cd` before price values were parsed. That manifest identifies the exact downloaded source bytes, not all historical exchange revisions. The raw cache is outside Git; the manifest, source URLs, observed/publisher-verified hashes and derived results are included. See `PREREG.md` for the pinned primary-paper, runner and fetcher hashes.

The source paper uses aggregated prices and a rotating liquid universe. This adaptation fixes six names that survived, caps exposure at one instead of two, omits the paper's 20% volatility-rebalancing band, and adds a full-day entry delay. A null here closes this fixed adaptation; it does not falsify every trend model or the original paper. No MEXC fill, futures funding, small-altcoin capacity or calibrated forecast-probability claim follows.

## Verification and reproduction

The full repository suite passed **187 tests**, including 24 new synthetic trend tests; the fetcher's separate 10 offline tests also pass. A fresh-directory rerun reproduced every research artifact byte for byte. An independent piecewise-linear fee solver checked all 36 accounts and 20,808 daily rows against the runner's bisection accounting; maximum absolute discrepancy was 7.2e-14. Output hashes are in `results/run_manifest.json`.

With the original raw cache present, reproduce using `python3 scripts/run_slow_trend.py --out /tmp/slow_trend_fresh_results`. The output directory must be fresh. From a new checkout, collect source files with `python3 scripts/fetch_trend_daily.py --manifest /tmp/slow_trend_download_manifest.json` first: preserve the committed `results/data_manifest.json` and `DATA.sha256`, then use those original pinned records for the runner. A changed publisher archive must fail the original snapshot comparison rather than silently revise the study.

Trials: two candidate portfolios, with one primary and one nondecisive diagnostic. The nine literature-selected component horizons are disclosed. Raw program trials before: 9,471,786; after: 9,471,788. Existing frozen lanes, findings and journals were not rewritten. A fresh prospective test and broader point-in-time universe would be needed for any later edge claim; this failed screen does not nominate a forward winner.
