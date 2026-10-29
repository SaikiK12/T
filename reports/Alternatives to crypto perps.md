# Alternatives to crypto perpetuals: a web scan

> **Historical review — 2026-10-26.** This document describes an earlier checkout. Its counts, data coverage, calculations and recommendations have not been refreshed or revalidated. The [original revision](https://github.com/SaikiK12/T/blob/49e59af551cf636bfd5930cd20a4dfe31ecb6cde/reports/Alternatives%20to%20crypto%20perps.md) retains the received text. Use the [current panel](../docs/PANEL.md), [live queue](../registry/methods.csv) and linked lane evidence for present decisions. Local links below have been made portable; unavailable source paths are labelled.

Written 2026-10-26 on `ccr-23562535-bd0mr3`. The web results are search snippets and secondary summaries. Full texts were not read, and each claim below says what it rests on. Reachability was tested from the sandbox on 2026-10-26. Nothing was downloaded, frozen, registered or ordered.

## 1. Short answer

- **The switch has one structural argument: statistical power.** For an annual Sharpe S over T years, the t-statistic is about S·√T. Five years of crypto history gives t ≈ 2.2 only at S = 1. Commodity futures have decades of published history (Hurst, Ooi and Pedersen go back to 1880 in one source). A modest edge, S = 0.5 over 40 years, gives t ≈ 3.2. Whether it persists after costs is a separate question.
- **The best-supported mechanisms are carry or roll yield across commodities, and momentum in commodity futures.** Both have academic backing, although the snippets show no net-of-cost return tables.
- **The binding constraint is data, not ideas.** From this sandbox, CME and Stooq are unreachable, and Yahoo rate-limits. Continuous futures with contract months, which carry requires, are the blocker. COT and USDA data are reachable and free.
- **Grain seasonality and weather-driven returns are weak leads** on the evidence seen. Prediction markets show one structural bias, but legal access depends on jurisdiction.

## 2. What the registry has not tested

- No registry row mentions grains, softs, COT positioning, WASDE, weather, or stocks-to-use. A grain program would start with no spent holdout. The crypto holdout problem does not carry over.
- R237 tested cross-asset time-series momentum on 23 ETF, FX, metal and bond series (2 trials, NULL). R261 used gold, silver, crude and Brent only as leads for crypto. Carry across commodity futures has not been tested.

## 3. Options

| Option | Mechanism | What the web says (confidence) | Data reachable here | Verdict |
|---|---|---|---|---|
| Carry and roll yield across commodities | Convenience yield, inventories, storage costs; backwardation pays long holders, contango costs them | Koijen, Moskowitz, Pedersen and Vrugt, "Carry": carry forecasts returns across asset classes including raw materials, and falters in all of them together during global recessions. NBER w19325, published JFE 2018 per the author's CV, with conflicting years across sources. No commodity return figures seen (medium). | Needs multi-month settlement history. CME blocked, Yahoo front-month only | Strongest structural case. Data is the blocker. |
| Momentum in commodity futures | Trend and cross-sectional persistence | Miffre and Rallis: 13 of 56 momentum rules profitable over 1–12 months, contrarian rules failed, 31 commodities 1979–2004. Figures come from a 2006 version, so check the 2007 text (low). Hurst, Ooi and Pedersen (2017) run back to 1880 with simulated costs, which the authors say are imprecise. A 2025 *Journal of Futures Markets* paper finds heavy turnover eats factor-momentum gains (medium). | Front-month series would do for time-series momentum | Longest samples. Costs and turnover decide. |
| COT positioning | Hedging pressure; trend-chasing speculators | Positions track prices more than they lead them. Some in-sample timing from hedging pressure, 2000–2006 (CXO summary). R² of 0.02 for S&P positioning, 1995–2012 (CXO). Energy study (2004): little forecasting value (medium). | CFTC reachable (200). Free and weekly | Cheap to test. Prior is low to moderate. |
| Stocks-to-use (USDA) | Scarcity raises volatility and price levels | farmdoc (2016): tracks corn acceptably, soybeans R² 0.50. Flanders cointegration: prices fall as the ratio rises. farmdoc (2021): crop-year price variability has not risen as stocks shrank (medium) | NASS QuickStats reachable (200). A free API key may be needed, which is an owner step | Use as a regime or volatility conditioner. Not a clean return signal. |
| WASDE report reactions | Information shock on report days | Variance about 7× normal on report days, 1985–2006 (JAAE, via summary). A significant move appears about 30 minutes after release (NCCC-134, 2024) (medium) | USDA main site returns 403. Options data is costly | Strong event effect, but speed favours others. Poor fit for us now. |
| Weather | Forecast surprises move prices or volatility | Iowa State thesis: forecast weather information is absorbed quickly. Luo and Zhang (2024): weather improves volatility forecasts, not returns. Their wheat return claims (Sharpe near 10) look implausible, and I flag them as such (low) | NOAA NCEI reachable (200). Forecast archives are hard to get | Thin. Volatility forecasting at most. |
| Grain seasonality | Calendar patterns | Vendor commentary only (CQG). No returns, no tests, no peer-reviewed study found (low) | Not needed to test | Weak. Not worth a pre-registration on its own. |
| Prediction markets (Kalshi) | Favorite-longshot bias; maker and taker split | Bürgi, Deng and Whelan (Sept 2025), over 300k contracts: a dollar staked recovers about 80 cents before fees and 78 after. Takers lose about 32%, posters about 10%. May be weakening. One study, no replication (medium) | Public API and legal access unverified | Interesting maker-versus-taker structure. Check legal access before anything else. |

## 4. Data reachability from the sandbox (2026-10-26)

| Source | Status | Use |
|---|---|---|
| cftc.gov | 200 | COT positioning, weekly |
| publicreporting.cftc.gov | 301 | COT data endpoint, redirects |
| quickstats.nass.usda.gov | 200 | USDA crop and stock figures |
| usda.gov | 403 | WASDE PDFs, route unclear |
| ncei.noaa.gov | 200 | Weather history |
| fred.stlouisfed.org | 200 | Monthly commodity price series, not futures |
| cmegroup.com | unreachable | Settlement history blocked from here |
| stooq.com | unreachable | Blocked from here |
| query1.finance.yahoo.com | 429 | Rate-limited today. Front-month only |
| barchart.com | 200 | Terms and free history unknown |
| Nasdaq Data Link CHRIS | not verified | The search found no current page. Status unknown |

## 5. Costs for a micro grain contract

- Micro corn, soybean and wheat contracts are 500 bushels, one tenth of the standard 5,000 (CME contract specs).
- Minimum increment is a half cent per bushel (CME advisory). CME's rulebook gives $2.50 per tick for micro corn and soybeans. A third-party post gives $1.25 for soybeans, which is likely wrong. Verify on CME.
- Commission for non-members: $0.50 per side, per a third-party post. Unverified.
- Margins were not found. Cash settled, no delivery.
- **Order of magnitude:** a half-cent tick at an illustrative $5 per bushel is 10 bp. One tick per side is about 20 bp round trip, the same order as our crypto cost tiers. The drag is smaller for strategies that trade monthly.

## 6. Recommendation for the owner to decide

1. **Make the switch an explicit decision.** Open a separate commodities program with its own registry rows and room claims. Freeze new crypto families.
2. **Cheapest first step, no large download:** pull the CFTC COT reports (small files) and pre-register one positioning hypothesis with two variants and a declared trial count. Use fixed discovery, validation and holdout windows before anything is read.
3. **Best-supported step, blocked on data:** a carry and momentum test on a diversified basket (metals, energy, grains, softs). It needs contract-month settlement history from a source the owner provides: a CME download from an account-holder machine, or a paid vendor.
4. **No trading.** Any broker use is an owner decision and follows paper results (AGENTS rule 6).
5. **Prediction markets:** check legal access in the owner's jurisdiction before any measurement. Park it until then.

## 7. Not verified

- Full texts of Koijen et al., Miffre and Rallis (2007), Moskowitz, Ooi and Pedersen (2012), Hurst, Ooi and Pedersen (2017), and the Bürgi, Deng and Whelan study.
- COT disaggregated start dates, CME micro margins, Nasdaq CHRIS status, prediction-market API access, and current grain price levels.

## 8. Sources (search snippets)

- Carry: https://projects.nber.org/papers/19325 · https://som.yale.edu/sites/default/files/2025-06/CV_moskowitz_2025.pdf · https://www.advisorperspectives.com/commentaries/2018/08/24/why-commodity-carry-may-be-higher-than-you-think
- Momentum: https://climateinstitute.edhec.edu/publications/momentum-strategies-commodity-futures · https://fairmodel.econ.yale.edu/ec439/hurst.pdf · https://ideas.repec.org/a/wly/jfutmk/v45y2025i11p1934-1969.html
- Stocks-to-use: https://farmdocdaily.illinois.edu/2016/04/relationship-between-stock-to-use-and-prices.html · https://ageconsearch.umn.edu/record/302506/files/FlandersStocktoUse.pdf · https://farmdocdaily.illinois.edu/2021/06/stock-to-use-ratios-of-us-corn-soybeans-and-wheat-since-1960.html · https://farmdocdaily.illinois.edu/wp-content/uploads/2023/10/fdd101623.pdf
- COT: https://ideas.repec.org/a/eee/eneeco/v26y2004i3p425-445.html · https://www.cxoadvisory.com/sentiment-indicators/using-commitments-of-traders-reports-to-time-asset-allocations
- WASDE: https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2024/pdf/Anderson_McKenzie_Noyes_NCCC-134_2024.pdf · https://core-cms.cambridgecore.org/core/journals/journal-of-agricultural-and-applied-economics/article/impact-of-situation-and-outlook-information-in-corn-and-soybean-futures-markets-evidence-from-wasde-reports/C584140E88E03FFB055D4622561132DC
- Weather: https://dr.lib.iastate.edu/entities/publication/bcd4f6d5-2e87-4436-8a23-b188c1167b76/full · https://ideas.repec.org/a/wly/jfutmk/v44y2024i2p151-217.html
- Grain seasonality: https://news.cqg.com/blogs/commentary/2026/03/25/weekly-grain-seasonal-review
- Prediction markets: https://www.karlwhelan.com/Papers/Kalshi.pdf · https://cepr.org/publications/dp20631
- Micro contracts: https://cmegroup.com/markets/agriculture/grains/micro-corn.contractSpecs.html · https://cmegroup.com/content/dam/cmegroup/notices/clearing/2025/01/chadv25-041.pdf
