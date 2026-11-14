# PREREG: cde_rate_contract_v1, exact sampled Advanced/MDA field identity

Freeze with `lab.prereg.freeze()` and commit before comparing any source rate
values. Frozen files never change; changed mappings need a new id and sample.

- **Registry id:** R423
- **Owner (single writer):** Codex, codex/cde-rate-contract-20261107
- **Date registered (UTC):** 2026-11-07
- **Claim:** issue7 comment6708023686; canonical M488 source qualification

## Question
On the first eight complete R419 packets, is the outer Advanced
`future_product_details.funding_rate` numerically identical to the public MDA
rate at exactly its declared `funding_time`, with no fitted multiplier, time
shift, tolerance or future information at the original receipt?

## Universe
Only BIP-20DEC30-CDE / BIPZ30 and ETP-20DEC30-CDE / ETPZ30, fixed by R419 before
its first capture. Eight packet hours are fixed by chronology and availability
at canonical state83e432544fc2e66a6020eb3e623f6f1b4eadff98:
**20261107T04,T05,T07,T08,T09,T10,T11,T12**. The06slot is absent, never filled.
No coin selection, cross-sectional score or survivor comparison. `cases.json`
and exact copied source/input manifests are hashed below.

## Data
R419's original CDE product bodies, eight packet records and native request
journal:25copied files, hashes verified against the fixed state commit. Only
source identity, schema/counts and the first outer04UTC timestamp were inspected
before this freeze; no rate-value comparisons. The nested timestamp is absent
in that first product; it is not substituted for the pre-named outer field.

The old saved MDA history ends02UTC and cannot match the first04UTC capture.
One bounded counts-only intake therefore made **2** ordinary public GETs,
**5,420client bytes**, **32rows per asset**, **2026-11-06 07UTC..Nov7 14UTC**.
URLs, organizationCoinbase, undated data publication status, exact access/receipt
times, source identities, bodies/hashes and consumed one-shot marker are in
`research/intake/funding_notional_20261103/cde_rate_contract_20261107/`.
No auth, browser-UA spoof, redirect, denied-resource retry or new forward tick.
This is a small historical qualification, not a native live-journal writer.

Historical allowance was not renewed: `budget_before.json` rounds the old
reported229.85MiB to230MiB and deliberately charges every existing market-body
and receipt in the whole bundle again. Including worst-case2calls/65,538bytes,
its conservative total is **7,796calls /247,153,619bytes**, below the original
8,000calls/250MiB. Old exact bytes remain marked unknown rather than invented.
Actual new responses are2,720 and2,700bytes; schema/time counts only before
this protocol. Rate strings were preserved without summarizing their values.

The separate official frontend qualification establishes MDA's **display**
convention as an hourly decimal fraction (direct parse, annualization*8760,
percentage export*100). It does not establish broker cash or the Advanced
field's identity; that exact sampled mapping is the question here.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Advanced outer value and declared time | future_product_details.funding_rate/funding_time | Coinbase public CDE BIP/ETP metadata; original decimal string and ISO UTC | fixed eight already-captured source hours | native request START/END UTC and monotonic receipt, bodySHA | original value was received then; a timestamp later than receipt is unqualified | forward-captured fixed native instruments | missing/nonfinite/naive/non-hour timestamp rejected, no0 or nested-field substitution |
| MDA final-series value | funding_rate/event_time/symbol | official public MDA BIPZ30/ETPZ30 historical tails, raw string | captured32-row slices; only exact declared-time joins decide | first received after the original Advanced snapshots | ex-post source qualification only, not known at the original trading time | latest-vintage history, possible revision semantics unproved | duplicate/wrong identity/missing key rejected; unmatched final rows stay missing |
| Exact sampled equality | the two raw decimal fields at the same UTC instant | both parsers Decimal and Fraction independently | no lag/scale/horizon search | computed once after frozen commit | no trading decision or rate forecast | only the fixed eight observations per asset | exact numeric equality, no fitted tolerance or rounding |
| Temporal and variation qualification | declared hour, original receivedUTCns, matched raw fields | source metadata, not a return series | per original observation | original clocks retained; no cross-host monotonic subtraction | future timestamp is unqualified even if it later matches | finite sampled contract only | missing coverage and zero/constant observations cannot certify scale/time |

## Rule or search space
One mapping: outer Advanced field equals the MDA raw field at exactly outer
`funding_time`. UTC representation may be canonicalized, never shifted. Only
finite explicit decimal strings; absent/NaN is not0. JSON fractional literals
are preserved as decimal strings at parsing, never rounded through float.

Per asset, report all8 source rows and exact equality/missing/future flags.
Decimal equality must agree with an independent Fraction comparison. No
ratio estimate, optimal multiplier, lag scan, rounding tolerance, average,
annualized rate, funding difference, return or selection is computed.

Per-asset outcomes, in this fixed order:
1. Any declared time later than original receipt: UNQUALIFIED_FUTURE_TIMESTAMP.
2. Any exact numeric mismatch: EXACT_FIELD_MISMATCH.
3. Fewer/more than8 observations or any unmatched MDA timestamp: INCONCLUSIVE_COVERAGE.
4. Fewer than2nonzero matched observations or fewer than2distinct nonzero matched
   values: INCONCLUSIVE_VARIATION. Constant/zero samples cannot identify time/scale.
5. Otherwise: SAMPLED_FIELD_CONSISTENT.

Whole-lane SAMPLED_CONTRACT_PASS requires both assets consistent. Everything
else is UNQUALIFIED_SAMPLED_CONTRACT, with each cause retained. Invalid source
or parsing gives a consumed ERROR result; never repair/rerun this id.

## Splits and cost
No predictive split, financial return or trading decision. **Costs1x/2x/3x:
N/A, not0.** R421's actual execution-cost table is separate and is not rerun.
This source identity can neither pay those costs nor establish positive carry.

## Gates
Full synthetic suite, integrity, staged catalogs and committed exact closure
before source values are compared. Exclusive RUN_STARTED precedes loading
the rate fields. One invocation only; failures are preserved, never reset.
Native source URL/complete HTTP200/body hashes and original receipts must
verify, including the copied source manifest and public-tail receipts.

Even a sampled PASS is not global field stability, current source freshness,
historical settlement/mark-price identity, nonrevision proof, CFSE cleared
cash, executable capacity, legal entitlement or profitable strategy evidence.
It only supplies this observed data-contract component for a separately frozen
economic model. No go-real or paper alpha gate is met by this registration.

## Null
No financial null/p-value. A mismatch is a failed exact mapping hypothesis,
not evidence of no trading edge. Coverage/variation/source failures remain
inconclusive or unqualified; do not pick another time/scale on this sample.

## Multiplicity
**0 predictive trials**, program total **9,784,345** at registration through
`registry.program_trials('registry/rounds.csv')`. Sixteen fixed source-field
comparisons are all reported, not independent trading trials or alpha hits.
No across-family selection or confidence-of-profit claim.

## Evidence lineage and admission
M488; R419 raw collection, R420 canonical first capture and the official MDA
display-source extraction. R421 cost arithmetic is a neighbor, not remeasured.
All metadata/history parents predate this qualification freeze and supply no
prospective strategy score. The copied GATES is hashed. No dependent-null,
trimming/leave-two-out or80%-power estimate applies to this nonpredictive
contract test. Historical marks/cash, real fees over time, account/margin and
France eligibility remain separate requirements for any economic admission.

## Stop rules
One frozen mapping, sample and run. No new hour, field, asset, scale, rounding
tolerance or lag after outputs. No additional API request or wider history,
protected2020/MEXC-only/reserved sample, source-budget reset, denied endpoint,
paid data, order, account, credential, native journal edit or subagent.
One-shot intake is already consumed and cannot be reset for this lane.

## Frozen input manifest

e4fa1c96fbb9df72bee0cad7645a80f2b388da3cd317870120ea418d7b2c8b98  experiments/cde_rate_contract_v1/inputs.json
