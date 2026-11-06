# PREREG: kraken_carry_v1, EEA spot/perp carry at fully funded capital

Freeze with `lab.prereg.freeze()` before running anything. This file is never edited after freeze.

- **Registry id:** R418
- **Owner (single writer):** Codex, codex/france-carry-execution-20261106
- **Date registered (UTC):** 2026-11-06
- **Canonical method:** M487; related M439 execution and M485 carry capital mechanics.
- **Claims:** issue #7 comments 6691777494, 6691943941 and 6692184814.

## Question
Does a fixed-quantity BTC or ETH spot/short-linear-perp hold on Kraken have
enough historical funding and basis PnL to clear current regular taker costs
and a predeclared capital hurdle, while respecting separate USD margin cash?

This is **gate 0 exploratory cost-model evidence**, not actual fills, a fresh
holdout, a statistical SIGNAL or an owner's access determination.

## Universe
Exactly BTC: PF_XBTUSD / spot XXBTZUSD, and ETH: PF_ETHUSD / spot XETHZUSD.
USD quotes/settlement, contractSize=1, fixed assets known before the study.
No universe scan, ranking, altcoin, reserved coin/path or 2020 row. No delisted
asset comparison or cross-sectional score: two named major-asset case studies.
Current metadata confirms these products, not historical universe completeness.

## Data
Direct closure: `inputs.json`, all raw bodies and receipts there, code, cases,
runtime pins, copied gates and the source/units note. SHA-256 checks before and
after the sole run; every frozen byte must be present in HEAD **before** it can
measure. Raw decompressed bodies must match acquisition receipt hashes too.

Public API data acquired 2026-11-06, latest vintage. Plumbing inspected only
schema, identity/rule metadata, counts, timestamps and missing-hour locations;
no funding/price distribution, return, basis, spread or depth-cost statistic.
The fixed holding period is **2025-12-01 00:00 through 2026-11-01 00:00 UTC**,
half open for funding, **335 days / 8,040 hourly periods**. No extension after
reading. Official source extraction is in the frozen note.

Actual spot daily traded bar opens, derivative daily traded bar opens and hourly
mark OHLC are benchmark prices. They are **not executable bid/ask fills** or
certified synchronized first transactions. Captured public books are a separate
dated entry-only diagnostic, never backfilled into the historical sample.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Always-on fixed inventory | predefined dates and identities; initial spot benchmark; common lot | Kraken USD spot and linear perps, base units | One entry at start, one exit at end; no monthly churn, resize or transfer | Historical bar opens; acquisition receipts preserve receive times | No signal; bar opens are retrospective execution proxies | Two current survivors, latest vintage; no panel selection | Missing start/end/day/mark refuses; no interpolation |
| Funding cash | absolute fundingRate, timestamp | Kraken historical-funding-rates v3; USD/base-unit/hour | timestamp is period start; q times rate for each full held hour | Retrospective source, hourly settled-rate history as documented | Not used to select entry/exit | 8,035 observed held hours per asset; 5 unknown | Do not use relative rates, assume zero or extend a last rate |
| Missing-hour range | missing clock, surrounding spot-index candle highs; current maxRelativeFundingRate | Kraken reference index / current contract metadata | Each missing hour; preceding/current/following hourly high envelope | Separate bounded counts-selected captures | Retrospective uncertainty diagnostic, never a predictor | Latest vintage; historical cap stability not certified | ±current relative cap times index-high envelope is an **assumed scenario**, not observed funding or an unconditional bound |
| Price/basis PnL | same q times spot exit-entry plus short entry-exit | Actual spot/trade opens, USD/base | Entire closed hold; daily spot/mark opens for NAV | Latest-vintage public history | No as-of feature or fill claim | No cash yield, leverage resize, quote parity or borrow assumption | Missing price refuses; no constant-notional phantom gain |
| Current fees and historical spread/impact | source table Tier 1 spot/perp taker; cases.json slip | Current published 0.80% spot / 0.05% derivative, USD quote-fee scenario; invented 1 bp/order-side slip | Four trades only; all capitals get same conservative tier ceiling | Current schedule extracted before freeze | Not owner entitlement or historical fee vintage | No earned volume/AoP discount; deprecated /feeschedules and AssetPairs fees excluded | Cost sensitivities 1x/2x/3x; no free maker fill |
| Margin/cash screen | hourly mark high; lower funding cash; current EEA retail schedule | europa/europa_crypto 10% initial / 5% maintenance below $30m next boundary | Separate USD short wallet; adverse ordering of negative pending funding before hourly high | Current captured tiers; old schedules unknown | Historical stress diagnostic only | No collateral offset, external top-up or transfer | Tier excursion refuses; possible breach/negative USD cash blocks model pass; no invented liquidation fill |
| Entry capacity diagnostic | actual displayed spot asks/perp bids, lots, minima and fee ceiling | One public snapshot pair per coin, price and base size | Four total capitals, three costs, matched same q | Separate UTC/monotonic receipt clocks | Conditional asynchronous displayed depth, no fill guarantee | Current capture only, no independent sample of future exits | Partial/unmatched or unfunded cases stay explicit; no liquidity extrapolation |

## Rule or search space
One rule, two asset implementations. Total capital C is **$10k/$25k/$50k/$100k**
per independent asset case, never C per leg. Half funds the spot wallet and half
funds the USD derivative wallet. Quantity is floored to the common lot once,
using the spot wallet including the **3x** entry fee/slip reserve, so inventory
is identical across costs and never rebalanced as price changes. Residual spot
USD is retained. Short proceeds are not free capital. USD quote-denominated
fees, no borrowing, cash yield, staking, transfers or non-USD conversion.

Historical model: buy spot/short perp at their initial daily open proxies plus
adverse execution price offsets; hold that same base quantity; funding credits
or debits USD; close both once at terminal daily opens with costs. All **24**
asset/capital/cost cases remain. Monthly rows attribute funding from this same
position; they do not create eleven selected trades or extra strategy trials.
Report funding on initial notional **and on total capital** separately, price
basis PnL, fees, assumed slippage, terminal interval and daily-mark drawdown of
the lower-scenario path. Annualization is simple 365/days, not a forecast.

At each hourly mark high, check short cash plus lower-scenario past funding,
negative pending hourly funding and unrealized short PnL against supplied EEA
maintenance. Positive pending funding is not lent in advance. Retain the first
possible maintenance breach and first possible USD cash deficit. A continued
ledger after either is **counterfactual**, with executable terminal PnL unknown;
do not fabricate a liquidation fill or pretend a recovery repaired a close.
This is not an actual liquidation algorithm or an outage/ADL replay. R417's
named crash accounting result remains separate and unchanged.

Entry books: buy spot and sell perp only, quantity sized once from the spot mid
with the same fee reserve and common lot. Sweep visible depth at each cost,
respect minima, show both quantities/fees, unmatched quantity, entry friction,
receive skew, spot budget and short initial-margin buffer at the supplied mid.
An unfunded/partial case is not capacity. No present-day or future exit capacity.

## Splits and cost
No fit, optimizer or claim that this spent archive is fresh. Entire window is
program version 1's old holdout, now gate 0 under current gates. Both assets and
all capitals/costs are reported, without picking a winner. At 2x/3x multiply
**all execution price deviations and fee fractions**, not funding, inventory,
capital or historical price moves. Historical 1 bp per-side slip is explicitly
an assumption; current observed depth cannot certify it for the past.

## Gates
Each named asset/capital clears this narrow screen only if:
1. all source/clock/identity/cash invariants and the independent rational checks pass;
2. no possible maintenance breach and no USD deficit at any of the three costs;
3. lower-scenario annual return on **total** capital exceeds **4% at 1x** and
   **0% at 3x**.

The 4% is a fixed **planning hurdle assumption**, not an observed T-bill yield.
State **MODEL_CANDIDATE_EXECUTION_UNPROVEN** or
**DOES_NOT_CLEAR_FROZEN_SCREEN** for every case. A pass earns only consideration
of a new prospective paper protocol with source-gap resolution and true
execution/account calibration. Exact executable net/capacity remain unknown.
A failure does not disprove all fee tiers, sizing policies or EEA venues.

The independent `scripts/check_kraken_carry.py`, written before freeze, imports
no Decimal kernel/runner. It checks raw funding/cash/basis/fee/quantity/NAV and
book arithmetic using Fraction within **USD 1e-12**, plus breach timestamps.

## Null
No statistical SIGNAL, p-value, bootstrap, Sharpe or effective independent-trade
count. It is a necessary economic screen, not an inferential null test. Record
negative/incomplete cases with the same care as a positive model interval.

## Multiplicity
**2** asset implementations count as trials; four capital sizes and 1x/2x/3x
are required implementation/cost sensitivities, with no best-case selection.
Program trials before registration: **9,784,343**; report the actual current
`registry.program_trials('registry/rounds.csv')` again with results. The sum is
bookkeeping, not independent-test correction. No across-family alpha admission.

## Evidence lineage and admission (future lanes only)
M487 extends M439's venue qualification and M485/R417's funded-cash discipline.
Other crypto funding carry parents and the owner's evidence review are already
seen. Current APIs overlap older Kraken archives; do not call this another
unseen venue/sample. No results from unfinished R404, reserved batches, Boros
settlements or paper journals are used. Current gates are copied and hashed in
the input manifest. No on-time forward days, dependent-null calibration,
10-day trim, leave-two-coins-out, power or selection-control evidence is being
claimed; these unmet requirements block gate 1/admission. Nothing here runs a
forward tick, recorder, order, account query or go_real.

## Stop rules
One invocation only after freeze and commit. Exclusive creation of `results/`
reserves the sole attempt, including a failure. Missing/unqualified source or
any invariant failure stops, with no rerun/price repair/fee reduction or new
dates after reading. Any changed frozen input, code or idea needs a new R-id.
The checker reads saved output; it never reruns the Decimal measurement.
Registration is append-only: its pre-run REGISTERED/PENDING row is not rewritten;
native FINDINGS and the method note carry the completed result.

## Frozen input manifest

27411b2937308afd2481f0431e26ab0e5d5c782ee8bd38c7edb9691e4441c41c  experiments/kraken_carry_v1/inputs.json
