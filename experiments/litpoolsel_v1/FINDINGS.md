# FINDINGS: litpoolsel_v1 (R452), gate 0

**NULL (stop)**, by the frozen rule. The 1x book's excess over the 4% hurdle is +3.2 points a year, but its NW t
is 0.33, far from the 2.0 required.

**The main readings:**
- **Picking Lighter's operator pools by their past record did not work, and the rule as frozen mostly picked dormant
  pools.** Pools whose share price moves on few days have a tiny sd, so a little drift gives them a high mean over
  sd. In 2026-01..04 every pick earned exactly 0.
- **The average operator pool loses money.** The equal-weight net of every eligible pool, after its fee, was −5.2%
  a year over the same months.
- **LLP beats them.** Lighter's own LLP earned +10.7% a year over the same months, and its worst month was −0.02%.
- **XLP**, Lighter's "Experimental Liquidity Provider" (its deposit rules were not found), lost about half its
  value: −51% a year, with a worst month of −48%.
- For the owner's question (do HLP's and LLP's competitors do better?): on Lighter, no. A deposit in LLP, with its
  LIT stake (R447), remains the better book.

- **Frozen:** PREREG sha256 `45627260…`, commit `641c76d`, before any operator pool's return was read.
- **Run:** `python scripts/run_litpoolsel.py --window gate0` on 2026-11-11. It checked the 4 pinned code files and
  the 2 gate-0 input files. Output in `results/gate0/`: `months.csv` and `report.json`.
- **Inputs:** they stay out of git (`experiments/*/data/` is lane data). Their sha256 are in the PREREG.

## Gate 0: formations 2025-11-30..2026-09-30, 11 held months
| Cost | Net, %/yr | Excess over 4%, pts | NW t (lag 3) |
|---|---|---|---|
| **1x** | **+7.21** | **+3.21** | **0.33** |
| 2x | +6.71 | +2.71 | 0.28 |
| 3x | +6.21 | +2.21 | 0.23 |

- **Month by month:** worst month −4.9% (formation 2026-09-30), which is also the maximum drawdown. The monthly sd
  of the excess is 3.8%.
- **Picks:** 4.5 slots filled on average (the first formation had no candidate), with 2.1 new picks a month.
- **The fee** took 4.5 points a year.
- **One month carries the result.** The 2026-05-31 formation earned +10.5% net, almost all from K Pool (+66% in
  June 2026; diagnostic). Without that month the book is below the hurdle.

**Monthly book, 1x net (%):** +0.34, +0.48, −0.06, −0.02, −0.04, −0.06, +10.51, −3.07, +1.25, +2.21, −4.93.

## Why the rule picked dormant pools (diagnostics, read after the freeze)
- At the 2026-01-31 and 03-31 formations, all 5 picks had a nonzero daily return on only 2-10% of the 90 days, and
  each held return was exactly 0.
- At 2026-05-31, 4 of 5 picks were dormant (0-3% of days active); the fifth, K Pool (99% active), made +66%.
- At 2026-09-30, the active picks earned +4.8%, +2.9% and −30.4% (FLEXIBLE POOL); the two dormant ones earned 0.
- A rule that requires activity would be a new lane. Its gate 0 would be this seen window, so it could only stop.
  With 11 monthly points it could not decide either way, and a forward read would take a year of months.

## Capacity (today's sizes of the last formation's picks)
- $77.7k, $408.7k, $65.5k, $70k, and $0.96k with status 1 (closed or frozen today).
- Most operator pools hold under $10k. A real $10k deposit fits only a handful of them, and each operator's minimum
  share caps deposits further.

## Program
- One trial. Program total 9,784,998 (`registry.program_trials()`).

## Notes on the PREREG
- It says Edge & Hedge's two printed share prices (2025-09-18 and 09-19) "precede every formation's signal window".
  Strictly, they fall inside the 2025-11-30 formation's 90-day window. The pool was created on 2025-09-18, so it was
  only 73 days old then and not eligible. From 2025-12-31 on, the window starts after those dates.
- It counts "11 held months"; the run has 11.

## Limits
- **Survivorship:** pools Lighter deleted would be missing from the list (not checked). That would bias the
  equal-weight mean up, not down.
- **Fee:** today's fee, applied monthly on gains (charged at withdrawal in reality).
- **Share prices** are what a deposit earns before the fee. No deposit or withdrawal cost is documented (10 bp per
  switch assumed).
