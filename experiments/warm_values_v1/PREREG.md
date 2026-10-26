# R316: prestarted fair workers versus matched cold-start requests

- **Registry id:** R316
- **Owner (single writer):** Codex, `codex/lab-consolidation`, draft PR #49
- **Date registered (UTC):** 2026-10-25
- **Canonical method:** M409 execution-input dependency, no predictive policy

Code/input manifest SHA-256: b39c5f466f7d1a7eae51dd7e15daa5e7df1465365834ee26edd8b3175f371acb

## Binding constraint and finite question

R311 remains INCONCLUSIVE on224/273 common validation days, and its calibration-
selected F0+B_h14 loses at registered2x/3x costs. Its12 variants, costs, historical
dates and missing-data rules stay unchanged. R315 supplied no jointly fresh
altcoin book/fair/index row. It measured owned-worker-inclusive REST latency
1.247–2.435s: requests scheduled1s before a grid never supplied that grid's
immediate value; only4/36 arrived by+300ms. No old lane is edited or rescored.

Does moving worker startup before the observation anchor improve causal MEXC
fair-publication availability, compared with unchanged R315 cold-start requests
at the same current grids/books/q? Keep the WS fair-change profile as a third
control. This is a local implementation/input-cost diagnostic, not an alpha,
cash, expected-return or prospective strategy test. The platform's concurrent
resource/transport contention is shared; measured latency is not isolated venue
latency. No general sampling precision or significance is claimed.

Six profiles (three source paths crossed with immediate/300ms), six symbols and
six grids enumerate **216 descriptive rows, zero predictive variants**. Program
trials remain9,478,782. Any inactive/missing/capped/unscored observation remains
visible; do not select a favorable profile as a strategy validation winner.

## New component and unchanged economic/source contract

Add `lab/fair_workers.py`: exactly six owned prestarted processes, one per fixed
public MEXC fair endpoint. Each has at most six request commands and <=4,096 body
bytes per command. Constructor/import/opener readiness performs **zero network
requests**. Require the ready message before the common observation anchor,
within one shared10s readiness deadline. Failed or exhausted workers are not
replaced/restarted; their remaining slots stay skipped. Fixed symbol URLs reject
private/account/arbitrary endpoints in the public parent API.

Each warm request records parent command dispatch, worker's application GET
dispatch (not observed physical wire time), full-body first-seen UTC/monotonic
receipt and parent request completion separately. Persistent worker shutdown is
recorded once, separately from per-request completion; never invent per-request
worker cleanup. No source timestamp is synthesized from readiness/GET/receipt.
The unchanged R315 cold path retains startup-inclusive dispatch/receipt and actual
worker-cleanup clocks. A dispatched command with uncertain network progress still
consumes its request slot and full unknown byte tail conservatively.

Use the same source-typed R315 values/ledger, R314 depth assembler/replay and R312
common-lot/cost kernel. REST `data.timestamp` remains **System timestamp**, WS
values remain their source publication clock, ticker time remains trade time.
A fresh publication is not an effective-price/cache-age/funding-engine attestation.
The new official Lighter reading finds: orderBookDetails has index/mark but no
own value clock; priceOracleInfo has a computation clock but source/median/cap
policy rather than actual current prices; marketPriceCharts uses hourly marks
for perps and index for spot; funding-rates directs real-time use to market_stats
without establishing API rate scale/settlement asset. These weak alternatives
remain received, not collected or combined by borrowing timestamps. Exact source
versions/read-unread scopes are retained in sources.json. No widened session or
idle-state permission is inferred.

## Frozen finite collection and input ordering

Commit/push this frozen spec, all code/tests/source identities and independent
checker before public market calls. Same six R312–R315 pairs BTC,WIF,SKR,ROBO,
MEGA,XPD with pinned R288 identity; no substitution after a failed input. XPD is
the metals/session control, BTC the reference. Hold the existing machine-wide
Lighter lock for one writer, waiting at most10s. Create one evidence directory;
refuse an existing directory, including a previously failed attempt.

At most **7 metadata GETs**, <=2MiB conservative body-read upper bound total,
<=1MiB/body and20s metadata request-start window, using the frozen bounded R314
reader. At most **72 fair GET commands**, <=4,096 bytes each (**288KiB** upper
bound), for **<=79 combined GET attempts**. Every failed/uncertain dispatch counts;
unused slots cannot buy extra requests. No redirect, retry, worker replacement,
historical query, account, credential, signing or order access.

After metadata and prestart readiness, establish one UTC/monotonic anchor. At
anchor+9,19,29,39,49,59s, dispatch six warm and six cold requests in a fixed
symbol-interleaved order; same planned dispatch time, at most12 concurrent
requests (six reusable warm and six transient cold processes). Each request has
an absolute **3s parent deadline**, including IPC/cold startup, rather than a
socket inactivity timeout. The warm worker also checks the65s request-start
window before application GET dispatch. Parent/body receipt precedes cleanup.
Partial/failed bodies remain raw evidence. Incomplete/unknown reads reserve the
whole4,096-byte tail; no cap+1 read. Terminate only owned failed processes, at
most two0.2s joins. Completed persistent workers stay idle until the next fixed
command, without automatic polling, reconnection or extra GETs.

Known HTTP401/403/429/451/503 aborts further metadata or future fair batches.
Already-dispatched batch slots may finish within their own bound. No inferred
Retry-After expiry or retry. Keep all72 planned fair slots and skipped reasons
if the stream stage was reached; metadata-stage failure may retain zero slots.
Warm command counters must match attempted warm slots. First readiness, worker
GET dispatch, body receipt and actual close must be causally ordered.

At most **2 public WS handshakes** (one per venue), no reconnect/replacement,
five-second open timeout. Same MEXC six full5 depth+six fair-change subscriptions
and Lighter six order_book+six market_stats. Inherited TLS/proxy/CA preserved,
compression disabled, receive queue one. **65s read/request-start window,120s total**
including lock, metadata, readiness and cleanup. Whole async phase <=75s or
remaining total less3s reserved for final worker cleanup. Each venue <=8MiB
decoded application payload,20,000 messages,256KiB/frame. Reserve a maximum frame
before each read. Record malformed/control/error frames and immediate unusable
boundaries separately from transport close, unchanged from R314. No idle heartbeat
or full-snapshot size/refresh SLA is assumed.

Capture calculates no economics. Seal every exact raw file to frozen code, then
commit/push input identity **before reporting outcomes**. One sample only; no
adaptive timing change/second capture if it fails. Differing output overwrite
is refused; reproduction writes a separate folder.

Historical R310/R311 approval stays **7,757/8,000 requests,229.85/250MiB**. This
separate bounded current diagnostic does not reset/extend it. Prerequisite source
reading used8 static requests (7HTTP200,1HTTP302 not followed),1,142,975 body bytes,
4.437s against8requests/4MiB/120s; no market/history data from that reading.

## Fixed causal controls, costs and missing-data policy

At anchor+10,20,30,40,50,60s evaluate full-depth paired books. Immediate valid
books alone define the common-lot base q by rounding down a $250 leg target
divided by the larger midpoint. WS_change,REST_cold,REST_warm and all +300ms
controls retain exactly that immediate q, without future backfill or resizing.
Reuse strict R314/R315 state/clock/identity guards unchanged: valid sequence,
receive age0..1s, source age-100ms..2s, cross-venue book/reference source and
receive skew<=1s, local UTC/monotonic movement<=50ms. Failed/closed/capped state
remains unusable; old unchanged liquidity/reference packets are not freshened.

Each REST profile independently selects its latest full-body reply/failure
actually received by the deadline. A latest known error poisons only that profile;
no older-good, cross-profile, WS or future-reply fallback. Preserve exact instrument
and value kind to each book. Failed/unknown source clock or schema remains missing.
REST system time ahead of receipt by>100ms is rejected. No HTTP Date or Lighter
policy computed_at_ms is imported as an index-value timestamp.

Report all36 pair/delay/profile cells: displayed-cost count, joint-publication
count, flags and fixed1x/2x/3x costs. Also report both REST paths' attempted/parsed
body counts, dispatch-to-full-body latency min/median/max and own-grid **receipt**
counts at0/300ms. Receipt counts may include a known error; distinguish parsed
success, receive freshness and true joint row availability. Summaries are
descriptive implementation evidence, not a general latency guarantee.

Reuse **$10,000 segregated capital,$5,000 per venue**, equal base q and fixed
**10/4bp per-side charge reserve PLUS displayed crossing**, stressed together
at1x/2x/3x. Report USD round-trip and break-even bp per mean one-leg midpoint
notional. It is a conditional current entry+unwind cost, not actual account fees,
exact R311 all-in replay or a guaranteed future exit. Report sampled q*reference
and one-bp sensitivities only with valid books and jointly fresh publication
packets; USDT versus unverified Lighter USD-quote settlement units are not netted.

All216 rows remain execution_ready=false, funding cash unscored. No position,
event-bound settlement value, actual rate unit/asset, source-certified effective
index age, authoritative session, account fee/fill, impact, two-leg recovery,
margin/financing/liquidation or prospective strategy proof is collected here.
An improvement to one input does not authorize net-PnL or activation claims.
The independent frozen checker reconstructs raw causal states and receipts,
matched q/books/costs, all1x/2x/3x tiers, products and latency/coverage summaries.
