# Implementation integrity review: labels, clocks and risk limits

Implementation follow-up: [opt-in gap-aware labels and holdout-price guard](TARGET_INTEGRITY_FIX.md) preserves the historical default and retains observed terminal losses. The complete-window recommendation below is an earlier proposal, not the revised policy: dropping terminal observations can select survivors. This original review remains a historical record; market-result impact is still unmeasured.

Read-only check of the project’s `claude/yo-9a1k5w` working branch on 2026-10-19. This note records code-path hazards and their synthetic reproductions for the active pipeline review. It does not edit code, change an active preregistration, or estimate how many historical results were affected. The checkout has no raw market-data archive, so prevalence and PnL impact are unknown.

## Findings to resolve before relying on confidence estimates

### 1. Multi-hour labels can bridge missing returns

[`lab/atlas.py::forward`](../lab/atlas.py) builds a prefix sum with `np.nan_to_num(r)`, then masks only a forward window’s *starting* row when `r` is NaN. A missing return inside a 4/12/24/72-hour outcome is therefore counted as zero while the label can remain finite. Default `nan_to_num` also substitutes finite extrema for infinities; invalid observations should be screened with `isfinite`, not only `isnan`.

**Synthetic reproduction:** return rows `[+1%, NaN, 0%]`, with a two-row horizon from row 0. The current prefix-sum expression returns `+1%`; a complete-window label must be missing because one of the two returns is unavailable. The reproduction passed against the expression in the checked-in implementation. No raw data were available to count affected windows.

**Review action:** maintain a cumulative count of invalid returns alongside cumulative sums, and set a horizon label to missing unless its entire return window is finite. Add tests for a gap at the start, inside, and end of each horizon, plus positive/negative infinity. Also confirm that daily aggregation, eligibility, and placebo paths all exclude the same invalid labels.

### 2. The R200 paper score starts before the signal is available

The checked-in [`scripts/forward_tick.py`](../scripts/forward_tick.py) sets `MARGIN = 12 minutes` and schedules an hourly row only after its candle has closed plus that margin. Binance USDⓈ-M klines are keyed by candle **open time**; the row for 13:00 closes at 14:00 ([official API schema](https://developers.binance.info/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data)). `compute_hours()` stores the signal under that 13:00 row while using its hourly close and feature rows. `score()` then defines the first return from `close[t]` to `close[t+1]`. That is the 14:00–15:00 close-to-close return, even though the 13:00 row’s signal is computed around 14:12.

This is an **unavailable entry-price assumption**, not proof that the signal uses future features: the first 12 minutes after the signal candle closes are already inside the scored return before the code would have the signal ready. Later performance can be higher or lower; the actual effect is unknown without arrival-time prices and a frozen accounting rule.

**Synthetic reproduction:** if the 14:00 close is 100, the 14:12 arrival mark is 101, and the 15:00 close is 102, the code’s close-to-close return is 2.00%, while the post-arrival markout is 0.9901%, a 1.0099 percentage-point difference for this invented path. This demonstrates the time alignment, not the effect on R200.

**Review action:** preserve current R200 journals and its frozen specification. For a future lane, record signal-ready time and use a price available after that time (preferably bid/ask or conservative executable quotes on the intended venue); align holding and exit timestamps to that entry. Do not retroactively repair the current paper series in place. Compare any new result with and without the delay only under a fresh preregistration.

The R200 specification also says that hours before its 2026-10-19 freeze were retrieved later from endpoints retaining about 28 days and are tagged `late`. The journal preserves that label, but `score()` does not filter those rows. This is disclosed in the frozen design and is not evidence of specification tampering; it means the pre-freeze segment is reconstructed history rather than a signal pipeline observed in real time. Keep late and on-time periods separate when describing operational validation. Binance’s public derivatives API distinguishes period timestamps from actual availability; code timestamp shifts and historical parity checks establish row alignment, not the first local receipt time of each feature ([official REST documentation](https://developers.binance.info/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data)).

### 3. Resampled bars can be partial without a coverage flag

[`lab/panel.py::resample`](../lab/panel.py) takes the last nonmissing close and `nansum`s volume inside a multi-hour block. If one or more hourly bars are absent, the result still looks like a complete (k)-hour bar. That may be an intentional treatment of no-trade or unavailable intervals, but the downstream feature cannot tell a full bar from a partial one. Sparse trades, data gaps and delistings have different meanings and should not be conflated.

**Review action:** calculate an hourly coverage count per block and expose or require it for features and labels. Define how no-trade hours differ from missing-feed hours; flag stale closes and reject bars below a prespecified coverage threshold. No data were available to estimate how often this occurs.

### 4. The scored return is a traded-close return, not mark, index or fill PnL

The current [`lab/panel.py`](../lab/panel.py) loads `klines_1h` closes as `close` and loads `premiumIndexKlines_1h` as the `premium` feature. Although [`lab/data.py`](../lab/data.py) declares archive kinds for `markPriceKlines`, the panel does not load mark-price candles or a spot/index-price series. [`lab/engine.py::forward_returns`](../lab/engine.py) calculates `close[t+1] / close[t] - 1` and subtracts a funding event. Therefore the portfolio target is Binance USDⓈ-M traded-perpetual close-to-close return with its modeled funding adjustment. It is not a mark-price liquidation path, an index/spot return, or an executable fill. The code documents close-to-close timing as its convention; the limitation is what that price family can establish, not an unannounced change to the convention.

The venue distinction matters: MEXC documents last, fair and index prices separately and exposes fair/index candle endpoints. Last price may move differently from the index, while liquidation references fair price. For future target-venue testing, preserve last trades, fair/mark, index, bid/ask and local receive time as separate series; label each return and fill by price family. Use actual arrival-side quotes or recorded fills for executable PnL, and fair-price paths for liquidation analysis. MEXC references: [ticker fields](https://www.mexc.io/api-docs/futures/market-endpoints/get-ticker-contract-market-data), [fair-price candles](https://www.mexc.co/api-docs/futures/market-endpoints/get-fair-price-candles), [index-price candles](https://www.mexc.co/api-docs/futures/market-endpoints/get-index-price-candles), and [price definitions](https://www.mexc.com/support/article/faq-on-index-price-fair-price-and-last-price-7950960183961).

**Synthetic price-family check:** last price 101→112 gives +10.8911%; mark price 100.5→111 gives +10.4478%; index 100→110 gives +10.0000%. The last/index basis widens from 1.00% to 1.82%, an 81.82 bp change. These invented prices show why the labels are not interchangeable; they do not measure Binance/MEXC basis or execution cost.

## Scope and safeguards already present

- `docs/AUDIT.md` and `R188` already describe a survivorship-aware, point-in-time eligibility design. `R200` uses current exchange metadata and explicitly treats delisted symbols as absent. Historical archive completeness still needs a symbol/contract lifecycle manifest; current exchange metadata cannot reconstruct every past listing or delisting episode.
- A separate [contract lifecycle review](CONTRACT_LIFECYCLE_INTEGRITY.md) describes the gap between economic-asset lineage and venue-contract continuity, including forced settlement and replacement listings. It identifies a path to audit; historical frequency and effect remain unmeasured.
- R205 tests Gate positioning features against **Binance** outcomes on Binance eligibility, costs and funding. Its own preregistration says that Binance outcomes on that window are already known. This is a cross-data-source discovery comparison, not evidence that Binance signals transfer to MEXC returns or fills.
- A future cross-venue join must use signal receipt/decision time, not just a matching exchange bar label. In a synthetic example, a feature window ends at 14:05, arrives at 14:07, and MEXC quotes are 100 at 14:05, 102 at 14:10, and 104 at 15:00. Matching on event time reports 4.00%; entering at the first quote after receipt reports 1.9608%. This is an invented as-of-join example, not an estimate of venue slippage. Use an explicit max-age rule and preserve local receive timestamps.
- The confidence review already flags that portfolio return statistics do not model contract-level maintenance margin, fair-price liquidation, or the path of a short squeeze. Hourly marks—and especially daily account-return simulations—cannot reconstruct intrabar liquidation. MEXC’s official [liquidation FAQ](https://www.mexc.com/support/article/faq-on-liquidation-for-futures-trading-8123281969561) and [margin guide](https://www.mexc.com/support/article/mexc-margin-calculation-guide-312054740132052992) use fair-price and mode/tier-specific rules; a venue-specific risk replay needs those rules plus mark-price and funding paths.

## Tests and limits

Four deterministic Python fixtures were run with invented values: the interior-gap prefix-sum case, the 14:00/14:12/15:00 timing case, the 14:05/14:07/14:10 cross-venue as-of join, and the last/mark/index return comparison above. They reproduced the identified discrepancies. These are implementation/arithmetic reproductions, not unit tests of a repaired function, market statistics or strategy backtests. The repository’s full unit suite was not rerun for this documentation-only review; the earlier attempt recorded 61 passes and 12 environment errors due to missing `numba` and `pyarrow`.

The immediate implication is to treat the associated historical multi-hour labels and current live-paper markout as **under review** until a code owner verifies the exact active branch, confirms whether these semantics were intended, and assesses affected observations. This note recommends review; it does not declare R200 invalid or quantify a correction.
