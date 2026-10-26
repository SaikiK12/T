# R334 — PARTIAL: confidence, costs and capital now meet in one paper decision

The new component joins supplied forecasts to the existing **PaperAccount**,
**PaperRisk**, first-seen depth/close-side cost kernel and **entry_threshold**.
It builds one ordered allocation plan against one account, separated by venue
and settlement currency. It does not create another financial ledger or queue.
**No positive executable expected return is established.**

Code, specification and input identities were frozen and pushed in
[`a98b737`](https://github.com/SaikiK12/T/commit/a98b737) before this round's held
cost diagnostic. PREREG SHA256:
`b0f5a222e9358f052b850bf6eafb99fc100beea5c05651f41d15dd30eae830e6`.

## What changed economically

A directional probability becomes an expected amount through its outcome
payoffs; a funding forecast enters as its own component. Both are expressed in
the settlement currency for the specified quantity and horizon. We then deduct
the current two-way spread/depth cost, both-side fee assumptions, an explicit
future-exit reserve and the supplied forecast-error allowance. Spread is counted
once; an already-net payoff convention is refused. A forecast never credits cash.

The same signed base quantity and strict 3x-cost inclusion decision apply across
all three reported cost tiers. Risk is evaluated by the actual persistent
PaperRisk object on the current account snapshot. Old stops survive; a supplied
green summary cannot replace that observation. Planned quantities also obey
projected venue and symbol gross limits, including short buyback notionals.

Within ONE batch, a proposed position consumes its own venue/currency's remaining
planning budget. It cannot borrow another currency's balance, spend unrealized
gains, or let several strategy ideas all use the same available capital. This
is a conservative unlevered diagnostic, not verified exchange margin capacity.

## Constructed example: 70% confidence can still lose

In the deliberately invented small-move case, a 70% chance of +1 and 30% chance
of -1 produces expected gross **+0.40 USDT**. The supplied current 99.5/100.5
book costs **1.00** to cross both ways, plus **0.20** in fees at 10 bp per side.
That is already **-0.80** before the additional uncertainty/exit allowances.

The finite protocol supplies a further 2-USDT error allowance and 0.50-USDT exit
reserve. These figures and the calibration pointer are **invented**, not fitted
or validated market inputs:

| Supplied forecast | Expected gross | 1x net after allowances | 2x | 3x | Included in batch |
|---|---:|---:|---:|---:|---|
| 70% small move | +0.40 | -3.30 | -5.00 | -6.70 | No |
| 90% illustrative large move | +80.00 | +76.30 | +74.60 | +72.90 | Conditional fixture only |
| Missing positive-mass funding payoff | Unknown | Unknown | Unknown | Unknown | No |

These are arithmetic illustrations, **not realized PnL, calibrated lower
confidence bounds or evidence that such opportunities exist**. The second row
does not earn money in the account: its cash remains 1,000 USDT, unchanged.

Fifteen constructed cases contain 18 opportunities. Five conditional inclusions
and 13 exclusions retain all scenarios: shared breakout/funding budget, repeated
capital, concentration, unknown calibration/funding/fees/session/exit/error,
future quotes, insufficient depth, wrong currency, risk stops and shorts.
Every financial account and its journal remain unchanged by these forecasts.
Known price components remain visible when funding and total value are unknown.

## Existing cost evidence stays incomplete

The runner emits every original R318 deadline, size and fixed cost tier:
**72 deadlines × six sizes × three tiers = 1,296 cells**. There are **390 known
conditional hurdle cells** (130 size/deadline states repeated across the three
tiers) and 906 unavailable ones. They are dependent cost illustrations, not
1,296 independent trade opportunities.

The original paired crossing-plus-reserve costs, quantities, 10,000 total /
5,000-per-venue quote-equivalent capital and conditional currency parity stay
unchanged. No new quote or favorable forecast is reconstructed from aggregate
fills. All actual expected gross/net values remain unknown and admissible
opportunities remain zero. Known costs alone cannot certify a positive edge.

This reuses the *published derived* R318 cost cells and original provenance,
not a fresh decode/audit of all raw frames. The separate checker verifies that
each reported hurdle is the exact retained parent cell. R318's original source,
session, fee, funding-value, latency and capacity limitations are preserved.
R310/R311 were read; neither was rescored, repaired again or relaxed.

## Verification and integration limits

- **1,436 tests pass, three skipped, 210.880 seconds**, with nine focused tests.
  Skips: unbuilt qx twin; unavailable built engine/R269 archive; absent funding
  archive. They are not claimed executed. The latest full run checks the final
  frozen code; an earlier interrupted run is not counted as a pass.
- **4,178 separate Fraction/identity checks pass** across the fixed invented
  cases and all 1,296 parent cost cells. The checker imports no production value,
  financial or selection functions. It is not calibration, raw-source or
  profitability certification.
- Three artifacts reproduce byte for byte in a fresh directory. Input/code
  hashes are checked before and after reporting. No new market/history/source
  acquisition, model weights or portfolio cash was added.

Repository integrity reports **151 rows, 146 local specs, 144 frozen, one planned
draft, one error and 13 legacy warnings**. The error is the already-unfrozen
Claude-owned `experiments/mlrank_v3/PREREG.md` without a sidecar: its bytes and
missing sidecar are verified against base `c54872e`, and the room already reports
the pending rename. It is not repaired from this checkout. **Zero new integrity
errors** are introduced, but the global integrity command is still red. Intake
validation passes: 408 methods/aliases, 329 queue rows, 20 source files, zero
errors/warnings. `verification.json` records the checks. Old frozen files, queue,
aliases and all old registry bytes remain intact; only two rows are appended.

This is a **single offline allocation batch**. It creates no durable capital
reservation, fill or order. Do not use it as a repeated/concurrent execution
allocator: reservation ownership, terminal release and joins to the existing
fill lifecycle still need implementation before that use. Calibration and market
contracts are supplied declarations with explicit identities; their authenticity
and statistical coverage are not verified by this module. Future exit liquidity,
fair/index funding values, owner fees/permissions and actual margin remain open.
Actual-order permission and activation are always false; prospective days zero.

Canonical linkage is to existing **M409/M410/M412**, whose strategy status and
tested/open scope remain unchanged. Claude's active R332/R333, shared panel,
method rows and forward journals were not edited. PR49 was already merged, so
this is one focused integration branch against Claude's `c54872e`.

The previously missing **R331** registry row now conservatively reserves its
full frozen **14-variant** family, as REGISTERED/PENDING. It remains unfinished
after the committed training/calibration-fit stages. No later selection,
validation or economic result was computed here, and 14 completed market tests
are not claimed. R334 adds **zero predictive trials**; the conservative program
denominator is **9,478,990**. No old registry row was changed.

Historical acquisition allowance remains **7,757/8,000 requests and reported
229.85/250 MiB spent**, exact remaining bytes unknown. No reset, orders, money,
secret values, activation, merge/closure or permanent execution guarantee.

Reproduce with Python 3.12.14 and the retained tracked artifacts:

```sh
python scripts/run_opportunity_value.py --out /fresh/R334-output
python scripts/check_opportunity_value.py /fresh/R334-output
```

The next missing link is specific: feed a causally calibrated payoff/error
contract and source-bound market inputs through this interface, then connect
admitted plans to durable paper reservations and the existing fill lifecycle.
No historical or constructed result authorizes that future strategy's activation.
