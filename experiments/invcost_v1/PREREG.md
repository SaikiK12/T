# PREREG: invcost_v1 (R456). R454's and R455's inventory books at measured costs

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R456
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_invcost.py` is the only writer of `experiments/invcost_v1/results/`.
  - It runs weekly in `.github/workflows/claude-xperp-reads.yml`, after R454's and R455's reads.
- **Date registered (UTC):** 2026-11-11

**Methods:** M510 and M511 (a cost read of their lanes; no new signal).
- **Paper only:** it reads files; nothing in the code can place an order or fetch data.

## Question
Do R454's books (HLP inventory, frozen `9df27190…`) and R455's books (LLP inventory, frozen `ea4f9f26…`) keep their
result when each trade pays what the venue's book actually charged, instead of the flat 9 bp both lanes assume? The
owner asked on 2026-11-11 that real trading match the paper; this lane is that check for the two inventory lanes, as
R453 is for R451.

## What the author has seen
- The recorders' output exists on `claude/xyz-books-data`: `main/` (Hyperliquid main-dex books, from 2026-11-11) and
  `lighter/` (Lighter books, from 2026-11-11). No cost value from either was printed or read.
- A smoke run of `scripts/record_lighter_costs.py` on 4 live Lighter markets into a scratch folder, counts only:
  4 books written, 0 failed, 0 with a $10k cell left blank.
- Neither parent has a ticket yet: both start with snapshots from 2026-11-12. No return of either was seen.
- `scripts/run_invcost.py` was run only on synthetic parents (tests/test_run_invcost.py).

## Data
- **Parents:** R454's and R455's own frozen code, snapshots and stored prices (`experiments/hlpinv_v1/journal/hl/`,
  `experiments/llpinv_v1/journal/px/`) and their tickets. Nothing is fetched.
- **Hyperliquid books:** `main/books/` on `claude/xyz-books-data`, written hourly by `scripts/record_xyz_books.py
  --dex ""`: the cost in bp from the mid of a market order of $1k, $5k, $10k and $25k walked through the 20 levels the
  API returns, by side.
- **Lighter books:** `lighter/books/`, written hourly by `scripts/record_lighter_costs.py`: the cost of a $1k and $10k
  market order walked through the first 100 orders shown, by side.

## Rule
Constants are in `scripts/run_invcost.py`.
- **Recompute** each parent's books with its own functions (`build`, its slices, hedge and returns), over the same
  rows its forward read would use, and charge each one-way trade, main and hedge legs, a cost per coin-hour:
  - **fee + slippage**, where the slippage is the mean of the buy and sell cost of a $1k market order in the snapshot
    of that coin nearest the trade, if that snapshot is within 90 minutes of it;
  - **fee:** 4.5 bp for R454 (Hyperliquid's tier-0 perp taker fee) and 0 for R455 (Lighter's Standard account, which
    pays no maker or taker fee);
  - **otherwise 9 bp**, the parent's own cost (no snapshot near the trade, or a book too thin for $1k).
  - A trade on row i executes at the close of the bar that opens at row i, so its time is the end of that bar.
- **Parity:** the recomputed 9 bp nets must equal every ticket the parent wrote (to 1e-9). A mismatch stops the read
  with an error and nothing is written; the cause is found, never loosened.
- Reported per book and day: the 9 bp net, and the measured net at $1k and $10k, each at cost multiples 1x, 2x and
  3x; the share of the book's traded coin-hours priced from a snapshot.

## Decision (per parent and book, on the parent's counted days in calendar order)
1. **At 90 counted days:** NO WORSE THAN ASSUMED if the mean of (measured $1k 1x net − 9 bp net) over the first 90
   is 0 or more; otherwise COSTLIER THAN ASSUMED. This reports the cost gap; it decides nothing about the signal.
2. **At 365 counted days:**
   - If the parent did not PASS, or hit its stop rule: n/a.
   - Otherwise EXECUTABLE AT MEASURED COSTS when, over the first 365 counted days:
     - the measured $1k 1x mean beats the parent's own placebo threshold (its seed, its 1,000 placebo books at 9 bp);
     - the measured $1k 1x mean is above 0;
     - the measured $1k 2x mean is above 0;
     - the trimmed mean (top and bottom 10 days removed) of the measured $1k 1x nets is above 0.

     Otherwise NOT EXECUTABLE AT MEASURED COSTS.
3. Only a book that is EXECUTABLE AT MEASURED COSTS can go to `lab.gate.go_real()` and the owner's own decision.
   Nothing here authorizes an order.

## Trials and reading
- **Trials:** zero trials. It adds no chance to pass: it can only withhold a parent's PASS. The program total stays
  9,785,003.
- Read against `registry.program_trials()`.

## Limits
- **Size:** $1k per trade is the primary level; a larger account pays more, reported at $10k. A slice of the books
  is far smaller than $1k for a $10k account, so $1k is conservative for that account size.
- **Snapshot timing:** one book snapshot an hour, taken minutes to an hour from the trade; the book between snapshots
  is not seen. GitHub can delay or skip the recorder; trades without a snapshot within 90 minutes keep 9 bp.
- **Thin books:** a market whose shown book cannot fill $1k keeps 9 bp, which can understate its cost.
- **Depth shown:** Hyperliquid's API returns 20 levels a side; Lighter's recorder reads 100 orders a side.
- **Fees:** tier-0 Hyperliquid fee and Lighter's Standard (zero-fee) account as of 2026-11-11; a later fee change is
  not modelled. Lighter's Standard account trades with added latency, which an hourly rule does not need to beat.
- **Threshold:** the placebo threshold is the parent's own, at 9 bp; it is not recomputed at measured costs.

## Stop rules
No new sizes, fees, gaps or thresholds after a result. A changed idea is a new lane.

```inputs
7eec3fbcb73d4c5a9873496d5bb0dec872c1ce1b4bb915e34d24a1271b3fbf96 scripts/run_invcost.py
307bca6931664f20072cc0464aa9a4384be5771da1da67844e4380b6e3b4f5ce tests/test_run_invcost.py
8d6ae65f33609173cb09d91d2e11fbe354b243212d9ef3557461d167a9fef653 scripts/run_llpinv.py
b842eec2ae944306f78184a3db329ff1e3fafbc24afcdccce44f0c0cf0419d2a scripts/run_hlpinv.py
d9cc1053883c17545e52292d20c18569c751c7418d90c73502c60f54bd147e91 scripts/run_flow_hlstock_mc.py
cecfa25866aa5873128f1e97b71f74fbeefbf00b9c2c261550062b07d4e61335 scripts/run_flow_hlstock.py
0c9b45bd4675d1f7177d09741fb1e65888214a9a30f4461f254310f6b45485f3 scripts/run_flow_hl.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
f691695930719a89ae4ededcd5b952f3aa6aabefbe8ea939970acd009e16b297 scripts/record_lighter_costs.py
73a9a5d4dded491e8d47565b5e6efa92bbbab843ee9545d317ba22de127e9b36 scripts/record_llp_positions.py
64f70363b8c41e5a1b7afca68405eb36828041667b1aa40e6c786c9c722b56ed scripts/record_hlp_positions.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
4b255a4da93acc25eacd06ed19659118485802577efbe2ccc97cca353d539a1f lab/slices.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 lab/carrylane.py
```
