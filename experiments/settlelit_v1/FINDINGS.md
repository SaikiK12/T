# FINDINGS: settlelit_v1 (R363). Short Lighter just before a deep Binance settlement, cover a minute later: +23.4 bp a hop at 1x on the 134 hops held out from R356

**Verdict: PASS by the frozen rule, recorded PARTIAL (gate 0), 6 trials.** The decided hops were not blind: R362 had
already read their Binance seconds, so this result says Lighter's minute closes carried a move that was known on
Binance. Only fresh settlements can test the route.

On R354's 134 θ 0.3-0.5% hops outside R356's book (27 coins, 127 settlement times, 2025-02..2026-08), a position on
Lighter against the side that received Binance's lump took the move. It was entered at the last trade before T and
closed at the last trade before T + 1 min.

- **Primary (enter before T, exit at T + 1 min):**
  - Price +40.1 bp a hop. Lighter's settlement at T −12.9 bp. Round trip 3.8 bp at 1x.
  - Net +23.4 / +19.6 / +15.8 bp a hop at 1x / 2x / 3x. CR1 t 4.34 / 3.58 / 2.83.
  - Hit rate 62% at 1x. +5.8 bp a calendar day of the hop's notional.
- **Checks** (PASS needs all five):

  | Check | Bar | Result | Pass |
  |---|---|---|---|
  | 1. CR1 t of the 1x net | ≥ 2.0 | 4.34 | yes |
  | 2. 2x mean net | > 0 | +19.6 bp | yes |
  | 3. 1x mean net in each half | > 0 | +21.8 / +23.8 bp | yes |
  | 4. 1x mean net without the best coin (KAITOUSDT) | > 0 | +20.6 bp | yes |
  | 5. GATES' trimmed mean of the 1x net | > 0 | +23.9 bp | yes |

- **Family:** all 6 trials on the unseen hops reach the Bonferroni t of 2.39 (from 3.02 to 4.47).

## The trials
bp a hop of the position's notional. Price is d · (exit / entry − 1). Funding is Lighter's settlement at T as the
position takes it. Cost is R354's Lighter band cost for a $1k order, a side.

| Trial (unseen 134) | Hops | Price | Funding | Net 1x / 2x / 3x | CR1 t 1x / 2x / 3x | Hit 1x | SD | Stale in / out |
|---|---|---|---|---|---|---|---|---|
| **in before T, out T + 1** | **134** | **+40.1** | **−12.9** | **+23.4 / +19.6 / +15.8** | **4.34 / 3.58 / 2.83** | **62%** | **63** | **18 / 4** |
| in before T, out T + 2 | 134 | +47.2 | −12.9 | +30.5 / +26.7 / +22.9 | 4.47 / 3.89 / 3.29 | 64% | 79 | 18 / 9 |
| in before T, out T + 5 | 134 | +45.0 | −12.9 | +28.3 / +24.5 / +20.7 | 3.02 / 2.61 / 2.19 | 62% | 108 | 18 / 15 |
| in before T − 5, out T + 1 | 128 | +59.7 | −12.9 | +43.0 / +39.2 / +35.3 | 4.23 / 3.84 / 3.44 | 67% | 117 | 13 / 2 |
| in before T − 5, out T + 2 | 128 | +66.9 | −12.9 | +50.2 / +46.4 / +42.5 | 4.31 / 3.97 / 3.62 | 69% | 131 | 13 / 7 |
| in before T − 5, out T + 5 | 128 | +63.8 | −12.9 | +47.1 / +43.3 / +39.4 | 3.53 / 3.23 / 2.94 | 64% | 150 | 13 / 12 |

- **The primary's robustness (unseen 134):**
  - Median +22.2 bp. Leave-two-coins-out +18.8 bp.
  - Without KAITO, RIVER, AVNT and BERA (72 hops, 77% of the sum), the other 62 hops net +11.5 bp.
  - The 10 best hops hold 46% of the sum. Without them, +13.8 bp.
  - By year: +25.8 bp in 2025 (42 hops), +22.3 in 2026 (92).
- **The tails (unseen, 1x):**
  - Worst hop −198.7 bp, 5th percentile −58.3.
  - Best hop +163.1, 95th percentile +131.1.
  - A quarter of the hops lose more than 8.7 bp.
- **R356's 87 seen hops (θ ≥ 0.5%; reported only):** price +95.9, funding −22.5, net +69.9 / +66.5 / +63.0 bp at
  1x / 2x / 3x (t 6.81). All 221: +41.7 bp at 1x (t 7.77).
- **Entering five minutes earlier** adds about 20 bp of price on every exit. Lighter falls into T on these hops, as
  R356's path showed on its 87 (Lighter's part +71.6 bp at T − 5 and +87.6 at T). That entry is a trial here, not the
  primary. It is noisier: the standard deviation roughly doubles.

## Where it comes from
- **Lighter follows Binance:**
  - Lighter's price move from the last trade before T to the close of T + 1 min correlates 0.80, hop by hop, with
    Binance's move from T + 1 s to T + 60 s (R362's ticks, all 221).
  - On the 134 hops, Lighter took +40.1 bp by its T + 1 min close. Binance had moved +60.8 bp by T + 60 s from its
    last trade before T: about two thirds.
- **Lighter's own settlement is the cost to beat:**
  - Lighter's hourly rate at T is deeply negative on these hops: the short paid a median 12.9 bp (10th percentile
    21.5) for that one hour. On the seen hops it paid 22.5 bp.
  - That fits the hedged capture trade: long Binance for the lump, short Lighter, which pushes Lighter below its index
    in the hour before T.
  - The book cost is small next to it: 3.8 bp a round trip at $1k on Lighter's zero-fee book.
- **Dose:**
  - By terciles of R354's forecast lump |e| within θ 0.3-0.5% (medians 32 / 37 / 44 bp): +22.8 / +15.7 / +31.5 bp a hop.
  - The seen hops, θ ≥ 0.5%, net +69.9.
  - The move grows with the lump across the books, not smoothly inside this narrow band.

## Costs (1x, 2x, 3x)
- **1x:** R354's Lighter band cost for each hop's coin and day, a $1k order's book cost from the October 2026
  snapshots (26.67 / 7.27 / 4.17 / 1.09 / 0.51 / 0.26 bp a side). Lighter charges no fee. The primary's round trip
  averaged 3.8 bp.
- **2x / 3x:** +19.6 / +15.8 bp a hop on the primary (t 3.58 / 2.83); every trial stays positive at 3x.
- **Larger orders:** not costed. Lighter's books on these coins are thin, and a settlement minute may be thinner;
  the bands are for $1k.
- **Funding is in every net:** Lighter's settlement at T, which the position cannot avoid.

## What this does and does not show
**It shows,** at gate 0 on R354's hops (2025-26):
- A short on Lighter placed before a deep negative Binance settlement and covered a minute after it kept +40 bp of
  price on hops R356 never read. That was enough to pay Lighter's own hourly settlement (−13 bp) and its book.
- It needs no speed, unlike the Binance route R362 closed. Both orders sit outside the settlement's seconds.
- It held in both halves, without the best coin, trimmed and leave-two-coins-out.

**It does not show:**
- **That it is out of sample.** R362 read these hops' Binance seconds before the freeze. The move was known; this run
  priced it on Lighter. Against 9,479,106 program trials, nothing here is proof.
- **Fills.** A minute close is the last trade, on either side of the spread. The book around a settlement, when the
  crowd trades, was never recorded. A live lane must walk the real book at both orders.
- **Lighter's settlement timing:** the run charges the settlement stamped at T. Whether Lighter's settlement can land
  before our entry or after our exit is not checked. Both orders sit at least a minute away from T, but that was not
  verified.
- **A live trigger:** the hops come from Binance's rate rebuilt from the archive an hour before T. Binance's live API
  is not reachable from this lab (HTTP 451). A forward lane must use what it can read live, and that changes the events.
- **Size:** the bands are for $1k. Thin coins (KAITO, RIVER, AVNT and BERA carry 77% of the sum) cannot take much more
  without paying more.
- **Margin and liquidation:** not modelled. The worst hop lost 2% in two minutes.

## What changes
- **M267's Lighter-route form becomes PARTIAL (gate 0).** It is the first form of the settlement hop that fits a
  scalp the owner asked for: a few minutes, no speed, no fee.
- **What the pass earns (the PREREG's terms):** a forward paper lane on Lighter, under a new id, frozen before its
  first ticket.
  - It reads the predicted rates point-in-time an hour before T, as R355 does, and places a paper ticket before T.
  - It scores the ticket on Lighter's live book, walking it at both orders.
  - It records the book around T, so fills and Lighter's settlement time are measured, not assumed.
  - No money moves: that needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **R355 is unchanged.** It keeps running the hedged hop forward on MEXC + Lighter.

## Lane details
- **Registry row:** R363, 6 trials.
  - PREREG sha256 `d381b1a2…2dd6`, frozen 2026-10-28 14:28:56 UTC and pushed in `c348696` before the run.
  - Claimed on #7 (comment 6471423185) before the freeze.
  - All 15 inputs matched, the 221 minute files matched their provenance before and after the run, and every
    Lighter funding file matched R354's manifest.
- **Reproduce:** `python scripts/run_settlelit.py` (a few seconds, after `python -I scripts/fetch_settlelit_1m.py` has
  rebuilt `data/settlelit_1m`); the log is `run.log`.
  - `results/` holds `summary.json`, `trials.csv` and `hops.csv.gz`.
  - The robustness lines, the tails, the years, the coins, the dose and the correlation with R362 were computed after
    the run from `results/hops.csv.gz`, R354's `hops.csv.gz` and R362's `results/hops.csv.gz`. They are reported, not
    decided on.
- **Read against the program:** trials go from 9,479,100 to 9,479,106 on this branch, or 9,479,123 counting #56's
  R338-R346.
