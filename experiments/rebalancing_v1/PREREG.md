# R232 rebalancing_v1: equal-weight cadence versus unchanged buy-and-hold units

- **Registry id:** R232
- Exploratory, 2026-10-20. Freeze before this lane reads cached market prices or calculates any new market statistic. Earlier six-coin and historical outcomes are known; there is no fresh holdout.
- Three fixed policy trials: DAILY, UTC Monday WEEKLY and UTC month-first MONTHLY equal-weight rebalancing, all relative to the previously untested fixed-unit buy-and-hold comparator. Monthly equals R229's existing passive benchmark and is not claimed as an independently invented strategy. No weekday, cadence, universe, date or parameter sweep.

## Method intake and source limits

Question: can periodic contrarian resetting to equal weights improve net results over letting the identical initial six-coin basket drift, after discovery-only risk scaling and full costs? Weak prior evidence does not bar this executable test. The mechanism can help under cross-asset reversals and lose under persistent trends; neither volatility reduction nor a source rating proves an arithmetic alpha.

Primary record: Hanicova and Vojtko, *Rebalancing Premium in Cryptocurrencies*, written December 10, 2021, posted December 14, revised December 20, 2021; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3982120 . Public primary abstract retrieved HTTP200 on 2026-10-20; it describes a 27-coin study and warns on trend following. Exact obtained HTML SHA-256: 797efecbd6be563f564b5b7127a5e7250465cb8dff38c8240dc1245d54e94b5f . No claim to have verified the full paper's code or results.

Discovery profile: https://quantpedia.com/strategies/rebalancing-premium-in-cryptocurrencies/ , HTTP200 on 2026-10-20, HTML SHA-256 4418e119a07887ca0e77ed31900a8406ea7b79f7604df2d0524e7b6abc082a8d . Its public page says transaction costs are not reported and its 100%-long/70%-short illustration chooses the short weight in sample. This lane is a bounded LONG-ONLY spot cadence adaptation, not that leveraged/gross-short portfolio, a dollar-neutral spread, a point-in-time universe replication or an independent validation of its ratings.

Duplication check: docs/QUANTPEDIA_RESEARCH_REVIEW.md mechanism3 proposes a larger perpetual/universe/long-short version; R229 uses monthly passive versus a trend signal, R230 weekly rotation changes the target selection, R231 partly approaches an unchanged trend target. None compares these three identical-universe rebalance schedules against fixed-unit buy-and-hold on a preregistered risk-adjusted primary screen. Monthly's prior use is explicitly disclosed.

## Fixed data and execution calendar

No new downloads, account credentials, trades, funding, model weights or short positions. Use ONLY the verified R229 Binance spot snapshot: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT; daily closes from 2021-01-01 through 2026-09-30, 2,099 daily rows/coin. Raw cache /workspace/quant-small-data/slow_trend_v1/raw. Reuse R229's bound loader to verify original frozen specification, data lock, manifest, every publisher checksum/ZIP and complete calendar; no missing values, substitutions or later publisher revisions.

Each scored return ending at C[i] may rebalance at C[i-1]. Fixed weights and calendar are known before that boundary, so no signal-derived arrival acceleration is involved. DAY i is the UTC date of the ending candle. DAILY resets before every scored daily return; WEEKLY resets before each UTC Monday return, using the preceding Sunday's close; MONTHLY before a UTC first-of-month return. All policies initialize at the boundary preceding their first scored return, even if off cadence. BUYHOLD initializes identical equal-dollar sleeves and keeps those UNITS and cash fixed thereafter until the common final liquidation. Do not reset buyhold at monthly/yearly boundaries or normalize its drifted weights.

Every split/cost/policy account starts units0,cash1; initial post-cost target is 1/6 each coin. Cadence targets reset to those same fixed weights; no momentum, volatility, chart, selection or market-data signal. Cash yield zero, no borrowing/leverage/shorts. Costs are proportional to changes from DRIFTED holdings, with exact R229 equation for desired post-cost weights w:

`NAV_after + c*sum(abs(w_j*NAV_after-current_dollar_holding_j)) = NAV_before`.

On the final split close, liquidate all remaining units and charge exits immediately to that day's return, including buyhold. Store held units before that exit so the scored price risk can be audited. Re-simulate every 1x/2x/3x account with one-way costs 0.0012/0.0024/0.0036 (assumed 10bp fee+2bp slippage at 1x), never subtract average costs from saved returns. These are assumptions rather than live fee/fill/capacity evidence.

Splits unchanged: discovery2022-01-01 through2023-12-31 (730days), validation2024-01-01 through2025-06-30 (547days), descriptive known_holdout2025-07-01 through2026-09-30 (457days). Positions restart each split rather than inheriting earlier performance; no warmup return is scored. All dates have been viewed by the project; the known_holdout cannot confirm this adaptation.

## Discovery selection and symmetric risk scaling

Select one of daily/weekly/monthly by greatest DISCOVERY Sharpe at 2x costs, with population SD and sqrt365. Exact ties favor MONTHLY, then WEEKLY, then DAILY, declared in that order before results. Zero/undefined candidate risk is INCONCLUSIVE. Buyhold is the comparator, not a fourth candidate. Unselected cadences remain saved diagnostics and cannot replace a failed primary.

From separate discovery1x unscaled selected and buyhold net returns, calculate sample-SD sp and sb. Set fixed capital fractions `scale_selected=min(1,sb/sp)`, `scale_buyhold=min(1,sp/sb)`. Thus both target the lower discovery risk and neither borrows/levers up. Nonfinite/zero SD is INCONCLUSIVE. Simulate selected again with equal weights scale_selected/6 at its original cadence; simulate buyhold again with only its initial equal weights scale_buyhold/6 and fixed cash thereafter. These SCALED accounts have full exact costs and final exits. Scales are fixed across all validation/known_holdout and every cost tier. Do not force realized prospective volatility equality; report mismatch and exposure drift.

Preserve all four raw policies plus selected_matched and buyhold_matched: six accounts per split/tier, 54 accounts and31,212 scored daily rows. Verify unscaled monthly reproduces R229's archived passive path for all splits and tiers, checking net,gross,cost fraction/dollars,turnover,exposure,NAV,cash and units on every day; discrepancy>1e-11 or a missing/extra date is INCONCLUSIVE. This overlap check is accounting evidence, not another discovery.

## Frozen primary decision and uncertainty

The sole primary is selected_matched minus buyhold_matched in VALIDATION at1x. PARTIAL exploratory evidence requires ALL:

1. validation1x Sharpe improvement >=0.15;
2. selected_matched validation2x mean net return >0;
3. selected_matched validation1x compound NAV max drawdown no worse than buyhold_matched;
4. paired validation1x mean-net-difference 30day-block95% interval lower endpoint >0.

Else NULL. Contract, missing-data or numerical failure is INCONCLUSIVE, not permission to add another model. A favorable unscaled result, other cost tier, unselected cadence or descriptive holdout may not rescue failure. PARTIAL would require new prospective registration before any edge validation, not deployment.

Use paired circular moving-block bootstrap:5,000replicates, primaryblock30days; nondecisive10/60day sensitivities also5,000 each. Seed20261020232+block. Uniform block starts within the547-day paired sample, wrap circularly, concatenate ceil(n/block) blocks, truncate to n; percentile2.5/97.5 endpoints. Historical reuse, three-policy selection and millions of prior project trials mean these conditional intervals are not corrected program-wide significance.

## Evidence and verification contract

Retain all54account metrics with day counts, additive meanbp/day, annual arithmetic mean, annual populationSDvolatility, populationSDSharpe, NW10t, compound NAVdrawdown including initial1, fee dollars, turnover, mean exposure, endingNAV, calendar coverage, mean gross and cost fractions, and cadence event counts. Save full daily net/gross/cost/units/cash/exposure/NAV paths as deterministic gzip CSV (LF before compression; gzip emptyfilename,mtime0), paired differences for allrawcadences versusrawbuyhold and the primary scaled pair, plus gross-minus-extra-cost decomposition by split/tier. Differences normalize each account by its own previous NAV and are not a common-notional hedge or actual tradable long-short PnL. Save scales, discovery scores, bootstrap/check/verdict, source/code/spec hashes, software versions and derived outputSHA256. Never overwrite; use a fresh --out for reproduction.

Synthetic checks must cover calendar timing, off-cadence initialization, unitsfixed buyhold, rebalancing drift, fees and final exits, no borrowing, reversal-mechanism example, exact monthly equivalence, no future-price leakage, train-only selection/scales/ties, deterministic compressed bytes/bootstrap, invalid inputs and output/source guards. Also independently check accounting with a distinct analytic solver, and byte-reproduce a fresh full run. Record evidence and limitations, especially survivors, known windows, traded-close proxies and assumed costs. No broad unregistered follow-up search.

## Bound executable and source bytes

Runner SHA-256: 4251e5d2c179da5ffa29c538b082a29745b6b2591ec11c57098022a36c73bf27
R229 runner SHA-256: 3f5b658dbb9bc6991e2c59507f457e6ff5c5720ef1228d1f2cc23cb83cbf724b
R229 fetcher SHA-256: 3377186f143bcc322d5e3b4bf67adca62edf8087700deef76cdcdfe0f0853f82
Statistics SHA-256: bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34
Preregistration helper SHA-256: 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508
R229 specification SHA-256: ad247ec8676b8ae817fea41a6a6a82303cedf298e49cdaaea35bfd55625f169b
R229 data manifest SHA-256: fc90fe4886608cbc090231374bcaf593082d54959bdc25de2ed1566d86fd42cd
R229 data lock SHA-256: 6abb626838107a3c6755f518f91b09011351a56d75dbf6bf13953275a08e9bda
R229 archived daily SHA-256: 4d879c17c61f3100e7af6ace0d5b5cef22eef7afca24941219f19139d16700fe
