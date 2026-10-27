# R338 — PARTIAL: durable account bridge, replay spelling defect retained

Frozen commit `6323593` preceded the diagnostic. The component closes R334's
missing cross-batch reservation/receipt bridge, but its direct entry point cannot
yet be used reliably with arbitrary typed liquidation-mark spellings. The finite
run retained **34 completed / 11 failed paths** out of 15 invented cases at each
of fixed **1x/2x/3x** costs. Actual executable expected return is **UNKNOWN**;
prospective days and predictive strategy trials are both **0**.

The independent standard-library Fraction oracle checked 14,576 assertions and
accepted all 34 complete paths. It reports the other 11 as failures, not passes.
Failures: cross-batch capital at 2x; same-sign shared basis at all three tiers;
and the 2x crash-fill, trade-ownership, unknown-fee/funding, gap/late-fill, short,
observed-loss and overfill paths. No path was removed or replaced.

## Defect and correction boundary

All 11 fail closed with `financial state changed during incomplete assessment`.
The strict unchanged-account guard compares snapshot text. A typed liquidation
mark such as Decimal `99.0` serializes into the normalized durable request as
`99`; replay can therefore change only monetary STRING spelling while preserving
the exact amount. For example, the failed cross-batch 2x saved mark has position
2, exit notional198 and estimated exit fee0.396. No collateral is freed on this
failure: its assessment remains visibly incomplete.

Keep this spec, implementation, fixtures and failures intact. R339 is a separately
frozen caller adapter that normalizes typed marks BEFORE this first snapshot;
it must keep the strict state guard, source clocks, financial arithmetic, risk
policy and exact input/cost scope. Its test explicitly reproduces this original
failure and verifies that a real subsequent cash change still blocks recovery.
Use neither the unadapted R338 entry point nor this diagnostic as market approval.

## Evidence and reproduction

- Full suite before freeze: 1,522 tests PASS, three skips, 191.124s. This includes
  21 targeted coordinator/oracle tests. A bounded independent pre-freeze review
  identified three implementation defects; exact quantity, explicit recovery and
  malformed-request regressions passed after correction. That review did not find
  the later retained replay-spelling failure.
- `results.json.gz`: deterministic gzip of every original reporter result,
  including all 11 failure rows. Decompressed SHA256:
  `e61f82435dbf206b116a479ebd3caa647b8b078d70e7fd6942c8bdb52e7e671b`.
- `journals.json.gz`: all source/account/risk/control journal text, including
  incomplete failed tails. SHA256:
  `f6f50e0cb0064a2d36b945afde0b31df65f288f0b55da0d67d01a46d19d426a2`.
- `audit.json`: original independent oracle output, `passed=false`, with all
  completed paths and the 11 explicit failures. A second fresh-directory report
  reproduced original result bytes and the complete gzip journal archive exactly.

```sh
python scripts/run_opportunity_execution.py --out .cache/r338-fresh
python scripts/check_opportunity_execution.py --out .cache/r338-fresh
```

The checker exits1 for these retained failures. The reporter is a diagnostic
archiver; its exit0 alone is not a pass. Compare counts, audit verdict and exact
archive bytes. Python/runtime/code/input identities are in the frozen manifests.

## Economic interpretation and limits

This is invented account validation, not a candidate return test. The stateless
R334 comparator uses the same actual toy account, forecasts and risk policy;
it has no durable pending hold. Completed paths verify that pending reservations
can change an otherwise positive supplied-forecast decision across batches.
Same-sign quantity attribution, segregated venue/currency capital, terminal
cumulative reports, original first clocks and explicit cash joins are enforced.
Reservations are capital floors, not another fee or a profit. Spread is in the
executed bid/ask prices once; fees scale 1x/2x/3x, funding amounts do not.
No market profitability claim can be drawn from favorable invented forecasts.

This local cooperating-writer component authenticates no market/source report.
It remains caller-driven for risk observation and supports only the stated
short-hold same-sign perpetual contract. Real synchronized quotes/depth, owner
fees, sessions, actual fills, calibrated forecasts and fair/index funding
notionals remain necessary. No collector integration, new prospective protocol,
continuous monitoring, real orders, money, secret access or activation occurred.
Market/source requests0; old historical7757/reported229.85MiB and closed66-request
source budgets unchanged. Program denominator remains9,479,013; added trials0.
