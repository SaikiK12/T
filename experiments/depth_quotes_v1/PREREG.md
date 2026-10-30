# R314: sequence-consistent depth and matched top-level cost control

- **Registry id:** R314
- **Owner (single writer):** Codex, `codex/lab-consolidation`, draft PR #49
- **Date registered (UTC):** 2026-10-25
- **Canonical method:** M409; descriptive execution-input/cost measurement

Code/input manifest SHA-256: 995b7ae3e124de60c454e567f04fae2d264257555ba7df343aa3bcc41f334e4e

## Binding question and prior evidence

Does a nonce-linked Lighter order book supply more displayed paired capacity
than its own top level on fixed causal deadlines, without relaxing source age,
receipt age, skew, quantity, capital or costs? Does that capacity remain available
on a fixed 300-ms access control? No signal, position, expected return, model
selection, confidence interval, hypothesis significance or activation is tested.

R311 is already seen and remains INCONCLUSIVE on 224/273 common scored days;
its calibration-selected F0+B_h14 loses at registered 2x/3x costs. R313 kept
7/144 cost-eligible rows, including zero delayed altcoin cost rows. Its separate
top-only stream and time window are historical context, not a matched control
here. R310–R313 files and spent historical dates remain intact. No alternative
validation policy or increased leverage can rescue them.

Predictive trials before and after this measurement: 9,478,782. The four profiles
(full/top-only crossed with 0/300 ms), six pairs and twelve grids enumerate
**288 descriptive rows, zero predictive variants**. Dependent observations do
not supply independent sampling uncertainty or a profitability test; no null or
multiplicity-adjusted inference is appropriate or claimed for this cost audit.

## Finite acquisition, frozen before any collection

Commit/push this frozen specification, all code/tests, primary-source identities,
runtime and static symbol identity before requesting market inputs. Exactly the
same six R312/R313 symbols: BTC, WIF, SKR, ROBO, MEGA, XPD. Pin R288's matching
MEXC/Lighter/Binance symbol table; XPD remains a metals/session control. BTC is
not an altcoin strategy replacement. No substitution after missing metadata.

One attempt only; evidence directory creation refuses an existing directory,
even after failure. Hold the existing machine-wide Lighter public API lock,
waiting at most ten seconds. At most seven public metadata GET attempts: Lighter
perp details once and MEXC detail once per symbol. Two MiB body-read upper bounds total,
one MiB/body; no cap+1 read, redirects or retries. Seven failures still exhaust
seven attempts. Parent request starts must be within the 20-s metadata window.

Each GET runs in an owned spawned worker with an absolute parent wall deadline
of three seconds or remaining metadata-window time, including worker startup.
The worker makes one request and sends capped chunks; the parent preserves any
received partial body and error, reserves the entire uncertain request tail
against the same accumulated byte allowance, terminates only its own worker at deadline and
allows at most two 0.2-s cleanup joins. This bounds trickling-body reads instead
of treating a socket inactivity timeout as an absolute request deadline. Recorded
body bytes distinguish retained bodies from the conservative read upper bound;
transport buffers and overhead are not claimed as measured application bodies.

At most two public read-only WebSocket handshakes, one per venue; five-second
open timeout, no redirects, automatic retries, replacement subscriptions or
reconnects. MEXC: six `sub.depth.full` (limit5) and six `sub.fair.price` channels.
Lighter: six `order_book/{market_id}` and six `market_stats/{market_id}` channels.
No account, signing, order, transaction, history or private endpoint is used.

One common UTC/monotonic anchor after metadata. Start application reads only
within a **65-s window**, with **120 s total** including lock, metadata and socket
cleanup. Each venue: at most **8 MiB decoded application payload, 20,000 messages,
256 KiB/message**. Reserve one full maximum-sized message before every read;
stop at capacity instead of truncating and claiming complete depth. Compression
disabled, receive queue one message, TLS verification and inherited proxy/CA
trust preserved. Ping/pong and every malformed/error/control frame are recorded
with individual receive UTC/monotonic clocks. Application sends have two-second
timeouts; recheck the read deadline after ping sends. Stop/failure makes the
connection unusable immediately, **before** possibly delayed socket cleanup;
record that boundary separately from actual close. The whole async phase is
bounded by remaining total time and 75 s, including subscription/close overhead.

No maximum full snapshot size or idle-market refresh SLA is documented in the
inspected official sections. The larger frame cap is ours, not a source promise.
A cap fault remains missing evidence, not permission for an adaptive second run.
R310/R311 history remains 7,757/8,000 requests and 229.85/250 MiB; this separate
finite current-data probe does not consume or renew that historical allowance.

Capture computes no economic results. Seal every exact raw file/hash to the
frozen code identity, then commit/push that input manifest **before report**.
Failed/partial collections still retain all grid rows and reasons. Immutable
outputs refuse a differing overwrite; reproduction uses a separate folder.

## Depth, source clocks and sessions

Reuse the committed `LighterDepthState`: initial subscribed snapshot, absolute
sizes, zero deletion, `begin_nonce == previous nonce`, increasing but possibly
nonadjacent offsets, atomic sides/metadata and explicit saved subscription epoch.
No automatic reset/recovery in this one-connection measurement. Gaps, malformed
identity, missing/regressing clocks, inconsistent duplicate fields, crossed books
or over-10,000-level state poison that market until a new protocol/epoch; no
same-run resubscription is budgeted. Unattributed corruption/shutdown poisons the
affected venue. Duplicates, pong and ineffective batches cannot refresh selected
liquidity age. Assembly counters count processed state outcomes, including
repeated poisoned states; they are not counts of distinct causal gap incidents.

MEXC full5/contract conversion, fair-price changes, market-order depth limits and
reference parsing reuse R313 unmodified. MEXC book `cts` is configured ms;
Lighter `last_updated_at` is configured us, distinct from publication timestamps.
No automatic unit guess, receipt-clock fallback or source-provenance attestation.
The unversioned MEXC full feed and Lighter timestamp units/UTC alignment remain
explicit source limitations. An effective deeper-level change may refresh the
whole assembled-book clock under this selected policy; it does not prove each
resting top order's survival.

Strict inherited guards: receipt age 0..1 s, reported event age −100 ms..2 s,
cross-venue source and receive skew each <=1 s; UTC versus monotonic movement
from anchor <=50 ms. Also check latest assembled metadata clock/deadline even
when liquidity did not change. A failed, capped or disconnected stream is unusable
at its recorded first stop boundary. Old unchanged orders may be tradable, but
this protocol does not certify them or loosen its guards after observation.

Metadata must explicitly report MEXC active/API enabled and Lighter active,
not frozen, known not force-reduce-only. Preserve raw `trading_hours`, flags and
their source receipt clocks. Empty or unparsed session text stays unknown; no
NYSE/CME reference calendar is asserted as this venue's execution permission.
MEXC fair and Lighter index observations keep independent publication/receive
clocks. Their sampled q*price products are not settlement cash, settled rates,
funding forecasts, a known fee tier, margin availability or fills.

## Fixed matched economic controls

At 5,10,...,60 s after anchor, evaluate full assembled Lighter versus MEXC full5.
At that immediate deadline only, use the existing common-lot routine to round
down a $250 leg target divided by the larger midpoint. Do not backfill quantity
from a future valid quote. A thin immediate book may still define a known
decision quantity; an invalid clock or metadata cannot. The delayed full profile
at +300 ms and both top-only controls use **that exact same immediate q**; no
resizing to a favorable later price or thinner top capacity.

The top-only control truncates **the same consistent assembled Lighter state**
to its single best bid/ask. Its nonce, first-seen/event clocks, status and metadata
are identical to the full profile. It is not a second ticker/venue sample. Keep
all 288 rows including unavailable costs; full-vs-top therefore isolates displayed
depth capacity under the selected shared-clock policy, not order fills or OFI.

Reuse `pair_costs`: $10,000 segregated $5,000 per venue, equal base quantities,
explicit 10/4-bp charge reserve per side PLUS shown crossing. The inherited reserve
is conditional, not measured account fees or exact R310 all-in-cost replay.
Fixed 1x/2x/3x multiplies crossing+reserve together. Report current-book round-trip
USD and break-even bp on mean one-leg midpoint notional; this is a quote-based
entry+unwind cost, not the cost of a future exit assumed available today. Only
matched eligible full rows receive the two-orientation 0→300-ms entry cash drift.
Never turn failed depth/age/sessions into zero cost or substitute successful pairs.

All rows remain `execution_ready=false`. No economic test can infer fills,
queue position, two-leg recovery, latency, capacity after our own impact,
counterparty/financing/liquidation safety, calibrated confidence or expected net
return from this short sample. No prospective lane is activated; its own frozen
policy, on-time input coverage and adequate independent evidence remain necessary.
