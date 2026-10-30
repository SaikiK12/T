# R310: twelve cost-aware funding/basis equations

- **Registry id:** R310
- **Owner (single writer):** Codex, `codex/lab-consolidation`, existing draft PR #49
- **Date registered (UTC):** 2026-10-24
- **Canonical method:** M409; source hypotheses recorded in the existing method intake
- **Decision group:** one possible new paper comparison against the MEXC/Lighter carry parent

Input manifest SHA-256: 33a9e57d06c1e4521cab30cf5765a7c2fdeaee8710141ae1eb9014a49b4f894f

Complete the bounded acquisition, hash the inputs and freeze with `lab.prereg.freeze`.
Commit and push the complete code/specification/data identity before the first market run.
After freezing, neither specification nor pinned code may change within this lane.

## Question and scope

Can settled-funding forecasts, with or without a price-basis correction, improve
net PnL at comparable training risk over the existing carry rule under the same
fixed-quantity, segregated two-venue accounting? The finite family has 12 policies;
it is not a broad strategy search. All historical estimates are **gate 0**.

Use exactly the 117 rows with both MEXC and Lighter in R288's frozen
`experiments/xfund_lt_v1/symbols.csv`. Require its existing nonempty Binance
field: no reserved MEXC-only, other long-tail or 2020 sample is read. The universe
is current-survivor-conditioned, not a point-in-time listing universe. Aliases
are inherited, not invented after returns. Current metadata and a trailing
identity guard can reject a pair; that is not historical identity certification.

## Inputs, clocks and limitations

`inputs.json` pins settings, implementation and dependencies, frozen symbol table,
current contract captures, acquisition receipts/status and every source file in
`data/equations_v1`. The offline runner verifies the manifest and exact parquet
inventory before and after calculation. No original forward cache is overwritten.
Acquisition uses unauthenticated public MEXC and Lighter endpoints, at most two
workers, 8,000 requests and 250 MiB wire bytes, 2025-04-27 through 2026-10-01.
Prices are hourly opens strictly before END, normalized to their close instants;
funding events keep their exact timestamps, inclusive of the terminal settlement.
Duplicates must agree. Silent timestamp flooring and source-value repair are forbidden.

Training/calibration is [2025-04-27, 2026-01-01); validation is
[2026-01-01, 2026-10-01), 273 calendar intervals. History before the validation
start remains available as trailing predictor input. All dates have been inspected
by the program or overlap earlier searches; this is **not fresh out of sample**.
Each split starts flat with $10,000, $5,000 segregated at each venue; no transfers.

Only trades' closing prices are available for historical funding notionals and
marking. MEXC actually charges funding on fair-price notional: these calculations
are explicitly a **close-price funding-notional proxy**, not exact settled cash.
Lighter's official rule uses underlying position size times **index price** times
the signed hourly rate; its historical index series is also absent. Lighter's raw
`value` field has unresolved documented units and is retained but
not used as cash. USDT/USDC parity is an assumption. Historical lot/minimum/margin
rules, index/fair-price paths, latency, spread, depth, partial fills, liquidation
and counterparty risk remain unverified. No gate 1/2/3 admission follows from a pass.

## Closed formula family

Let `f[v,c,d]` be the signed sum of settlements in (d-1 00:00, d 00:00],
positive when longs pay. A day is available only if every intervening hour has a
known event or certified non-event. Lighter needs each hourly record. For MEXC,
an inter-event gap is certified only when both surrounding `collectCycle` fields
equal that gap; a schedule transition is unknown. Source absence is never zero.

For each `H` in {1,7,14} days:

- **F0:** `F_hat = H * mean(f[d-13:d])` separately for each coin and venue.
- **F1:** `F_hat = H*mu30 + (f[d]-mu30)*sum(phi**j, j=1..H)`.
  The venue's `phi` is pooled AR(1) OLS on complete coin series over the last
  30 daily observations, each series centered on its own 30-day mean, clipped to
  [-0.99,0.99]. A constant training series has phi=0; unavailable fit stays missing.
- **B:** `x = log(P_L/P_M) - trailing_30_day_mean(log(P_L/P_M))`.
  Estimate a pooled no-intercept slope for each H over the last 30 eligible label
  origin dates. The label is the long-MEXC/short-Lighter equal-underlying-quantity
  H-day price PnL, divided by the larger entry price. Entry/exit labels use 01:00
  closes. Only labels ending **strictly before** today's 00:00 forecast are admitted:
  origin `j < d-H`; at least 20 distinct label dates are required. Then `B_hat=beta*x`.

Policies are **F0, F1, F0+B, F1+B**, each at H=1/7/14: exactly 12, in settings order.
Forecasts are recomputed causally at 00:00. Online updates during validation use
only observations already closed then; no refitting on future labels.
Require current usable contract rules, both fresh midnight prices, current paired
price ratio 0.95..1.05, at least 20 paired fresh daily returns in the last 30 days
with correlation >=0.9, and complete 14-day funding. F1 and B additionally require
their own complete inputs. No fallback to predicted zero when a model is missing.

## Inventory, costs and capital

At 01:00, consider flat / long MEXC-short Lighter / short MEXC-long Lighter.
Value a target in quote dollars using predicted funding on current leg notionals
plus the B price term when present, less **2x immediate turnover cost and 2x planned
terminal exit cost**. Flat includes actual exit cost of existing inventory.
Choose the exact additive cardinality solution for at most 20 pairs; ties preserve
inventory, then flat, then frozen table order. This solves the state-score problem,
not a claim of global optimality after venue gross constraints.

Allocate at most $250 per leg per new pair, multiplied by its frozen training
risk scale. Round MEXC contract units down, then Lighter base units down, enforce
both minima, no leg above its budget and <=1% underlying-unit mismatch. Keep
underlying quantities unchanged while the state is retained: no daily notional
reset or hidden rebalance. Cover both legs before flipping. Process removals
first, then new entries in frozen coin order, enforcing 2x-cost per-venue equity
>= gross exposure plus new fees. Never increase a budget above 1x its base.

The one-way scenario costs are **MEXC 10 bp, Lighter 4 bp** on actual traded
notional. Report 1x,2x,3x with identical quantities/decisions; 2x equity governs
admission. These are declared cost scenarios, not measured historical BBO costs.
The terminal fee in state choice is a forecast penalty only; the ledger charges
executed turnover and terminal liquidation once. At a shared clock: mark old
positions, settle old positions, then fill. A new 01:00 position receives no
00:00 or 01:00 funding. Close-price fills at that instant are a historical proxy,
not proof a signal can execute without latency.

Unknown held price or funding makes the affected day unscored and requests paired
exit at the next fresh quote; realized price moves bridge the hole, never zero-fill.
A known zero-volume close may mark last-trade PnL but cannot fill. Unknown current
funding blocks new inventory. A forced exit cannot reopen on the same clock.
A gross/equity breach is unscored and its exit request persists until tradable;
hourly nonpositive venue equity is flagged at every cost tier. Terminal END funding
is paid before paired close; an unavailable terminal quote leaves explicitly open legs.

## Controls and risk matching

Primary **reference**: original R288 MEXC/Lighter Book parameters (14-day mean,
5% annualized entry spread, half-threshold exit, 20 slots), R294's causal
three-stale-day forced exit, under the **same** eligibility, 01:00 fills, rounding,
fixed quantities, segregated accounting and cost scenarios as the candidates.
It is a parameter/control replay, not exact reproduction of the old result bytes.
The untouched original Book's global archive-end `last_fresh` exit supplies a
separate **legacy accounting diagnostic**, never the primary state or selector.
Cash is zero return at all tiers; no extra candidate is selected from controls.

First simulate calibration at base size. A risk-eligible series has >=60 scored
days, >=60 active days and 2x daily return SD >1e-12. The common target is the
smallest positive training SD among eligible candidates and the reference. Scale
only down by target/SD; rerun the same calibration with the smaller lot budgets.
These are budget ratios, not a guarantee of exact realized volatility parity.
If the reference or every candidate is ineligible, return INCONCLUSIVE.

Select **one** eligible candidate by highest risk-adjusted-size calibration 2x
mean **dollar** PnL, tie by lower turnover, then fixed policy order. Persist the
choice and scales before building full-period forecasts or simulating validation.
Validation cannot replace that choice. Report all 12 candidates, not just the pick.

## Tests, gates and multiplicity

Trials: **12**; program trials before this lane: **9,478,758**.
This reuses R288/R294 carry economics and contributes to one funding/basis paper
decision group. It does not reset program-wide selection history.

Inference uses actual daily NAV returns at 2x costs against the matched reference.
Require >=60 common validation days and no missing common calendar day; do not
compress gaps into adjacent bootstrap observations. No selected candidate, a
degenerate paired variance, or incomplete common evidence is INCONCLUSIVE.

- Family SPA on the 12 paired streams, stationary bootstrap mean block 10 days,
  2,000 replicas, seed 20261024; zero-variance columns are excluded computationally,
  not removed from the trial count. Require consistent p<=0.05.
- Selected paired mean test: 5,000 stationary-block replicas, seed+1; one-sided
  null centered at zero; plus-one p<=0.05/12 and percentile 95% lower bound >0.
- Selected 2x net mean >0; selected-minus-reference mean >0 in each half;
  3x net mean >0; remove the two largest candidate coin contributions and require
  remaining mean dollar PnL >0; independently trim best/worst 10 days and require
  positive candidate and paired-gain means.
- Selected validation SD <=1.10 reference SD; both primary accounts entirely
  scored, no gross breach, no nonpositive venue equity at any tier, no open legs.

Every gate must pass for **PARTIAL**, a gate-0 paper candidate only. Any failed gate
with sufficient common evidence is **NULL**, with every failure retained. Insufficient
evidence is registered **DONE/PENDING** and explained as INCONCLUSIVE, not a hit/null.
Report NW(10) t, PnL decomposition, drawdown, coin attribution, position/ticket counts,
venue equity, data flags, raw and matched training risk, and all cost sensitivities.
SPA and Bonferroni are conditional family controls, not protection against the
program's adaptive prior 9.48 million trials or the survivor-conditioned universe.

## Prospective condition and stop rules

No forward activation is part of a historical pass. Only if the preselected
candidate earns PARTIAL may a **new** prospective comparison be frozen, against
the same reference, with new on-time days only (all hours within 60 minutes),
delayed quotes/depth/partials, measured costs and venue-specific funding notionals.
Before any scoring, calibrate sequential 90-day futility / 180- and 365-day looks
under a dependent zero-mean null; report 80%-power days, 10-day trimming and
leave-two-coins-out. A long required horizon is explicitly a futility screen.
One family, one decision: diagnostics do not create additional chances. Gates 1–3
and a separately documented executable paper result remain required before owner
review; this lane cannot authorize trades, leverage changes or real capital.

The current `docs/GATES.md` hash is in inputs.json. Freeze code and inputs before
outcomes; verify before/after; use a single-writer lock and a fresh output directory.
Preserve nulls, input/source versions, original lanes and append-only journals.
No retuning, rescued validation winner, extra horizon/threshold/window, reserved
read, fee reinterpretation or retrospective source repair after results. A code
defect requires preserving the failed lane and registering a new version/id.

## Primary references (mechanics, not profitability)

- MEXC Futures Calculation Guide:
  https://www.mexc.com/support/article/mexc-futures-calculation-guide-312060306409668608
- Lighter historical funding API:
  https://apidocs.lighter.xyz/reference/fundings
- Lighter's official hourly settlement, funding direction and index-notional rule:
  https://docs.lighter.xyz/trading/funding
- Lighter public rate limits:
  https://apidocs.lighter.xyz/docs/rate-limits
- Official Lighter SDK Funding model exposes the four fields without defining
  `value` units; its inspected version is retained in inputs.json:
  https://github.com/elliottech/lighter-python/blob/main/lighter/models/funding.py
- Inan, *Predictability of funding rates*, pre-proof available 2026-10-17:
  https://doi.org/10.1016/j.irfa.2026.105464
  BTC Binance/Bybit sample and candidate inspiration only; not altcoin/MEXC evidence.

Gates policy SHA-256: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926
