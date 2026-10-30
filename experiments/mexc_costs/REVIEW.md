# R224 depth-field schema audit — 2026-10-23

This note corrects an earlier draft review that said R224 had read the wrong depth field. That conclusion was premature.
The existing frozen R224 specification, hash sidecar, journal rows and registry history were not changed or recomputed.

The current MEXC REST and WebSocket pages describe a row as `[price, order_count, order_quantity]` ([REST](https://www.mexc.com/api-docs/futures/market-endpoints/get-contract-order-book-depth), [WebSocket](https://www.mexc.com/api-docs/futures/websocket-api/order-book-depth)). The older official contract API page instead describes the second value as contract volume ([legacy contract docs](https://mexcdevelop.github.io/apidocs/contract_v1_en/#get-the-contract-s-depth-information)). The labels in the current REST/WS prose appear inconsistent with the live payload.

I checked small, read-only public Futures responses on 2026-10-23:

- `GET /api/v1/contract/detail?symbol=BTC_USDT` returned `contractSize: 0.0001`.
- REST depth returned `[81460.7, 54145, 4]` at the best ask. Treating field 1 as contracts gives 5.4145 BTC (about $441,069); treating field 2 as contracts gives 0.0004 BTC (about $32.58).
- A WebSocket `push.depth.full` sample returned ask `[81393.6, 33284, 7]`; field 1 gives 3.3284 BTC (about $270,878), while field 2 gives 0.0007 BTC (about $56.98).

The values and MEXC's own `contractSize` therefore support the live row layout `[price, contract_quantity, order_count]`, matching R224's use of the second element as quantity and the legacy official docs. This is a bounded schema check, not a reanalysis of R224's recorded costs. It does not validate every R224 assumption or make its snapshots execution-time fills; fees, spread, sample timing, coverage and hidden/vanishing liquidity still need their stated limitations.

`lab/tape.mexc` used the same field mapping for M264. This audit found no basis to invalidate its size columns on this issue. The shared decoder now validates the three-field shape and fails closed on malformed snapshots; it does not change the historical bytes already captured or compacted.

A separate R310 collector draft was never registered, frozen, or run. It was discarded because R224 already uses the live quantity field and a second collector would duplicate the same measurement. No R310 sample or outcome was produced. The public schema probes above are the only new market reads in this review; no trade or credential was used.
