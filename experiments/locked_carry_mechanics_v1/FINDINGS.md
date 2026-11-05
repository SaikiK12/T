# R407: fee-aware sizing and terminal cash mechanics

**DATA_PASS, mechanics component only.** The frozen12 invented cases produced
90 fee/price worlds:81 known-exit worlds exactly matched the separate inverse
cash-ledger cross-check,9 kept exit cash unknown, and both incomplete/thin cases
blocked.27 worlds retained an unknown grid-cash floor. Predictive trials:0.
Prospective paper days:0. Market requests:0. No strategy profitability verdict.

## What was found and implemented

The new `lab/locked_carry.py` uses exact rational arithmetic and fixes both orders
at the declared3x sizing fees. It walks actual supplied inverse levels, sizes
face only after reserving entry fees in coin, and retains quote savings and
residual coin at1x/2x. Spot entry and exit obey the declared quantity grids and
minima. Fee debit asset/basis is explicit. No unknown fee becomes zero.

Two constructive examples show why the native R406 expression is not an exact
price-independent cash payoff:

| Invented case | Native face | Native residual coin | New fixed face at3x fees |
|---|---:|---:|---:|
| Deeper bids plus entry fees |100|−0.515375|70|
| Flat bid;3.5bp entry and assumed2.5bp delivery |10,000|approximately−0.06|9,980|

The first case's native modeled cash varies from73.8582 to−54.3381 as the
declared delivery price changes from50 to300. The second varies from9946.7638
to9931.8392 across the same invented prices. These are calls to the unchanged
native rule on artificial books, not observations of R406's live locks. Its
actual journal and scheduled first read were not read or changed.

The defect has two sources: best-bid sizing can overstate the face covered by
deeper bid levels; entry coin fees reduce collateral after that sizing. An
inverse delivery fee also belongs to `face/delivery_price` coin at delivery,
rather than being deducted at the entry reciprocal price. The new module
separates those operations. Its nonnegative residual is still long coin, not an
exact constant payoff; the result reports that distinction.

**Grid exit matters separately.** With100USD face, zero residual/fees and a
delivery price of20,000, the terminal inventory is0.005coin. Under the declared
0.01coin minimum no sale is admissible. The continuous reference is100quote,
but cash from the sale is0 and0.005coin remains held. This is not a total-value
loss: the coin was not sold. The completed terminal cash return stays unknown.

A grid-cash lower bound therefore needs explicit extra assumptions: an exit
ratio floor, a delivery-price ceiling, and proven base/quote minima throughout
that range. The bound includes rounding loss; no bound is inferred from entry
half-spread or assumed spot/index equality. Actual ratio/ceiling breaches are
flagged. The derivation and source scope are in SOURCES.md.

## Evidence and reproduction

- Freeze commit: `d3ad39557f9fbebd583f2c5df305b3f9e05e5fc0`, published before
  [BEGIN](https://github.com/SaikiK12/T/issues/7#issuecomment-6662762635) and run.
- PREREG SHA256: `3332dfbd5f2ddaff8b62a11175b8eae2eaff404ba0f8b63c02091b93ca969cee`.
-18-file manifest: `ae87392f9cd2d93c027213aa98b954142e7aded896778711963028ba253fb552`.
- Before the lab-code commit:2352 Python tests passed,3 skipped;40 targeted
  tests passed. The bounded mathematical review checked the hedge and grid-floor
  inequality and identified the continuous-exit/minimum-size issue before freeze.
- The cash-ledger check shares the depth walker and planned spot input. It is
  separate accounting validation, not an independent end-to-end sizing audit.
- Reproduce into a new file: `python scripts/audit_locked_carry_mechanics.py
  --run --output /new/path/results.json`. Every computational digest is checked
  before and after; an existing output cannot be overwritten.

## What this earns

A reusable pricing component and a falsification of exact native payoff
invariance in the stated examples. It does not establish a positive current
carry opportunity, actual fees, access, matching, future exit liquidity,
exchange margin/path safety or venue survival. The mathematical exit bounds
are supplied assumptions, not verified price/FX limits. M244 stays PARTIAL.
R335/R406's frozen records retain their original scope and native status; any
new prospective use of this component needs its own frozen protocol and gates.
