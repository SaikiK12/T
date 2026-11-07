# R229 slow_trend_v1: bounded spot trend ensemble screen

Exploratory study, 2026-10-19. Freeze this specification and runner/fetcher hashes before collecting history or computing market statistics. R227 is reserved for Kronos and R228 for the allocation diagnostic. This is a small, fixed-universe spot adaptation of a published model, not a full paper replication or a MEXC-perpetual confirmation.

- **Registry id:** R229

## Question and known evidence

Does the fixed slow long/cash ensemble below improve validation performance over a passive portfolio of the identical coins after modeled transaction costs and matching training risk? R185's short-horizon conditional bins, R203's intraday momentum and R222's cross-sectional skip-month signal do not settle this question. Prior project research has already viewed these calendar regimes, and the public paper has influenced this choice. Every historical split is exploratory, including the window named known_holdout. No fresh confirmation is possible here.

Source: Zarattini, Pagani and Barbon, *Catching Crypto Trends*, cover dated 9 April 2025, PDF https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf . SHA-256 `9fc2811b2c8062cd1fae92c3f1464d3883fdb7cae588604dea34c20d6742945d`. The upload path and SSRN revision dates differ from this cover date; this exact PDF supplies the rules. Quantpedia is a discovery source, not an independent replication.

## Bounded data collection and contract

- Symbols, fixed before collection: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, Binance SPOT only. These six surviving liquid coins are selected by the published evidence and do not represent a survivorship-free altcoin universe.
- Daily 1d OHLCV monthly files, January 2021 through September 2026 inclusive: 69 months times six symbols = 414 archives. URL: `https://data.binance.vision/data/spot/monthly/klines/{symbol}/1d/{symbol}-1d-{YYYY-MM}.zip`, with publisher SHA-256 from the adjacent `.CHECKSUM`.
- Hard download bounds: at most 5 MiB of ZIP payload in total and 64 KiB per ZIP, maximum four concurrent requests; no API keys, bulk hourly/trade data or model weights. Cache mismatches fail closed; never replace a conflicting file silently.
- Fetcher: `scripts/fetch_trend_daily.py`.
- Runner: `scripts/run_slow_trend.py`.

Fetcher SHA-256: 3377186f143bcc322d5e3b4bf67adca62edf8087700deef76cdcdfe0f0853f82
Runner SHA-256: 3f5b658dbb9bc6991e2c59507f457e6ff5c5720ef1228d1f2cc23cb83cbf724b

- Raw cache: `/workspace/quant-small-data/slow_trend_v1/raw`; manifest `experiments/slow_trend_v1/results/data_manifest.json`. Record URLs, collection time, verified publisher/observed hashes and sizes; publisher checksums identify the source revision obtained. After collection, parent pins the manifest hash in `experiments/slow_trend_v1/DATA.sha256` before the runner opens prices. Every runner invocation verifies that lock and all archive bytes. Preserve the manifest and hashes in the PR; do not commit bulky raw cache.
- Official spot archive columns are the twelve Binance kline fields. Timestamps are milliseconds before 2025 and microseconds from January 2025; normalize both open and close timestamps to epoch milliseconds. Expected row per UTC date is open=00:00 and close=next midnight minus 1 ms. Require exactly one complete daily candle for each symbol/date from 2021-01-01 through 2026-09-30 (2,099 rows each), without gaps, duplicates or fills. Validate finite positive OHLC, high>=max(open,close), low<=min(open,close), high>=low and nonnegative finite volume/quote volume. Recognized header rows may be removed; unexpected schemas fail.
- Missing archive, checksum mismatch, incomplete calendar or invalid prices produces INCONCLUSIVE. No alternate venue, symbol list, missing-value repair or shortened window is chosen after data collection. Checksums prove downloaded source identity, not historical absence of exchange revisions.

## Fixed trend model

Nine component horizons in CALENDAR daily observations: 5,10,20,30,60,90,150,250,360. For each symbol/horizon, U[t] and D[t] are max/min of the last n CLOSES including C[t]; M[t]=(U[t]+D[t])/2. Before n closes, the component is flat.

At each close t: if C[t]==U[t], be long (entry has precedence over exit, including ties); a new entry initializes the stop for t+1 to M[t]. Otherwise an existing long exits when C[t]<=the stop fixed for day t. Otherwise retain the preceding position. An existing retained long updates its next-day stop to max(previous stop,M[t]). Exits clear the old stop; a later entry resets it. Do not use today's midpoint to trigger today's exit.

Signal s[t] is the arithmetic mean of the nine binary long indicators. The primary `trend_vol` target per coin is `s[t] * min(1,0.25/vol90[t]) / 6`, where vol90 uses the trailing 90 simple close-to-close returns through t, sample std ddof=1, annualized sqrt365. Zero volatility yields a capped multiplier of one; unavailable vol yields zero. Diagnostic `trend_plain` uses `s[t]/6`.

The explicit adaptations are fixed six-coin exchange prices instead of the paper's monthly point-in-time aggregated universe, a 100% per-coin sleeve cap instead of 200%, no 20% volatility-rebalance band, simple returns with ddof1/sqrt365, and the extra execution delay below. Neither variant may be retuned or replaced after outcomes. Count two candidate trials (one primary and one diagnostic); disclose the nine literature-selected component horizons rather than claiming they are independent discoveries.

## Timing, execution and self-financing accounting

For the daily return ending at C[i], execute at C[i-1] using only target[i-2]. Thus the signal is known a full daily bar before the modeled entry boundary. These are traded-close price proxies with assumed costs, not recorded fills.

Use long-only spot units and cash, no borrowing/leverage/shorts, cash interest zero. Before each daily trend rebalance, mark existing units at C[i-1]. Desired weights are fractions of POST-COST NAV; solve `NAV_after + c*sum(abs(target_j*NAV_after - current_dollar_holding_j)) = NAV_before`, c=0.0012 at 1x (assumed 10 bp fee plus 2 bp slippage one way), then update units/cash. A bisection or equivalent exact self-financing solver must preserve nonnegative cash and invested fraction <=1. Trade costs use drifted holdings, not yesterday's target weights. At each split's final close, liquidate all positions and charge that exit to the final day.

Rerun the account from cash=1 for EACH split and each 1x/2x/3x cost tier (12/24/36 bp one way); include initial entry, all rebalances and final exits. Compute net returns from consecutive NAVs, mark-to-market gross contribution and transaction-cost fraction; no funding applies to spot. The fee/slippage numbers are frozen assumptions, not verified account-specific schedules or capacity evidence.

Passive benchmark: same six coins, equal post-cost weights summing to one, rebalanced before the return on each UTC month's first day and at split initialization; otherwise allow units/weights to drift. Charge the identical cost model and final exit. It needs no signal delay because its universe/weights are known ahead of time.

Score discovery 2022-01-01 through 2023-12-31, validation 2024-01-01 through 2025-06-30, and descriptive known_holdout 2025-07-01 through 2026-09-30. Calendar 2021 supplies indicator warm-up only. Targets and stops continue through split boundaries using past closes, but accounts start from cash on each split. No transaction during warm-up is scored.

## Primary comparison and inference

After discovery simulation at 1x only, set fixed `k=min(1,std(discovery trend_vol net)/std(discovery passive net))` using sample std. Fail if either std is undefined/zero. Simulate a separate monthly passive benchmark with total target weight k (cash for the remainder), with k fixed for every validation/known_holdout and every cost tier. Do not match prospective or validation realized risk ex post. Report the scale and realized risk mismatch.

The sole screen is positive if trend_vol has validation Sharpe at least 0.15 above this risk-matched passive benchmark at 1x, validation additive mean net is positive at 2x, validation compound drawdown is no greater than the matched benchmark at 1x, and the paired validation bootstrap 95% lower bound of mean(trend_vol net - matched passive net) is above zero at 1x. A positive screen is PARTIAL exploratory evidence; otherwise NULL. The unscaled trend_plain diagnostic and the known_holdout cannot rescue a failed primary.

Paired circular moving-block bootstrap of validation daily return differences: primary length 30 days, 5,000 replicates, seed `20261019229 + block_length`, percentile 2.5/97.5 interval; report lengths 10 and 60 as nondecisive sensitivity. Uniformly sample block starts, wrap within the split, concatenate ceil(n/block) blocks and truncate to n. This is conditional historical uncertainty, not program-wide selection correction or proof of a fresh edge.

For every strategy/benchmark, split and cost tier report mean bp/day, annualized arithmetic mean, population-std Sharpe sqrt365, NW(10) t, compound NAV maximum drawdown including initial NAV, total costs, turnover, mean exposure, ending NAV and calendar coverage. Save full daily returns/positions/cost summaries and paired differences. Also report discovery-fixed scale, source/code/spec hashes, software versions and the deterministic verdict. No parameter sweeps, alternate horizons, cost assumptions, universes or extra post-result filters. Register two trials and preserve null results.

Outputs use LF CSV bytes and output SHA-256 hashes in `run_manifest.json`. The default output folder is `experiments/slow_trend_v1/results/`; only the collection manifest may already exist. A rerun must use `--out` with a fresh directory; never overwrite prior study results. Unexpected numeric/validation failures are INCONCLUSIVE, not an invitation to change the frozen model.
