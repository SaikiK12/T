# R401: current public-source qualification for the R391 carry cohort

Registry id: R401

Registered prospectively on 2026-11-04 in room #7. This protocol and its exact
source plan must be published before the sole capture. One final append-only
registry row records the attempt afterwards; no existing row is edited.

## Question and scope

Can the current public MEXC and KuCoin contract inventories describe the whole
published R391 symbol table, and can two deterministic MEXC snapshots supply
conditional one-way depth arithmetic? This is source/execution-input
qualification, not a strategy, historical rerun, fill calibration or alpha test.
No predictive hypothesis, return label, fitted parameter or reserved read.
Predictive trials: **0**. Prospective paper days: **0**.

## Fixed cohort and capture

Keep all 28 rows of experiments/reserved_batch2/symbols.csv, including missing
venue entries. Do not read saved trades/results or choose symbols by return.
The only depth candidates are BLEND_USDT and BP_USDT: the first two economic
keys, alphabetically, with both MEXC and KuCoin entries. No replacement when a
candidate is absent or unsupported. Quote notional:1000 USDT per one-way walk.

Order: MEXC contract inventory, KuCoin active-contract inventory, then candidate
MEXC depths in declared order if metadata qualifies. Depth limit20. At most4
public GETs,2 MiB per response and5 MiB conservative total body-read budget.
Network dispatch window20 seconds, each owned worker at most3 seconds plus
bounded cleanup. Partial/unknown tails consume their whole body reservation.
No retries, redirects, alternate hosts, keys, orders or authorization bypass.
Any access/backoff/transport/body failure stops future requests; retain partial
raw evidence and receipts. A protocol-local started guard consumes the attempt
before dispatch, even if interrupted. A different output path cannot reset it.

## Conditional conventions and unknowns

MEXC quantity is contracts multiplied by contractSize. Qualify symbol/base,
linear USDT quote/settlement, open state and published API flag from reported
metadata. KuCoin requires linear, noninverse, perpetual USDT identity and an
explicit multiplier/lot. Missing or unsupported identities stay unscored.
Reported eligibility is not authentication of the owner's account or access.

Walk the shown MEXC asks and bids separately with continuous quote notional;
report each VWAP and impact relative to that snapshot's mid. These are not
lot-rounded orders, observed fills, executable prices or future exit costs.
Require bounded ordered depth and a reported version/timestamp. No sequence
continuity, source-clock synchronization or arrival-time freshness is proved.
KuCoin L2 schema/units remain UNQUALIFIED, so pair execution cost stays UNKNOWN.
Account fees, funding, transfers, margin and collateral are not established.
At1x/2x/3x total pair costs and PnL remain UNSCORED; do not invent a fee or exit.

## Decision and reporting

DATA_PASS means both metadata inventories were received without stop conditions,
at least one cohort contract per venue meets the declared schema, and both
predeclared MEXC snapshot walks can be computed. It certifies that narrow input
qualification only. Every other outcome is PARTIAL in the registry; native
FINDINGS distinguishes unavailable access, incomplete data and schema refusals.
No source outcome admits or promotes R391 or another strategy. Preserve all
cohort rows and exclusion reasons, raw response hashes/bounds, local receipt
clocks and process cleanup receipts. Publish a source summary and limitations,
not a new ranking of trading candidates. Verify declared inputs again after run.

## Frozen plan and inputs

Plan SHA256: 02666c07e4eb8751c3b03c9a93b7003a6ac70083ef2b7b9743235c656d2749a8

```inputs
f50159fad3f4319868eb38717b91d55843c41e9803014c8de05e116a6d0bcfdc  .python-version
5ebfaec83a5c2c47831ec5fbf9b0e683ac3bdf0e88562caf99bfbb834c9ed748  experiments/reserved_batch2/symbols.csv
3d6d7084f45b01e9e24669ec9914673cde56ca04cadea5cfe01ef22072f404bb  lab/mexc_depth.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
4cf65930e08965601cefe33b1785271bb024d22f39eac22582e5fd393bb2b466  requirements-test.lock
172a7e6b8d8cc60fd1c5d9c324d14124e6628a4faab97b342dd61d2415d491c2  scripts/qualify_carry_costs.py
```
