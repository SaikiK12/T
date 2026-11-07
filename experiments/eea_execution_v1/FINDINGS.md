# R421: displayed depth covers the tested sizes; real carry remains unproved

**One registered run**, after freeze+commit/push `cab6273f`. The first R419
packet is the only market observation used. **0 predictive trials**;
`registry.program_trials('registry/rounds.csv')` = **9,784,345**. All **144**
fixed coin/unit/phase/notional/cost scenarios have complete *displayed* sweeps.
The independently implemented Fraction checker passed **5,472** equalities
within **1e-12USD**, without importing either execution implementation.
This is **ACCOUNTING_PASS / conditional depth costs**, no return or capacity
admission. The append-only registration row remains REGISTERED/PENDING.

The [full report](results/report.json), [independent check](results/check.json),
[one-run marker](results/RUN_STARTED.json) and [validation](validation.json)
bind the frozen hashes. No economic/capture rerun, new download, protected
sample, order, account, credential or parent frozen edit.

## What was measured

Coinbase CDE BIP/ETP and Kraken PF_XBTUSD/PF_ETHUSD, packet20261107T04,
**2026-11-07 around04:08UTC**. The original public-source HTTP bodies and
UTC/monotonic receipts were copied exactly from state commit
`686be7fb3982f4d4170bb970a212728cb1428540`; see [manifest](source_manifest.json).
Each targetN is notional **per leg**, withN initial USD cash at each venue:
total2N. The owner10k/25k/50k/100k account cases therefore use5k/12.5k/25k/50k
per leg. The extra10k/100k per-leg targets remain in the full report; the
100k-per-leg stress needs200k initial cash and is outside the owner range.
Contract rounding leaves some capital idle; fees are paid out of cash and no
margin adequacy is certified.

Each side is walked only through supplied depth. An entry buys one venue and
sells the other; the reverse direction supplies the hypothetical immediate
close. This consumes each bid/ask side once **at that snapshot**, not at an
unknown future exit. Drag is measured from each venue's own mid, with no
cross-venue basis booked as profit. Initial and delayed books remain separate.
The actual same-book reobservation gaps are about **4.24..4.56seconds**, not a
fictional exactly3-second execution delay. Quotes may disappear between reads.

## Costs1x/2x/3x, both raw CDE size conventions

CFSE regular fees: **0.02% of actual fill notional +0.12USD per filled native
contract per side**. Kraken: published **Tier1 taker0.05%**. Fixed charges are
not per BTC/ETH unit or once per order. No favorable maker or owner-tier claim.
The source organization, date, URL, exact tariff and read scope are in
[tariffs](tariffs.json): CFSE fee PDF updated2026-09-30, accessed2026-11-07;
Kraken table updated2026-10-30, accessed2026-11-06. This is the published fee
formula, not an observed broker cash debit; fee-cash rounding, owner preview,
collateral conversion and any other account charges remain unverified.

Sensitivity scales adverse book deviation and the proportional/fixed fees by
1/2/3 at unchanged quantities. These stressed prices are synthetic. Tables
show **whole-pair round-trip friction in USD**, rounded for reading; full
precision is retained in the report. Neither table is selected as a winner.

**If CDE displayed size counts native contracts:**

| Asset | Initial total cash USD | 1x initial / delayed USD | 2x initial / delayed USD | 3x initial / delayed USD |
|---|---:|---:|---:|---:|
| BTC | 10,000 | 8.50 / 8.81 | 16.99 / 17.62 | 25.49 / 26.44 |
| BTC | 25,000 | 23.04 / 23.92 | 46.07 / 47.85 | 69.11 / 71.77 |
| BTC | 50,000 | 47.24 / 48.91 | 94.49 / 97.82 | 141.73 / 146.74 |
| BTC | 100,000 | 100.90 / 102.74 | 201.81 / 205.49 | 302.71 / 308.23 |
| ETH | 10,000 | 14.64 / 14.64 | 29.28 / 29.28 | 43.91 / 43.91 |
| ETH | 25,000 | 37.45 / 37.45 | 74.90 / 74.90 | 112.35 / 112.35 |
| ETH | 50,000 | 78.53 / 78.53 | 157.07 / 157.07 | 235.60 / 235.60 |
| ETH | 100,000 | 167.70 / 167.55 | 335.40 / 335.10 | 503.10 / 502.65 |

**If CDE displayed size is base-asset quantity:**

| Asset | Initial total cash USD | 1x initial / delayed USD | 2x initial / delayed USD | 3x initial / delayed USD |
|---|---:|---:|---:|---:|
| BTC | 10,000 | 8.50 / 8.81 | 16.99 / 17.62 | 25.49 / 26.44 |
| BTC | 25,000 | 22.99 / 23.87 | 45.97 / 47.75 | 68.96 / 71.62 |
| BTC | 50,000 | 46.39 / 48.06 | 92.79 / 96.12 | 139.18 / 144.19 |
| BTC | 100,000 | 95.65 / 98.99 | 191.31 / 197.98 | 286.96 / 296.98 |
| ETH | 10,000 | 14.64 / 14.64 | 29.28 / 29.28 | 43.91 / 43.91 |
| ETH | 25,000 | 37.20 / 37.20 | 74.40 / 74.40 | 111.60 / 111.60 |
| ETH | 50,000 | 75.49 / 75.49 | 150.97 / 150.97 | 226.46 / 226.46 |
| ETH | 100,000 | 153.70 / 153.55 | 307.40 / 307.10 | 461.10 / 460.66 |

At10k total cash, the initial1x friction is8.495424USD for BTC and14.63796775USD
for ETH in both conventions. For the native-contract convention these are
**8.50/16.99/25.49USD** (BTC1x/2x/3x) and **14.64/29.28/43.91USD** (ETH).
The larger100k account's initial1x costs are **100.90USD BTC /167.70USD ETH**
in the native-contract convention versus **95.65USD /153.70USD** in the base
convention. The unverified unit can therefore affect measured impact materially
at larger sizes, even though all displayed sweeps complete under both hypotheses.

## What this result permits and leaves open

It establishes a reproducible finite cost proxy on one real sampled packet,
including contract fixed fees and the correct2N capital denominator. Displayed
depth is not the present binding constraint for these particular snapshots.
It does **not** establish real fills, simultaneous order arrival, depth
persistence, source freshness, a future close, margin safety, cleared funding,
client eligibility from France, capacity over time or profitable carry.
No return, annualization, p-value, funding payment or funding difference was
computed. A positive carry must first reimburse these costs and survive the
other risks; the arithmetic check does not establish that it does.

The useful next economic test is narrow: qualify the distinct Advanced rate
field against the already unit-qualified MDA history, specify the funding
mark/fixing and cash rule, then freeze a fixed two-perp test at these fee and
capital terms. R419's later packets were not consumed as additional samples
here, and R404's gated window was not opened. Historical mark proxies, if
needed, must be explicit scenarios with bounds rather than paid-cash claims.
M488 remains **PARTIAL**. The full synthetic suite passes **2,518 tests,
3 skipped**; twelve new tests include fixed fees, basis exclusion, partial
inventory, unit ambiguity, source hashes and consumed failed-run markers.
