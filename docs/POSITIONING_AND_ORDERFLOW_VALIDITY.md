# Positioning, open interest and signed flow: feature definitions before prediction

Originally reviewed 2026-10-19; literature addendum 2026-10-29. This note distinguishes what the feeds measure, what the literature can transfer, and the integrity checks needed before treating a feature as predictive. It reports no new project return result.

## Similar names can mean different market objects

Binance USDⓈ-M exposes at least three different long/short measures: a global account ratio; a top-trader account ratio that counts accounts once; and a top-trader position ratio that compares position quantities. “Top trader” means the top 20% by margin balance, not proven profitability, and cohort membership can change. Keep the three series separate. Open interest is the outstanding contract stock, not signed demand: opening and closing counterparties can make OI rise, fall or stay flat while substantial trading occurs. Record contract count and notional separately when normalizing across coins ([Binance USDⓈ-M market-data docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics)).

Signed executed flow is different again. Binance aggregate trades expose whether the buyer was maker, allowing an aggressor-side reconstruction; interval taker-buy/sell aggregates are a coarser measure. MEXC's public trade feed documents buy/sell and open/close fields, but its public docs do not establish the buy/sell field as a maker/taker aggressor flag. Its public WebSocket aggregates deals by default; `compress=false` disables that aggregation. Validate the field against quotes and prints before naming it signed flow ([Binance aggregate trades](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Compressed-Aggregate-Trades-List); [MEXC deal stream](https://www.mexc.co/api-docs/futures/websocket-api/deal)).

Liquidation messages are a censored event feed, not a position census. Binance's force-order stream sends at most the latest liquidation order for a symbol during each 1,000 ms interval. No event in the stream does not establish that no liquidation occurred. MEXC's public market-data docs reviewed here do not expose a market-wide liquidation stream; account-history endpoints describe the user's own orders ([Binance force orders](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Liquidation-Order-Streams); [MEXC market endpoints](https://www.mexc.co/api-docs/futures/market-endpoints/get-recent-trades)).

## Evidence is real but does not validate this project's five-minute perp features

The clearest positioning evidence in the reviewed literature is lower-frequency and institutionally classified. Baur and Smales report timing information in weekly CFTC trader categories for CME Bitcoin futures, especially changes in leveraged-money short positions. Those observations are taken Tuesday and normally released Friday, so the Tuesday record cannot be used as if it were known Tuesday. Dunbar and Owusu-Amoako also find predictive relations using CFTC-based trader-behavior measures. Neither study establishes that Binance's margin-balance-ranked ratios predict MEXC altcoin perpetual returns ([Baur & Smales 2022](https://doi.org/10.1002/fut.22332); [Dunbar & Owusu-Amoako 2023](https://doi.org/10.1016/j.jbef.2023.100812); [CFTC release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm)).

Recent cross-asset order-flow evidence aggregates buyer-initiated less seller-initiated trades across hundreds of exchanges and multiple fiat quote currencies. It supports testing signed transaction flow as its own feature family; it cannot validate exchange positioning ratios, venue-specific execution, or the five-minute project feature ([Anastasopoulos et al. 2026](https://doi.org/10.1016/j.finmar.2026.101047)). OI evidence is more directly useful as a possible activity or risk-state measure. It should be tested against price, volume, funding, basis and signed flow rather than given a directional interpretation by definition.

## A distinct weekly CFTC option-position result (2026-10-29)

Shen, Li and Luo's 2026 Finance Research Letters paper, [“Option positions, non-momentum trading, and Bitcoin
futures returns”](https://www.sciencedirect.com/science/article/pii/S1544612326008287), uses weekly CFTC CME Bitcoin
data (2020-01-21 to 2025-03-04). The accessible publisher abstract/search extract reports that asset-manager
option-only position changes predict a second-week-ahead non-momentum component, with futures returns leading the
position changes. This is a forecast association, not causal flow or net trading PnL. The publisher and author
repository pages returned 403 in this review, so the full methods and portfolio construction were not independently
audited or reproduced.

The CFTC says observations are taken Tuesday and generally released Friday, normally at 3:30 p.m. Eastern; holidays
can change the schedule. It also cautions that deriving options-only figures by subtracting futures-only from
combined reports can lose information about spreads. Thus this source is too slow for an intraday lane and must use
the actual public release time. It is related to blocked M100's weekly CFTC timing idea, but the asset-manager options
measure is not the same as leveraged-money positioning. Check M100's existing source/data scope before considering
any new queue item; this paper alone does not earn a lane.

Sources: [publisher record](https://www.sciencedirect.com/science/article/pii/S1544612326008287),
[Hull repository record](https://hull-repository.worktribe.com/output/5680567/option-positions-non-momentum-trading-and-bitcoin-futures-returns),
and [CFTC COT descriptions and release timing](https://www.cftc.gov/es/node/128971).

## Timestamp and archive risks

Binance's REST documentation limits OI statistics, long/short ratios and taker buy/sell history to roughly the latest 30 days; OI intervals with no trades may be omitted. Endpoint timestamp labels differ: taker aggregates are described as period-start stamped, while several OI/ratio endpoints use period-end labels. Store the documented interval boundary and local receipt time, not only the returned timestamp.

There is also an unresolved **user-reported archive concern**, not a confirmed Binance notice: public-data issue #491 alleges a `create_time` convention change on 2026-06-25 that shifts five-minute metrics and duplicates midnight labels across adjoining daily files. The reporter describes comparison against trades and OI polls, but Binance has not confirmed the cause or the change. Reconstruct candidate windows from underlying aggregate trades and independently compare live REST snapshots before relying on affected archive rows ([Binance REST docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics); [public-data issue #491](https://github.com/binance/binance-public-data/issues/491)).

For MEXC, current ticker data include OI (`holdVol` in contracts) and the public deal stream provides a prospective flow-capture path. The reviewed docs do not provide a historical public OI or long/short-ratio series. This means Binance-to-MEXC feature transport and MEXC-native prospective collection are different tests ([MEXC ticker](https://www.mexc.co/api-docs/futures/market-endpoints/get-ticker-contract-market-data); [MEXC candles](https://www.mexc.co/api-docs/futures/market-endpoints/get-candlestick-data)).

## A fair, point-in-time test

Prespecify each measure separately: top-position ratio, top-account ratio, global account ratio, OI quantity/value change, taker imbalance, trade-derived signed volume, or liquidation-event count. For flow, one possible normalized measure is `(buy_volume - sell_volume) / (buy_volume + sell_volume)`; it is undefined when total volume is zero. For OI, define units and scaling before comparing symbols. Do not infer zero from a missing row or forward-fill stale values as fresh data.

Record source venue, product, symbol, raw interval, units, event time, window start/end, API timestamp, first local receipt time and whether the interval is complete. A five-minute feature can only predict a strictly later return window after it is available; using same-window price movement embeds contemporaneous information. Hold the eligibility universe and contract identifiers point-in-time, including renamed/delisted contracts.

Check feature integrity before testing incremental value. Rebuild Binance taker imbalance from aggregate trades; compare with the interval feed. Check OI changes against trade volume with measured reporting delays. Validate the meaning of MEXC trade-side codes against book changes. Then compare a price-history baseline and market-only baseline with each feature block added separately, controlling for lagged return, volatility, funding and basis. Score direction separately from volatility/tail risk and executable portfolio PnL. For cross-venue claims, hold out venues or instruments; do not label a Binance feature result as MEXC evidence.

My evidence-weighted starting point is signed executed flow as a directional hypothesis, while OI/positioning ratios are initially more defensible as crowding or risk-state variables. Liquidation feeds are incomplete stress indicators. This is a test priority, not an established ranking of project alpha.

No new market data or backtest was run for this note. The Binance timestamp issue remains a report pending independent reproduction.

## References

- [Binance USDⓈ-M market-data documentation](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics).
- [Binance public-data issue #491: reported `create_time` labeling concern](https://github.com/binance/binance-public-data/issues/491).
- Baur & Smales (2022), [Trading behavior in bitcoin futures: Following the “smart money”](https://doi.org/10.1002/fut.22332).
- Dunbar & Owusu-Amoako (2023), [Predictability of crypto returns: The impact of trading behavior](https://doi.org/10.1016/j.jbef.2023.100812).
- Anastasopoulos et al. (2026), [Order flow and cryptocurrency returns](https://doi.org/10.1016/j.finmar.2026.101047).
- [MEXC futures deal stream](https://www.mexc.co/api-docs/futures/websocket-api/deal).
- [MEXC futures ticker](https://www.mexc.co/api-docs/futures/market-endpoints/get-ticker-contract-market-data).
