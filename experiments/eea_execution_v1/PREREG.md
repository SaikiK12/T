# PREREG: eea_execution_v1, fixed CDE/Kraken displayed-depth cost screen

Freeze with `lab.prereg.freeze()` and commit before decoding any source depth
for this measurement. This file and every hashed input are immutable thereafter.

- **Registry id:** R421
- **Owner (single writer):** Codex, isolated codex/eea-execution-20261107 worktree
- **Date registered (UTC):** 2026-11-07
- **Claim:** issue7 comment6702227320; M488, engineering execution evidence

## Question
What conditional entry and immediate-round-trip friction does the first R419
CDE/Kraken BTC/ETH packet display, at the real published regular tariffs and
fixed contract granularity, without guessing raw CDE quantity semantics or
converting incomplete displayed depth into executable capacity?

## Universe
Only BTC BIP-20DEC30-CDE / PF_XBTUSD and ETH ETP-20DEC30-CDE / PF_ETHUSD.
These instruments were fixed in R419 before its first collection. No asset
selection, delisted comparison or cross-sectional primary score. This is a
current venue-own pair, not a survivor-free historical trading universe.
`cases.json`, `source_manifest.json` and the closed input manifest are hashed
below. The six per-leg notionals are5k/10k/12.5k/25k/50k/100kUSD. Added5k and
12.5k explicitly map the owner's10k/25k total accounts to two separate equal
cash wallets. The original four claimed execution targets remain reported;
100k per leg implies200k total cash and is outside the owner's capital range.

## Data
One existing forward-captured packet, **20261107T04**, generated after R419 and
R420's committed freezes. Exact bytes copied from canonical state commit
`686be7fb3982f4d4170bb970a212728cb1428540`, not acquired again. Thirteen copied
files total73,149 compressed bytes; only file hashes/counts and native schema
counts were inspected before this freeze, no price/depth cost or return.
`source_manifest.json` binds the original paths and copied hashes. The native
START/END journal binds URL, complete HTTP200 body SHA256 and UTC/monotonic
receipts. New runner verifies these before interpreting any book.

Raw Coinbase books are100 levels per side, with named products. Kraken's book
symbol is bound by the request receipt, not echoed by the book body. CDE
contract sizes0.01BTC/0.1ETH and whole native increments come from the captured
metadata and European SID; Kraken quantity precision comes from the captured
instrument. Raw quantity convention for CDE's book is not certified: report
both **native contracts** and **base-asset quantity** hypotheses. Reject a
convention implying fractional displayed native CDE contracts. Do not select
the hypothesis with the cheaper cost or larger apparent depth.

Public regular tariffs are held at the captured/current source vintage:
CFSE **0.02% of fill notional +0.12USD per native contract per side**, primary
Fees and Charges updated2026-09-30, read2026-11-07; Kraken **Tier1 taker0.05%**,
primary cross-platform table updated2026-10-30, read2026-11-06. Exact URLs,
organizations, read scopes and limits are in `tariffs.json` and the frozen
parent source notes. No owner's fee tier, account entitlement or fee preview.
Funding fields, historical funding, mark returns, margin tiers and settlement
prices are not used in this execution-only measurement.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Normalized depth | exact price/size levels, two fixed size hypotheses | CDE BIP/ETP and Kraken PF_XBTUSD/PF_ETHUSD; USD/base and base quantity | first and delayed books from one packet, never mixed into a simultaneous book | native receipt journal UTC/monotonic, computation only after freeze | descriptive after capture; no historical or live trading decision | forward-captured named pair fixed by R419 | aggregate duplicate prices, omit zero size, reject invalid/crossed/empty book; never extrapolate |
| Matched quantity | target per leg, maximum of the two mids, contract lots | same pair, fixed base units | each snapshot separately; same quantity at all cost multiples | computed after freeze | no executed decision | same limited snapshot | round down to exact common lot; minimum failure is not a free trade |
| Fill quote and drag | supplied side depth, own-venue mid | USD per leg, no basis credit | walk each existing side best-first | as above; actual sequential source timing retained | no guarantee of fill or persistence | only displayed sampled depth | preserve partial quantity, unmatched exposure and unknown full cost |
| Execution fee | fill quote, actual filled CDE contracts, tariff vintage | CFSE percent plus USD/contract; Kraken percent | per-side regular taker scenario | current published tariffs, held fixed for packet | no owner account/preview certificate | current fee-source vintage | no missing fee treated as0, no maker/VIP assumption |
| Immediate round-trip friction | both directional entry frictions | USD, bp of one-leg mid and of initial2N cash | consumes each bid/ask side once within the same snapshot | computed after freeze | diagnostic cost proxy only | no actual future exit or same-time matching guarantee | full cost only if all four sweeps complete; no depth refill or 3-second profit |
| Receipt gaps | native received clocks | original host UTC/monotonic nanoseconds | observed initial/delayed response times | original receipts retained | no on-time alpha label | sequential capture, 3-second group wait is not a fixed per-book latency | no invented common timestamp |

## Rule or search space
**144** fixed coin/unit/phase/target/cost scenarios:2coins x2raw-unit hypotheses
x2snapshots x6notionals x3cost multiples. Both entry directions are reported
within each scenario. This is an execution sensitivity table, not144 trading
strategies or a search for a winning cell.

Reuse R417's immutable `Book`, `common_quantity` and `pair_sweep` arithmetic.
Q=floor(N/(max(midCDE,midKraken)*common_lot))*common_lot. Initial cash isN on
each venue, total2N, before fees. This denominator is always explicit; account
leverage, collateral offsets and funding earnings are not inferred. Source
size normalization aggregates identical price levels and sorts best-first.
CDE's fixed fee is charged per **filled native contract**, never per BTC/ETH
unit and never once per order. Preserve partial fills and unmatched base.

For each side, drag is its adverse quote deviation from that venue's mid.
Entry friction is both drags plus both fees, only if both legs are fully
displayed. Sum both directions to obtain the hypothetical same-snapshot
round-trip friction. Cross-venue mid differences are never credited as a
profit. First and delayed books are separate diagnostics: no3-second trading
gain, disappearance-intent inference or simultaneous-execution claim.

## Splits and cost
No return split or hypothesis test. Report **1x/2x/3x** by multiplying deviation
from each venue's mid, the proportional fee at the stressed quote and the
per-contract fixed fee, with quantity and supplied depth unchanged. Those
synthetic stressed prices are not recorded market prices. No estimated maker
fills, borrowed cash, zero spread, liquidation fee for a regular trade, funding
income, currency conversion or spread extrapolation. A future economic lane
must supply their actual applicable mechanics separately.

## Gates
Before a run: frozen closed inputs, full synthetic suite, integrity and staged
catalogs. Commit this protocol and its closure before any market measurement.
Exclusive `results/RUN_STARTED.json` precedes decoding. One runner invocation;
any failure consumes this lane, and no marker is removed. The independent
Fraction checker runs once on saved results and must match every available
quantity/quote/drag/fee/cost within **1e-12USD**. It imports neither execution
implementation. A failed check is recorded, never repaired by changing inputs.

There is **no** alpha, legal-access, margin or executable-capacity PASS gate.
All rows are conditional source scenarios even if fully displayed. A future
paper/real admission requires verified units, funding cash, mark/fixing rules,
multiple genuine prospective observations, effective margins and actual
execution evidence. No order/account/credential or other source acquisition.

## Null
No predictive null or p-value. Empty/invalid source, unit inconsistency,
unfilled depth, unknown full cost and arithmetic failure stay explicit. Zero
cost is never substituted for a missing observation. Neither a complete book
nor high apparent capacity demonstrates profitable carry.

## Multiplicity
**0 predictive trials**, program total at registration **9,784,345** via
`registry.program_trials('registry/rounds.csv')`. The144 sensitivities are all
reported with no winner/admission and are not claimed independent trials.
This bookkeeping is not a multiple-testing correction for any later strategy.

## Evidence lineage and admission
Canonical M488; R417 arithmetic and R419 raw collection are direct parents.
R418's NULL is not retested and its spot fee is not used. Source qualification
MDA hourly-rate convention is separate and is not transferred to Advanced.
Only the already captured first packet enters this lane; later packets,
R404's gated book window, protected2020 and all reserved coins remain unread.
No prospective alpha day, across-family selection control, trimming,
leave-two-coins-out or80%-power claim: there is no return series. The copied
GATES is hashed, and every monetary/execution admission remains unmet.

## Stop rules
One closed run, one independent verification, no additional packet, target,
unit convention, fee, haircut, source or parameter after results. Source or
code change requires a new id. No native journal or parent input is edited.
No historical archive read, endpoint retry, source-budget reset, live tick,
real trade, new account, credential, paid service or subagent.

## Frozen input manifest

ae0d583df1a295539125c6e778788584729f7e0b58a87aaffb7aa516ae515e9b  experiments/eea_execution_v1/inputs.json
