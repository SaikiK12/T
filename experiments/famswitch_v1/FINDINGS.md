# FINDINGS: famswitch_v1 (R414). A blind switch earns more in raw return but much more risk; holding all wins on risk

**Verdict: NULL for HEDGE and for FTL by the frozen rule. 2 trials, gate 0 (archive streams, in sample).**

- The run: `run.log`, 2026-11-06 11:52 UTC, PREREG `b872e7b6fbf6`, 12 inputs matched. One run.
- Results: `results/summary.json` and `results/daily.csv`.
- Window: 2023-08-31 to 2026-09-30 (1,127 days), 12 streams (R278 B from 2025-08-12).

## The rules against holding everything (1x unless stated)

| Rule | Return / yr | Sharpe | NW t | Max drawdown | Worst month | Turnover / day |
|---|---|---|---|---|---|---|
| **EQ** (equal capital, the baseline) | +32.6% | **2.64** | 4.56 | **−8.4%** | **−2.8%** | 0 |
| **HEDGE** (exponential weights) | +49.3% | 1.03 | 1.67 | −54.7% | −28.3% | 0.13 |
| **FTL** (last 90 days' leader, monthly) | +69.7% | 1.30 | 2.06 | −48.7% | −33.3% | 0.03 |
| ORACLE (knows each month's best, impossible) | +184.8% | 3.43 | 5.31 | −31.3% | +0.5% | 0.05 |

At 2x and 3x switching cost: HEDGE +39.6% / +29.9%; FTL +67.9% / +66.0%; EQ +32.6% / +32.5%.

## The decision (daily difference rule − EQ)

| Check (SWITCH_ADDS needs all four) | Bar | HEDGE | FTL |
|---|---|---|---|
| 1. Mean at 1x | > 0 | +4.6 bp/day, yes | +10.2 bp/day, yes |
| 2. NW t at 1x (lag 10) | ≥ 2.24 | 0.69, no | 1.28, no |
| 3. Mean at 2x | > 0 | +1.9, yes | +9.7, yes |
| 4. 1x in each half | > 0 | +7.7 / +2.1, yes | +11.9 / +8.8, yes |

## What happened
- **The switchers rode the most volatile book.**
  - FTL held R218 X2, a flow book, 59% of the time, and the unlock shorts 16%.
  - HEDGE gave X2 38% on average.
  - X2 alone made +125% a year with a 49% drawdown. The switchers inherited its swings.
  - Their extra return over EQ is not significant (t 0.7 and 1.3), and it cost five to six times the drawdown.
- **The blind switch rarely found the month's winner.**
  - FTL held that month's best stream in 29% of months.
  - The oracle's +185% a year shows what perfect switching would pay, and how far a blind rule stays from it.
  - What led the last 90 days kept leading in under a third of months. This matches R263's weak persistence
    (IC 0.044).
- **Holding everything was the better trade-off.**
  - EQ's Sharpe of 2.6 is more than double either switcher's, with a worst month of −2.8%.
  - The three families are close to uncorrelated (R285's archive: 0.000-0.014), so they smooth each other.

## Reading
- **"Ride whatever works this month" adds return only by concentrating risk.** Done blind, it does not track the
  winners: it catches them in about 3 months out of 10.
- **The higher-return path is the diversified book, sized up.** A calculation, not a measured result: the same EQ book
  at twice the capital gives +65% a year with a −16% drawdown (from `results/daily.csv`). That is FTL's return at about a third of
  its drawdown.
  - It ignores the cost of leverage, capacity and the fact that these streams are in-sample.
  - The flow books' own holdout (R198) was not confirmed.
- **What follows.** No switching rule is promoted. The diversified book is already in forward paper as R285 (M281),
  with weights fixed in advance. Its first look is at 180 days. Sizing it up is a decision for after that look.
- **Program context.** The read is against 9,784,336 + 2 program trials. Neither rule would survive that bar.

## Limits
These are as frozen in the PREREG:
- in-sample streams whose levels are inflated by their lanes' selection;
- no capacity or leverage limits when moving all capital into one book;
- one 3-year window.

The streams' own 2x and 3x costs are in their lanes' FINDINGS; m here scales only the switching cost.
