# R418 findings: reachable Kraken EEA carry does not clear the capital hurdle

**Native verdict: DOES_NOT_CLEAR_FROZEN_SCREEN for all 8 asset/capital cases.**
Gate 0 exploratory economic screen only; no statistical SIGNAL or exact
executable PnL. The sole measurement ran **2026-11-06T18:45:49.665660+00:00 to
2026-11-06T18:45:51.577620+00:00**, after freeze/input commit
`f599e4dc7c4f77396e364609f213e4093b5eb01f` was pushed. No rerun.
Program trial sum: **9,784,345**, including this lane's **2** implementations;
not a multiple-testing correction or an independent-sample count.

## What this changes in the lead selection

Kraken's EEA products and public history are real research candidates, and its
captured BTC/ETH books have enough displayed depth for these account sizes.
But this particular fully funded, static spot/perp carry is economically weak
under the frozen current Tier 1 ceiling. Even the **upper** missing-funding
scenario at 1x costs stays below the fixed **4% annual capital hurdle** in every
case; the lower scenarios are negative at all costs. Do not launch a new paper
lane for this version or reprice it with cheaper fees after reading this result.
Other fee tiers, venue pairs and capital policies are untested, not disproved.

## Historical cost-model return on total funded capital

One continuous fixed-base hold **2025-12-01..2026-11-01 UTC**, **335 days**;
spot plus separate USD short wallet, approximately half the capital per leg,
including the spot purchase cost reserve. No monthly trading or resizing.
Prices are bar-open execution proxies; historical spread/impact is the frozen
**1 bp per side assumption**, not measured past liquidity. Fees are the
**current** published Tier 1 taker ceiling (**0.80% spot / 0.05% perp**) held
constant, not an owner rate or historical fee-vintage reconstruction.

Ranges below are **conditional scenarios**, not confidence intervals. The API
omits **5 of 8,040 held hourly rates per asset**. Those payments remain unknown;
the lower/upper cases use the documented current relative cap and surrounding
index-high envelope as explicit assumptions for old gaps. Exact net is unknown.

| Asset | Total USD capital | 1x annualized net range | 2x annualized net range | 3x annualized net range |
|---|---:|---:|---:|---:|
| XBT | $10,000 | -0.585% to +1.756% | -1.444% to +0.897% | -2.303% to +0.038% |
| XBT | $25,000 | -0.585% to +1.756% | -1.444% to +0.897% | -2.303% to +0.038% |
| XBT | $50,000 | -0.585% to +1.756% | -1.444% to +0.897% | -2.303% to +0.038% |
| XBT | $100,000 | -0.585% to +1.756% | -1.445% to +0.897% | -2.304% to +0.038% |
| ETH | $10,000 | -0.432% to +1.717% | -1.243% to +0.906% | -2.054% to +0.095% |
| ETH | $25,000 | -0.432% to +1.717% | -1.243% to +0.906% | -2.054% to +0.096% |
| ETH | $50,000 | -0.432% to +1.717% | -1.243% to +0.906% | -2.054% to +0.096% |
| ETH | $100,000 | -0.432% to +1.718% | -1.243% to +0.907% | -2.054% to +0.096% |

At **$10,000 total capital**, the actual 335-day dollar intervals are:

| Asset | 1x | 2x | 3x |
|---|---:|---:|---:|
| XBT | $-53.72 to $+161.14 | $-132.56 to $+82.30 | $-211.40 to $+3.46 |
| ETH | $-39.66 to $+157.61 | $-114.08 to $+83.19 | $-188.50 to $+8.77 |

These are cash-model results before personal taxes and funding the starting USD
account; no actual fills, deposits, withdrawal, FX or future-return claim.
The archive is spent/latest vintage, and current metadata/fees do not certify
point-in-time historical rules. No fresh-sample admission, Sharpe or p-value.

## Margin, cash and attribution

No possible maintenance breach or USD cash deficit in the supplied hourly-high /
lower-funding scenario at any of the **24** cases. This is a retrospective screen
with **current** EEA first-tier margin rules, not a promise about future jumps,
ADL, exchange default or actual liquidation processing. The named Oct-10 crash
is outside this lane; R417 remains the separate cash-mechanics result.

At $10k capital / 1x costs:

| Asset | Fixed base units | Funding range, USD | Basis PnL, USD | Fees + assumed impact, USD | Min short maintenance buffer, USD |
|---|---:|---:|---:|---:|---:|
| XBT | 0.0540 | +24.24 to +239.11 | +0.87 | 78.84 | 4,337.07 |
| ETH | 1.631 | +36.37 to +233.64 | -1.61 | 74.42 | 3,945.11 |

Daily lower-scenario marked-NAV drawdown is in the saved report (roughly 0.94%
BTC / 0.95% ETH at $10k, 1x). It is neither intraday worst drawdown nor an
unconditional bound on drawdown over possible missing-rate paths.

## Conditional displayed entry depth

Both legs complete at every requested size/cost, zero unmatched base quantity,
funded spot budget and positive initial-margin buffer at the supplied perp mid.
**Total account capital** below is different from the per-order notional targets
in R417. The source books were captured separately; receive skew was
**378.011637 ms BTC / 286.759290 ms ETH**. No synchronized-source freshness,
queue/fill, future-exit, current capacity or repeated-liquidity claim.

| Asset | Total capital | Entry friction 1x | 2x | 3x |
|---|---:|---:|---:|---:|
| XBT | $10,000 | $41.59 | $83.17 | $124.76 |
| XBT | $25,000 | $104.13 | $208.26 | $312.40 |
| XBT | $50,000 | $209.11 | $418.21 | $627.32 |
| XBT | $100,000 | $419.79 | $839.57 | $1,259.36 |
| ETH | $10,000 | $42.20 | $84.41 | $126.61 |
| ETH | $25,000 | $105.69 | $211.39 | $317.10 |
| ETH | $50,000 | $211.99 | $424.00 | $636.02 |
| ETH | $100,000 | $426.66 | $853.35 | $1,280.08 |

Entry friction is spread/impact relative to each own mid plus the fee ceiling;
it is not a round-trip cost or expected profit. Future exits were not captured.

## Verification and provenance

- [Saved report](results/report.json), [independent check](results/check.json),
  [sole run log](run.log), [checker log](check.log), [frozen inputs](inputs.json).
- Independent Fraction arithmetic, importing no Decimal kernel/runner:
  **16,632 equalities PASS**, tolerance **USD 1e-12**, including cash/funding,
  basis/costs, base quantity, daily NAV, breach clocks and displayed-book sweeps.
- Before freeze/commit: **2,455 tests OK, 3 skipped**, exit 0, including **20**
  new synthetic tests. Integration tests use only invented API bodies in a temp
  directory and reject a tampered dollar result. No gitignored market data.
- Integrity: **0 errors / 14 pre-existing warnings**; catalogs match the index.
- PREREG hash: `7a62e3eeb69a39fbd7adcccbce9e0dec4f552ecff5377b856b681609f6841817`.
- [Source/fee/units qualifications](../../research/intake/funding_notional_20261103/kraken_eea_sources_20261106.md)
  carry exact primary links, dates and quotations; raw responses/UTC receipts
  are in its linked capture folder. No alternate blocked venue host or private
  endpoint, recorder, forward tick, subagent, account, credentials or order.

## Queue and next economic question

M487 becomes **TESTED** for this closed screen; exact executable net and access
remain unproved. M439 stays UNTESTED for its different execution/lead-lag
question. M485 remains PARTIAL: these real same-venue entry quotes and EEA tiers
are useful inputs, but not the requested matched cross-venue crash/ADL replay.
R417's frozen files and every forward journal remain unchanged.

Next qualify Coinbase's **European** products and public settled funding/fees,
starting from its official launch including France. Do not substitute global
Coinbase International products for CFSE. A new economic rule, input scope or
fee schedule needs a new frozen R-id. No repeated Kraken test with an easier
threshold or fee discount is authorized by this result.
