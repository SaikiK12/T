# FINDINGS: settlehop_exit_v1 (R356). Close the hop right after the settlement: +50.5 bp a hop instead of +30.9, mostly from the funding hour it skips

**Verdict: PASS by the frozen rule, recorded PARTIAL (gate 0), 5 trials.**

R354's 87 primary hops (Binance + Lighter, θ 0.5%, 26 coins, 2025-01-17..2026-09-30) were closed at the 1-minute close
of T + k instead of T + 1 h. Entry, direction, funding at T and costs are R354's. The minute rebuild reproduced R354's
T + 60 and T exits in 87 of 87 hops.

- **Primary, k = 5:**
  - Net +50.5 / +30.1 / +9.6 bp a hop at 1x / 2x / 3x, against R354's +30.9 / +10.4 / −10.0.
  - Daily book: +1.41 / +0.84 / +0.27 bp a day (NW t 4.08 / 3.33 / 1.44).
  - Paired gain over T + 60: +19.6 bp a hop, CR1 t 3.99, higher in 70% of hops.
- **Checks** (PASS needs all five):

  | Check | Bar | Result | Pass |
  |---|---|---|---|
  | 1. NW t of the 1x daily net | ≥ 2.0 | 4.08 | yes |
  | 2. 2x daily mean | > 0 | +0.84 bp | yes |
  | 3. 1x daily mean in each half | > 0 | +0.75 / +2.08 bp | yes |
  | 4. 1x daily mean without the best coin (RIVERUSDT) | > 0 | +1.17 bp | yes |
  | 5. CR1 t of the paired gain over T + 60 | ≥ 2.0 | 3.99 | yes |

- **Family:** all 5 exits pass R354's four checks, and all 5 gains reach the Bonferroni t of 2.33.
- **But the gain is mostly the funding hour, which was known before the run:**
  - Of the +19.6 bp, +15.2 is funding. The early exit no longer pays Lighter's settlement at T + 1 h, net of the floor
    hops' second Binance lumps it no longer receives. That number was computed from R354's columns and written into
    the PREREG.
  - Only +4.4 bp is price (CR1 t 1.22). The question the lane was built for, whether a few minutes after T keep part
    of the pre-settlement price, has a no: **the giveback comes in the first minute.**

## The exits
bp a hop are of the hop's notional on each leg. bp a day are of the book's capital (5 slots). Funding is what the hop
keeps: the lump at T for every early exit, both hours for T + 60.

| Exit | Price | Funding | Gross | Net 1x / 2x / 3x a hop | Hit 1x | bp a day 1x / 2x / 3x (NW t) | Gain over T + 60 (CR1 t) | of which price |
|---|---|---|---|---|---|---|---|---|
| T + 1 | −12.1 | +84.6 | +72.5 | +52.0 / +31.6 / +11.1 | 93% | +1.46 (4.44) / +0.88 (3.81) / +0.31 (1.89) | +21.1 (3.80) | +5.9 |
| T + 2 | −12.1 | +84.6 | +72.5 | +52.1 / +31.6 / +11.2 | 89% | +1.46 (4.41) / +0.88 (3.77) / +0.31 (1.87) | +21.2 (4.06) | +6.0 |
| **T + 5** | **−13.7** | **+84.6** | **+71.0** | **+50.5 / +30.1 / +9.6** | **87%** | **+1.41 (4.08) / +0.84 (3.33) / +0.27 (1.44)** | **+19.6 (3.99)** | **+4.4** |
| T + 15 | −20.0 | +84.6 | +64.6 | +44.1 / +23.7 / +3.2 | 84% | +1.24 (3.75) / +0.66 (2.77) / +0.09 (0.50) | +13.3 (2.79) | −1.9 |
| T + 30 | −12.2 | +84.6 | +72.4 | +51.9 / +31.5 / +11.0 | 86% | +1.45 (4.43) / +0.88 (3.71) / +0.31 (1.72) | +21.1 (5.13) | +5.9 |
| T + 60 (R354) | −18.1 | +69.4 | +51.3 | +30.9 / +10.4 / −10.0 | 68% | +0.86 (3.24) / +0.29 (1.37) / −0.28 (−1.31) | | |

- **Robustness of every early exit:**
  - Halves: +0.72 to +0.82 bp a day in the first, +1.71 to +2.20 in the second.
  - Without RIVERUSDT: +1.02 to +1.20 bp a day.
  - GATES' trimmed mean (without the 10 best and 10 worst hops): +45.9 to +51.6 bp a hop.
  - Leave-two-coins-out: +39.0 to +48.3 bp a hop.
  - Per-hop CR1 t: 6.6 to 8.6.
- **Untraded exit minutes** (the leg's last earlier trade is used): Binance none; Lighter 1, 2, 6, 11 and 7 hops at
  T + 1, 2, 5, 15 and 30.

## The minute path
The mean hedged price of S against H, in the hop's favour, in bp from the entry close (`results/path.csv`):

| Minute | T − 60 (entry) | T − 30 | T − 15 | T − 5 | T − 1 | T (last trade before) | T + 1 | T + 2 | T + 5 | T + 15 | T + 30 | T + 60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hedged, mean | 0 | +27.2 | +28.9 | +32.5 | +30.4 | +25.5 | −12.1 | −12.1 | −13.7 | −20.0 | −12.2 | −18.1 |
| Hedged, median | 0 | +24.6 | +24.9 | +28.1 | +29.0 | +27.6 | −8.3 | −9.4 | −11.8 | −14.1 | −12.1 | −14.9 |
| Binance part | 0 | −17.6 | −31.6 | −39.1 | −57.8 | −62.1 | −194.3 | −203.9 | −214.1 | −242.7 | −259.5 | −337.5 |
| Lighter part | 0 | +44.7 | +60.5 | +71.6 | +88.1 | +87.6 | +182.2 | +191.8 | +200.5 | +222.7 | +247.3 | +319.4 |

- **The first minute after T takes it all back:**
  - Hedged, −37.6 bp a hop on average (median −34.4), negative in 85% of the hops.
  - The coin itself fell about 1% in that minute on both venues (these are 86 long-Binance hops before deeply
    negative settlements), and Binance fell 37 bp more than Lighter.
  - After T + 1 the hedged price wanders between −10 and −23 bp until T + 60.
- **Most of the pre-settlement gain comes in the first 30 minutes after the entry** (+27.2 by T − 30; the peak is
  +33.0 at T − 24), not in the last minutes.
- **What it fits:** traders who bought the Binance perp for its lump sell it the moment the lump is paid. They are
  faster than any minute bar; an exit at T + 1 already sells after them.

## Where the gain comes from (computed after the run)
- **The 8 hops forecast at or below −2.4%** (the floor hops, which received a second Binance lump at T + 1 h when held):
  - net +118.1 / +123.2 / +135.1 bp a hop at T + 1 / T + 5 / T + 60;
  - closing early costs them 15.5 bp of funding each.
- **The other 79 hops:** +45.3 / +43.1 / +20.3 bp a hop at T + 1 / T + 5 / T + 60. Here the early exit saves 18.3 bp
  of funding and doubles the net.
- **Concentration falls:**
  - The 10 best days hold 48% of the T + 5 book's sum, against 72% at T + 60.
  - Without them, T + 5 makes +0.73 bp a day (t 3.77), against +0.24 (t 1.79) at T + 60.
- **Coins:**
  - Without RIVERUSDT, T + 5 nets +46.7 bp a hop (T + 60: +26.8) over 78 hops.
  - Without RIVER, NMR and ZK, it nets +42.5 (T + 60: +21.6) over 73 hops.
- **Years:** the T + 5 gain is +25.1 bp a hop in 2025 (27 hops) and +17.2 in 2026 (60).

## Costs (1x, 2x, 3x)
- **1x:** R354's, per hop. Binance API 8.5 bp a side; Lighter by trailing-volume band, 1.73 bp a side on average. A
  round trip averaged 20.45 bp.
- **2x:** T + 5 nets +30.1 bp a hop, +0.84 bp a day (t 3.33).
- **3x:** T + 5 nets +9.6 bp a hop, +0.27 bp a day (t 1.44). Every early exit stays positive at 3x; R354's T + 60 hop
  does not (−10.0).
- **The gain itself is cost-free:** the same four sides are paid at every exit.

## What this does and does not show
**It shows,** at gate 0 on R354's hops (2025-26, Binance + Lighter):
- Closing the hop within minutes of the settlement instead of an hour later adds about 20 bp a hop, mostly by not
  paying Lighter's next hourly settlement.
- The capture crowd's exit is immediate: by the first minute's close after T, the whole pre-settlement price gain is
  gone. No exit after T keeps it.
- The early-exit book is steadier than R354's: positive at 3x, half as dependent on its 10 best days, and earned by
  the ordinary hops rather than the floor hops.

**It does not show:**
- **That it holds out of sample.** This is gate 0, on R354's hops. The funding part was known before the run. Against
  9,479,093 program trials, a t of 4 is no proof.
- **Fills in the first minutes after a settlement.** Exits are priced at last trades, with R354's flat costs. The books
  right after a settlement, when the crowd is selling, were not measured.
- **Seconds.** Whether anything can be kept by exiting within seconds of T needs tick data; it was not read.
- **MEXC.** These are Binance hops. MEXC's displayed rate and its own settlement behaviour are R355's to test.
- **Margin:** not modelled, as R354.

## What changes
- **M267's exit-time form becomes PARTIAL (gate 0).** The hop should close right after the settlement, not an hour
  later.
- **What the pass earns (the PREREG's terms):** a forward paper lane with the quick exit, under a new id, frozen
  before its first day, on MEXC + Lighter as R355. Its PREREG must say how its decision relates to R355's.
  - R355 is frozen and keeps running unchanged, so the two lanes will see the same candidates and differ in the exit.
  - No money moves. That needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **What the forward lane must record, from this run:** each leg's book at the exit minute, because the crowd sells
  in that minute and bar closes say nothing about the fill.

## Lane details
- **Registry row:** R356, 5 trials.
  - PREREG sha256 `157849e9…a199ea`, frozen and pushed in `f84a8fb` before the run.
  - Claimed on #7 (comment 6457871518) before the freeze.
  - All 13 inputs matched, and the 164 minute files matched their provenance before and after the run.
- **Reproduce:** `python scripts/run_settlehop_exit.py` (a few seconds); the log is `run.log`.
  - `results/` holds `summary.json`, `books.csv`, `hops.csv.gz`, `daily.csv.gz` and `path.csv`.
  - Everything under "Where the gain comes from" was computed after the run from those files and R354's `hops.csv.gz`.
    It is reported, not decided on.
- **Read against the program:** trials go from 9,479,088 to 9,479,093 on this branch, or 9,479,110 counting #56's
  R338-R346.
