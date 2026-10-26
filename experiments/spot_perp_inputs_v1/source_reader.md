# R324 — bounded MEXC spot source contract reading

Read-only source subtask, 2026-10-26 UTC. This is a source contract note, not an acquisition of market/account/history data or evidence of a profitable result. `AGENTS.md` and `docs/ROOM.md` were read. The parent owns the live issue #7 claim, implementation, preregistration/freeze and any separately authorized fresh public capture. Nothing here changes a canonical/frozen module or journal.

## Acquisition and exact scope

Six ordinary static GETs, 30,341 response-body bytes combined, maximum response 21,731 bytes, acquisition wall 7.460440 seconds. Bounds were 6 GETs / 2 MiB combined / 512 KiB per response / 90 seconds; all respected. TLS verified through inherited normal proxy. Current cloud runtime reports enforced unrestricted HTTP policy, no VPN, no configured credentials; no credential values inspected. No redirects, retries, login, proxy bypass, orders, market/history/account/RPC calls, or historical data downloads. No further requests are authorized by this subtask.

| Source | Result and received scope | Actually read | Unread / limitation |
| --- | --- | --- | --- |
| `https://api.github.com/repos/mexcdevelop/websocket-proto/git/trees/main?recursive=1` | HTTP 200; complete 4,352-byte metadata tree, `truncated=false` | Full small path/blob manifest, for locating the two protos | No other blob bodies were acquired; a full repository was not downloaded |
| `https://api.github.com/repos/mexcdevelop/websocket-proto/git/blobs/bd77f48b6ed95efa15f755613323f64f06970e55` | HTTP 200; complete 3,063-byte API JSON containing 2,008 decoded proto bytes | Entire `PushDataV3ApiWrapper.proto`, including comments, imports and every field | Imported message definitions other than the separately acquired depth message were not read |
| `https://api.github.com/repos/mexcdevelop/websocket-proto/git/blobs/5a31293f1d5ad998e98f2f68271538015d80ef29` | HTTP 200; complete 1,024-byte API JSON containing 531 decoded proto bytes | Entire `PublicLimitDepthsV3Api.proto` | No live frame, generated decoder implementation or deployment correspondence checked |
| `https://www.mexc.com/api-docs/spot-v3/websocket-market-streams` | HTTP 200; complete 21,731-byte base/index HTML; Last-Modified `Fri, 09 Oct 2026 10:39:32 GMT` | Full main prose and navigation link targets; parsed visible text retained | Linked protocol/subscription/partial-depth/local-book pages were not acquired/read; script/style bundle contents not read |
| `https://www.mexc.com/api-docs/spot-v3/market-data-endpoints` | HTTP 503; complete 91-byte failure body | Full error: upstream connect timeout before headers | No exchangeInfo/depth contract obtained; no retry or alternate request |
| `https://www.mexc.com/api-docs/spot-v3/account-endpoints` | HTTP 404; complete 80-byte error JSON | Full not-found response | Guessed path failed; no account or fee documentation obtained; no account API call |

Every actual response URL, start UTC, status, permitted headers, exact byte count, SHA-256 and cap/completeness result is in `receipts.json`. `complete=true` for error responses means a complete error body, not successful source acquisition. The failed docs paths cannot support their intended endpoint claims.

## Exact version identity

The supplied official repository was addressed as `mexcdevelop/websocket-proto`. The mutable `main` tree request returned Git **tree** `0c9c4f35dd0fadc3a46a350e909a93379d81e811`, pinned tree URL `https://api.github.com/repos/mexcdevelop/websocket-proto/git/trees/0c9c4f35dd0fadc3a46a350e909a93379d81e811`.

This is a tree identifier, **not a commit**, release, deployment ID or proof that the venue currently emits this exact wire schema. No commit metadata was requested. The base documentation retrieved here does not itself link this repository; official-repository provenance is supplied by the parent's task, while the content identities were independently validated below.

| File | Git blob identity in returned tree, API and local recomputation | Decoded SHA-256 |
| --- | --- | --- |
| `PushDataV3ApiWrapper.proto` | `bd77f48b6ed95efa15f755613323f64f06970e55` | `1869bbb700319ea4a0844ec11860dade0868c6a3a444dd3db6455db3c578c4fd` |
| `PublicLimitDepthsV3Api.proto` | `5a31293f1d5ad998e98f2f68271538015d80ef29` | `16a5a787aaf40d71bfcc42224fe14cf1f64fe463c9f91e0677898682ae5f410c` |

For each blob the locally computed Git SHA-1 of `b"blob " + decimal_byte_length + NUL + decoded_bytes` equals both the tree entry and API `sha`. API transport-body SHA-256 is separately recorded; it differs from the decoded source SHA-256. The repository tree/Last-Modified date and docs Last-Modified date are not live quote clocks.

## Verified protobuf fields

Both files use `syntax = "proto3"`. String and embedded message fields have wire type 2; `int64` has wire type 0.

| Message | Field | Tag | Exact declared type / presence |
| --- | --- | --- | --- |
| `PushDataV3ApiWrapper` | `channel` | 1 | `string` |
| same | `symbol` | 3 | `optional string` |
| same | `symbolId` | 4 | `optional string` |
| same | `createTime` | 5 | `optional int64` |
| same | `sendTime` | 6 | `optional int64` |
| same `oneof body` | `publicLimitDepths` | 303 | `PublicLimitDepthsV3Api` |
| `PublicLimitDepthsV3Api` | `asks` | 1 | `repeated PublicLimitDepthV3ApiItem` |
| same | `bids` | 2 | `repeated PublicLimitDepthV3ApiItem` |
| same | `eventType` | 3 | `string` |
| same | `version` | 4 | `string` |
| same | `lastOrderCreateTime` | 5 | `int64` |
| `PublicLimitDepthV3ApiItem` | `price` | 1 | `string` |
| same | `quantity` | 2 | `string` |

The wrapper additionally declares body tags 301–315 for public/private messages, including `publicIncreaseDepths=302` and `publicAggreDepths=313`. Only their names and wrapper tag/type declarations were read, not their schemas. Do not decode a 313/302 body as a 303 snapshot. Full wrapper bytes remain available for inspection.

The wrapper Chinese comments say `createTime` is message generation time (`消息生成时间`) and `sendTime` is message push time (`消息推送时间`). Neither comment states a unit. The depth proto begins with the comment `// spot@public.limit.depth.v3.api.pb` and declares `quantity` as a string. It does not specify a depth suffix, depth count, push frequency, subscription JSON, quantity asset, tick/lot increment, timestamp unit, sort order, snapshot-vs-delta replacement rule, version sequencing rule, or eventType enumeration.

## Verified WebSocket base rules

The retrieved base document explicitly states:

- Base endpoint: `wss://wbs-api.mexc.com/ws`.
- A connection lasts no more than 24 hours.
- All trading-pair names in the symbol must be uppercase.
- The illustrative trade channel is `spot@public.aggre.deals.v3.api.pb@100ms@BTCUSDT`. This example is for trade streams and does **not** establish the partial-depth channel or the clock unit of any wrapper field.
- Without a valid subscription, the server disconnects after 30 seconds; with successful subscription but no data flow, it disconnects after one minute. The client can send a ping to keep the connection alive.
- A connection supports at most 30 subscriptions.
- The document says to process documented returned parameters and not use undocumented parameters.

No API key, signature or auth requirement appears in this base market-stream page, but absence from this page is not a full access-control specification. The word `Public` in schema/channel names alone is not a normative proof of access rights. No authenticated connection was attempted.

## Unresolved mechanics and conservative implications

These are limitations or implementation recommendations, not facts supplied by unread documents:

1. **Timestamp units remain unresolved.** The two acquired schemas do not normatively establish milliseconds for createTime/sendTime/lastOrderCreateTime, and the retrieved base page has no timestamp examples. Do not label units as documented ms based on field names, magnitude, an unrelated 100ms stream-rate example, or Java type. Server push time also is not automatically the underlying matching-engine event time. Optional clock presence must be checked; missing quote clock is missing evidence. Do not substitute local receive time, an index mark, a server-time request or a metadata HTTP Date for the missing quote clock.
2. **Quantity asset and executable constraints remain unresolved.** A `string quantity` proves serialization, not whether units are base asset, quote asset, contracts or lot counts. Base-asset units are a plausible spot convention, not established by these acquired bodies. Price/quantity decimal strings should retain precision. No verified LOT_SIZE/minQty/stepSize/minNotional/quoteAmountPrecision/status/baseAsset/quoteAsset contract or current values were obtained. Do not invent a minimum lot or reuse perp contract units in spot solely on this note.
3. **Depth-five subscription remains unresolved.** The proto's root channel comment and field tag 303 are source facts. An inferred `...@SYMBOL@5`, SUBSCRIPTION JSON shape, supported depth counts, snapshot semantics and whether version increments monotonically are not established here. `version` is a string; no timestamp or sequencing semantics are declared. A partial book is bounded visible liquidity; it cannot establish liquidity beyond received levels.
4. **Cash/fees access is outside this source acquisition.** The account docs path returned404. No acquired source here establishes a precise trade-fee endpoint, request security category, fee asset or the owner's commission tier. The task's no-credentials/no-account-access restriction still applies: finding an ACCOUNT/USER_DATA/API-key endpoint in other sources would not authorize accessing it. Public promotion/zero-fee pages are not evidence of the owner's actual execution fee. Cash ledger assumptions, fee parameters, fill-side fee denomination and treatment of locked balances need explicit verified inputs or conservative stated assumptions.
5. **Clock/version/wire alternatives remain open.** A matching tag/type parse does not validate deployment compatibility, numeric positivity, symbol/channel agreement, crossed-book handling, completeness, stale-source rejection, clock skew or exchange status. A documented wrapper push time could be a permissible source clock if its units and intended role are independently verified and preregistered; absent that, fail closed rather than inventing a fallback.

## Discovered official follow-up URLs — links only, unread

These exact hrefs were present in the retrieved base HTML, not visited. They are pointers for separately budgeted work, not permission or support for their contents:

- `https://www.mexc.com/api-docs/spot-v3/websocket-market-streams/protocol-buffers-integration`
- `https://www.mexc.com/api-docs/spot-v3/websocket-market-streams/live-subscriptionunsubscription-to-data-streams`
- `https://www.mexc.com/api-docs/spot-v3/websocket-market-streams/partial-book-depth-streams`
- `https://www.mexc.com/api-docs/spot-v3/websocket-market-streams/how-to-properly-maintain-a-local-copy-of-the-order-book`
- `https://www.mexc.com/api-docs/spot-v3/market-data-endpoints/`
- `https://www.mexc.com/api-docs/spot-v3/account/`
- `https://www.mexc.com/api-docs/spot-v3/trade/`

All small acquired bodies and the two decoded schemas are retained only under this ignored cache directory. No files outside `.cache/R324-spot-source` were written. No outcome statistics, financial performance claims or canonical integration were produced.
