# R428 source scope: new raw observations, not a strategy verdict

Prepared by Codex on2026-11-07. This implements data collection for existing
M441/M474, following [R427](../lighter_trade_contract_v1/FINDINGS.md), whose
recorded position identities support true=ask-maker/buyer-taker. R427 did
not establish a predictive edge, current global API stability or actual own
fills. Its original source files and outcomes stay unchanged.

## Sources read and limits

- **Project implementation, partial**, the retained
  [Lighter ticker/trade parser](../../lab/tape.py), specifically its `lighter`
  function, read2026-11-07. It uses `/stream`, ticker/trade channels, colon
  market IDs in received envelopes, ticker a/b price/size and
  last_updated_at, and separates subscribed trade snapshots from updates.
  This is an inherited implementation hypothesis, not a newly verified full
  exchange specification. The new collector fails closed if the actual
  source differs; it never silently repairs a missing numeric field.
- **Primary SDK/source snapshots, partial**, the elliottech trade model,
  agent-kit example and prover contexts retained in
  [R427's intake](../../research/intake/lighter_contract_20261107/SOURCES.md),
  accessed2026-11-07 with exact hashes/read scopes there. The original raw
  numeric strings and maker/taker before-state are now retained, avoiding a
  new float conversion. Source/deployment vintage is still not certified.
- **Primary reference metadata only in this pass**,
  [Lighter websocket reference](https://apidocs.lighter.xyz/docs/websocket-reference),
  retained R314/R315receipt from2026-10-25 in
  [sources.json](../funding_values_v1/sources.json), stated date_modified
  2026-10-18 and bodySHA861d70b16479e9303a42826aece613a06d7ab15d9456566f80e39c8f8ff16c5c.
  The full cached body was not recovered or newly read here. No claim that
  its entire current ticker/trade/API document was verified.
- **Primary software implementation, partial**, Python websockets16.0,
  [async client](https://github.com/python-websockets/websockets/blob/16.0/src/websockets/asyncio/client.py),
  installed locked version, read locally2026-11-07: `process_redirect` and
  `__await_impl__` follow eligible HTTP redirects even in a single context
  connection. This collector returns the original exception from that hook
  before another target request. The single context form makes no reconnect
  iteration. Locked `http11.MAX_BODY_SIZE` is checked against the retained
  reservation before the handshake; error bodies are preserved if exposed.
  No full software/security audit or measured network-wire bound is claimed.

## Fixed data route

Only public metadata:

- https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id=145
- https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id=159

and one public `wss://mainnet.zklighter.elliot.ai/stream` connection per slot,
subscribed only to ticker/145,trade/145,ticker/159,trade/159. No account,
order, token, authorization, alternate provider or browser impersonation.
The URLs provide instrument identity and current source data, not historical
owner fees, margin entitlement or access from France. Current market minima
are not automatically projected onto old dates.

Four start-eligibility windows are fixed in [capture.json](capture.json):
Nov7qualification65s, then Nov8/9/10observations180s each. Actual receive
clocks, pauses, bootstrap rows and cuts remain visible. These are selected
short windows, not continuous days, market-wide history, source clock
calibration or a replacement for R367's three full-day requirement.

The frozen [reservation](acquisition_reservation.json) retains the original
historical proof and reserves the entire32calls/8MiB campaign up front:
7851calls/259609578bytes total under8000/262144000. There is no grant reset
or refund. Native R419 and auxiliary paper caps stay separate and unchanged.
The [baseline receipt](baseline_receipt.json) verifies582canonical file hashes
at stateb57bd4032c4577037518baa428cb22e653f8f30d before migration, including
the original442auxiliary calls/15186923charged bytes. New R422appends before
migration are inherited, not discarded or rebased to that older balance.

No source price, flow, position relationship, markout or PnL is read by this
campaign. Schema/identity/row/byte/clock counts are its only measurements.
Future model work must freeze its own transforms, publication/receipt rules,
completed horizons, account concentration controls, fee/inventory/exit costs
and independent day-block evaluation before looking at those outcomes.
