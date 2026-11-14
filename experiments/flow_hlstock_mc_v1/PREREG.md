# PREREG: flow_hlstock_mc_v1 (R453). R451's books at measured xyz costs

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R453
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_flow_hlstock_mc.py` is the only writer of `experiments/flow_hlstock_mc_v1/results/`.
  - It runs weekly in `.github/workflows/claude-xperp-reads.yml`.
- **Date registered (UTC):** 2026-11-11

**Methods:** M126 (book A) and M127 (book B), as traded by R451.
- Parent: R451 (`experiments/flow_hlstock_v1`), whose positions this lane reuses unchanged.
- **Paper only:** it reads files; nothing in the code can place an order.

## Question
Would a real account trading R451's books on xyz pay what R451's paper charges? R451 charges each one-way trade the
lab's tier cost by Binance rank (6, 8, 12 or 20 bp), never below 9 bp. This lane recomputes the same positions with
the fee xyz actually charges and the slippage its order books actually show, and asks whether the net is no worse.

## Why this lane
- The owner asked on 2026-11-11 that a funded account earn what paper earns.
- R451 is the France-reachable execution check of R200, the lab's best forward candidate. Its costs are assumed:
  - **Fee:** on 2026-11-11, 117 of xyz's 122 markets ran in HIP-3 growth mode, with a deployer fee scale of 1.0 on
    all 122. Hyperliquid's fee formula (hyperliquid.gitbook.io, trading/fees) gives a tier-0 taker fee of
    4.5 bp × 2 × 0.1 = 0.9 bp one way in growth mode, and 9 bp without it.
  - **Depth:** never measured. R451's limits say a few thousand dollars on a small xyz market could pay more.
- `scripts/record_xyz_books.py` (`claude-xyz-books.yml`, hourly at :07, data branch `claude/xyz-books-data`, from
  2026-11-11) records each xyz market's book and fee settings.

## What the author has seen
- R451's PREREG and gate-0 FINDINGS (seen window 2026-10-01..11-10).
- The fee formula and growth-mode rule above. Counts from the recorder's first snapshot (2026-11-11 01:24 UTC, run
  in the session): 122 markets, 122 books, 0 failures. Its markets file: growth mode on 117 markets, blank on 5
  (among them `xyz:GOLD`), fee scale 1.0 on all.
- A smoke run of this script on R451's gate-0 window, with R451's frozen gate-0 price files as the store: 41
  complete days, 24 symbols, 21 mapped. Only the window's last hour (21 coin-hours, none traded) lay within 90
  minutes of the one snapshot; their values were not printed. Every other cost equalled R451's (checked). The smoke's
  daily nets were compared with R451's gate-0 file only by correlation (0.64 for A, 0.54 for B: the smoke enters at
  R200's recorded run times, gate 0 one bar late).
- **Not seen:** any slippage value in any snapshot, any spread or depth, and any R451 forward ticket (R451's forward
  starts 2026-11-12).

## Data
- **Positions and assumed costs:** recomputed from R200's journal (`experiments/flow72_fwd2/journal/signals.csv` and
  `ticks.csv`) and R451's stored xyz prices (`experiments/flow_hlstock_v1/journal/hl/`), exactly as R451's
  `forward()` computes them (its functions are imported, unchanged).
  - **Parity check:** each recomputed 1x daily net must equal R451's ticket for that day and book within 1e-9.
    Otherwise the run stops with an error and decides nothing.
- **Measured costs:** a checkout of `claude/xyz-books-data` at the read date: `books/*.csv` (hourly snapshots) and
  `markets/*.csv` (fee settings by day). The commit read is written into the report.

## Rule
Constants are in `scripts/run_flow_hlstock_mc.py`.
- **Trade time:** row i's trades execute at the close of the bar that opens at t0 + i hours, so at t0 + (i + 1) hours
  (R451's grid and returns).
- **Fee** of a coin on that UTC day: Hyperliquid's tier-0 taker fee of 4.5 bp, times 2 × the deployer fee scale (or
  1 + the scale when it is below 1), times 0.1 when growth mode is "enabled". It reads the markets file of the latest
  day at or before the trade's day. With no markets file yet, 9 bp.
- **Slippage:** the mean of the buy and sell cost of a $1k market order, in bp from mid, in the coin's snapshot
  nearest to the trade time. Only a snapshot within 90 minutes counts; a side too thin for $1k counts as missing.
- **Measured one-way cost:** fee + slippage (slippage floored at 0). Where no snapshot counts, or for a symbol
  without an xyz coin, R451's own cost is kept. A coin-hour without an R451 cost stays out, as in R451.
- **Books:** R451's books A and B, their positions, hedge, funding and cost multipliers unchanged. Only the cost
  matrix changes.
- **Reported sizes:** $1k (primary), $5k and $10k, each at 1x, 2x and 3x the measured cost.

## Decision (per book, on R451's strict on-time days in calendar order)
1. **At 90 counted days:** the gap is the mean daily 1x net at measured cost minus R451's 1x net, over the first 90
   days.
   - **NO WORSE THAN ASSUMED** if the gap is 0 or above.
   - **COSTLIER THAN ASSUMED** otherwise, with the gap in bp/day.
2. **At 365 counted days:**
   - If R451's own final read is not PASS, or its stop rule was hit: **n/a**.
   - If R451 passes: **EXECUTABLE AT MEASURED COSTS** when the measured-cost book meets R451's PASS conditions on the
     same 365 days (1x mean above R451's bootstrap threshold, 2x mean above 0, trimmed mean above 0); otherwise **NOT
     EXECUTABLE AT MEASURED COSTS**.
3. Before 90 counted days the read is a status with no decision.
4. An owner stake on these books needs R200 to pass, R451 to pass and this lane to read EXECUTABLE. Then
   `lab.gate.go_real()` and the owner's own decision apply. Nothing here authorizes an order.

## Reported, not deciding
- The share of the book's traded coin-hours priced from a snapshot (the rest fall back to R451's cost).
- Measured-cost nets at $1k, $5k and $10k, at 1x, 2x and 3x.

## Trials and reading
- **Zero new trials.** The lane cannot add a pass: a book is executable only if R451 passes on its own costs. It can
  only add a failure. The program total stays 9,784,999.
- Read against `registry.program_trials()`.

## Limits
- **Order size:** the $1k level stands for one coin's trade in one hour on a $10k account. A larger account pays
  more; the $5k and $10k reads show how much.
- **Snapshot timing:** one snapshot an hour, taken minutes after the hour, not at the trade's own second. Spreads
  move inside the hour.
- **Depth:** the API returns 20 levels a side. A $10k order deeper than those is missing and falls back.
- **Fee tier:** tier 0, with no staking, referral or maker discount. A maker order would pay less but might not fill.
- **Growth mode** can be switched off by the deployer (30-day cooldown per asset). The markets file dates every change.
- **Hedge leg:** R451's hedge cost averages the basket's costs, as in R451. This lane changes the inputs, not that
  formula.

## Stop rules
No new sizes, windows, venues or books after a result. A changed idea is a new lane.

```inputs
d9cc1053883c17545e52292d20c18569c751c7418d90c73502c60f54bd147e91 scripts/run_flow_hlstock_mc.py
518eeaa95469cf0a4d2d06d6d63fb50815aa0a2de59739d38d05fbfc39fef04f tests/test_run_flow_hlstock_mc.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
cecfa25866aa5873128f1e97b71f74fbeefbf00b9c2c261550062b07d4e61335 scripts/run_flow_hlstock.py
0c9b45bd4675d1f7177d09741fb1e65888214a9a30f4461f254310f6b45485f3 scripts/run_flow_hl.py
4b255a4da93acc25eacd06ed19659118485802577efbe2ccc97cca353d539a1f lab/slices.py
66ac88bdf3034e11401d18e1dac09e7379d59cbb0654332e4d1458200fca0a27 lab/engine.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea experiments/venue_gap_v1/results/tradfi_symbols.json
89eceed0a3f8a16b6a07f25862a0938c087d00dbdef0552da56532f17b7c8635 experiments/flow_hlstock_v1/PREREG.md
fcc56b1c906ffc4c4e41ec40b0831717f63c2189aea3cd53d224880d38892805 experiments/flow_hlstock_v1/results/gate0/daily.csv
```
