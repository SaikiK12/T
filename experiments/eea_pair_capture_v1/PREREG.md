# PREREG: eea_pair_capture_v1, bounded public paired observations

Freeze with `lab.prereg.freeze()` before operational activation. Never edit a frozen input.

- **Registry id:** R419
- **Owner (single writer):** Claude's operational container, only after explicit operational activation.
- **Implementation owner:** Codex, codex/france-carry-execution-20261106
- **Date registered (UTC):** 2026-11-07
- **Canonical method:** M488. Related M439 and M485 remain separate questions.
- **Claim:** issue #7 comment 6693130896; this is a new raw-data writer, not a change to an existing writer.

## Question
Can one operational writer preserve bounded public BTC/ETH Coinbase CDE and
Kraken raw books/rate metadata, with independent receipt clocks and no invented
funding cashflow, to make a later European carry experiment possible?

**Collection only, zero predictive trials. Not an economic paper strategy.**
No capture is run in Codex's container. Unit tests use synthetic temporary
directories and injected HTTP responses. The default CLI is inactive.

## Universe
Exactly **BIP-20DEC30-CDE / PF_XBTUSD (BTC)** and
**ETP-20DEC30-CDE / PF_ETHUSD (ETH)**, raw USD-listed linear product observations.
Named CDE contract sizes are **0.01 BTC / 0.1 ETH**; their metadata will be
revalidated on each packet and agree with the public product-specific SID.
This does not certify the owner's eligibility or eventual book/funding cash
units. No asset scan or winner.
Daily Kraken instrument metadata contains its full public rule catalog; only
the named pair identities/EEA schedules are validated, no other market data is
queried, ranked or scored. No reserved path, MEXC-only coin or 2020 row.

## Data
Closed inputs in `inputs.json`: implementation, CLI, configuration, source
qualifications and captured plumbing evidence, runtime pins, shared freeze
helpers and copied gates. Every byte must be committed and verify before/after
an operational invocation. Immutable new output lives only under
`data/recorders/eea_pair_capture_v1/`. Nothing reads or writes existing journals.

The **only** requested URLs are the fixed allowlist in the module: named CDE
public product/book, named Kraken public ticker/book, plus daily public Kraken
instrument rules. Only unauthenticated GET; urllib's normal UA; no redirects,
cookies, keys, accounts, orders, host overrides or retries within a packet.
Denied CDE history host `api.exchange.fairx.net`, OKX and One Trading are absent
from the allowlist. No historical query can spend or reset the old allowance.

Source qualifications already inspected only schemas, identity/rule metadata,
counts and timestamps. Their asynchronous old bodies are not a paired forward
sample. [Preflight counts](preflight_counts.json) validate nine existing source
shapes without any price/rate summary, sweep, return or source-recorder run.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Raw CDE product/rate metadata | full public product JSON | BIP/ETP on CDE via Advanced; raw published strings, contract size in base units | One observation per UTC-hour slot | Separate wall/monotonic request start and response receipt; native timestamps preserved | No trading decision in this protocol | Fixed current names agree with source SID; owner entitlement unverified | Zero stays a present value; missing stays missing; no settlement or APR conversion |
| Raw CDE book | pricebook with native price/size rows, product id/time | Same named CDE products | Up to 100 levels/side as provided; empty arrays retained | Same independent clocks; API payload/time unaltered | Not a fill | Captured source depth only; no liquidity extrapolation | Missing side/id mismatch stops; empty is explicit, not filled from older data |
| Raw Kraken ticker/book | native absolute/relative current and predicted rates, marks/index, book arrays | PF_XBTUSD/PF_ETHUSD | Same hour packet, separately received | Native and local clocks remain separate; book id bound by exact request | No assumption of simultaneous venues or whole-hour state | Fixed named products | Never merge current/predicted or treat a snapshot as settled funding |
| EEA risk metadata | full instruments payload; named marginSchedules.europa.retail | Kraken current public rules | First successful packet per UTC date; later packets link it | Its own request/receive times | No risk computation yet | Current forward capture, no old-tier reconstruction | A failed metadata response never supplies the daily cache; missing EEA identity stops |
| Provenance/counters | raw body hashes, START/END events, code/config/freeze ids | Local append-only writer | Bounded campaign, no rows overwritten | UTC ns plus monotonic ns per request | Availability bound for a later experiment, not alpha evidence itself | Captured/observed vintage only | Incomplete START keeps worst byte reservation; cut journal stops without repair |

No predictor, derived financial feature or cross-sectional score. A subsequent
strategy must freeze independently; collecting dates before that does **not**
automatically make them unseen strategy evidence or gate-1 days.

## Rule or search space
One finite collection campaign **2026-11-07 00:00 .. 2026-11-14 00:00 UTC**,
at most one packet per UTC hour (**168 slots**). First packet of a UTC day has
up to **13 GETs**, subsequent packets **12**. Each packet first requests the
product/ticker/books, waits a fixed **3 seconds** after that whole initial
group, then requests the same four books again. Actual per-book elapsed times
are in the independent receipts, never assumed to equal three seconds. This is
a planned second observation, not a retry of a failed request. It preserves
depth disappearance/replenishment for a later latency-aware execution test;
two L2 snapshots cannot identify individual orders, fills or spoofing intent.
No depth statistic is calculated here. The original cumulative caps are kept;
extra book observations can shorten the campaign. No scheduler or daemon is started by
this implementation. Claude alone may add the verified CLI to his existing
single writer loop; that activation has not been performed here.

Output creation is exclusive per hour; a second invocation returns without
network. A nonblocking file lock enforces one writer. Requests have durable
START reservations **before** network and END receipts afterward. Each raw body
and per-hour counts file is new/exclusive, raw JSON body bytes hashed before
gzip. No deleting, compacting or rewriting data. A crash's unfinished request
remains conservatively charged; a cut journal is never silently repaired.

Hard stops from `capture.json`: **1,351 requests** total, **16 MiB client-read
body allowance**, **8 MiB stored directory cap**, **256 KiB response cap** or
**1 MiB** for daily instrument rules, each with the one-byte overflow sentinel
reserved. These are small prospective ceilings, not a new historical allowance
or a promise the whole week fits. The first binding budget/window ends capture;
no automatic extension/reset. The protocol has no permission for paid/bulk data.

401/403/404/429/451, redirects, HTML/bot responses, overlarge bodies and identity
or schema drift stop further packets pending new review. Other transient
network/5xx failures end the packet; another UTC-hour slot may retry within the
same accumulated caps, never the same hour. Preserve failed bodies/receipts.

Registration/freeze occur on 2026-11-07 after the planned window opens. No
campaign data was collected before the freeze. Elapsed slots stay missing;
there is no catch-up or backdated capture. Actual collection starts only after
the committed freeze and Claude's operational activation, if he activates it.

## Splits and cost
No return, split, entry, exit, fee charging or PnL. **Costs 1x/2x/3x: N/A,
not zero.** The source note supplies the public future fee inputs, including
CBFSE's per-contract fixed charge, for a later economic protocol. No fee
benchmark is converted into expected profit by this data collector.

## Gates
Engineering acceptance only: synthetic tests pass writer exclusion, same-hour
deduplication, immutable bodies/hash provenance, zero-vs-missing rates, identity
drift, empty/disappearing books, the fixed second-observation delay and end-of-
window refusal after that delay, accumulated request/byte caps, crash reservations, refusal
of private/denied endpoints and inactive CLI. Counts-only old-source preflight
must match the fixed identities. These checks do not certify deployment,
source settlement units, paper fills, capacity, profitability or account access.

## Null
Not an inferential test. No SIGNAL/NOISE, p-value, model fit or fee-reduced
rescue of R418. Missing data and failures remain explicit. No scored market
measurement will be performed by this lane, including after activation.

## Multiplicity
**0** predictive trials. Program trials at registration: **9,784,345**; report
the current `registry.program_trials('registry/rounds.csv')` with native status.
This is bookkeeping, not a cross-family statistical correction.

## Evidence lineage and admission (future lanes only)
M488 primary EU disclosures/fees and live public endpoint qualification;
R418's already-seen Kraken metadata/books supply old-schema preflight evidence.
R418's weak economic result motivated the new two-perp data question; it is not
being retested or improved after observing it. Old quote files are asynchronous
and do not score this source campaign. No reserved/data-gated parent is read.
Copied gates are hashed. No calibrated dependent null, power, trimming,
leave-two-coins-out, prospective strategy day or cross-family admission exists.
Nothing invokes go_real or authorizes money, a new account or credentials.

## Stop rules
Only this finite source campaign, one writer/packet per hour, no score. The
collector is **not activated** in this PR. Do not run it here to prove it can
fetch; its real endpoint shapes were already qualified by bounded plumbing.
Any changed frozen code, URL, limit, date, identity or later trading idea needs
a new R-id. Do not change operations.py or another writer's file in this lane.
Native FINDINGS records code-ready/not-started status; append-only registration
records pre-activation REGISTERED/PENDING and is not rewritten afterward.

## Frozen input manifest

bf8c7c3da424a1fde23406ce7fe8725456ef24b11ee6c6b6b132d60f9e52d0ec  experiments/eea_pair_capture_v1/inputs.json
