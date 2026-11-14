# R428: bounded participant-source windows with one selected paper runtime

- **Registry id:** R428
- **Owner (single writer):** Codex; serialized reviewed GitHub Actions only.
- **Date registered (UTC):** 2026-11-07

## Question

Can the selected single writer preserve existing native papers and their
original spend while collecting four finite, raw Lighter participant/BBO
windows with exact receipts and conservative bounds, without scoring alpha?

## Universe

Only Lighter WTI market145 and BRENTOIL159, fixed from M441/R426/R427 before
this acquisition. Each slot first verifies public instrument identity/status
through the named orderBookDetails routes. No market/account selection by
prices, returns or participant success; all received public account IDs in
the allowed messages are retained. An account ID is not a person.

## Data and fixed campaign

One campaign with exactly four start-eligibility windows, each attempted at
most once, in the first selected runtime cycle inside that window:

| Slot | UTC start eligibility | Stream duration |
|---|---|---:|
|qualification|Nov7,20:00..Nov8,00:00|65s|
|observation1|Nov8,18:00..23:00|180s|
|observation2|Nov9,18:00..23:00|180s|
|observation3|Nov10,18:00..23:00|180s|

The right endpoint is exclusive. These are eligible start times; a stream
that starts near the right boundary may finish after it. No late/backdated
replacement for a missed window. The source library rechecks eligibility
at its recorded start. Timestamps and actual elapsed time remain visible.
Shorter/cut/empty windows are partial or missing, never full days or zero PnL.

Two ordinary public metadata GETs, one ordinary WebSocket handshake and four
read-only ticker/trade subscriptions per slot. Only
`wss://mainnet.zklighter.elliot.ai/stream` and the two fixed market metadata
URLs are allowed. No account/token/key, order, transaction, alternate
provider, browser-UA spoof, geo/451/bot/paywall workaround or reconnect.
HTTP and WebSocket redirects are refused before a target request. The
locked websockets16redirect hook is explicitly disabled; no async reconnect
iterator is used. Handshake error bodies are bounded by the locked library's
MAX_BODY_SIZE and retained when supplied by its exception.

Original UTF8/binary payload bytes are retained as base64 with individual
SHA256, local UTC/monotonic full-message receipt clocks and unchanged source
strings, inside one gzip journal per slot. Metadata raw bodies/receipts are
separate. Bootstrap trade snapshots remain labelled as such by message type;
they are never counted as new live trade updates. No source price, signed
flow, position difference, markout, forecast or return is summarized.

Source counts and schema assumptions use the inherited project Lighter
ticker/trade parser and R427's sampled role qualification. Current global
API schema/stability and deployed serializer version are not thereby proved.
Future consumer tests need separately frozen rules and source identities.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Source / units | Window / close | Publication / receipt | Decision availability | Vintage / missing and revision rule |
|---|---|---|---|---|---|---|
| Raw source frame | exact socket message bytes | Lighter fixed ticker/trade subscriptions | only the four named finite windows | original provider clocks plus local UTC/monotonic after full message receipt | available only after receipt, not at an earlier matching-engine time | immutable raw/base64+hash; malformed/error frames retained and stop source |
| Instrument identity | metadata market_id,symbol,status | public orderBookDetails145/159 | before each slot's subscription | actual HTTP start/receipt | no quote/PnL decision | wrong/missing identity stops, no market substitution |
| BBO/participant schema counts | message type/channel, ticker a/b, trade IDs/account IDs/positions/entry-quote strings | raw source strings, not normalized cash | per received message; bootstrap and updates separated | original source fields retained; no cross-host latency estimate | counts only, not a predictive feature | missing field stops, no inferred0 or float conversion; timestamp lexical integers preserved |
| Native health and resource counts | original journals/statuses, request START/END/CONTENT, reservations | R419/R413/R406 plus new source; bytes/calls/clocks | immutable baseline plus append-only tails | actual native timestamps; skips do not refresh source time | operational evidence only | missing/corrupt/cut/unknown state fails closed, old spend and denials retained |

## Resource contract

The source campaign reserves **32requests/8MiB** inside the SAME accumulated
historical allowance, not a new grant. Prior conservative proof is
7819calls/251220970bytes; including the whole new campaign reservation gives
**7851calls/259609578bytes** under8000calls/262144000bytes, leaving149calls/
2534422bytes unreserved. No reservation refund, date reset or new allowance.

Each attempted slot keeps its full **8calls/2MiB** reservation even if it
fails early. Calls include metadata GETs, handshakes and subscriptions;
protocol heartbeats are control traffic, not additional market-data requests.
Decoded application-body processing is capped1556480bytes/slot, including
metadata, with262144byte maximum frames, queue1 and10000frames. Metadata
responses are capped8192bytes. Stop before another receive when a complete
maximal frame cannot fit; the remaining reservation retains buffered/unknown
spend. These are application-body/resource bounds, not measured TLS/socket
wire traffic. A partial/crashed slot is never credited as complete.

The original native paper **16MiB auxiliary ceiling and4096total-call limit**
are unchanged and separate. Frozen baseline stateb57bd403 has442calls/
15186923charged auxiliary bytes,1590293bytes remaining. R422 can append
before migration; all those extra requests are inherited too. The inactive
R420 ledger must match exactly; the R422 ledger must extend its frozen
prefix. Their immutable copies are concatenated once into the new runtime's
baseline. Content-file paths in those old rows still refer to their original
folders; only new R428aux bodies use the new folder.

R419 keeps its own1351call/16MiB/hour guards and Nov14end. Existing auxiliary
source stops and unknown reservations survive. Whole dispatch still ends
Nov19. This finite pilot does not guarantee recorder coverage through the
papers' Dec25/2027settlements. State storage stays capped64MiB.

## Single-writer deployment and run rules

Only after frozen/committed code, full tests and current-head CI/merge may
the owner's `/quant-participant-migrate` activate R428 on the canonical
`codex/quant-runtime-state` branch. No local tick/recorder/daemon or fake
GITHUB_ACTIONS. The new immutable workflow shares the old global concurrency
group, checks the selected active_contract, and publishes migration and its
own prepared checkpoint before HTTP/WS. Previous frozen workflows are not
edited; unselected ones skip. No foreign process is killed.

Migration requires a finished R422host and verified baseline prefixes,
hashes and original source limits. Journals/raw history are kept, not reset.
Duplicate paper attempts are checked using actual prior task-start UTC,
including the predecessor and the new runtime's earlier report. R419's own
hour guard remains intact. A source child can use the parent's published
reservation across an hour boundary; it may not fabricate another hour.

The new cron requests minute37, with delay/drop still possible. The distinct
owner command `/quant-participant-tick` is for an actually missing hour only,
after pending/running writers and native receipts are checked. No routine
comment while a needed workflow is pending. No more than one manual request
per hour; a prepared/lost hour is never silently retried.

Only new code writes source SLOT_STARTED/FINISHED/BLOCK events. A previous
denial, schema/error envelope, missing/cut ledger, unfinished source attempt
or incompatible state stops further acquisition; no next-date retry around
a failure. Slot directories and raw payloads are never overwritten/deleted.
All old R419/R413/R406 source scripts and journals remain their native code's
work. Broad/continuous legacy recorders stay blocked/paused.

## Splits, cost and gates

No signal, statistical return test, price measurement, toxicity estimate,
strategy selection or prospective paper day. **Costs1x/2x/3x:N/A, not zero.**
Plumbing before freeze was source/clock/schema/identity/counter reading only,
including582canonical file hashes. No new market connection was made here.

Run this one registered campaign through its fixed slots, not repeated
financial searches. Retain every failure and gap. R428 may validate source
collection and writer continuity only; M441 stays UNTESTED and M474 stays
PARTIAL until separately registered economic evidence. Three short source
windows are not three full UTCdays and cannot rescue R367. Funding cash,
actual own fills/queue/latency, fees, margin/capacity and France eligibility
remain separate. No real-money or go_real admission follows.

## Multiplicity, null and stop rules

**0predictive/economic trials**, program9784361before registration. Any new
feature/markout/performance reading requires its own prior frozen protocol;
do not inspect these future prices and then choose a filter. Source failure
is a source failure, not economic NULL. An enabled workflow/green CI/controller
exit is not a source receipt, profitable method or future-uptime proof.

No extra slot, symbol, endpoint, duration, field, cap or retry after outcomes;
no frozen input edit, protected2020/MEXC-only/reserved read, paid/large pull,
account/credential/money/order, subagent, reset or waived scientific gate.
Changed code or idea needs a new R-id, preserving old outcomes and spend.

## Frozen input manifest

0d797bbc26cdba31619922534dfcb22142603b2d89846e05981621829a6b1a27  experiments/participant_capture_v1/inputs.json
