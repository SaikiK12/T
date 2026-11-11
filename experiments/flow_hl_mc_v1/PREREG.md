# PREREG: flow_hl_mc_v1 (R458). R448's books at measured Hyperliquid costs

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R458
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_flow_hl_mc.py` is the only writer of `experiments/flow_hl_mc_v1/results/`.
  - It runs weekly in `.github/workflows/claude-xperp-reads.yml`.
- **Date registered (UTC):** 2026-11-11

**Methods:** M126 (book A) and M127 (book B), as traded by R448.
- Parent: R448 (`experiments/flow_hl_v1`, PREREG `e87e3aed…`), whose positions this lane reuses unchanged.
- **Paper only:** it reads files; nothing in the code can place an order.

## Question
Would a real account trading R448's books on Hyperliquid's main dex pay what R448's paper charges? R448 charges each
one-way trade the lab's tier cost by Binance liquidity rank (6, 8, 12 or 20 bp). This lane recomputes the same
positions with the fee Hyperliquid charges and the slippage its order books show, and asks whether the net is no
worse.

## Why this lane
- The owner asked on 2026-11-11 that a funded account earn what paper earns.
- R448 is the France-reachable execution check of R200's crypto flow books. Its gate 0 left book A at +4.9 bp/day at
  1x and +0.1 bp/day at 3x (FINDINGS): its result depends on the cost, and the cost is assumed, not measured.
- R453 does the same for R451 on xyz, and R456 for R454 and R455. R448 had no such read.
- `scripts/record_xyz_books.py --dex ""` (`claude-xyz-books.yml`, hourly, data branch `claude/xyz-books-data`, from
  2026-11-11) records each main-dex perp's book in `main/books/`.

## What the author has seen
- R448's PREREG, its gate-0 FINDINGS and `results/gate0/` (seen window 2026-04..09). R448 has no forward ticket; its
  forward starts 2026-11-12.
- **Structure of `main/books/`** on 2026-11-11 (one day file): column names, 1,253 rows, 179 coins, timestamps in
  milliseconds from 02:17 to 07:09 UTC, coin names as R448 maps them (`kPEPE`, `kBONK`...). No cost, spread, depth or
  price value was printed or read.
- **Code tests** (`tests/test_run_flow_hl_mc.py`) on a synthetic R200 journal and price store, run through R448's own
  `forward()`; no market data.

## Data
- **Positions and assumed costs:** recomputed from R200's journal (`experiments/flow72_fwd2/journal/signals.csv` and
  `ticks.csv`) and R448's stored Hyperliquid closes and funding (`experiments/flow_hl_v1/journal/hl/`), exactly as
  R448's `forward()` computes them (its functions are imported, unchanged).
  - **Parity check:** each recomputed 1x daily net must equal R448's ticket for that day and book within 1e-9.
    Otherwise the run stops with an error and decides nothing.
- **Measured costs:** a checkout of `claude/xyz-books-data` at the read date, `main/books/*.csv` (hourly snapshots).
  The commit read is written into the report.

## Rule
Constants are in `scripts/run_flow_hl_mc.py`.
- **Trade time:** row i's trades execute at the close of the bar that opens at t0 + i hours, so at t0 + (i + 1) hours
  (R448's grid and returns).
- **Fee:** Hyperliquid's tier-0 taker fee of 4.5 bp one way, on every main-dex perp.
- **Slippage:** the mean of the buy and sell cost of a $1k market order, in bp from mid, in the coin's snapshot
  nearest to the trade time. Only a snapshot within 90 minutes counts; a side too thin for $1k counts as missing.
- **Measured one-way cost:** fee + slippage (slippage floored at 0). Where no snapshot counts, or for a symbol without
  a Hyperliquid coin, R448's own cost is kept. A coin-hour without an R448 cost stays out, as in R448.
- **Books:** R448's books A and B, their positions, hedge, funding and cost multipliers unchanged. Only the cost matrix
  changes; the hedge's cost is R448's formula on the new matrix.
- **Reported sizes:** $1k (primary), $5k and $10k, each at 1x, 2x and 3x the measured cost.

## Decision (per book, on R448's strict on-time days in calendar order)
1. **At 90 counted days:** the gap is the mean daily 1x net at measured cost minus R448's 1x net, over the first 90
   days.
   - **NO WORSE THAN ASSUMED** if the gap is 0 or above.
   - **COSTLIER THAN ASSUMED** otherwise, with the gap in bp/day.
2. **At 365 counted days:**
   - If R448's own final read is not PASS, or its stop rule was hit: **n/a**.
   - If R448 passes: **EXECUTABLE AT MEASURED COSTS** when the measured-cost book meets R448's PASS conditions on the
     same 365 days (1x mean above R448's bootstrap threshold, 2x mean above 0, trimmed mean above 0); otherwise **NOT
     EXECUTABLE AT MEASURED COSTS**.
3. Before 90 counted days the read is a status with no decision.
4. An owner stake on these books needs R448 to pass and this lane to read EXECUTABLE. Then `lab.gate.go_real()` and
   the owner's own decision apply. Nothing here authorizes an order.

## Reported, not deciding
- The share of the book's traded coin-hours priced from a snapshot (the rest fall back to R448's cost).
- On those coin-hours, the mean one-way cost R448 assumed and the mean measured: the direct real-versus-paper gap.
- Measured-cost nets at $1k, $5k and $10k, at 1x, 2x and 3x.

## Trials and reading
- **Zero new trials.** The lane cannot add a pass: a book is executable only if R448 passes on its own costs. It can
  only add a failure. The program total stays 9,785,005.
- Read against `registry.program_trials()`.

## Limits
- **Order size:** the $1k level stands for one coin's trade in one hour on a $10k account. A larger account pays more;
  the $5k and $10k reads show how much.
- **Snapshot timing:** one snapshot an hour, taken minutes after the hour, not at the trade's own second. Spreads move
  inside the hour.
- **Depth:** the API returns 20 levels a side. A $10k order deeper than those is missing and falls back.
- **Fee tier:** tier 0, with no staking, referral or maker discount. A maker order would pay less but might not fill.
- **Hedge leg:** R448's hedge cost averages the basket's costs. This lane changes the inputs, not that formula.

## Stop rules
No new sizes, windows, venues or books after a result. A changed idea is a new lane.

```inputs
d26aea1e75a60c7663ea07b93b19c4219c1e03563ce46daddea8ddb5106a0ddb scripts/run_flow_hl_mc.py
3cf0db7f4d8a0e9c93e03ba28a102623d9c23fc7997de580226c69ba6c78290e tests/test_run_flow_hl_mc.py
0c9b45bd4675d1f7177d09741fb1e65888214a9a30f4461f254310f6b45485f3 scripts/run_flow_hl.py
d9cc1053883c17545e52292d20c18569c751c7418d90c73502c60f54bd147e91 scripts/run_flow_hlstock_mc.py
cecfa25866aa5873128f1e97b71f74fbeefbf00b9c2c261550062b07d4e61335 scripts/run_flow_hlstock.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
4b255a4da93acc25eacd06ed19659118485802577efbe2ccc97cca353d539a1f lab/slices.py
66ac88bdf3034e11401d18e1dac09e7379d59cbb0654332e4d1458200fca0a27 lab/engine.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea experiments/venue_gap_v1/results/tradfi_symbols.json
e87e3aed6b54312fd23914f71ab41a8fa4cf04b07abb7ec9a67ac713e63b180d experiments/flow_hl_v1/PREREG.md
4dec288ba00dd91a0b13ff6bc2dfffdb86c2170eaa77d1aeddfb87cf1aeb32a2 experiments/flow_hl_v1/results/gate0/daily.csv
```
