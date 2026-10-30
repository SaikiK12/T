# FINDINGS: settlehop_v1 (R353). The settlement-window hop: the hedge holds, but the last settled rate does not forecast the next lump

**Verdict: NULL by the frozen rule, 12 trials, gate 0.**

The primary book is MEXC + Lighter at θ 0.5%: 120 hops on 29 coins over 521 days (2025-04-28..2026-09-30), about one
hop every four days.
- **The forecast and what came:** the signal promised 75.8 bp a hop. Funding paid +13.5 bp: S's lump +25.2, less
  11.7 for two hours of Lighter.
- **The price part was small:** −5.8 bp (−3.1 before T and −2.7 after). Gross is +7.7 bp.
- **Costs** were 20.1 bp a round trip at 1x. Net is −12.4 / −32.5 / −52.7 bp a hop at 1x / 2x / 3x.
- **Daily book:** −0.57 / −1.50 / −2.43 bp a day (t −1.98 / −3.95 / −4.68).
- **Checks** (PASS needs all four):

  | Check | Bar | Result | Pass |
  |---|---|---|---|
  | 1. NW t of the 1x daily net | ≥ 2.0 | −1.98 | no |
  | 2. 2x daily mean | > 0 | −1.50 bp | no |
  | 3. 1x daily mean in each half | > 0 | +0.13 / −1.27 bp | no |
  | 4. 1x daily mean without the best coin (VVV) | > 0 | −0.70 bp | no |

- **Family:** none of the 12 books reaches a 1x t of 2.0, nor the Bonferroni 2.64. Eleven are negative at 1x. The
  twelfth (MEXC + dYdX at θ 0.5%) holds one hop.

## The books
bp a hop are of the hop's notional on each leg. bp a day are of the book's capital (5 slots).

| Book | Hops | Coins | Mean e | Funding | Price | Gross | Cost 1x | Net 1x / 2x / 3x a hop | 1x bp a day (t) |
|---|---|---|---|---|---|---|---|---|---|
| MEXC + Lighter θ 0.3% | 308 | 42 | 52.5 | +11.3 | −6.4 | +4.9 | 20.3 | −15.4 / −35.7 / −56.0 | −1.82 (−3.96) |
| **MEXC + Lighter θ 0.5%** | **120** | **29** | **75.8** | **+13.5** | **−5.8** | **+7.7** | **20.1** | **−12.4 / −32.5 / −52.7** | **−0.57 (−1.98)** |
| Binance + Lighter θ 0.3% | 299 | 41 | 53.3 | +9.2 | −6.8 | +2.3 | 20.5 | −18.1 / −38.6 / −59.1 | −1.74 (−4.72) |
| Binance + Lighter θ 0.5% | 122 | 31 | 75.8 | +12.6 | −10.9 | +1.7 | 20.0 | −18.3 / −38.2 / −58.2 | −0.72 (−3.36) |
| Gate + Lighter θ 0.3% | 265 | 45 | 60.1 | +16.2 | −12.6 | +3.6 | 18.5 | −14.8 / −33.3 / −51.8 | −1.26 (−2.87) |
| Gate + Lighter θ 0.5% | 132 | 35 | 81.7 | +20.6 | −11.5 | +9.1 | 17.5 | −8.5 / −26.0 / −43.6 | −0.36 (−1.03) |
| MEXC + dYdX θ 0.3% | 5 | 5 | 42.6 | +2.2 | −188.6 | −186.4 | 31.0 | −217.4 / −248.4 / −279.4 | −0.42 (−1.03) |
| MEXC + dYdX θ 0.5% | 1 | 1 | 52.5 | +2.9 | +224.8 | +227.7 | 31.0 | +196.7 / +165.7 / +134.7 | +0.08 (1.01) |
| Binance + dYdX θ 0.3% | 9 | 9 | 51.5 | +9.3 | −147.1 | −137.8 | 31.0 | −168.8 / −199.8 / −230.8 | −0.28 (−1.19) |
| Binance + dYdX θ 0.5% | 4 | 4 | 67.6 | +17.8 | −46.4 | −28.6 | 31.0 | −59.6 / −90.6 / −121.6 | −0.04 (−0.91) |
| Gate + dYdX θ 0.3% | 15 | 14 | 55.5 | +9.4 | −465.0 | −455.6 | 28.0 | −483.6 / −511.6 / −539.6 | −1.36 (−1.04) |
| Gate + dYdX θ 0.5% | 6 | 6 | 80.5 | +1.7 | −1,165.3 | −1,163.6 | 28.0 | −1,191.6 / −1,219.6 / −1,247.6 | −1.34 (−1.04) |

## Where the lump went (Lighter pairs; computed from `hops.csv.gz` after the run)
A hop has two parts, and the post-run split shows which one failed.
1. **The price part is small: the hedge works.**
   - Over the two hedged hours, S against H moved 6-13 bp against the hop.
   - Regressed on the lump S actually paid, the price part gives back 0.26 of it on MEXC (SE 0.09, HC1). That is
     0.13-0.15 on Binance and 0.03-0.05 on Gate.
   - So the PREREG's no-arbitrage world, where S jumps by the payment, is not what happens. R223's single-venue
     loss (−72.3 bp against +47.6 an event) was mostly the coin's own move, which the hedge removes.
2. **The funding part is a third of the forecast: the signal fails.**
   - The signal was S's previous settled rate. The lump at T had the hop's sign 84-85% of the time, but it was only
     0.29-0.36 of the previous one.
   - Two hours of H cost another 7-13 bp.

| Book | Hops | Previous S lump (the signal) | S lump at T | Ratio | H paid | Price slope on the S lump (SE) |
|---|---|---|---|---|---|---|
| MEXC + Lighter θ 0.3% | 308 | 57.5 | 19.1 | 0.33 | −7.9 | −0.21 (0.06) |
| MEXC + Lighter θ 0.5% | 120 | 83.6 | 25.2 | 0.30 | −11.7 | −0.26 (0.09) |
| Binance + Lighter θ 0.3% | 299 | 59.6 | 18.2 | 0.31 | −9.0 | −0.15 (0.04) |
| Binance + Lighter θ 0.5% | 122 | 85.2 | 25.1 | 0.29 | −12.6 | −0.13 (0.06) |
| Gate + Lighter θ 0.3% | 265 | 64.3 | 22.8 | 0.36 | −6.6 | −0.03 (0.09) |
| Gate + Lighter θ 0.5% | 132 | 87.4 | 29.7 | 0.34 | −9.1 | −0.05 (0.09) |

- **By direction (primary):**
  - **103 hops long S and short H,** after a deeply negative S rate: funding +27.2 bp, price −11.4, net −4.1 a hop.
  - **17 hops short S and long H.** In these, H's hourly rate had moved first and S's previous rate had not. S's next
    lump then went the same way as H's, and the hop paid it: funding −69.5 bp, net −63.1. Every Lighter book shows
    the same, with −67 to −112 bp of funding in this direction.
- **By S interval (primary):** 114 of 120 hops are on 4-hour settlements, netting −13.9 bp a hop. The six 8-hour ones
  net +14.8.
- **By year (primary):** 2025 has 53 hops at +3.4 bp a hop; 2026 has 67 at −24.9.
- **The crash day:**
  - 2025-10-11, the morning after the 10/10 liquidations, holds 9 primary hops summing +350 bp.
  - It has the book's five largest hops by size, and all four of its stale exits (Lighter did not trade in the exit
    hour at 04:00).
  - Without that day, the primary nets −16.6 bp a hop.

## dYdX
- **The identity check keeps only 1-15 hops in each dYdX book,** out of 293-528 candidates. dYdX's extreme hourly
  rates sit on idle markets (plumbing), and their daily closes do not track the 4/8 h venue's.
- **The few hops kept carry crash prints:** six Gate + dYdX hops lose 1,165 bp on price.
- These books say nothing either way.

## Costs (1x, 2x, 3x)
- **1x:**
  - MEXC and Binance 8.5 bp a side; Gate and dYdX 7.
  - Lighter by trailing-volume band. The primary's Lighter legs averaged 1.56 bp a side: 31 hops at 0.51, 66 at 1.09,
    22 at 4.17 and 1 at 7.27.
  - A primary round trip (four sides) averaged 20.1 bp.
- **2x / 3x:** the primary loses 1.50 / 2.43 bp a day (t −3.95 / −4.68). Every Lighter book loses at 2x.
- **MEXC web** (3 bp a side, reported only): the primary still loses: −1.43 bp a hop, −0.07 bp a day (t −0.23).
- **Exit at the close at T** (an optimistic bound: no real exit gets the price before the payment): the primary
  nets −2.05 bp a hop. Gate + Lighter at θ 0.5% nets +18.6 bp a hop.

## What this does and does not show
**It shows,** at gate 0 on hourly bars in 2025-26:
- Hedged across venues, an S perp is not repriced by its funding payment over the two hours around it. The price
  part gives back 0-26% of the lump.
- The last settled rate is a poor forecast of the next lump at extremes:
  - only about a third of it recurs;
  - when the hourly venue's rate moves first, the next lump goes against the hop.
- At the lab's API costs (about 20 bp a round trip on four legs), this stale-signal hop loses on every Lighter book.
  It also loses at MEXC's web fee.

**It does not show:**
- **The hop on the live predicted rate.** Every venue publishes the rate it will settle at T, and a trader sees it an
  hour before. This lane's signal did not use it, by design, because no venue's history file holds it.
- Exits seconds after T. Hourly bars charge one more hour of basis noise after T.
- Maker entries, MEXC's own order books, or the reserved coins.

## What changes
- **M267's stale-signal form is TESTED (NULL).** The settlement-window idea itself is not closed. The part that
  failed is the forecast, not the hedge.
- **Next: the same hop on a point-in-time predicted rate.**
  - Binance sets its funding from its premium index. The lab holds that index hourly for 896 perps
    (`data/premiumIndexKlines_1h`), and no lane has read it for funding.
  - The rate an hour before T can be rebuilt from it with only what was published by then.
  - That is a new lane with a new id, frozen before any statistic. It is gate 0 on these prices, since this run read
    the hops of the same settlements.
  - A pass would earn a forward paper lane on the live predicted rates.
- **No forward lane starts from R353.**

## Lane details
- **Registry row:** R353, 12 trials.
  - PREREG sha256 `37727fd2…3a1381`, frozen and pushed in `aa8c029` before the run.
  - Claimed on #7 (comment 6456192143).
  - All 37 inputs and the 2,196-file data manifest matched. The Lighter bands were recomputed from their 22
    snapshots.
- **Reproduce:** `python scripts/run_settlehop.py` (about 3 minutes); the log is `run.log`.
  - `results/`: `summary.json`, `books.csv`, `hops.csv.gz` and `daily.csv.gz`.
  - The lump, slope, direction, interval, year and crash-day numbers above were computed from `hops.csv.gz` after the
    run. They are reported and not decided on.
- **Read against the program:** trials go from 9,479,069 to 9,479,081 on this branch, or 9,479,098 counting #56's
  R338-R346.
