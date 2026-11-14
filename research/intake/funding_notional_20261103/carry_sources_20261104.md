# Public contract and depth mechanics checked for R402, 2026-11-04

Targeted official web excerpts only; no whole-document, account-access, fill,
strategy or return claim. No login/private endpoint or access bypass. Other
sections, future source drift and executable mechanics remain unqualified.

| Official source | Exact read scope | Extracted mechanics |
|---|---|---|
| [MEXC domain announcement](https://www.mexc.com/announcements/article/futures-api-access-domain-update-17827791532974) | Announcement body, domains and dates | api.mexc.com announced enabled January12,2026, old-domain retirement planned January19; features/parameters described as unchanged. This does not prove retirement happened: R401 received HTTP200 on the old host. Use the announced host, with no fallback after failure. |
| [MEXC Futures docs](https://mexcdevelop.github.io/apidocs/contract_v1_en/) | Public-authentication statement, detail parameters/fields/rate, REST depth tuple/units/version/timestamp | Detail supports symbol filtering, one request per five seconds. contractSize converts contracts to base quantity; volUnit is a contract increment. REST depth describes price/contract-volume/order-count triples, version and millisecond timestamp. Raw or successful enveloped REST shapes are explicitly accepted; missing triples refuse. apiAllowed is reported separately from owner eligibility. WebSocket semantics were not qualified. |
| [KuCoin contract detail](https://www.kucoin.com/docs-new/rest/futures-trading/market-data/get-symbol) | Endpoint, permission, weight, response fields/example | Public /api/v1/contracts/{symbol}, weight3; exact symbol/base, USDT quote/settlement, open perpetual, multiplier and lot required. Advertised fees are not owner fees. |
| [KuCoin partial depth](https://www.kucoin.com/docs-new/rest/futures-trading/market-data/get-part-orderbook) | Public Futures depth20 endpoint, permission, weight, response structure | Public /api/v1/level2/depth20?symbol=..., weight5; symbol, sequence, price/size pairs and raw ts. No time-unit or clock synchronization is inferred from digit count. Private unified-account endpoints are outside scope. |
| [KuCoin contract quantities](https://www.kucoin.com/support/26685254904601) | Contract quantity, multiplier and position-size definitions | Contracts times multiplier gives base position size. R402 converts units before matching the rational least common multiple of both base lot increments. This establishes no owner access, minimum notional, fee, latency or future closing cost. |

R402 is a separate engineering successor to R401's incomplete inventory response.
All28 published cohort rows remain; only MEXC/KuCoin public sources are requested.
R401's2MiB remains charged inside the same accumulated5MiB allowance. No new
predictive method, historical outcome or alpha promotion follows from these docs.
