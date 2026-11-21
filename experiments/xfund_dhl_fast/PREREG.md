# PREREG: xfund_dhl_fast (R521). A fast read of R520 (Deribit + Hyperliquid) on funding net of measured costs

Freeze with `lab.prereg.freeze()` before R520 has a scored day. Never edited afterwards.

- **Registry id:** R521
- **Owner (single writer):** none. The read writes nothing; it reads R520's journal.
- **Date registered (UTC):** 2026-11-21

**Methods:** M560 (a faster decision on R520's journal; R510's design). Carry, candidate C13.
- **Paper only.**

## Why
- **The owner, 2026-11-21:** "we need a breakthrough".
  - The review `docs/reviews/breakthrough_20261121.md`: the binding constraint is time to evidence on the one
    replicating edge.
- **R520's own looks are slow.** At 90 and 180 days, the expected NW t on the whole net is 1.87 and 2.64 at R519's
  level.
- **The price legs are noise.** They hedge the same coin.
  - On R519's history (its reported R275 book), the funding part net of costs had a daily Sharpe ratio of 0.43, and
    the whole net 0.15.
  - A read on funding net of measured costs, with the whole net as a guard, can decide in weeks.

## Rule (`scripts/read_xfund_dhl_fast.py`)
- **Inputs, per scored day of R520's book A** (R512's `series` with Deribit's 3.5 bp fee, through R520's read):
  - fund_book = funding − measured cost / 40;
  - net_book is R520's decided series.
- **Looks: 30 and 45 scored days** (about 2026-12-22 and 2027-01-06).
  - **PASS** if NW t (lag 5) of fund_book ≥ 2.5 and the cumulative net_book > 0.
  - **FAIL** if the mean fund_book ≤ 0, or if R520's kill switch fired (cumulative net_book < −3% within the first 45
    days).
  - Otherwise **NOT YET** at look 1, and **NO EARLY PASS** at look 2. R520's 90- and 180-day looks then decide.
- **A verdict is final.** Each look is read once on its day.

## Calibration (computed before the freeze on R519's history; descriptive, the same seen data)
- **Windows:** sliding windows every 5 days over R519's 1,272 book days, with R275's book at 7 bp a leg.

  | Window | Real series: pass rate (power) | Demeaned series: pass rate (size) |
  |---|---|---|
  | 30 days | 0.67 | 0.03 |
  | 45 days | 0.73 | 0.04 |

- So the rule has power about 0.7 if the gap holds at R519's level, and a false-pass rate near its nominal level
  when the mean is zero, despite funding's autocorrelation.
- **The two looks share days,** so the overall false-pass rate is below the sum, about 5%.

## What a PASS earns
- **Earns:** a small stake through `lab.gate.go_real()`, placed by the owner, on Deribit + Hyperliquid:
  - at most $2,000 of two-leg capital;
  - cross margin, at most 2x, with alerts above each venue's liquidation line.
  - The owner said on 2026-11-21 that venue access is theirs to arrange.
- **Does not:** R520's looks still decide whether the lane passes. This read decides nothing about scaling.

## What the author has seen
- R519's full history (see R519 and R520).
- R520's journal: 30 replay days, never scored. No scored day exists at this freeze.

## Trials
- **This round:** 1.
- **Program trials:** 9,785,764 before, 9,785,765 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/read_xfund_dhl_fast.py` | bc1926e6a1bdc4b613011322382a10c2840c484eceaf533aabad9cdaa6494096 |
| `tests/test_read_xfund_dhl_fast.py` | 4a08e6c95e3abfea30509b10ba5b8838900854e49a118a00378534aa482a777e |
| `scripts/read_xfund_dhl_fwd.py` | 71b0dd622e1a5ddfc0c5c410358ff8f7786c1900b75dad1b11845e771c429735 |
| `scripts/read_xfund_eea3_fwd.py` | e20f356fc55980e4ff2a0c7fb02f846b9ce6f7151b2951478dad169e4b38ae3d |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
