# PREREG: source-bound encoded funding component and common-account integration

- **Registry id:** R322
- **Owner (single writer):** Codex; one bounded source reader/reviewer, no overlapping code writers
- **Date registered (UTC):** 2026-10-26

## Question and boundary

Can a conservative, conditional implementation reproduce the newly located
Lighter source funding equation, accrue OLD inventory before resize, prevent
overlapping/renamed receipts paying twice, and retain unknown cash in the same
paper accounting component? Canonical method M409; no new method/strategy.
Source application helpers narrow R321's gap; the full deployed/API cash bridge
remains UNVERIFIED. No R310/R311 or R320/R321 outcome is rescored or reclassified.

The received prover identifier is a tree object, not an attested deployed commit.
For supplied initialized encoded size q, multiplier Q, checkpoint C and market
prefix P, conditional collateral F=q*Q*(C-P); no second index/rate factor.
F/10^12 is conditional USDC collateral value, not authenticated paid API cash.
Use the conservative integer domain in contract.json; reject overflow rather
than invent circuit wrap semantics. Stale initialization, helper constraints,
full persistence, API encodings, actual prefix records and decimal epochs remain
unverified. The partial floor-margin component is not a second funding payment.

## Finite inputs and code identity

Bound manifest SHA-256 values are inserted before freeze below. No raw source
repository is published. Exact URLs/body/blob hashes, BUSL headers, received vs
read/unread ranges and missing mechanics remain in sources/source_receipts and
source_review. Fifteen calculation/test/input-verification files form the closed
code identity. The shared account CLI is a dispatch-only convenience; its engine
is frozen, and its actual reproduction is checked separately.

- `code_inputs.json`: `2e172606f76ab17327f2a2c1e9b65b9980fecb283cf75afc71a1cdebe9b1c269`.
- `inputs.json`: `a60e0bbd4f2ca4f4e62884768c77ddbb62bd82eaf9baefafbe821fbb28419410`.
- `fixtures.json`: `9a4d2208fe69ffbd88bf22fe60d646863f9cff250ef1280f4314bb6ca399aa0e`.
- `contract.json`: `e4d7b60c78a529e42840329168617e1356d8e0ba17dcf0f5f77643761b8d8c47`.
- `sources.json`: `095813f8a8cf2aa4617395fc46189e5a5f01b557c236c3391546c9a816a6cfbc`.

## Fixed engineering cases

All inputs are invented component fixtures, not historical/prospective markets.
Arithmetic: q in{-1000000,0,1000000,2000000}, Q in{1,100,10000}, C in{-1000,0,1000},
P in{-2000,0,2000}, mode in{cross,isolated}: exactly216 cases. Retain zero/negative
amounts; they do not establish inactivity or actual cash on a real account.
Partial margin component: old collateral in{0,1,999999,1000000,1000001} and
delta in{-1000001,-1,0,1,1000001}:25 cases. Compare exact rational floor arithmetic
for fixed entry quote only; imported circuit division remains unaudited.

Eight path definitions are fixed in fixtures.json: long,short,increase,flip,
close,isolated short,missing prefix,unverified encoding. Their14 total updates
are repeated at1x/2x/3x fees with registered-prefix and same-position/no-funding
controls:48 common-account runs,84 funding/alias receipt pairs. Every run uses
the EXISTING PaperAccount and append-only durable journal; reopening must match.
Provider labels and first-seen receipt provenance remain saved separately from
the stable financial start-state identity. Reused starts with changed endpoints,
sizes or mode require reconciliation, not another payment. A valid advanced
start has a new identity. Caller-declared states are not authenticated histories.

Each fixture declares1,000,000 size units per physical base, flat price100,
Q100, fee fraction0.0002 per filled notional, and $10000 initial total model
capital segregated $5000 each in MEXC-model and Lighter-model buckets. USDT/USDC
parity and base mapping are INVENTED declarations, not source-derived API units,
actual fees or executable prices. Charge all opens/resizes/closes; mark a remaining
position and future exit fee conservatively in the invented flat-price market.
No spread is fabricated or subtracted twice. Cost tiers scale fees only. Cash
reference has zero activity/net0; report components and total-capital denominator.
Different inventory paths are accounting stress cases, not equal-risk strategies
to rank. Physical-source exposure reconciliation is not established by this model.

Unverified/missing funding stays pending and withholds the complete net result;
its known component is not reported as a known zero total. Unknown states never
advance into a successful source transition. No strategy may be activated.

## Verification, inference and decisions

Ten predetermined financial hand tests and full unittest discovery precede the
code commit. The bounded review is limited to the exact module/test hashes,
not runner, full circuit, source authenticity or this full fixture family.
After freeze, use an independent literal Fraction reconstruction of all216
encoded products,25 partial margin cases and48 account decompositions, capital
denominators, saved journals and alias suppression. It shares source interpretation
and supplied inputs, not a separately executed Rust circuit or raw API decoder.
Reproduce deterministic outputs/journals byte-for-byte through the shared CLI
in a fresh directory; no existing output is overwritten.

PARTIAL means the bounded component checks pass while actual inputs/API/deployment
remain absent. A mismatch is a recorded failure requiring a new lane for changed
frozen code. No coefficient, sample or acceptance threshold is tuned to results.
There are0 predictive variants/trials and0 prospective days;216+25+48 engineering
cases and all84 update/alias pairs are reported, not hidden as strategy samples.
No statistical test, confidence claim, dependent-null transfer or multiplicity
waiver is justified by deterministic component fixtures. Program trials entering
this lane:9,478,938; R321 remains NOT_ACCEPTED. Market net return is unknown at
1x/2x/3x, even when an invented short/funding path has positive component net.

## Access and stop rules

Four static source GETs/322994 body bytes within declared4GET/1MiB/256KiB-per-body/
90s bounds, no retries/redirects/login or repository mirroring. No market/history/
account/RPC acquisition. Cumulative historical allowance remains7757/8000 requests
and reported229.85/250MiB spent, not reset. No orders, funds, secrets, weights,
merge/PR closure, inferred actual cash, reserved sample or permanent execution.
