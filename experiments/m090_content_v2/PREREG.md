# PREREG: bounded M090 signed-content capture after interrupted R373

- **Registry id:** R374
- **Owner (single writer):** Codex, continuing owner-authorized implementation
- **Date registered (UTC):** 2026-11-02
- **Inputs manifest SHA-256:** a995d4d784b443ea173db80387c56a9443598dc7118b0b2bf3516778ec13e2c7

## Question and prior knowledge

Can a single bounded public BTC_USDT input packet be written durably to a
local journal, sealed by a pinned RFC3161 authority and independently replayed
without refetching or changing bytes? This is content/input engineering,
not a forecast, clock certification, trading strategy or PnL test.

R373 was interrupted before commit/push/acquisition; its original frozen text
and digest are preserved separately, without substituting lost inputs. This
new protocol changes scope. It uses OpenSSL's ASN.1/CMS implementation and
supplies no UTC interval, even if Accuracy is present. The Oct 29 invented-byte
DigiCert/FreeTSA probes verified signatures but omitted Accuracy. Current
CP/CPS 7.09 section 6.8 did not establish the older indexed one-second bound.
Those historical probes are not a blind test or eligible forecast sample.

## Closed acquisition and inputs

Freeze this text and its exact input manifest; commit and push before the one
live capture. Start promptly afterwards, without selecting a favorable rate
or settlement window. Fixed archive: data/m090_content_v2, exactly one packet.
Maximum five public requests: two fresh HTTPS CRLs, MEXC displayed funding,
MEXC history page one (20 rows), and one DigiCert RFC3161 timestamp. The fixed
endpoints, policy OID, signer DER pin, public root/intermediate material and
all direct Python inputs are hashed in inputs.json. No private credentials.

20-second HTTP timeout, no retries/redirects, 1 MB per response and aggregate
response bytes; archive capped at 4 MB. Timestamp request sends a hash and
nonce to the documented HTTP endpoint; signature/pin checks authenticate the
reply. Market and CRL requests retain standard HTTPS verification/proxy.
No historical bulk/reserved data, private API, book, fills or orders.

## Publication, verification and restart

An exclusive writer retains raw bodies, URL and local wall/monotonic request
bounds (UTC unverified), fresh CRLs and normalized CRL bytes. Parse exact
nextSettleTime and newest preceding provider-reported page-one settleTime;
never assume an eight-hour interval, round/floor ids, or replace missing
events with another event or zero. Rates are fractions per reported event.
Page-one identity is not authenticated history/schedule completeness.

Exclusive files are flushed/fsynced together with directories. A random
256-bit manifest nonce binds the capture; a canonical journal record commits
its hash with sequence 1 and zero predecessor. The signed checkpoint binds
the exact journal bytes. A SHA256 RFC3161 query requests the fixed policy and
positive nonce. Verification requires identical content/query/nonce/policy,
the exact signer, certificate chain and timestamp EKU, plus CRLs valid at the
signed genTime. The selected provider uses second-resolution genTime; other
formats fail closed. OpenSSL output is checked for unambiguous fields.

A signature is an operator-key/content-existence witness, not authenticated
exchange truth, public dissemination, physical durability, key-security audit
or independently proven UTC. Report Accuracy verbatim; never infer precision
from missing Accuracy, an old CPS, HTTP Date or the host clock. This version
always returns utc_interval=null, forecast_eligible=false, gate_eligible=false,
scoring_enabled=false, prospective_events=0. It has no forecast-loss scorer,
UTC admission, later-label pairing or scheduler.

The archive audit checks exact file set, hashes, manifest, journal bytes,
checkpoint and signatures. Retain the head in an externally committed result
receipt. A repeated completed capture audits without network calls. Incomplete
files, partial tails, unexpected files, symlinks and oversized archives block
the lane and remain retained. No truncation, deletion or automatic refetch.

## Stopping, outcomes and counts

Stop after one capture, a head-pinned offline audit and a completed-id replay.
Publish raw-byte hash inventory, signed metadata, exact parsing, actual result
receipt equality, and a compact immutable public packet bundle for reviewers.
Do not retake a failure until it passes. Report any partial capture as such.

Native terminal status is DONE/DATA_PASS if content verification and input
parsing succeed, otherwise DONE/PARTIAL with the failure and retained bytes.
DATA_PASS is engineering only; M090 remains blocked for prospective inference.
Costs 1x/2x/3x: N/A, because no trade, capital ledger or loss/PnL is computed.
Strategy trials=0 and program trials unchanged. The append-only registry row
is a REGISTERED/PENDING snapshot; immutable outcome.json and FINDINGS record
the terminal result. Future clock/source/cohort/inference rules require their
own frozen forecast lane and trial accounting. Claude's R380-R389 and all
active forward journals remain untouched. No reserved read before its date.
