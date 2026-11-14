# R403: two official metrics archive schemas and time labels

Registry id: R403

Source-engineering qualification only. Predictive trials:0. Prospective paper
days:0. Registered in room#7 before any archive request. Freeze and publish the
protocol, exact plan and code before one capture; append one final registry row
afterwards. No numerical metric values, prices, returns, labels for forecasts,
fitted model, reserved sample or strategy comparison is interpreted.

## Question and fixed sources

Can two exact old official Binance metrics objects be retrieved, verified with
their companion SHA256 checksums, and their schema/raw create_time labels read?
The fixed objects are BTCUSDT daily metrics2026-06-24 and2026-06-25. These dates
are selected to qualify community issue491's reported label-range difference,
not by PnL. The community report is not exchange confirmation of semantics.
This is not an audit of every historical symbol or the missing daily_v2 panel.

Order: June24checksum,June24ZIP,June25checksum,June25ZIP. At most4public GETs,
65536bytes per response and262144bytes total reservations. A new distinct tiny
Binance metadata scope under the owner's latest request to obtain missing data;
no renewal/reset of any R310/R311 or blocked R401/R402 allowance. Dispatch window
30seconds, worker3seconds,5seconds reserved per attempt including cleanup. Recheck that a full reservation fits
after journal locking and before transport; cancelled reservations remain charged.
No keys, auth, retries, redirects, pagination, alternate host or substituted day.
Stop all dispatch on access/backoff/incomplete-body/transport/budget failure,
invalid checksum, hash mismatch or unsupported schema. Preserve every raw body,
receipt, byte reservation and failure. No interrupted attempt may be resumed.

Protocol-local exclusive started marker is file/directory-fsynced before any
request, with an off-host BEGIN notice before launch. Append-only BudgetJournal
reserves before dispatch and never refunds. Output path cannot reset the attempt.
No protection against external deletion or storage rollback is claimed.

## Parsing and unknown semantics

Accept only stored/DEFLATED compression. Each ZIP must have exactly one
expected regular unencrypted CSV member, no
traversal/symlink/duplicate member, compressed cap65536bytes, expanded cap131072
bytes checked against actual bytes, exact eight unique columns and at most400
rows. Interpret only the header, exact BTCUSDT symbol and strict create_time
labels; keep every numeric metric cell opaque. Require labels between declared
calendar midnight and the inclusive next boundary. Compare unzoned strings on
an explicitly declared UTC calendar; the source timezone/clock is not proved.

Record row count, raw/first/last/min/max labels, duplicates, ordering, adjacent
steps different from300seconds, and labels shared across the two files. Never
silently deduplicate, shift or fill. A label-range difference alone cannot prove
start/end-period semantics, source availability, revision vintage or full
historical coverage. Those remain UNKNOWN even if the pattern matches issue491.
Do not apply an automatic five-minute correction to any old lane or new input.

## Decision and reporting

DATA_PASS means both exact archives pass checksum/schema/label parsing without
a global stop. It certifies only this narrow input qualification, regardless of
which label ranges are observed. Otherwise PARTIAL, with the source failure
stated. Gaps and duplicates are reported; this is not a completeness gate.
No strategy promotion, new predictive trial, new paper day or historical truth
is earned. At1x/2x/3x total net costs/PnL remain UNKNOWN, no actual orders or
activation. Reverify all declared input hashes after capture. Publish native
FINDINGS, raw identities, budgets and unknown fields in the source receipt.

## Frozen plan and inputs

Plan SHA256: 3404be27bafda10182b4d9122ebe299711e192e13f94b6feffebed7078818822

```inputs
f50159fad3f4319868eb38717b91d55843c41e9803014c8de05e116a6d0bcfdc  .python-version
0a5da0a741d8fa1280f0a8a5b2e08f1e4ced787565de8260bb0d53c101ea98bb  lab/acquisition_budget.py
3d6d7084f45b01e9e24669ec9914673cde56ca04cadea5cfe01ef22072f404bb  lab/mexc_depth.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
4cf65930e08965601cefe33b1785271bb024d22f39eac22582e5fd393bb2b466  requirements-test.lock
172a7e6b8d8cc60fd1c5d9c324d14124e6628a4faab97b342dd61d2415d491c2  scripts/qualify_carry_costs.py
112a585d3aa1cbe66ab01fc355ff0cd7e0a535773a17f14fcd3ba405ec49156a  scripts/qualify_carry_costs_targeted.py
5c5f022728fb9b72ef83683089c6040206eb3a829bce1e6e2bce617bbee848ca  scripts/qualify_metric_archives.py
```
