# FINDINGS: settlehop_pred_v1 (R354). The settlement hop on a predicted rate: a gate-0 pass, earned in rare squeezes

**Verdict: PASS by the frozen rule, recorded PARTIAL (gate 0), 6 trials.**

The primary book is Binance + Lighter at θ 0.5%: 87 hops on 26 coins over 622 days (2025-01-17..2026-09-30), about one
hop a week.
- **The trade it found:** 86 of the 87 hops are long the coin on Binance and short it on Lighter, an hour before a
  deeply negative settlement. At the entry the Binance perp sat about 2.8% under its index.
- **The forecast and what came:**
  - The predicted lump was 152.2 bp in the hop's favour. Binance paid 111.8, which is 0.73 of it. The correlation was
    0.80, and the sign was right in 86 of 87 hops.
  - Two hours of Lighter cost 42.4. Funding nets +69.4 bp.
- **The price part:** −18.1 bp (+25.5 before T, −43.5 after). Gross is +51.3.
- **Costs:** 20.45 bp a round trip at 1x. Net is +30.9 / +10.4 / −10.0 bp a hop at 1x / 2x / 3x.
- **Daily book:** +0.86 / +0.29 / −0.28 bp a day (t 3.24 / 1.37 / −1.31).
- **Checks** (PASS needs all four):

  | Check | Bar | Result | Pass |
  |---|---|---|---|
  | 1. NW t of the 1x daily net | ≥ 2.0 | 3.24 | yes |
  | 2. 2x daily mean | > 0 | +0.29 bp | yes |
  | 3. 1x daily mean in each half | > 0 | +0.56 / +1.17 bp | yes |
  | 4. 1x daily mean without the best coin (RIVERUSDT) | > 0 | +0.67 bp | yes |

- **Family:**
  - 5 of the 6 books reach a 1x t of 2.0. The exception is MEXC + Lighter at θ 0.3% (t 0.92).
  - Two reach the Bonferroni 2.39: the primary, and Gate + Lighter at θ 0.5% (t 2.75).

## The books
bp a hop are of the hop's notional on each leg. bp a day are of the book's capital (5 slots). F̂·d is the forecast lump
in the hop's favour.

| Book | Hops | Coins | F̂·d | S paid | H paid | Price (before / after T) | Gross | Cost 1x | Net 1x / 2x / 3x a hop | bp a day 1x / 2x / 3x (t) |
|---|---|---|---|---|---|---|---|---|---|---|
| Binance + Lighter θ 0.3% | 221 | 34 | 99.9 | +79.9 | −32.4 | −13.9 (+17.6 / −31.5) | +33.6 | 20.7 | +12.9 / −7.7 / −28.4 | +0.92 (2.24) / −0.55 (−1.38) / −2.02 (−3.43) |
| **Binance + Lighter θ 0.5%** | **87** | **26** | **152.2** | **+111.8** | **−42.4** | **−18.1 (+25.5 / −43.5)** | **+51.3** | **20.5** | **+30.9 / +10.4 / −10.0** | **+0.86 (3.24) / +0.29 (1.37) / −0.28 (−1.31)** |
| MEXC + Lighter θ 0.3% | 215 | 31 | 99.7 | +74.2 | −33.1 | −16.0 (+14.4 / −30.5) | +25.0 | 20.4 | +4.7 / −15.7 / −36.1 | +0.38 (0.92) / −1.30 (−2.50) / −2.98 (−3.76) |
| MEXC + Lighter θ 0.5% | 85 | 25 | 148.7 | +98.8 | −42.0 | −17.7 (+19.5 / −37.2) | +39.2 | 20.4 | +18.8 / −1.6 / −22.0 | +0.61 (2.36) / −0.05 (−0.22) / −0.72 (−2.55) |
| Gate + Lighter θ 0.3% | 205 | 33 | 99.4 | +84.2 | −26.4 | −21.4 (+23.6 / −45.0) | +36.4 | 19.4 | +17.1 / −2.3 / −21.7 | +1.12 (2.21) / −0.15 (−0.32) / −1.43 (−2.31) |
| Gate + Lighter θ 0.5% | 95 | 26 | 145.9 | +115.5 | −33.6 | −24.8 (+31.3 / −56.1) | +57.0 | 19.0 | +38.0 / +19.0 / 0.0 | +1.16 (2.75) / +0.58 (1.55) / 0.00 (0.00) |

- **Hit rate** (1x net > 0): 52-68%.
- **Trimmed net** (1% each tail) is within 3 bp of the mean in every book.
- **No exit was stale.**

## Where the money comes from (computed after the run)
These numbers come from `hops.csv.gz`, `daily.csv.gz` and the lane's own manifest-listed bars, premium and funding
files.

### 1. The forecast works, up to Binance's floor
- **Sign and miss:** in every book, the rate S settled at T had F̂'s sign in 99-100% of hops. The median miss was
  22-24 bp at θ 0.5% and 10-13 bp at θ 0.3%.
- **Size:** the lump paid was 0.73 of the forecast on Binance, 0.66 on MEXC and 0.79 on Gate. MEXC and Gate use
  Binance's premium as a proxy for their own.
- **The −2% floor** binds the largest forecasts:
  - 7 primary hops were forecast at −2.4% to −7.0% and settled at −2.00%. Per hop, the slope of the settled rate on
    F̂ is only 0.28.
  - After settling at the floor, Binance moved those coins to hourly settlements. The hop then received a second lump
    at T + 1 h, of −0.08% to −1.16%.
  - Those 7 hops net +126.8 bp each, a third of the primary's sum. Without them, the primary nets +22.5 bp a hop over
    80.
- **Hand check:** RIVERUSDT at 2026-02-18 00:00 (4 h interval).
  - Rebuilt from the raw premium file, using only the three bars closed by 23:00, F̂ is −1.404%, the same as the hops
    file.
  - Binance settled at −1.156%.

### 2. Lighter's hourly rate costs less than half of the lump
- Its two settlements in the hold cost 42.4 bp against Binance's 111.8. The forecast for them was 54.8.
- Every hop's signal is driven by F̂, not by Lighter: |F̂| ≥ |2·h_prev| in all 87.

### 3. The price part is the capture crowd
The mean path of S against H in the hop's favour, in bp from the entry close (primary):

| | T − 3 h | T − 2 h | T − 1 h (entry) | T | T + 1 h (exit) | T + 2 h |
|---|---|---|---|---|---|---|
| S against H | −22.1 | −27.3 | 0 | +25.0 | −19.8 | −17.0 |
| Binance premium, signed for the hop | −290 | −312 | −279 | −134 | −212 | −187 |

- **The pattern:** S rose against Lighter for two hours into the settlement, then gave it all back in the hour after.
  That fits traders buying the paying perp for the lump and selling after it. The hop enters an hour early and exits
  an hour late, so it rides both moves.
- **Closed at T,** the primary would net +89.6 bp a hop. That is a bound: no exit gets both the pre-payment price and
  the payment.
- **The pre-T gain is not mainly a dip at the entry close that later reverses**, which would be a fill no one gets:
  - S had already risen 27 bp against H in the hour before the entry, and rose 25 more to T.
  - Hop by hop, the move into the entry and the next hour's move correlate at −0.39, so part of it does reverse.

### 4. Concentration
- **Days:**
  - Without 2025-10-10/11: +0.77 bp a day (t 3.05).
  - Without the 10 best days: +0.25 (t 1.87). Those 10 days hold 72% of the sum.
  - In the other five books, removing their 10 best days leaves −0.41 to +0.19 bp a day.
- **Coins:**
  - RIVERUSDT's 9 hops sum +598 of the book's +2,685 bp.
  - The top three coins (RIVER, NMR, ZK) hold 41%. Without them, the book nets +21.6 bp a hop over 73.
  - The worst coins are DUSK (−190) and PIPPIN (−150).
- **Not only fresh listings:** the median hop came 270 days after the coin's first Binance bar, and 9% came within
  90 days.
- **The moves are large:**
  - Over the two-hour hold, the coin moved a median 3.4% (10.4% at the 90th percentile, 42.6% at most).
  - Its 24-hour close range before the entry had a median of 27%.
- **Years:** 2025 has 27 hops at +32.3 bp a hop; 2026 has 60 at +30.2.
- **Intervals:** 84 of the 87 are 4-hour settlements.

### 5. Not R353 again
- Only 23 of the 87 primary hops were R353 hops, and R353 had taken 11 of those the other way.
- The 64 new hops net +23.5 bp a hop.

## MEXC and Gate (Binance's premium as the proxy)
- **MEXC + Lighter θ 0.5%:**
  - +18.8 bp a hop, t 2.36. It loses at 2x (−0.05 bp a day).
  - At MEXC's web fee (3 bp a side, reported only): +29.8 bp a hop, +0.97 bp a day, t 3.27. At θ 0.3% it is +15.7 bp
    a hop, t 2.67.
- **Gate + Lighter θ 0.5%:** +38.0 bp a hop, t 2.75. +0.58 bp a day at 2x (t 1.55), 0.00 at 3x.

## Costs (1x, 2x, 3x)
- **1x:**
  - Binance and MEXC 8.5 bp a side; Gate 7.
  - Lighter by trailing-volume band. The primary's Lighter legs averaged 1.73 bp a side: 16 hops at 0.51, 50 at 1.09
    and 21 at 4.17.
  - A primary round trip (four sides) averaged 20.45 bp.
- **2x:** the primary makes +0.29 bp a day (t 1.37). Only the two θ 0.5% books on Binance and Gate stay positive.
- **3x:** every book is at or below zero. The primary makes −0.28 bp a day (t −1.31).

## What this does and does not show
**It shows,** at gate 0 on hourly bars in 2025-26:
- Binance's premium index forecasts its next settlement an hour ahead. In extreme cases the sign is right 99% of the
  time and the size is 0.73 of the forecast; the rest is lost to the −2% floor.
- Hedged on Lighter, a two-hour hop collects most of that lump:
  - Lighter's hourly rate takes back about 40% of it.
  - The capture crowd's round trip takes back another 15-25%.
- At API costs, the primary nets +31 bp a hop at 1x and +10 at 2x, and loses at 3x.
- The money is in rare squeezes: about one hop a week, with 10 days carrying 72% of it.

**It does not show:**
- **That it holds out of sample.**
  - This is gate 0, on prices R353 had read.
  - Against 9,479,087 program trials, a t of 3.24 is no proof. The forward lane is the test.
- **Fills:**
  - Both legs are priced at hourly closes, entered at the same close as the premium the signal reads.
  - A real entry comes seconds to minutes after the published premium, in a fast market. How much that slips is
    unknown.
- **Margin:**
  - The coins moved up to 42.6% within a hold, and each leg is margined on its own venue.
  - No liquidation is modelled.
- **Depth at size:** Lighter's costs come from October 2026 books by volume band, not from the books during these
  squeezes.
- **MEXC's own displayed rate:** the MEXC books use Binance's premium as a proxy.
- **The floor and the hourly switch:** both come from what settled; neither was forecast.

## What changes
- **M267 becomes PARTIAL.** Its predicted-rate form passed at gate 0; its stale-signal form stays NULL (R353).
- **What the pass earns (the PREREG's terms):**
  - A forward paper lane with a new id, frozen before its first day, on MEXC + Lighter with MEXC's displayed rate from
    the ticker recorder.
  - The reserved MEXC-only and Gate long-tail coins become a batch-2 candidate.
  - No money moves. That needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **What the forward lane must record, from this run:**
  - the displayed rate and both order books at the decision time;
  - fills taken from those books after the rate is read, not bar closes;
  - each leg's margin and its distance to liquidation;
  - floor settlements and interval switches.
- **Speed:** the MEXC θ 0.5% book took 0.16 hops a day, with a standard deviation of 75 bp a hop.
  - If its backtest mean held, a t of 2 over hops would need about 64 hops at +18.8 bp (API), or about 13 months.
  - At +29.8 bp (web), it would need about 25 hops, or about 5 months.

## Lane details
- **Registry row:** R354, 6 trials.
  - PREREG sha256 `799ffb1b…1426e05`, frozen and pushed in `5cf41fc` before the run.
  - Claimed on #7 (comment 6456536264) before the freeze.
  - All 36 inputs and the 1,071-file data manifest matched. The Lighter bands were recomputed from their 22
    snapshots.
- **Reproduce:** `python scripts/run_settlehop_pred.py` (about 20 seconds); the log is `run.log`.
  - `results/` holds `summary.json`, `books.csv`, `hops.csv.gz` and `daily.csv.gz`.
  - Everything under "Where the money comes from" was computed after the run: the rate at T, the settlements in the
    window, the price and premium paths, coin age and the moves. These numbers are reported and not decided on.
- **Read against the program:** trials go from 9,479,081 to 9,479,087 on this branch, or 9,479,104 counting #56's
  R338-R346.
