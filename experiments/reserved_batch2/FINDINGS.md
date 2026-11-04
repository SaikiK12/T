# FINDINGS: reserved_batch2 (R391)

**Verdict: PASS, but small.** R275's carry book clears its frozen gate-1 rule on long-tail data no lane had read: the
KuCoin, dYdX and Lighter reserved folders, paired with MEXC. On the book's capital it earns +2.5% a year, below a
cash rate. That is because only 5.3 of its 20 slots fill, and the top 10 days make up 95% of the sum.

## Read
- **Run once** on 2026-11-03 at 22:22:56 UTC, with `scripts/qx_run_verified.py experiments/reserved_batch2`.
  - All 26 frozen inputs and the four data folders matched their provenance records before and after the run.
  - Run receipt: `results/run_receipts/20261103T222256.385627Z-070c4208.json`.
- **Decision** by `scripts/decide_reserved_batch2.py`, in `results/decision.json`.
- **Order:**
  - `RESERVED.md` and `PREREG.md` were frozen before the read: PREREG sha256 `74cfb3e0…`.
  - Both were committed and pushed in `d486b0f`.
  - The RUNNING registry row was written before the run.
- **Rehearsal before the freeze:** the same spec on open data the lab had already read, reported in the PREREG. It is
  not evidence.
- **Reads spent:** read 1 of 4 of the KuCoin, dYdX and Lighter long tail.
  - No 2020, Gate or MEXC-only row was read.
  - `docs/GATES.md` is a frozen input of R367, so its batch table is not edited. This round's registry row and this file
    record the read.

## Result (one book: kucoin+dydx+lighter+mexc, L14d, th5%, K20)
The window runs from 2025-05-12, the start of MEXC's history, to 2026-10-19: 526 days. 18 of the 28 contracts were ever
eligible.

| | 1x | 2x | 3x |
|---|---|---|---|
| Net, %/yr on book capital | **+2.48** | +1.93 | +1.38 |
| Mean daily net, bp | +0.68 | +0.53 | +0.38 |

| Check (frozen) | Value | Bar | Pass |
|---|---|---|---|
| Newey-West t at 1x (lag 10) | 3.90, one-sided p 4.8e-5 | p ≤ 0.05 | yes |
| 2x mean daily net | +0.53 bp | > 0 | yes |
| 10% trimmed mean at 1x | +0.51 bp | > 0 | yes |
| Without the two best coins (CTC, WOTAMALAILE) | +0.34 bp | > 0 | yes |

**Reported, not decided on:**
- **Halves:** +0.41 / +0.95 bp a day.
- **By year:** 2025 +1.4%/yr; 2026 +3.3%/yr.
- **Max drawdown:** −0.43%.
- **Funding share:** 0.83.
- **Engine gates:** all seven pass (reality-check p 0.0005 over 1 book).
- **Slots held:** 5.3 of 20 on average, with 4.8 coins a day at or above the 5% threshold.
- **Trades:** 113.
  - By pair: kucoin+mexc 81, lighter+mexc 26, kucoin+lighter 6. dYdX took no trade: its 9 contracts never made the
    widest eligible pair.
- **Per coin (1x, bp a day):**
  - top: CTC +0.18, WOTAMALAILE +0.16, BP +0.08, NEIROCTO +0.07, CRO +0.06, MNT +0.04;
  - three coins are slightly negative (NES, DATA, STONK).
- **Top-10-day share: 95% of the sum.** The book is a slow carry with rare large funding days. The trimmed and
  leave-two-out checks hold, but the size rests on few days.

## How to read it
- **Gate 1 is met on a sample nobody read.** This replicates R275, R277, R288 and batch 1's C14 on contracts with no
  Binance perp, at R275's cost and at 2x and 3x.
- **It is not a discovery against the program's trials.** `registry.program_trials()` is 9,784,330 after this round.
  A Bonferroni bar over all of them would be p ≤ 5e-9, and this p (4.8e-5) does not reach it. This is a
  pre-registered confirmation of one already-replicated family, read once, not the best of many tries.
- **The money is small.** +2.48%/yr on the full book's capital is below a T-bill (about 4%). Per filled slot, it is
  about 9%/yr (2.48 × 20 / 5.3), before any margin or idle-cash yield. The long tail adds capacity to the carry
  family; it is not a separate high-return strategy.
- **Costs are not measured on these books.** The coins are thin. The 3x net (+1.38%/yr at 21 bp per leg per side)
  is the only cushion shown. Measured spreads could be wider than 3x on some of them.
- **What the PASS earns (GATES):** a frozen forward paper lane, with a new id and measured book costs. It earns no
  money. The next step is to measure those book costs on KuCoin and MEXC for the 18 eligible contracts before the lane
  is written. A pass here does not make `go_real()` any closer for any book.

## Files
- **Lane:**
  - `PREREG.md`, `RESERVED.md` (the engine's reserved-read declaration), `spec.toml`, `symbols.csv`;
  - `results/` holds `strategies.csv`, `daily.csv`, `trades.csv`, `report.json`, `SUMMARY.md` and `decision.json`, plus
    the run receipts.
- **Scripts:**
  - `scripts/reserved_venue_table.py` builds the symbol table from contract lists and file names;
  - `scripts/decide_reserved_batch2.py` runs batch 1's checks for this one candidate.
- **Data provenance:** `docs/provenance/lighter_hist.json`, new (2026-11-03). Its hourly coverage is recorded for
  `open/` only.

## Audit note, 2026-11-04 (after the read; the verdict is not changed)
- **H1, verified in `engine/src/spread.rs:147-159` ([review](../../docs/reviews/hidden_edge_audit_20261104.md)).** The
  engine counts a day as fresh only when a bar ends exactly at midnight. A daily KuCoin bar always does. An hourly
  dYdX or Lighter bar does only when the coin traded in the 23:00 hour.
  - The identity guard needs fresh days, so most thin dYdX coin-days fail it.
  - The 7 dYdX-only contracts were never eligible, which is why dYdX took no trade.
- **What this means.** This read measured "R275's frozen engine on these coins", which is what was registered. It
  does not measure what dYdX's long tail would earn under a venue-neutral rule.
- **No re-read.** These rows are now spent for this sample (read 1 of 4). A corrected engine (M468) may read them
  only through a later frozen batch PREREG that counts it as a further read.
