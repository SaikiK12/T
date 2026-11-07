# PREREG: M090 public-input publication engineering

- **Registry id:** R373
- **Owner (single writer):** Codex, owner-authorized implementation while Claude is absent
- **Date registered (UTC):** 2026-10-29
- **Inputs manifest SHA-256:** c9fd370613cdf25d669d6d6ed927c1d2c349e3647cbfe4f2a50b3223d5bfad4a

## Question and prior knowledge

Can one bounded public BTC_USDT source capture be preserved, published to an
append-only local journal and independently reverified against nonce-bound
RFC3161 signatures, pinned public certificate material and fresh CRLs? Does
the signed evidence supply the explicit precision needed by the proposed
M090 timing rule? This is infrastructure validation, not a funding forecast
comparison, strategy test, gate pass, independent UTC certification or PnL.

Pre-registration engineering probes sent invented bytes to FreeTSA and
DigiCert. Both signatures verified; neither response contained Accuracy.
DigiCert's current CP/CPS 7.09 section 6.8 did not specify the older indexed
one-second bound. The endpoint and public signer are selected with this
limitation already known. No live M090 market response or forecast outcome
has been acquired by this lane before freezing. This is not blind discovery.

## Closed acquisition and scope

Exactly one capture id `engineering1`, started after this PREREG and the exact
inputs are frozen, committed and pushed. Do not wait for a favorable funding
rate or retake a failed capture under another id. The fixed archive is
`data/m090_publication_v1`. A completed id replays without network access.
There is no scheduler or persistent collection promise.

Six public requests maximum, no retries or redirects: two HTTPS CRLs; one
DigiCert pre-request timestamp; MEXC displayed funding and history page one;
one DigiCert timestamp over the durable journal checkpoint. Request timeout
20 seconds, response cap 1 MB each and 1 MB aggregate response bytes. Existing
archive bytes plus a 3 MB reserve must fit the 8 MB archive cap. The source
endpoints, CRLs, signer DER hash, policy OID, pinned root/chain/public baseline
CRLs, code and strict accuracy policy are bound by inputs.json. Only public
material is used. The documented HTTP TSA endpoint carries a digest/nonce;
signatures authenticate the response. Market requests retain standard HTTPS.

Raw responses, request wall/monotonic bounds and their hashes are retained.
Local wall times are explicitly unverified. No depth, book, account, private
API, money, orders, historical bulk download or reserved data is accessed.

## Publication and content verification

An exclusive writer creates a random 256-bit challenge bound to the prior
commit head and capture identity. Its nonce-bearing SHA256 timestamp query
and signed response are preserved and verified before source requests.
Each raw body is written exclusively, flushed and fsynced with its directory.
A manifest binds the raw evidence and parsed ticket. The journal then appends
one canonical, chained manifest-commit record and fsyncs it and its directory.
A second, distinct-nonce timestamp binds the exact entry and journal prefix.
The complete packet is checked again after the final inventory is written.

Every audit checks the raw file set, hashes, policy, manifest identity,
canonical journal chain, query/imprint/nonces, signed CMS content, exact
signer, timestamp policy, EKU/certificate chain and CRL validity at signed
genTime. Clock/key security remains an operator trust assumption; verification
at genTime is not a later revocation audit. The RFC3161 parser uses exact
rational time and outward millisecond rounding.

Signatures establish content/prefix existence under the trusted authority;
they do not prove market truth, public dissemination, honest collector I/O,
physical storage guarantees or an independently audited UTC clock. A trusted
external copy of the latest head is needed to detect deletion of a valid
suffix. This lane retains that head in the committed immutable result receipt.
Interrupted files, an incomplete journal tail or orphan packets are preserved
and block the archive. No automatic truncation, deletion or refetch recovery.

## Ticket, timing and labels

Keep exact `nextSettleTime` and `settleTime`; never round/floor an event or
assume an eight-hour cycle. Rates are fractions per exact reported settlement.
Use the newest strictly descending provider-reported page-one history event
before the target as the provisional previous event. A nonempty, bounded
page is not authenticated completeness or an independently verified schedule.

Only explicit signed Accuracy in (0, 1,000,000] microseconds supplies
conditional UTC bounds. Missing/zero/excessive Accuracy supplies no interval;
there is no fallback to an old CPS, server Date, host wall clock or zero error.
For a conditional input candidate, the pre lower bound must be >= T−3h,
the post upper bound <= T−1h, and their interval <=60 seconds; distinct nonces
and revocation checks are required. The previous event must precede the
pre-request lower bound and the decision. Bounds are conditional on the
timestamp operator's stated accuracy. Endpoint receipt durations must be
nonnegative and <=30 seconds on the monotonic clock.

The exact-event adapter can select the last qualifying candidate per target
and pair it only with an identical settlement id from a verified later
capture whose pre lower bound is strictly after that settlement. Conflicting
rates remain missing; no nearest-event or older-event replacement. This
one-shot lane cannot supply a later label. Unknown captures conservatively
block their target; late captures may supply labels but not forecasts.
The adapter's 90-event/30-UTC-date coverage minimum is descriptive, not
significance, power or permission to score. All forecast scoring is disabled.

## Outcomes, trials and stopping

Stop after this one capture and an offline, head-pinned reproduction. Report
actual signatures, bytes, exact input parsing, admission reason, restart
idempotence and byte equality. A signature/precision failure is retained as
an engineering result, not recaptured until it passes.

Native terminal result is `DONE/PARTIAL` if content and archive verification
pass but UTC precision or source/timing eligibility fails; `DONE/DATA_PASS`
would mean only conditional engineering eligibility. Runtime/incomplete-data
failure is `DONE/PARTIAL` with its exact failure and retained files. No outcome
is CONFIRMED alpha. Costs 1x/2x/3x are N/A: no trades, capital account, rate-loss
score or PnL is computed. Strategy trials = 0; program trials remain unchanged.

The append-only registry row is a REGISTERED/PENDING registration snapshot;
terminal native status/verdict and references go in immutable outcome.json
and FINDINGS.md without rewriting that row. A later forecast lane needs a new
frozen source/clock/schedule policy, fixed collector/cohort, dependent inference,
power/selection disclosure and strategy-trial count. Existing frozen primitives
and Claude's active forward lanes/journals remain unchanged.
