# PREREG: R339 canonical-mark correction of the R338 paper bridge

- **Registry id:** R339
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-27
- Claim: https://github.com/SaikiK12/T/issues/7#issuecomment-6431896811

## Exact known failure and finite correction

R338 freeze6323593 yielded34 completed/11 failed invented paths. Its durable
request normalizes Decimal spelling, but the initial financial snapshot uses the
caller's original mark spellings. The strict account-state hash can reject equal
amounts after re-reading the normalized request. All original failures, frozen
files and provenance stay intact in opportunity_execution_v1. These fixtures
are now SEEN engineering inputs, not new unseen financial evidence.

Add a thin NEW OpportunityExecutionV2 adapter over the unchanged R338 coordinator.
Before calling its original admit, reconstruct each typed CloseMark with the
same exact normalized Decimal spellings used by its durable request. Preserve
values, clock, quantity, source timestamp and source identity. Do NOT change
PaperAccount, R334, the account-state guard, receipt deduplication, capital floors,
risk policy, quote guards, model forecasts, event quantities, costs or any source.
Inherited explicit risk observations call this same adapted admission method.

Bind suffix `|canonical-marks-v1` in the dedicated account id; this adapter cannot
silently open/adopt a prior R338 coordinator journal. No migration or repair of
old journals is authorized. This preserves the existing evidence component and
receipt schema, not an additional cash ledger. It is still one cooperating local
writer with the limitations and bounds in R338's frozen PREREG.

## Frozen identity and identical inputs

- code_inputs.json SHA256 8266b74067c35ac32589d38293d2b5401c0a07386e4547a1808a3dcf001ce088
- data_inputs.json SHA256 02fbb6e635678c52b0788f7cb8e6a2a0759cf39aa587a452faf8726d234fcac1
- fixtures.json SHA256 103f188232c2d23e202c901775e8bbdc25135ea591bc67a647b5dfc487027ea6

Pin R338's entire 22-file closure plus the new adapter, fixture construction,
driver/checker wrappers and regression tests. Pin R338 spec, retained failed
results, journals and oracle audit as prior known evidence. R339 fixtures.json
must be byte-identical to R338 fixtures.json: no new favorable cases or removed
weak/unknown/failure cases. Both driver and unchanged independent Fraction oracle
verify R339 hashes before and after execution. Freeze and commit before replay.

Reuse R338's exact 15 named invented cases, each at 1x/2x/3x, total45 dependent
engineering paths. Inherit EVERY operation, fill rule, risk observation, injected
failure, expected inclusion/release and output capture from the frozen driver;
only construct the fixture with the new dedicated adapter. Same R338 toy risk
policy, account balances, first clocks, source identities and stateless R334
control. Quantities/actions fixed, no outcome/parameter/model selection.

For costs, fill price=mid+signed order side*k*half-spread, fee=abs(base)*price*
10bp*k; marks use the opposite bid/ask and exit fee at k. Preserve original 3x
planning reserve for every tier. Funding amounts do not scale with execution
costs. All fees/funding/price components are quote amounts in their own segregated
asset; no USD/USDT/USDC aggregation or capital/leverage change.

## Checks, result and exclusions

Four pre-freeze regression tests: reproduce original R338 spelling failure and
same-value adapter success; normalization idempotence/exact high-precision values
and first clocks; a genuine financial-state change STILL blocks a pending
assessment; and old journal identity cannot be silently adopted. Run the complete
unittest suite before the new lab code commit.

After commit run the finite reporter, the UNCHANGED R338 independent rational
oracle via a thin wrapper using R339's manifest, and byte reproduction in a fresh
directory. The oracle imports no production accounting/execution/selection code.
Its original scope includes journal hashes/prefixes, first-clock joins, original
capital floors, cost thresholds, fill stress, pooled accounting, unknown cash,
segregation, conserved collateral and terminal release. Keep all failures and
check counts. Do not edit any frozen code to improve the resulting verdict.
The wrapper also compares final per-venue/asset cash, NAV and known realized
components on every previously complete R338 path using exact Fractions; the
correction must not change those amounts. Prior failed paths remain retained.

PARTIAL means a checked reusable component; actual executable expected return
remains UNKNOWN. R338 failures remain a prior result even if this correction
passes. The invented same-input replay cannot supply calibrated uncertainty,
market edge, independent strategy evidence, new prospective days or activation.
Report final toy price/fee/funding/exit costs without calling them realized market
gains. Literal positive supplied forecasts are not measured expected returns.

All R338 contract limits remain: fresh dedicated perpetual account, same-sign
inventory, four opportunities/call,64 active, eight submissions/allocation,
12h maximum horizon,40 decimal places, explicit source terminal/cash resolution,
caller-driven risk observations, no continuous scheduler/forced-close guarantee.
Actual sessions/fees, authenticated synchronized books/fills, calibrated forecast
error and fair/index funding notional still block actual paper evidence. Do not
alter R310/R311, Claude's R337 or live forward journals, or the canonical queue.

Predictive strategy trials0; program9,479,013 unchanged. These are45 corrected
engineering paths, not45 new hypotheses or 100 completed enhancements. Prospective
days0, actual orders/activation false. Market/source requests0. Historical budget
still7757/8000requests and reported229.85/250MiB; the66-request public-source batch
remains closed. No orders, money, secrets, weights, new market archive, merge or
PR closure. Append one R339 row with exact outcome using the registry helper.
