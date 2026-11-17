# PREREG: cmeterm_grid_v1 (R506). 432 cost- and confidence-aware variants of commodity carry on CME, read with walk-forward selection

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R506
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_cmeterm_grid.py` is the only writer of `experiments/cmeterm_grid_v1/results/`.
  - It reads R505's data with R505's frozen loader and writes no data.
- **Date registered (UTC):** 2026-11-17

**Methods:** M551 (new: a counted grid of cost- and confidence-aware variants of M549's commodity carry book). Carry
family.
- **Paper only:** it reads metered historical data already pulled; nothing in the code can place an order.

## Why this lane
R503-R505 read one textbook rule, with a few variants reported but never chosen. On 2026-11-17 the owner asked why there
are so few parameters:
- costs can be managed by strategy and by confidence;
- losses can be anywhere, and so can the edge.

**Searching wide is legitimate if the search is counted and the verdict is out of sample.** So:
- every variant is fixed here, before any CME settlement is read;
- all 432 are counted as trials;
- the verdict is on a walk-forward strategy that picks each year's variant from the past only;
- Hansen's SPA asks whether any variant beats zero at all, given all 432.

This PREREG was written and frozen **before R505's run**, so nothing in the grid reacts to R505's result.

## What the author has seen
- **No CME commodity settlement or price inside the window.** R505's frozen `fetch` was still pulling settlements
  when this was frozen (6 of 221 root-years done). None was read, summarized or printed beyond kept-row counts.
- **Everything disclosed in R503, R504 and R505's PREREGs:**
  - out-of-window samples for 2026-11;
  - contract definitions only, for the plumbing.
- **Synthetic worlds in the tests.**
  - In a world with carry planted, a 16-variant sub-grid gave PBO 0.73 even though the edge is real: many variants
    share it, and picking among near-twins is a coin flip.
  - So PBO is reported here, not used as a gate.

## Data
R505's data, loaded by R505's frozen `load()`:
- settlements from `data/databento/cmeterm_v3/`;
- ranks and details from R504's pinned map and snapshots, plus R505's follow-up definitions.

Same calendar, contracts, units, validity rules and costs as R503: $3.00 per contract per side plus 1 tick, in bp of
the held contract's notional.

### Frozen inputs
| File | sha256 | After the freeze |
|---|---|---|
| `scripts/run_cmeterm_grid.py` | b1be8a8ae558c4384053a5914777592a9a429574e2fdb64d2d0dd96722836d60 | fixed; `run` refuses to start if any row here changed |
| `scripts/run_cmeterm_v3.py` | 98064ca0ee4ad11dfe610b9efcf4eddab64193c9c3a078385761bf38cd53c068 | fixed: R505's loader |
| `scripts/run_cmeterm.py` | 0d035322383ebac8df92922ed2edd214b17988e81cb5d1edb4aacfb0ae48e08a | fixed: R503's rule pieces |
| `lab/inference.py` | 96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f | fixed: CSCV PBO, SPA, deflated Sharpe |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 | fixed: Newey-West t |

## The grid (4 × 3 × 3 × 3 × 2 × 2 = 432 variants)
| Dimension | Levels | R503's rule |
|---|---|---|
| Signal | carry; carry12 (mean of the root's monthly carry readings over the last 365 days, at least 8: damps seasonal curves); mom12 (sum of the n.1 contract's same-contract daily returns from 365 to 30 days back, at least 150); combo (cross-sectional z of carry + z of mom12) | carry |
| Roots per leg | 2; 3; a third of the valid roots | a third |
| Weights in a leg (each leg 0.5) | ivol (1/volatility); ew; conf (\|cross-sectional z of the signal\| / volatility: bigger when the signal is more extreme) | ivol |
| Signal frequency | every two weeks (the month's first settlement day and the first on or after the 15th); monthly; quarterly (Sep, Dec, Mar, Jun) | monthly |
| Band | off; on: a root already long stays long while it ranks in the top k + 1 (shorts likewise) | off |
| Cost gate | off; on: a root is a candidate only if \|carry\| over the holding period (14, 30 or 91 days) covers 4 × its per-side cost (entry, exit and one roll) | off |

**Common to every variant.**
- Candidates are R503's valid roots:
  - ranked contracts and a carry;
  - the far contract 40 or more days from expiry, with a positive entry price;
  - a volatility.
- No book is held with fewer than 9 signals.
- Entry is at the next settlement day after the decision.
- Held contracts are rolled to the current far contract on every monthly date, at every frequency. A roll pays both
  sides.
- Weights are held constant between signal dates.
- Costs follow R503's formula.

The variant with R503's rule reproduces R503's engine exactly (tested).

## Primary read: walk-forward, 2014-01..2026-10
- Each 1 January it switches to the variant with the best net daily Sharpe from 2010-09 to the day before, at 1x costs.
- It pays the cost of moving from the previous variant's holdings to the new one's, and of entering at the start.
- **Cost sensitivity.** The whole procedure is rerun at 2x and 3x costs: picks and switches at that cost.

## Verdict
- **GRID_PASS:** all three of:
  - walk-forward net > 0 with Newey-West t ≥ 2.0 at 1x;
  - walk-forward net > 0 at 2x;
  - Hansen's SPA (consistent) p < 0.05 over the 432 variants' daily nets at 1x (stationary bootstrap, 1,000 draws,
    mean block 20, seed 0).
- **GRID_WEAK:** walk-forward net > 0 at 1x, not PASS.
- **GRID_NULL:** walk-forward net 0 or below at 1x.

## Also reported (where the edge and the losses sit), never chosen among
- the walk-forward strategy:
  - by year;
  - its picks by year;
  - gross by root and by leg (long, short);
  - its break-even cost multiple (gross / 1x cost);
- every variant's net %/yr (1x and 2x), Sharpe, NW t, maximum drawdown and cost per year (`results/grid.csv`);
- each grid dimension's levels across all variants: mean and median net, mean Sharpe, share positive;
- the share of variants positive at 1x and 2x;
- the ten best and five worst variants;
- R503's rule inside the grid;
- PBO by CSCV (16 blocks, monthly nets at 1x);
- the deflated Sharpe of the best full-sample variant, deflated by 432 trials.

## Null and multiplicity
- **Registry trials: 432.**
- **Program trials so far: 9,785,315.**
- The walk-forward strategy is the one pre-specified selection procedure. The best full-sample variant is reported only
  with its deflated Sharpe.
- **Power, stated before the read.**
  - Over 12.8 out-of-sample years, a true Sharpe of 0.6 gives t ≈ 2.1, and 0.4 gives t ≈ 1.4.
  - So a PASS needs a strong edge that persists and that the past picks well. A WEAK is weak evidence either way.
- **What a PASS earns.** No money: a capital and micro-contract feasibility study for the owner, then a forward paper
  lane on the walk-forward strategy.

## Evidence lineage
- **Parents:**
  - R505 (same data; its primary rule is this grid's carry/third/ivol/monthly/no band/no gate variant);
  - R503 and R504 (frozen rule and plumbing);
  - room 2;
  - the owner's 2026-11-17 question.
- **One decision this feeds:** whether any cost- or confidence-managed version of commodity carry is worth a capital
  and broker study.
- **docs/GATES.md** sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. This is gate 1
  on history.

## Not checked before the freeze
- **Costs.**
  - Measured CME spreads per root: one tick is assumed.
  - The owner's fees.
- **Contract mechanics.**
  - Integer contracts and minimum capital for the variants.
  - First notice dates beyond R503's 40-day rule.
- **Model.**
  - Switch costs use each root's current far contract on the switch day. They undercount slightly when two variants
    hold different contracts.
  - Constant weights between signal dates (an implicit daily rebalance at no cost).
