# R344: executable-input carry costs, conditional gains only

**PARTIAL component. No validated expected net gain or strategy activation.**
The same-venue spot/inverse account is now implemented and checked against one
new public batch. Small conditional gains do not establish an edge after
capital opportunity cost, future sale/FX uncertainty and actual account rules.

R343 freeze `555add4` preceded acquisition; raw identity `4cb12cd` preceded any
economic report. R343's mistaken spot contract_size=1 constraint and all failed
outputs remain intact at `93df894`. Separate R344 freeze `736a105` corrects
ONLY that literal to the exact observed 0.00000001. Shown spot quantities remain
base coin; no contract-count conversion. Original lot, price, depth, clock,
fees, ordering, capital and all economic controls are unchanged. Bounded review
verified the exact diff and caught three evidence-path substitutions before
freeze. Its limited scope is in review.md; no full-system certification.

## Actual inputs and availability

Eight Deribit public GETs returned HTTP200: four fixed instrument records and
four five-level books. 6609 accepted body bytes; 524288 conservative reserved
bytes /56 cumulative reserved seconds. No retry, redirect, account, history,
order or alternate symbol. This one-time scope is CLOSED. R344 adds ZERO
requests and reuses the original ten raw evidence files without copying them
or resetting the budget. Historical7757/8000requests, reported229.85/250MiB,
closed R340 and old source allowances remain unchanged.

The four actual full-body book receipts span **2026-10-27 07:07:30.932991 through
07:07:31.146420 UTC** (213.429ms skew). Request/body latency1105..1319ms is
COLLECTION time, not known order-execution latency. All four publication/body
guards passed at that original common receipt decision:2s age,1s skew,50ms
clock step. Recalculation never replaces these clocks with a later timestamp.
This is one simultaneous-availability observation, not continuous availability
or an executable matching-engine quote lifetime.

Both spots are explicitly Coinbase-routed, active/open, base BTC/ETH, quote and
counter USDC, contract_size1e-8, min_trade_amount1e-8; amounts stay base coin.
Futures are dated inverse USD face, coin settlement, expiry2026-12-25 08UTC.
Exact current source grids are checked; no contract_size-as-step inference.

| Snapshot reference | BTC | ETH |
|---|---:|---:|
|Spot midpoint, USDC/coin|79504.935|2299.505|
|Dated-future midpoint, USD/coin|80233.75|2314.375|
|Public spot taker scenario|5bp|5bp|
|Public inverse taker scenario|3.5bp|3.5bp|
|Dated delivery scenario|2.5bp|2.5bp|

Public fee scenarios are not owner tier/debit/rounding evidence. Larger public
hints would be charged; no fee waiver or native zero-fee inference. Future
settlement and spot-sale prices differ; no USD/USDC peg is established.

## Capital, capacity and complete matrix

Each alternative owns ONE10000USDC account, ordered BTC then ETH. The purchased
net coins are earmarked ONCE as inverse collateral, not another deposit. No
second spot inventory credit in combined terminal wealth. At5000face/coin,
gross spot purchase is0.06248671BTC and2.16627881ETH, fixed across all controls.
Full-depth worst3x quote-debit reserve is9964.588653USDC;35.411347 remains.
At1000face/coin the worst reserve is1992.810893USDC;8007.189107 remains. Cash
is segregated within each alternative; these portfolios are never pooled.

All48 model cells and432 dependent terminal worlds retained. Three of four
portfolios have complete public inputs;324 worlds have conditional numbers.
The5000top-only control fails BTC's shown future bid capacity (2680face at the
first level versus fixed5000). No resizing or favorable-coin substitution.
Its ETH financial path is retained, but all108 aggregate worlds stay UNKNOWN;
it is not promoted into a one-coin strategy. The1000full/top outputs coincide
on these shallow quantities and are not independent observations. There is
only ONE source batch/two spot-future pairs, not432opportunities.

## Conditional money after costs

For the following tables ONLY: supplied delivery reference equals the source
future midpoint; sale-price/delivery-reference ratio rho=1. Idle USDC earns0.
The quoted result is a MODEL terminal amount above the original WHOLE10000USDC,
not realized PnL, expected PnL or an available future exit. Cost multiples stress
entry crossing and all modeled entry/delivery/exit fees; they cannot certify
future exit impact or latency. Same bought quantities and face at every cost.

|USD face per coin / spot fee debit|1x net USDC|2x net USDC|3x net USDC|
|---|---:|---:|---:|
|1000full / base|12.256428|8.965288|5.676365|
|1000full / quote|12.263692|8.978793|5.695090|
|5000full / base|61.107335|44.471953|27.847672|
|5000full / quote|61.143656|44.539484|27.941302|
|5000top-only / either|unknown|unknown|unknown|

Zero-charge CONTROL still pays source entry crossing; it is not an actual fee
offer. Its1000full excess is15.460634/15.371475/15.282311USDC, and5000full excess
77.128874/76.503858/75.878771 at1x/2x/3x. Base/quote coincide when fees are0.
All delivery scales1/2,1,2 and benchmarks0/3/5% remain in results.json.gz;
the table is a fixed reference world, not selection of a winning world.

The capital comparison changes the interpretation. A HYPOTHETICAL3% annual
simple cash scenario over the exact remaining expiry interval earns48.523105
USDC on the same10000. It is a fixed benchmark, not a newly observed available
T-bill/USDC yield.5% gives80.871842USDC. Whole capital is charged ONCE, idle
credited ONCE; undeployed cash cannot disappear from the denominator.

|5000full / base-debit reference world|1x|2x|3x|
|---|---:|---:|---:|
|Excess versus3% cash scenario, USDC|12.584230|-4.051152|-20.675433|
|Excess versus5% cash scenario, USDC|-19.764507|-36.399889|-53.024171|
|Minimum common sale/reference ratio to beat3%|0.998742907|1.000405357|1.002072203|
|Net versus original cash if sale ratio=.99, USDC|-38.998424|-55.468430|-71.927446|

At3x, even matching a zero-interest cash account requires rho>=0.997208956
in this base-debit reference world. The roughly28USDC conditional gain tolerates
only about0.279% deterioration in the common sale/reference ratio. A1% adverse
ratio consumes it and more. This ratio includes eventual sale timing/spread,
delivery reference differences and USD/USDC effects; its future distribution
has not been measured. Quote-debit cases and other scales are preserved, not
substituted for the fixed illustration.

## What the checks prove, and what remains open

Independent stdlib oracle **PASS8726 exact checks**, reconstructing raw plans,
fixed ordering/reserves, all48 model accounts/432worlds and132 hash-chained
journals. Coin identity, fee debit once, harmonic inverse conversion, common
cash and terminal sum agree. Parent incomplete-path pass is not reused as this
financial-path pass. Fresh-directory results, journal pack and audit reproduce
byte-for-byte offline. Full1559tests passed before freeze (207.203s,3existing
skips); original+new20targeted tests passed. See tests_before_freeze.json,
scope_check.json, audit.json and reproduction.json.

Unresolved: owner account/custody mode, routed-spot eligibility, settled
spendability and collateral earmark route, fee currency/minimum/rounding,
partial-hedge latency/fills, true source effective time, future executable spot
exit and delivery/TWAP/FX, margin/haircuts/ADL/insurance and default risk. The
nonnegative residual-coin proof is MODEL1x coverage, not liquidation immunity.
Risk equivalence with cash or an unhedged passive coin is not established.

One batch provides no calibrated mean return, confidence interval, p-value or
independent null distribution. Positive conditional money above zero-interest
cash is insufficient; the3% reference already loses at2x/3x. Retain M244 as a
testable weak hypothesis with exact current cost/capacity hurdles, not an
activated strategy. Full entry/roll rules, continuous executable acquisition
and actual expiry evidence remain unrun. R310/R311 and confidence R342 results
are unchanged. No new prospective strategy day or predictive variant; program
9479013 unchanged. No order, money, secret, merge/closure or permanent service.

Reproduce from this checkout with Python3.12.14, no network:

```
/workspace/T-consolidation/.venv/bin/python scripts/run_same_venue_v2.py --out .cache/r344-fresh
/workspace/T-consolidation/.venv/bin/python scripts/check_same_venue_v2.py --out .cache/r344-fresh
```

New prospective scoring needs a separately frozen finite strategy protocol and
on-time new observations. This snapshot and its corrected replay cannot count
as future paper profits. Original frozen specs, raw bodies, old failures and
append-only journals remain intact; related work stays in existing draft PR56.
