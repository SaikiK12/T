# R428: native papers deployed; participant stream blocked by jurisdiction

## Observed deployment, 2026-11-07

**The runtime was deployed; the new participant stream did not collect data.**
Migration comment 6712606118 ran reviewed merge b4063110 through workflow
42411122446. Canonical state 34bed1882942a49555f092d79840881e702a7d38 selects
R428. The [read-only deployment proof](deployment.json) independently verifies
all 656 manifest hashes and 42 new auxiliary wire/content pairs.

R419 captured its 20:00 UTC packet: 12 GETs/172,589 body bytes. R413 updated at 20:27:52 UTC
(13 ticks, 4 locks, 0 settled); R406 at 20:27:59 UTC (16 ticks, 2 locks, 0 settled).
These are actual native receipts, not source health inferred from workflow
success. Five legacy lanes remain stale; all-project-running remains false.

At 20:28 UTC the two Lighter metadata GETs returned 200 (1,739/1,743 bytes), but the
WebSocket handshake returned **HTTP 400, provider code 20558**, with this exact
primary response from Lighter's runtime API (undated publication, retained
at 20:28:00 UTC; accessed from the stored body on 2026-11-07):

> You are accessing Lighter from a restricted jurisdiction. For more information, see the https://lighter.xyz/terms

Endpoint: `wss://mainnet.zklighter.elliot.ai/stream`. The 153-byte body has SHA256
`9504eba0eed7d0ebeccb2d6394693664e9d12c4822995806bd69a34bafe1e4f7`.
The source attempt made 3 requests, processed 3,635 known application-body bytes
and received **0 frames/0 transactions**. Its 8-call/2 MiB reservation is retained;
the whole 32-call/8 MiB campaign remains reserved inside the original historical
cap, with no refund. The original native auxiliary total is now 484 calls /
15,221,875 charged bytes, leaving 1,555,341 of 16,777,216 bytes.

**BLOCKED_JURISDICTION, not an economic null.** The source wrote SOURCE_BLOCK;
subsequent windows cannot retry it. No readonly/query/header/IP/provider/
region/REST variant was attempted after learning the restriction. Successful
metadata access is not proof of permission to use the refused stream. This
observed server restriction does not determine every French resident's legal
status; individual execution eligibility is still unqualified. Already-held
data remains intact. No quote, position-flow, markout, strategy PnL or new
source day was measured; no real orders, money or credentials.

The paragraphs below preserve the code-registration scope and limits.

At code registration, the source campaign has **no actual market connection
or captured window yet**. The implementation is locally validated and
inactive until reviewed merge and the recorded native migration. Do not
infer deployment, future uptime, a paper day or PnL from this document/CI.
The canonical manifest's active_contract/last_report and source-slot receipts
are authoritative after activation.

## What this advances

M441's participant-toxicity and M474's quoting work need new receipt-time
data. R427 supports the existing maker-side convention on219recorded
position transitions, but the old short fragment is spent. This registers
four bounded new raw ticker/trade windows, preserving public account
before-state, source numeric strings and UTC/monotonic receipt clocks.
No participant rank, flow, markout, return or strategy is scored here.

One qualification window65seconds on Nov7, then180second observations on
Nov8/9/10, at the first selected cycle within each fixed eligibility window.
All missed/partial windows stay visible. These are short samples, not three
full UTCdays, and cannot meet R367's unrelated coverage requirement.

## Writer and resource preservation

Only the reviewed selected GitHub Actions composition may collect. Explicit
owner migration selects R428; immutable previous workflows then skip. All
share the same concurrency group. The new distinct command and minute37cron
reduce overlap, without promising GitHub scheduling. Migration/prepared
checkpoint publication precedes HTTP/WS, and existing source/paper attempts
are not duplicated across the transition or an hour boundary.

R419/R413/R406 retain their source code and journals. The frozen canonical
baseline at b57bd403 verifies582file hashes and442old auxiliary calls /
15186923charged bytes. All later R422appends must also be inherited; the
original16MiB auxiliary ceiling,4096total-call limit, R419Nov14end,
dispatcher Nov19end and64MiB state cap remain. This does not fund or prove
coverage through the papers' later settlements.

The new campaign holds32calls/8MiB inside the **original historical**
allowance, including all prior reservations: **7851calls/259609578bytes**
under8000calls/262144000bytes. Each attempted slot keeps8calls/2MiB,
including failures/unknown buffered spend; no automatic refund or new grant.
Decoded-body processing is distinct from unmeasured TLS/network wire.
No broad archive, paid source, account/credential, order or real stake.

HTTP/WS redirects, source denials, unknown/cut state and reconnects are
blocked. An observed source/schema failure persists rather than being retried
on the next date. Payloads, bootstrap labels, raw error bodies where supplied,
clock/byte/row counts and partial records remain. No source numeric string
is silently converted to float or missing value0.

## Validation and exact lineage

Before freezing: **2604tests passed,3skipped,385.845seconds**, including17
new synthetic client/state/transport tests, with no real source connection
or local GITHUB_ACTIONS spoof. The final suite covers redirect refusal,
wrong-window rejection before clients, unreconciled reservation retention,
raw byte/clock preservation, source failure persistence and cross-hour paper
attempt checks. Earlier pre-freeze test attempts and the final log identity
are retained in [pre_measurement_validation.json](pre_measurement_validation.json).
No existing dependency lock or old frozen implementation was changed.

The137-input closure and [PREREG](PREREG.md) froze
`634cc63e3fac021a2dc142304021789c127ab916718a0c6da70e78a3e36067b5`
before acquisition. [Source scope](SOURCE_SCOPE.md), [baseline](baseline_receipt.json)
and [full campaign reservation](acquisition_reservation.json) give exact
inputs/limits. The pre-source commit must be retained through normal merge.

**Costs1x/2x/3x:N/A, not zero. 0predictive/economic trials; program9784361.**
No alpha/capacity/access/own-fill/funding-cash or real-money gate is passed.
M441 remains UNTESTED, M474 PARTIAL. Future consumers must freeze their own
causal features, completed horizons, actual cost/inventory/exit rules and
day-block evaluation before measuring these newly collected outcomes.
