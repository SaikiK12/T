# C11 quarter-hour signed flow: a data gate, not a new claim

Reviewed 2026-10-19. This is a scoped follow-up to the existing C11 in `docs/CLAIMS.md` and the candidate already listed in `docs/CONCEPTS.md`. It is not a new claim or preregistration, does not authorize a large historical download, and contains no project return test. The remaining gap is data feasibility and a clean project replication, not discovering that the paper exists.

## What is still untested

R226 tested six unsigned 24-hour trade-count and trade-size books; its count surge was almost the same feature as quote volume. Those nulls do not test aggressor direction. The C11 feature measures signed aggressor flow during the first ten seconds after quarter-hour boundaries.

Kim and Hansen's 2026 arXiv preprint studies BTC, ETH, XRP, SOL, DOGE, and ADA USDT perpetuals on Binance from 2021-01-01 to 2024-10-31. The main specification pools :00/:15/:30/:45; Appendix A.11 separates :00 and finds the :15/:30/:45 phase carries stronger medium-horizon content. The existing C11 claim includes all four phases. Testing only :15/:30/:45 would be a narrower paper-motivated follow-up, not an exact replication, and must be frozen as such before any new outcomes.

Keep the paper's two evidence types separate. Its approximately 0.5 bp opening-return finding comes from a separate out-of-sample quarter-hour forecasting exercise. Its 4–12-hour order-imbalance regressions and 16.9 bp interquartile contribution of the decomposed public-signal component use the full 2021–2024 sample; they are in-sample associations, not out-of-sample trading results. The study is a preprint on a small major-coin universe, not evidence of a net strategy on this project or of MEXC altcoin fills.

The repo's `CONCEPTS.md` already records the approximately 0.5 bp opening-return result against about 5 bp taker costs. The paper's 16.9 bp figure sometimes cited for the 12-hour horizon is the interquartile contribution of a **decomposed public-signal component**, not the raw 10-second imbalance and not net portfolio PnL. These quantities have different definitions and sample status; neither establishes a tradable edge.

The paper's order-imbalance variable is volume-normalized signed quantity, not a verified MEXC trade PnL signal:

$$
OI_t=\frac{\sum_{k\in t} q_k D_k}{\sum_{k\in t}q_k},\quad
D_k=+1\ \text{if buyer is taker},\ -1\ \text{if seller is taker}.
$$

For Binance USD-M aggregate trades, `isBuyerMaker=False` means the buyer was taker; `True` means the seller was taker. Preserve the exact event time and use the paper's volume-based definition for replication. Do not silently substitute quote-notional flow, sum several windows, or search other transformations in the same lane.

## Proposed sequence

1. **Feasibility only:** verify the chosen source's event-time, maker-side semantics, timestamp precision, symbol coverage, and 10-second completeness. Distinguish a complete interval with zero trades from a collector/feed gap: the former is a real zero-activity observation but makes the ratio's denominator zero, while the latter is missing data. Preserve an explicit zero-trade indicator, preregister whether the signal abstains for those windows, and report their frequency. The repository currently has hourly klines and coarser taker metrics, not the required 10-second trade tape.
2. **Data gate:** historical Binance `aggTrades` archives are large; `AGENTS.md` requires the owner's explicit approval before such a download. No download was made or authorized here. Without that approval, build a forward-only capture first, freeze its collector and clock/receipt-time checks, and wait for an uncontaminated sample.
3. **Forecast test:** only if the data gate passes, register one exact feature window, the volume-normalized formula above, one 12-hour outcome horizon, and the six named contracts. Compare with a fixed past-only/market baseline and at most one phase-shift placebo fixed before collecting outcomes; treat the old 2021–2024 paper dates as exploratory. Use one family-level statistic with date blocks shared across all six assets because the horizons overlap and shocks are common.
4. **Trading test only after forecast skill:** map the frozen score to a single fixed position rule in a separate lane. Price arrival-time fills, fees, spread, depth, funding, and turnover at an owner-stated notional. Require positive net evidence at 1x and 2x costs, report 3x, and do not call a book-walk or markout an executed fill.

The preprint's 12-hour appendix reports a 16.9 bp interquartile effect for its public-signal component after a two-stage decomposition; this is not the raw feature's guaranteed return and is not net of the project's costs. R224's two-snapshot MEXC $10k API estimate is about 9.6 bp one way, and the listed API taker fee alone is 8 bp per side. Those quantities use different samples and definitions, so this comparison is only a warning that the gross forecast scale may be small relative to two-sided execution costs.

## Current Binance capture and repair limits

The current Binance USDⓈ-M [Compressed/Aggregate Trades List](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Compressed-Aggregate-Trades-List) documentation, checked 2026-10-19, adds an important limit to the data gate. `/fapi/v1/aggTrades` aggregates fills at the same price and taking side within 100 ms. It exposes aggregate ID `a`, first/last trade IDs `f`/`l`, event time `T`, and `m` (whether the buyer was the maker). In particular, `m=true` means the seller initiated; `m=false` means the buyer initiated, matching the paper's side convention.

The endpoint only serves trade history from the previous 48 hours, returns at most 1,000 rows per request, and requires a `startTime`–`endTime` interval shorter than one hour. It supports inclusive `fromId` pagination; the docs caution against combining time bounds with `fromId`. Therefore a capture must reconcile any suspected gap while it is still inside the 48-hour window, paginate rather than accept a capped response as complete, and mark unreconciled signal windows missing. Once a gap ages past 48 hours, this endpoint cannot repair it; that window must not be reclassified as a genuine zero-trade interval.

The current response also distinguishes `q` (aggregated quantity) from `nq` (quantity excluding trades involving retail-price-improvement orders). A prospective study must freeze which quantity it uses before capture and record that source-definition choice: silently switching between `q` and `nq` would change the signal. Use aggregate IDs to order and deduplicate messages, but validate completeness against the bounded REST backfill rather than treating an apparently monotone ID sequence as proof that no feed events were missed. These are current-feed engineering constraints, not evidence for the predictive claim.

## Falsification and scope

Do not proceed if the event feed cannot establish complete 10-second windows or accurate aggressor side. Reject a forecast claim if the frozen signed-flow model fails to improve the declared future-return score against its baseline on genuinely prospective data. Reject a trading claim if net results fail the predeclared cost stress or depend on zero/stale fills. A positive Binance forecast would still require a separate transfer and execution test before making any MEXC or small-altcoin claim. Since C11 is already in the claim ledger, update that existing research thread rather than creating a duplicate claim or implying the idea was previously absent.

## Source

- Kim and Hansen (2026), [The Quarter-Hour Effect: Periodic Algorithmic Trading and Return Predictability in Cryptocurrency Futures](https://arxiv.org/abs/2607.09426), v2, posted 2026-07-16. The reported 16.9 bp figure is from the 12-hour interquartile effect of the decomposed public-signal component; it must not be read as a net trade return.
- Binance, [Compressed Aggregate Trades List](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Compressed-Aggregate-Trades-List).
- Project-specific cost/execution limits: [MEXC execution and account risk](PERP_EXECUTION_AND_RISK.md) and [R224 preregistration](../experiments/mexc_costs/PREREG.md).
