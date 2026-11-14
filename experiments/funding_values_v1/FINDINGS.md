# R315: funding-value contracts implemented; synchronized inputs still missing

**PARTIAL input/accounting evidence, no return or activation result.** The new
source-typed ledger rejects estimated rates, unbound settlement values, incomplete
exposure intervals and incompatible units/assets. The matched live diagnostic
does **not** resolve the fair/index input gap: zero altcoin rows have both valid
paired displayed capacity and jointly fresh reference publications, with either
value profile. No funding cash is scored. R311 remains INCONCLUSIVE on 224/273
days and its preselected policy remains negative at registered 2x/3x costs.

## Registration, exact inputs and budget

Frozen [PREREG](PREREG.md), 30-file [code identity](code_inputs.json) and independent
checker were committed/pushed in **b8ee6b7** before collection. Exact raw evidence
was [sealed](evidence_inputs.json), committed/pushed in **faa2820** before economic
reporting. One attempt, no retry/reconnect or threshold change. Anchor UTC:
**2026-10-25 06:26:11.942652**. Four descriptive profiles, six fixed grids and six
pairs retain all **144 rows**; **zero predictive trials and zero prospective days**.
Program trials remain **9,478,782**. The observations are dependent; no sampling
precision, calibrated significance or expected-return claim is made.

| Acquired input | Actual scope | Frozen bound |
|---|---:|---:|
| Metadata GET attempts / body-read upper bound | 7 / 404,135 bytes | 7 / 2 MiB |
| Dedicated fair GET attempts / body-read upper bound | 36 / 3,604 bytes | 36 / 144 KiB |
| Combined GET attempts | 43 | 43 |
| WS handshakes | 2 | 2, no replacement |
| MEXC messages / decoded payload | 468 / 130,489 bytes | 20,000 / 8 MiB |
| Lighter messages / decoded payload | 1,410 / 796,706 bytes | 20,000 / 8 MiB |
| Common read-start window / total elapsed | 65 s / 72.263 s | 65 s / 120 s |

All fair responses HTTP200; no capture/GET errors, budget overruns or backoff
responses. Retained-body bytes equal the conservative read upper bound here;
the code also budgets unknown tails on partial requests. Compressed raw files and
receipts total **243,970 bytes**, excluding the seal manifest. Transport overhead
is not claimed as measured application body size. Both streams stopped for
duration completion, with separately retained unusable and cleanup clocks.

The bounded primary-source reading separately used **8 GETs / 1,447,969 bytes /
5.237 s**; [source identities and actual read/unread scope](sources.json) retain
the eight ordinary public responses plus the cached Lighter WS reference. No
history, model weights, credentials, accounts or copyrighted corpus was acquired.
R310/R311 historical spend remains **7,757/8,000 requests, 229.85/250 MiB**; these
small current-data/source budgets do not reset or extend that approval.

## Matched availability result

Each cell is **displayed-cost eligible / also jointly publication-fresh**, out of
six fixed grids. The REST and WS profiles use exactly the same books, immediate
decision q and costs. The 300-ms control retains that q without resizing.

| Pair | WS immediate | REST immediate | WS +300 ms | REST +300 ms |
|---|---:|---:|---:|---:|
| BTC | 6 / 1 | 6 / 0 | 6 / 0 | 6 / 0 |
| WIF | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| SKR | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 |
| ROBO | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 |
| MEGA | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| XPD session control | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 |
| All pairs | 9 / 1 | 9 / 0 | 9 / 0 | 9 / 0 |

There are **18/72 distinct book/deadline cost rows**, duplicated identically across
the two reference profiles. The independent audit checks 108 cost scenarios
(36 profile-labelled cost rows *3), not 108 independent market opportunities.
Altcoins have **2/24 immediate and 2/24 delayed** cost rows: SKR and ROBO once each.
Neither profile has a jointly fresh altcoin row. At the two delayed altcoin cost
rows the REST MEXC publication passes its freshness guards, while both Lighter
index publications fail receive/source age. No stale reference is backfilled.

The fixed GET scheduling is itself insufficient at these deadlines. Requests
start 0.610–13.920 ms after planned dispatch (median1.484 ms), but full-body
latency **including owned-worker startup** is **1,247.070–2,434.535 ms
(median1,487.132 ms)**. Scheduling one second before the grid leaves **0/36**
replies known at the immediate deadline and only **4/36** known by +300 ms. The
latest prior reply remains stale rather than being replaced with future data.
Successful REST system timestamps are 78.031–99.064 ms behind full-body receipt
UTC (median83.625 ms); this publication clock does **not** certify when the fair
value was effective, cache age or funding-engine value. The latency includes
local startup/scheduling/transport; it is not an isolated venue latency estimate.

Across all six pairs/grids, individually fresh MEXC/Lighter publications are
9/36 and4/36 for WS immediate, 0/36 and4/36 for REST immediate, 8/36 and5/36 for
WS delayed, and4/36 and5/36 for REST delayed. Their intersection with valid books
and the fixed skew guards is shown above. The only joint row is BTC/50s/immediate
WS; its q*value products are249.8321 USDT and249.94246 USD quote units, sensitivities
0.02498321 and0.024994246 quote units per one bp. These assets are not netted, and
the products are not a realized payment or signal.

This is a new time window, so R314's larger cost count is historical context,
not a controlled deterioration estimate. The valid comparison here is the two
reference profiles on the same current states. All six raw Lighter
`market_config.trading_hours` values are empty, despite active status flags.
Sessions, actual fill permission and timestamp/effective-value guarantees remain
unknown. Every observation has `execution_ready=false` and unscored funding cash.

## Conditional economics at all registered costs

$10,000 capital remains segregated $5,000 per venue; $250 target leg q is rounded
to the common lattice at the immediate deadline. Fixed 10/4-bp **per-side charge
reserve PLUS current displayed crossing**, stressed together at1x/2x/3x. These
are not measured account fees or the exact historical R311 all-in assumptions.
Each range covers distinct eligible immediate/delayed book rows; reference
profiles cannot change it. Hurdles are bp on mean one-leg midpoint notional.

| Pair | Distinct cost rows | Round-trip USD 1x / 2x / 3x | Hurdle bp 1x / 2x / 3x |
|---|---:|---|---|
| BTC | 12 | 0.7002–0.7094 / 1.4004–1.4189 / 2.1006–2.1283 | 28.02–28.40 / 56.05–56.79 / 84.07–85.19 |
| SKR | 2 | 0.8104–0.8177 / 1.6209–1.6354 / 2.4313–2.4531 | 32.57–32.86 / 65.14–65.73 / 97.72–98.59 |
| ROBO | 2 | 1.3642 / 2.7284 / 4.0925 | 54.61 / 109.21 / 163.82 |
| XPD | 2 | 1.3510–1.3598 / 2.7021–2.7196 / 4.0531–4.0794 | 54.20–54.55 / 108.40–109.10 / 162.60–163.65 |
| WIF, MEGA | 0 | unavailable at all three tiers | unavailable at all three tiers |

Altcoin hurdles overall: **32.57–54.61 / 65.14–109.21 / 97.72–163.82 bp**. No
benefit forecast is compared to those costs because the required cash/value
contract is missing. Current entry+unwind quotes do not guarantee a future exit;
impact, failed legs, financing and liquidation costs remain outside these figures.

## Implementation and independent checks

- `lab/funding_values.py` separates publication/trade/effective/settlement roles,
  contract-bound exposure and explicit fraction/percent units. Linear and inverse
  formulas pass the official -3 USDT/-0.0001 BTC fixtures. Estimated or unknown-unit
  rates cannot post nonzero model cash. A MEXC exposure must span the entire
  documented15-second ambiguous inclusion interval; missing exposure is not flat.
- The append-only assessment ledger deduplicates event/time, rejects conflicting
  revisions and shifted-time reuse of known settled event IDs, and segregates
  venue/asset totals. A complete hypothetical calculation is labelled model cash,
  never real account credit. The live capture supplies none of the necessary
  actual event/position/settlement-value attestations, so no cash is manufactured.
- Independent pre-freeze financial review found and resolved four material issues:
  future effective/publication values, event-ID time collisions, unbound exposure
  units/instruments and reference-to-book identity. Further dispatch/backoff checks
  were resolved before freezing. All25 new focused tests passed independently.
- Full local suite: **1,153 tests run, 2 skipped**, successful. The frozen
  [standard-library Decimal checker](check_values.py) imports no production replay
  or cost module: **144 rows,36 fair receipts,276 causal value receipts,108 cost
  scenarios and2 notional sensitivities**; maximum absolute numerical difference
  **4.38e-12**. Exact counters are in [audit.json](audit.json).
- `results.json` and `observations.jsonl.gz` reproduce byte for byte in a separate
  folder. All errors, stale/missing rows and the adverse REST timing result remain.
- Canonical integration: **346 source records/aliases,54 provider entries,328
  queue rows**; nine mechanical refinements added, all337 prior method objects,
  old alias bytes and old registry prefix preserved. Intake validation has0
  errors/warnings. Integrity has0 errors/13 existing legacy/planned warnings,
  with128 frozen local specifications verified and one planned draft retained.

Reproduce without network or accounts:

```bash
python experiments/funding_values_v1/check_values.py
python scripts/probe_funding_values.py report --out /path/to/new-empty-report-folder
```

## Decision

Retain M409 as PARTIAL and M267's exact settlement-window strategy as QUEUED/unrun.
The remaining binding contract is synchronized causal index/fair **effective**
value and session/inclusion evidence, with a collector schedule that fits observed
first-seen latency. A future acquisition/implementation must be separately finite
and frozen; this result does not authorize resampling or relaxing the old guards.
Ticker trade clocks cannot solve idle freshness by relabelling timestamps. No
increase in leverage, old policy substitution, PnL or prospective paper claim.
