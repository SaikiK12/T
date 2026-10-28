# R339 — PARTIAL: shared paper capital survives batches and recovery

**45/45 invented paths completed; independent oracle PASS, 24,602 checks.**
Freeze `96def32` preceded this corrected replay. The adapter normalizes monetary
spelling before R338's first snapshot; it leaves the strict account-state guard,
financial arithmetic, source clocks, fees, sizing, capital floors and risk policy
unchanged. All 34 previously complete R338 paths keep the same final per-asset
cash/NAV/known realized amounts. The original 11 failures remain intact in R338.

This is a verified account/execution component, **not a profitable strategy**.
Actual executable expected return is UNKNOWN. Predictive strategy trials0,
prospective days0, orders/activation false; program denominator9,479,013 unchanged.

## Concrete behavior and control

In the 1,000USDT invented account, model A reserves522USDT. After restart, model B
asks for another522. The frozen R334 stateless comparator admits B against its
single-batch budget; the durable coordinator rejects it because capital and gross
are already committed. After A's actual partial fill, confirmed cumulative
cancellation, close and terminal release, the next522 allocation is admissible.
This behavior is identical at all three registered execution-cost tiers.

The other finite cases cover pending symbol/venue ceilings, same-sign shared
basis, cancellation with missing final total, crash-visible financial joins,
crash between risk and admission, global trade ownership, unknown fee/funding
resolution, gap/late-fill exposure, weak/uncalibrated forecasts, segregated
MEXC-USDT/Lighter-USDC cash, shorts, observed loss then price recovery, and an
observed overfill. All event quantities/actions and fixed expected decisions
were registered before replay; no tier or favorable path was selected afterward.

Requests and full trade quantities never imply terminal fill success. Release
requires own flat quantity, explicit terminal cumulative reconciliation and known
cash. The full original reserve remains a floor through partial execution.
An unjoined fill blocks later writes until explicit recovery; that recovery keeps
the original first clock. Unknown amounts preserve known components without
turning them into qualified cash. A later recovered price does not erase an
already observed persistent risk stop. New entry remains gated after resolution.

## Cost sensitivity and money interpretation

Every listed amount is an **invented accounting diagnostic in USDT**, not measured
expected or prospective return. These are all five registered paths that actually
complete a filled flat round trip; other inactive, open, incomplete-source and
failed-intent paths remain in the artifacts and are not treated as profitable0.

| Registered path | Net at1x | Net at2x | Net at3x |
|---|---:|---:|---:|
| Partial fill, close/release, later allocation | -2.400 | -4.800 | -7.200 |
| Two models sharing a pooled basis | -54.552 | -59.108 | -63.668 |
| Crash before cash join, explicit recovery | -1.200 | -2.400 | -3.600 |
| Unknown fee/funding, then source resolution | -1.400 | -2.600 | -3.800 |
| Short flat-midpoint round trip | -2.400 | -4.800 | -7.200 |

For the unknown-amount path, price PnL is -1/-2/-3, fees are0.2/0.4/0.6, and
funding is a fixed -0.2 at1x/2x/3x respectively. Thus the known final cash is
998.6/997.4/996.2 from1,000. No principal is spent as a cash expense; collateral
and planning reserves are counted once. Spread is already reflected in the fill
prices, not subtracted a second time. Fees/spread scale with k; funding does not.
The same supplied favorable forecast never credits that forecast to actual cash.

## Validation and reproducible artifacts

- Before the correction freeze: **1,526 tests PASS /three skips,197.070s**. Four
  new regressions reproduce the old failure, preserve exact normalized values and
  clocks, reject real cash changes during pending assessment, and refuse silent
  adoption of an old journal. R338 had1,522tests/three skips before its own freeze.
- The unchanged standard-library Fraction oracle validates all45 paths and
  24,602 assertions. Its thin R339 wrapper additionally compares all34 old
  completed paths' financial amounts. No production financial, allocation or
  execution function is imported by that oracle.
- Two fresh-directory reports produce byte-identical result JSON and journal
  gzip bytes. `results.json.gz` is deterministic gzip of the original JSON;
  decompressed SHA256:
  `001356299db3fe7b774c9cddb70cb87f43d5c4526c69771416b3e5118df4c1c2`.
- `journals.json.gz` retains every source/account/risk/control journal. SHA256:
  `a50ca09c47881c14b713146828715b5abd1c2871cd8e3be872b68d77801353cd`.
  `audit.json` contains the complete independent result, no discarded failures.

```sh
python scripts/run_opportunity_execution_v2.py --out .cache/r339-fresh
python scripts/check_opportunity_execution_v2.py --out .cache/r339-fresh
```

Use a fresh output path and the pinned Python3.12.14 closure. Production caller
entry is `lab.opportunity_execution_v2.OpportunityExecutionV2`; the old R338 entry
point has the known spelling defect. The adapter binds a new account-id suffix
and does not migrate/repair existing journals. Results/forecasts/marks are invented
and this diagnostic does not authorize deployment into another existing account.

## Remaining boundary

The component handles one cooperating local writer and a fresh dedicated account,
same-sign linear perpetuals only; maximum four opportunities/call,64active,
eight submissions/allocation,12h horizon and40decimal places. Attributed money
uses the actual account's pooled basis, not fictional per-model PnL. Conservative
original floors can reduce usable capacity after a partial fill. There is no
opposite-direction hedge-mode contract or distributed/host-failure transaction
guarantee. Financial rejection stays visible rather than rewritten.

Risk observations are explicit caller operations, not a continuous monitor or
guaranteed close/schedule. No collector is connected automatically. The source
report contracts remain unauthenticated. Real synchronized quotes/depth, sessions,
owner fee terms, actual source fills, calibrated forecasts and fair/index funding
notionals still prevent a new executable expected-return/paper claim. A frozen
prospective strategy protocol and new on-time observations remain necessary.

Market/source requests0, downloaded market bytes0. Historical budget remains7757
requests/reported229.85MiB; the66-request source batch remains closed. R310/R311,
Claude's R337/forward work, old journals and the single canonical queue are intact.
No order, money, secret, model download, PR merge/closure or permanent execution.
