# PREREG: famswitch_v1, a blind switch between the lab's strategy streams against holding them all

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R414
- **Owner (single writer):** Claude (session claude/yo-9a1k5w)
- **Date registered (UTC):** 2026-11-06
- **Method:** the owner's request of 2026-11-06, a blind switch between strategies. It extends M281 (the
  cross-family book, R285) with dynamic weights.

## Question
Each day, can a rule that sees only the past choose between the lab's 12 strategy streams so as to beat holding them
all equally, after switching costs, on 2023-09 to 2026-09?
- **The owner's idea:** when one strategy follows the chart for a month, ride it; when another takes over, switch to
  it, blind.
- **The rules:**
  - an exponential-weights learner (HEDGE);
  - a monthly follow-the-leader (FTL).
- **The bound:** an ORACLE that knows each month's best stream is reported as the upper bound no blind rule can reach.

## What was seen before (gate 0)
Every stream is an archive result its own lane already read, inside the windows those lanes used. These are in-sample
numbers.
- **R285's archive context** (`experiments/xbook_fwd/archive/context.json`) gives each stream's mean, Sharpe and the
  correlations: carry about +12%/yr, flow about +83%/yr, events about +79%/yr.
  - The flow books' R197 one-shot holdout (R198) was **not confirmed**.
  - Most event lanes are still in forward paper.
- **Earlier switching lanes, all NULL:**
  - R263 (walk-forward pick of chart strategies);
  - R233 (regime choice among flow books);
  - R186 and R187 (merges).
  - R263's persistence IC was 0.044.
- **Plumbing** (`plumbing.log`): 12 streams, 1,218 days. Allocation can start on 2023-08-31; R278 B joins on
  2025-08-12.

So a SWITCH_ADDS here is gate 0 only. It can only earn a forward paper test. It is never a real-money step.

## Data
- **Streams:** rebuilt with `scripts/xbook_archive.py`'s functions from the files hashed below, daily, over
  2023-06-01..2026-09-30. Each is a daily net return at its lane's 1x cost on one unit of capital.
  - **carry:** R278 A, R278 B, R279 A, R279 B;
  - **flow:** R215 A, R215 B, R218 X2;
  - **events:** R266 unlocks, R268 delist, R270 montag, R272 FF and R272 PL. Each event lane's legs sum by exit day
    over 10 slots, with 0 on days without a leg.
- **Availability:** a stream can be weighted on d once it has 90 days of data up to d − 2, and has data on d.

## Rule (scripts/run_famswitch.py)
Weights for day d use returns through d − 2 only. Weights sum to 1 over the available streams.
- **EQ (baseline):** equal capital over the available streams.
- **HEDGE:**
  - each stream's score is its discounted cumulative return (half-life 30 days) through d − 2;
  - weight ∝ exp(20 × score), so a 5-point lead weighs e ≈ 2.7 times more.
- **FTL:** on the first day of each month, all capital goes to the stream with the highest return over the 90 days
  ending d − 2. It is held for the month.
- **ORACLE (reference, not a trial):** each month, all capital is in the stream with that month's highest return.
- **Switching cost:** m × 0.20% per unit of capital moved (Σ|w(d) − w(d − 1)|), m = 1, 2, 3. The first day pays its
  entry.
  - The streams already carry their own 1x costs.
  - Each lane's own 2x and 3x are in its FINDINGS; here m scales the switching only.

## Decision
- **Trials:** 2 (HEDGE, FTL). The read is against `registry.program_trials('registry/rounds.csv')`.
- **SWITCH_ADDS for a rule** needs all four, on the daily difference rule − EQ:
  1. the mean at 1x > 0;
  2. Newey-West t (lag 10) at 1x ≥ 2.24 (one-sided 1.25%, Bonferroni over 2);
  3. the mean at 2x > 0;
  4. the 1x mean > 0 in each half: 2023-09..2024-12 and 2025-01..2026-09.
- **Otherwise NULL** for that rule.
- **Reported for every rule at 1x, 2x and 3x:**
  - annual return, Sharpe, NW t, maximum drawdown, worst month and turnover;
  - mean weights;
  - the share of months in which FTL held that month's best stream;
  - each stream alone.

## Known limits (stated now)
- **In-sample streams:** they are inflated by their own lanes' selection. Both EQ and the switchers use them, so the
  comparison is fairer than the levels. The levels are not forecasts.
- **No capacity or leverage limits:** moving all capital into one event or flow book ignores that book's capacity.
- **One window:** 2023-09 to 2026-09.

## Inputs frozen with this file
```inputs
16c9a28c7569124d2ee403af77141a1487f182e0a21b8b01289c46322fd5db5d  scripts/run_famswitch.py
284eb1ed3ac401248d6077ede31aa37d353c53cb2b8cfdb550495540f92a67ec  scripts/xbook_archive.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
d0f59fd6943f5869c91e5c607a27fadd955e440ae54be35aa4d5a8a13b9e1bfe  tests/test_run_famswitch.py
790d4a0fae2d0fa51e3c5c8e0d28c9ce7be9c5f037187c39b95959fb68fa8dfc  experiments/xfund_v1/results/daily.csv
0ab7db847cb9e0e51c93d59ad205a64888664a067fb8255a4093494c48d6b7ab  experiments/xfund_kd_v1/results/daily.csv
3ea686670c35c9946a560cc29cd1087b79cbeef40a78208840ab3b3e86aa0ec5  experiments/sizing_v1/results/daily.npz
0aeb33d4cce29fd97a8077e6934180881411b5893f0a76346de5d59791ec2535  experiments/unlocks_v1/results/events_priced.csv
4064307ea36154ee84b0ff8521cd63a7220b8d4219bedce34734095cf5bc3897  experiments/delist_v1/results/legs_priced.csv
2dedd3a19223a3a5428ef3bd73fda824918fb1c21bb2230bb42ddb22d8fc6874  experiments/montag_v1/results/legs_priced.csv
ee835a7410ff2a9aaed350e869295a879d357848f9609d46ee6568c386b5dcba  experiments/announce_v1/results/legs_priced.csv
```
