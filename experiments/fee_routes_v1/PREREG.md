# R317: source-labelled taker fee routes on already-seen paired books

- **Registry id:** R317
- **Owner (single writer):** Codex, `codex/lab-consolidation`, draft PR #49
- **Date registered (UTC):** 2026-10-25
- **Canonical methods:** M409 execution/funding inputs; related M267/M227 open scopes

Code/source manifest SHA-256: 32cb294b6220d6a3534f7edb4057102bfe9c501f7fa8ff665f810333e6be2071
Held-data identity SHA-256: 221e691dbe628f811aa965db60d101fdfeae50e64dbece0de393b148ad2b2c12

## Economic question, known history and limits

What part of the paired round-trip hurdle is displayed crossing, the unchanged
10/4bp reserve, or a named **conditional public fee assumption**? Does an observed
access deadline even meet the source's additional venue-delay parameter? Bind
order class, rate unit, source kind and unknown entitlement rather than treating
instrument zeros or a marketing page as the owner's charged fees.

R311 remains INCONCLUSIVE on224/273 common days; its calibration-selected policy
is negative at2x/3x costs. Do not rerun that incomplete historical panel, change
its assumptions/selection, increase leverage or claim a lower-cost rescue.
R316 already measured a useful request-start fix, but has zero joint altcoin
book/fair/index rows. This study uses **already-seen R316 raw books**; its outcomes
and public metadata have been seen. The fee documentation was read later and
is not an as-of fee schedule for the capture. This is a post-hoc descriptive
cost/input decomposition frozen before its new calculations, not an unseen
trading-policy test, calibrated significance, net-return result or paper evidence.

There are **8 distinct fee paths x6symbols x6grids x2deadlines =576 retained
descriptive rows**. Underlying book/deadline states number72, not576 independent
opportunities. All three fixed cost tiers stay visible; **zero predictive trials**.
Program trials remain9,478,782. There is no strategy ranking/selection or
dependent-null/SPA inference to claim from these known dependent quote rows.

## Source contracts and received alternatives

MEXC charges use each fill's price*contracts*contractSize*rate. The official
example30000*10000*.0001*.02%=6USDT explicitly converts .02%=.0002=2bp. Applying
the public JSON takerFeeRate as a fraction is a **nominal interpretation consistent
with that example**, not separately verified account/API-effective scaling.
The current docs describe /detail/country; R316 used /detail. Region/account
equivalence is not established. NORMAL/BASE versus LEVERAGE/TIERED/TEMP remain
different source modes. Unknown/missing/mismatched/future/clock-stepped metadata,
zero-promo tags, zero nominal rates or nonbase/TEMP schedules cannot grant a
nominal cost path. Temporary end, eligibility and remaining quota are unknown.

The generic MEXC0%maker/.04%taker statement gives a second explicit4bp taker
hypothesis. Same source says zero-fee eligibility/quota/expiry/risk can vary;
the separate fee page mentions region/events and actual trade history. **4bp is
not a proven worst-case cap, owner fallback or replacement for a missing nominal
rate.** Do not select the cheaper conflicting public statement as account fact.
MX deduction needs assets, settings, eligibility and capital/FX costs; unrun.

Lighter's newly read fee page distinguishes regular Standard0bp taker/300ms
additional delay, unstaked Premium/Advanced2.8bp/140ms and Plus0.5bp/300ms.
Premium maker0.4bp and post-only/cancel latency, Standard TWAP/advanced/RFQ1bp,
maker role versus marketable limit, staking ladders, MX deduction and larger
account/transaction quotas remain received **unrun alternatives**, enumerated in
sources.json/intake. No maker fill, discount or staking exposure is assumed.
Paid Lighter tier hypotheses require explicit public fee-enabled metadata; an
absent/false flag is unknown, not permission to infer a new discount. The public
account-type assumption is not a claim about the owner or actual fee-debit asset.

Previously unread official prover code in repository **tree object**16c0f36d75f2306ee242e26e507e4c237f7f4074
applies funding using prior stored index **before** same-block oracle updates;
application time is an actual block-time trigger, with integer/clamped/price-
weighted prefix sums and account checkpoints. The full index is committed state,
not an authenticated value in the inspected partial public input. This reading
supplies neither API scaling/settlement-asset mapping nor deployment/proof
verification. No later index publication can be backfilled as that event's
settlement value. Exact six protocol submechanisms/read-unread versions are
retained without compiling/mirroring BUSL source or acquiring private witnesses.

## Exact existing inputs, no new market acquisition

Commit/push this frozen spec, all implementation/tests/independent checker,
source versions and data identity before computing the new fee-path outcomes.
data_inputs.json must bind exactly six existing R316 identities: PREREG.md,
PREREG.sha256,code_inputs.json,evidence_inputs.json,results.json and
observations.jsonl.gz, explicitly labelled already seen. The pinned old raw seal
fixes every raw body/frame/metadata/receipt; its own immutable loader verifies
the inventory, caps, source hashes and36-file parent code before decoding.
New code verifies its own manifest/runtime plus held input identity before/after
reporting. Refuse differing output overwrite; reproduce in a fresh folder.

No new market, RPC, account, historical or model-weight acquisition. No capture
mode. Only the two source readers' finite static requests occurred: fee reader
8GET/4MiB/120s, index reader6GET/3MiB/120s, each<=1MiB/body. Actual fee bodies876687
bytes/4.644s (two semantic404 bodies with HTTP200 preserved); index289548bytes/
2.543s,allHTTP200. No redirect/retry/login bypass. Raw pages/code remain ignored
cache; compact hashes, actual read/unread scope and provenance are committed.
Historical accumulated spend stays **7,757/8,000 requests,229.85/250MiB**.

## Fixed matched states, fee paths and equations

Reuse R316's exact six pairs BTC,WIF,SKR,ROBO,MEGA,XPD and grids10,20,30,40,50,60s.
Reconstruct full paired depth at immediate and+300ms with unchanged R314/R316
source/receive age, skew, sequence, metadata and transport-stop guards. At the
immediate deadline only, derive the common-lot base q from $250 divided by the
larger midpoint. All paths/delayed states retain exactly that q, without resizing,
future backfill, discarded missing grids or alternative source clocks.

| Fixed path | MEXC taker assumption bp | Lighter taker assumption bp | Additional Lighter delay ms |
|---|---:|---:|---:|
| reserve_control | 10 | 4 | 0, stress control only |
| crossing_floor | 0 | 0 | 0, mathematical floor only |
| nominal_standard | held nominal; unknown zero/TEMP | 0 | 300 |
| nominal_premium | held nominal; unknown zero/TEMP | 2.8 | 140 |
| nominal_plus | held nominal; unknown zero/TEMP | 0.5 | 300 |
| advertised_standard | 4 | 0 | 300 |
| advertised_premium | 4 | 2.8 | 140 |
| advertised_plus | 4 | 0.5 | 300 |

Only ordinary **regular market/taker** execution is hypothesized. Explicit bp,
percent and fraction conversions are typed; negative/boolean/nonfinite/unknown-
unit rates fail. All paths use the same displayed sweeps and segregated capital
**$10,000,$5,000/venue**, equal base quantity and conditional USDT/USD-quote parity.
No real settlement asset/FX or credit/debit is asserted. Per-venue charge equals
(current buy cash+current sell cash)*fee_fraction. Pair hurdle equals crossing
plus those charges. Fixed1x/2x/3x multiplies crossing+charge together, retaining
the original reserve path exactly. Also report reserve charge minus candidate
charge as **assumption sensitivity**, never saved/earned money or PnL.

The crossing-only path assumes nonnegative taker charges and no other costs;
it is a mathematical floor on this limited current-book model, not executable
zero-fee access or a floor on all future trading costs. An unknown nominal fee
remains null; it does not silently become zero or generic4bp. Keep the separate
advertised paths as declared counterfactuals even when nominal is unknown.

Compute pure conditional arithmetic for a valid book even if its0ms deadline is
below the hypothesized140/300ms venue delay, but mark minimum_delay_satisfied=false
and exclude it from minimum-delay-supported counts. No such row is an admissible
route claim. +300ms only reaches the quoted additional delay threshold: it is
neither exact140ms Premium execution nor total submission/network/matching/fill
latency. No actual order was submitted, and even a supported row stays blocked.

## Output, controls and honest decision boundary

Retain every576 row, with exact fee/source/metadata flags, quantity, book clocks,
the unchanged reference_reserve_cost, new conditional cost or missing value,
minimum delay, account/as-of verification flags and capital/asset assumptions.
Report96 symbol/deadline/path cells with cost rows, separately minimum-delay-
supported cost counts, flags and1x/2x/3x USD/break-even-bp ranges. All fields retain
profile duplication; no uncertainty from row counts. Independent Decimal audit
reconstructs raw paired states/q, source rate interpretations, all eight controls,
charges, sweeps, capital, stress tiers, missing entitlement and support flags.

All rows have account_effective_fee_verified=false,fee_schedule_asof_verified=false,
execution_ready=false and funding cash unscored. Actual sessions/index-effective
value, inclusion, account fees/order class/permissions, fills/queues/impact,
financing/liquidation/two-leg recovery remain unresolved. No positive expected
net return, old R311 policy rescue, maker profitability or prospective paper
activation is authorized by a smaller conditional quote-cost number.
