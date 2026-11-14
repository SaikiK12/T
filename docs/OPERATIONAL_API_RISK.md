# Operational and API risk: the edge can fail before the trade

Reviewed 2026-10-19. The repository has no order path or credentials, and its
historical returns are not a live-execution record. This note records the controls
needed before a future owner-authorized MEXC integration. It is an engineering and
venue-source review, not permission to place orders.

## The venue constraint

MEXC states that its API connects directly to the live trading environment and that
it does not offer a sandbox or test environment ([API FAQ](https://www.mexc.co/mexc-api)).
An integration therefore cannot establish order semantics with harmless test orders
on a venue-provided paper account. Begin with read-only credentials and a shadow
ledger. Any later live order must be an explicit owner action under the repository's
real-money rule.

MEXC's futures endpoints expose an external order identifier, order identifier,
status, filled quantity and average deal price. The API documents querying an order
by `externalOid`, querying open positions, and cancelling all orders for one contract
or all contracts. Batch placement is rate-limited to four requests per two seconds;
the cancel-all endpoint is rate-limited to twenty per two seconds. These are venue
limits, not a guarantee of timely response or fill ([batch place](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/batch-place-order),
[query by external ID](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-order-by-external-id),
[open positions](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-open-positions),
[cancel all](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/cancel-all-orders-under-a-contract)).

Treat `externalOid` as a reconciliation key, not as proof that a timed-out submit
was rejected or that retrying is safe. A network timeout can leave an order accepted
at the venue. On an ambiguous response, query the external ID and current position
before submitting another intent. Store the request payload, local send/receive
times, venue response, order state transitions and deal records.

## A minimal fail-safe state machine

For every intended position change, persist this sequence:

`signal ready → intent created → order submitted → venue acknowledged → fills
observed → position reconciled → risk limits checked`.

Each transition needs a timeout and a terminal error state. The risk process should
be able to:

- stop new entries when the data clock, book sequence, position reconciliation or
  fee/contract metadata is stale;
- cancel working orders by the exact contract and, if the incident is broader, use
  the venue's all-contract cancel endpoint;
- close only with a reduce-only order where the chosen position mode supports it;
- compare the private position response with the internal ledger after every fill and
  after reconnect; and
- cap total notional, per-contract notional, gross leverage, open order count and
  loss over the venue's funding and UTC-day boundaries.

An emergency cancel request is not an emergency flat position. A cancel can leave a
partial fill, so the follow-up position query and a separately authorized close path
are required. Do not infer a fill from an order acknowledgement alone.

## Market-data health is part of the strategy

MEXC's futures depth stream carries a version and matching-engine timestamp. Its
local-book instructions require a snapshot, ordered updates and recovery when the
version is discontinuous ([depth](https://www.mexc.co/api-docs/futures/websocket-api/order-book-depth),
[book maintenance](https://www.mexc.co/api-docs/futures/websocket-api/incremental-order-book-maintenance-mechanism)).
Invalidate every markout and shadow fill that spans an unrepaired gap. Record both
exchange event time and local receive time; monitor clock offset and message age.
The documented 200 ms depth cadence is a feed property, not proof that a process can
submit within 200 ms or that a quote remains available.

The trade stream can aggregate events. A feature called signed flow must therefore
record the stream mode and its aggregation window, and be validated against the
venue's documented trade fields before it is used as an aggressor signal. A stale
or partially reconstructed book should produce an abstention, not a zero-cost fill.

## Shadow capture before any live path

Freeze a target-venue contract manifest and capture, for each decision:

- signal-ready time, modeled submit time and first usable quote;
- symbol, contract size, tick and quantity steps, state and risk tier;
- best bid/ask, depth versions, trades, fair/mark and index prices;
- intended side, quantity, order type, time-in-force and reduce-only flag;
- modeled fee tier, funding event and every partial/complete-fill assumption; and
- data age, sequence status, network errors, reconnects and rejected requests.

Run the order state machine against a shadow ledger for a prospective period. Compare
the intended position with venue market data and, where authorized, the private
read-only account state. Report stale-data abstention, order-completion coverage,
quote age, arrival-to-markout cost, partial-fill exposure and reconciliation errors.
A shadow fill estimates a counterfactual; it does not establish private API fill
probability or account liquidation behavior.

## Security and change control

Use a separate account or subaccount, least-privilege keys, IP restrictions where
available, withdrawal disabled, encrypted secret storage and key rotation. Keep
credentials out of the repository and logs. Pin the API base URL and schema version,
validate response fields, and treat documentation changes, contract-list changes,
fee notices and funding-cycle changes as versioned inputs. A current endpoint cannot
reconstruct the historical rules that applied to an old contract.

Before enabling a new endpoint or order type, replay recorded responses through a
parser test and a failure-injection harness: dropped packets, duplicate messages,
out-of-order updates, delayed acknowledgements, partial fills, cancel rejection,
unknown order state and a process restart. The harness should prove that a retry does
not duplicate an intent and that a stale-data condition fails closed. It can be run
without sending orders.

## What this changes about confidence

An attractive historical return does not cover API ambiguity, stale books, partial
fills, contract changes or an unobserved position after a reconnect. The first live
milestone should be an audited shadow ledger whose state agrees with the venue's
public and read-only private data. Only after that, and after a fresh venue-matched
paper result clears the statistical and risk gates, should the owner decide whether
to place a small order. This operational lane cannot rescue a signal that fails its
untouched forward test.

No live request, order, credential or market-data download was made for this note.

## Sources

- MEXC, [API FAQ](https://www.mexc.co/mexc-api), [batch place order](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/batch-place-order), [query by external ID](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-order-by-external-id), [open positions](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-open-positions), and [cancel all orders](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/cancel-all-orders-under-a-contract).
- MEXC, [futures depth stream](https://www.mexc.co/api-docs/futures/websocket-api/order-book-depth) and [incremental order-book maintenance](https://www.mexc.co/api-docs/futures/websocket-api/incremental-order-book-maintenance-mechanism).
