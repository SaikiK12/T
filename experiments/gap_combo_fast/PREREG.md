# PREREG: gap_combo_fast (R523). A combined fast read of two independent design-gap lanes: R509 and R520

Freeze with `lab.prereg.freeze()` before 20 common scored days exist. One common scored day exists at this freeze;
it was counted, not read. Never edited afterwards.

- **Registry id:** R523
- **Owner (single writer):** none. The read writes nothing.
- **Date registered (UTC):** 2026-11-23

**Methods:** M560 and M553 together (the framework of `docs/reviews/framework_20261123.md`). Carry, candidate C13.
- **Paper only.**

## Why
- **The owner, 2026-11-23:** "Voit si les frameworks sont de meilleurs choses que les stratégies".
- **The design-gap books are nearly uncorrelated in sample.** On 343 common days, R508's and R519's funding-net
  series had a correlation of −0.04. So a combined read reaches significance sooner than either lane.
- **Independent pairs only.**
  - R509 (Kraken + Hyperliquid) and R520 (Deribit + Hyperliquid) share only Hyperliquid's floor.
  - R512 is left out: it overlaps R509 on Kraken.

## Rule (`scripts/read_combined_gap_fast.py`)
- **Inputs:**
  - R509's days come from R510's `series` (fund_book = funding − measured cost / 40, and net_book);
  - R520's days come from R512's `series` with Deribit's 3.5 bp fee.
- **Combined day:** the mean of the two lanes on days both scored.
- **Looks: 20 and 30 common scored days** (about 2026-12-13 and 2026-12-23).
  - **PASS** if NW t (lag 5) of the combined fund_book ≥ 3.0 and the combined cumulative net_book > 0.
  - **FAIL** if the mean combined fund_book ≤ 0, or if either lane's cumulative net_book falls below −3%.
  - Otherwise **NOT YET** at look 1 and **NO EARLY PASS** at look 2. R510, R521 and the lanes' own looks then
    decide.
- **A verdict is final.**

## Calibration (before the freeze; R508's and R519's in-sample histories, 343 common days, sliding windows every 3 days)
| Threshold | Window | Power (real series) | Size (demeaned) |
|---|---|---|---|
| 3.0 | 20 days | 0.78 | 0.046 |
| 3.0 | 30 days | 0.92 | 0.038 |
| 2.5 (not used) | 20 / 30 days | 0.92 / 1.00 | 0.06 / 0.08 |

- At threshold 2.5, either book alone had power 0.81 / 0.79 at 20 days.
- 3.0 keeps the size under 5%.

## What a PASS earns
- A small stake on both pairs through `lab.gate.go_real()`, placed by the owner:
  - at most $2,000 in total, split by risk;
  - leverage at most 2.5 under `lab/margin.py` with daily rebalancing (`docs/reviews/stake_dhl_20261123.md`).
- It decides nothing about either lane's own verdict.

## What the author has seen
- R508's and R519's in-sample histories.
- The count of common scored days (1). No forward value was read.

## Trials
- **This round:** 1.
- **Program trials:** 9,785,770 before, 9,785,771 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/read_combined_gap_fast.py` | 3adda4d9460946ec0e4cc05bfdd27f3f4b1576ac8e791524a0ffcd741a070c0d |
| `tests/test_read_combined_gap_fast.py` | 02a533cf4a08dabd449d50dff14f74dccbc791d1f84d54a032ca94246d873ef8 |
| `scripts/read_xfund_eea_fast.py` | 4a8236d533262f1c0a0a520a666b28d37a9f873b3a76010704ed7ccaf1bfdfc1 |
| `scripts/read_xfund_dhl_fwd.py` | 71b0dd622e1a5ddfc0c5c410358ff8f7786c1900b75dad1b11845e771c429735 |
| `scripts/read_xfund_eea3_fwd.py` | e20f356fc55980e4ff2a0c7fb02f846b9ce6f7151b2951478dad169e4b38ae3d |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
