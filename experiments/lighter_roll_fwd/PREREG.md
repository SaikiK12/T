# PREREG: lighter_roll_fwd (R389). Does Lighter's BRENTOIL book lag the documented index roll steps?

Freeze with `lab.prereg.freeze()` before the first step window (2026-11-06 23:29 UTC). Never edited afterwards; a
change is a new lane.

- **Registry id:** R389
- **Claim:** Claude block R380-R389, claimed on issue #7 on 2026-11-02.
- **Method:** M462 (web-deep SRC1103-014).
- **Evidence class:** forward paper event study on data recorded after this freeze. Paper only, no orders.

## Why
- Lighter documents that its BRENTOIL index rolls from the front to the next ICE month in five 20% steps. One step
  falls on each London business day 5-9, at 23:59 London; the docs table says 7:00 PM ET, one minute later.
- At each step the index moves by 0.2 × (next − front) while the underlying market does not.
- If Lighter's book lags the published step, a position in the step's direction over the window collects part of it.
- The steps are forced and scheduled, a flow the lab has not tested. Five steps a month on one contract means a slow
  event study.

## Data (recorded forward only)
- **Recorder:** `scripts/record_lighter_index.py`, Lighter's public `market_stats/<id>` websocket for BRENTOIL (159)
  and WTI (145).
  - It keeps every message (`kind` 0) and a once-a-second snapshot of the latest message while connected (`kind` 1).
  - Fields: index, mark, mid, best bid and ask, last trade, funding rate and stamp, open interest.
- **Start:** 2026-11-03 21:35 UTC.
- **What the author saw before this freeze:** the probe output and the first rows, which show current BRENTOIL and WTI
  index, mark and quotes on 11-03, and the recorder's row counts. No step window has occurred yet.

## Calendar
- **Step days:** London business days 5-9 of each month (weekdays, excluding England and Wales bank holidays as listed
  in the scorer), from 2026-11 to 2027-05.
- **November 2026:** 11-06, 11-09, 11-10, 11-11, 11-12, which matches Lighter's table (F27 → G27).
- **Window:** each step day's window runs from 23:29 UTC to 00:30 UTC the next day, so it holds both stamps (London is
  UTC and New York is UTC−5 from November to March). From 2027-03-28 London is UTC+1, so 23:59 London is 22:59 UTC.
  - **Deviation fixed now:** the windows stay at UTC 23:29-00:30. Steps that fall outside them are reported, never
    rescued.

## Rule (`scripts/score_lighter_roll.py`, unchanged after this freeze)
1. **Direction.** Each month's step 1 sets d = the sign of the change in (index − mid): its median over
   [00:02, 00:10] UTC on the next day minus its median over [23:50, 23:58] UTC. Each median needs at least 60 rows.
   - Step 1 is never traded. With no direction, the month's steps are missing.
2. **Trades.** Steps 2-5 are paper trades in direction d.
   - Entry: the touch at 23:29 UTC (the ask for a long, the bid for a short).
   - Exit: the touch at 00:30 UTC.
   - Each touch comes from the last row at or before the instant, no older than 60 s; otherwise the step is missing,
     never filled.
3. **Net.** gross = d × (mid at exit − mid at entry) / mid at entry. Funding is −d × Lighter's settlement stamped at
   00:00 UTC (reported in percent). Cost is the two half-spreads.
   - Net at m× = gross + funding − m × cost, all in bp.
   - Lighter charges 0 fee on standard accounts. Size is not modeled; the book's top level only.

## Decision
- **Mechanism stop.** If November's five index-minus-mid jumps are all measured and do not share one sign, the
  documented step is not seen: the verdict is NULL and the lane stops.
- **Primary.** Taken on the first 20 traded steps (about 5 months). PASS needs all of:

| # | Check | Bar |
|---|---|---|
| 1 | t of the 1x mean net, steps independent | ≥ 2.0 |
| 2 | 2x mean net | > 0 |
| 3 | The book does not move before the step: mean d × (mid at 23:58 − mid at 23:29) | < half the mean gross, and the mean gross > 0 |

- Otherwise NULL.
- If fewer than 20 steps are traded by the end of 2027-05, the lane is INCONCLUSIVE.
- **Trials:** 1.
- **Reported, not decided on:** 3x, each step's index-minus-mid jump, missing steps and why, WTI over the same windows
  as a placebo, and the funding share.

## What a PASS earns
- A frozen live paper lane (new id) with walked book fills at a stated size, and R364-style live cost gating.
- No money moves; real orders need `lab.gate.go_real()` and the owner.

## Power
- 20 steps. If the lag were 0.5 × the step (about 5-15 bp on a $0.2-0.6 F27/G27 spread at $100) and the hour's mid
  noise is 30-60 bp, the t is far below 2.
- A PASS needs the book to miss most of the step on most days. A NULL is the expected outcome, and it says the book
  prices the roll.

## Multiplicity
- Program trials before this lane: 9,784,325 (`registry.program_trials('registry/rounds.csv')` on 2026-11-03).

## Code and inputs
- `python -I scripts/score_lighter_roll.py [--through YYYY-MM-DD]` verifies this PREREG first.
- `results/` is rewritten on each score, and no interim score changes the rule.

```inputs
30aa7d1e974da636d04bf75d9d5937dd1d345203d43f16461d04f1d6cbfa9064  scripts/score_lighter_roll.py
2d5c0cdac4906904ae7417e4f6708aff78e1481501b5f58d2a1d5b25511dfeec  scripts/record_lighter_index.py
a4d7d1c9ad49a8786406076663f6e420d704803e905f3051ad003f01c7f27bdc  scripts/record_lighter_trades.py
```
