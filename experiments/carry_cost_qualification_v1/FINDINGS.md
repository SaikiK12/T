# R401 source qualification: PARTIAL / incomplete source body

The sole attempt ran after publication of the frozen protocol/code at
`ee6f1f7d7db50075d59884e4bf96d0b480a4e472` and the off-host consumed-attempt notice
in [room #7](https://github.com/SaikiK12/T/issues/7#issuecomment-6625617079).
The original plan and all frozen input hashes verify after the attempt.

## Observation

The first MEXC inventory GET returned **HTTP200**, not an access denial. Its body
reached the fixed **2097152-byte** cap, so completeness could not be established.
The worker was reaped, the exact partial body and receipt were retained, and the
collector stopped. No JSON inventory was decoded or source contract qualified.
KuCoin and both predeclared MEXC depths were not requested. All28cohort rows remain
in the report with missing-source reasons. There was no retry or larger request.

| Measure | Result |
|---|---|
| Requests |1 of4 permitted|
| Conservative body bytes charged |2097152 of5242880|
| Metadata inventories decoded |0|
| Depth snapshots requested |0|
| Pair execution cost at1x/2x/3x |UNKNOWN / UNKNOWN / UNKNOWN|
| Pair PnL at1x/2x/3x |UNSCORED / UNSCORED / UNSCORED|
| Predictive trials / prospective paper days |0 /0|

This result identifies a collection-design limit, not an unavailable public
endpoint or an economic NULL. A future separately frozen design can request
explicit contract endpoints, preserving this refusal and accounting for these
already consumed bytes; it cannot reset this attempt or label its inputs complete.
No conclusion about R391 profitability, owner's fees, executable fills or queue
position follows. No historical return or reserved sample was read.

## Evidence

- [Qualification](evidence/qualification.json), [request receipt](evidence/mexc_metadata.receipt.json).
- Raw compressed partial body SHA256: `3b371767cbc291d258e42ecd16ee521c66741b9cb6e851ac19c280d263418401`.
- Decoded-body SHA256 reported by receipt: `64c985ab3ff20d017bcc511e293cb0ae9c83cf14aac546f153229c50bb55793b`.
- [Frozen protocol](PREREG.md), [plan](plan.json), [started marker](qualification.started.json).

The protocol-local guard persists ordinary process interruption, but no storage
rollback/power-loss durability of that marker is claimed. The off-host notice
records the consumed attempt even if local artifacts are lost. The guard and
published refusal must not be removed to run again.
