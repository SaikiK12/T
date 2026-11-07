# FINDINGS: settleticks_v1 (R362). The price falls about 85 bp in the 15 seconds after a deep Binance settlement, and a safe entry comes after it

**Verdict: NULL by the frozen rule, 7 trials (4 decided).**

On R354's 221 θ 0.3% hops (34 coins, 204 settlement times, 2025-02-22..2026-08-13), a Binance taker who opens against
the side that received the lump at T + 15 s, the first second Binance's FAQ makes safe, and closes at T + 60 s, makes
+5.4 bp gross a hop. That is a third of the 17 bp round trip.

- **Primary (enter T + 15 s, exit T + 60 s):**
  - Net −11.6 / −28.6 / −45.6 bp a hop at 1x / 2x / 3x.
  - CR1 t −2.93. Hit rate 37% at 1x.
  - On the 134 hops nobody had read: −20.6 bp at 1x (t −4.80).
- **Checks** (PASS needs all five):

  | Check | Bar | Result | Pass |
  |---|---|---|---|
  | 1. CR1 t of the 1x net | ≥ 2.0 | −2.93 | no |
  | 2. 2x mean net | > 0 | −28.6 bp | no |
  | 3. 1x mean net in each half | > 0 | −17.0 / −10.4 bp | no |
  | 4. 1x mean net without the best coin (FFUSDT) | > 0 | −12.6 bp | no |
  | 5. 1x mean net on the 134 unseen hops | > 0 | −20.6 bp | no |

- **Family:** none of the 4 decided exits reaches a CR1 t of 2.0, let alone the Bonferroni 2.24.
- **The power was there.** The per-hop standard deviation was 58 bp, so the t ≥ 2 bar sat at about +8 bp net. The
  test could have found a modest edge. The decided exits do not have one.

## The scalps
Gross and net are bp a hop of the scalp's notional. Cost is 8.5 bp a side at 1x (R354's Binance API charge).

| Scalp | Decided | Gross (median) | Net 1x / 2x / 3x | CR1 t 1x | Hit 1x | Unseen 134, net 1x (t) | Seen 87, net 1x | SD |
|---|---|---|---|---|---|---|---|---|
| in T + 15 s, out T + 30 s | yes | +0.4 (0.0) | −16.6 / −33.6 / −50.6 | −6.94 | 27% | −19.0 (−6.06) | −12.9 | 35 |
| **in T + 15 s, out T + 60 s** | **primary** | **+5.4 (0.0)** | **−11.6 / −28.6 / −45.6** | **−2.93** | **37%** | **−20.6 (−4.80)** | **+2.1** | **58** |
| in T + 15 s, out T + 120 s | yes | +14.1 (+7.2) | −2.9 / −19.9 / −36.9 | −0.49 | 42% | −11.9 (−1.97) | +11.0 | 85 |
| in T + 15 s, out T + 300 s | yes | +19.5 (+17.0) | +2.5 / −14.5 / −31.5 | +0.25 | 50% | −9.9 (−1.19) | +21.6 | 132 |
| in T + 1 s, out T + 60 s | reported | +45.7 (+37.5) | +28.7 / +11.7 / −5.3 | +5.75 | 62% | +9.7 (+1.90) | +57.9 | 75 |
| in T + 2 s, out T + 60 s | reported | +24.0 (+18.5) | +7.0 / −10.0 / −27.0 | +1.58 | 52% | −4.3 (−0.89) | +24.5 | 66 |
| in T + 5 s, out T + 60 s | reported | +17.7 (+11.5) | +0.7 / −16.3 / −33.3 | +0.15 | 48% | −10.4 (−2.26) | +17.7 | 64 |

- **The decided exits, robustness:**
  - GATES' trimmed mean of the 1x net (without the 10 best and 10 worst hops): −16.3, −12.1, −4.3 and +0.5 bp.
  - Leave-two-coins-out: −17.9, −13.4, −12.6 and −11.3 bp.
  - bp a calendar day (538 days): −6.8, −4.8, −1.2 and +1.0.
- **Fills:**
  - The entry trade came a median 0.05 s after T + 15 s (90th percentile 0.4 s, max 2.4 s).
  - Every primary exit filled on its own side within 5 s. Two exits on the other decided legs (T + 30 s, T + 300 s)
    took the first trade of either side. No exit was stale.
- **The early entries are inside Binance's 15-second deviation and are not tradeable as written.** A position opened
  there may pay the whole lump: R354's forecast was 30 to 600 bp on these hops, 61 on average (median 44). The T + 1 s
  row nets +28.7 bp at 1x before that risk.

## Where the move went
The mean price against the receiving side, in bp from the last trade before T (`results/path.csv`; a positive number
is the scalp's gain):

| Second | −300 | −60 | −10 | −1 | 0 | 0.25 | 0.5 | 1 | 2 | 5 | 10 | 15 | 30 | 60 | 120 | 300 | 600 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| All 221, mean | −15.6 | −2.0 | −0.7 | +2.4 | −0.2 | +20.9 | +36.0 | +44.4 | +65.4 | +72.3 | +80.6 | +84.6 | +84.8 | +89.3 | +98.0 | +103.1 | +108.2 |
| All 221, median | −6.8 | 0.0 | −2.0 | 0.0 | 0.0 | +14.9 | +28.7 | +39.4 | +59.1 | +63.5 | +71.1 | +77.1 | +74.3 | +79.2 | +88.8 | +86.4 | +95.5 |
| Unseen 134, mean | −9.9 | −0.4 | −3.2 | +1.5 | −0.1 | +17.5 | +27.1 | +34.5 | +48.1 | +54.4 | +61.6 | +64.6 | +62.5 | +60.8 | +69.2 | +70.8 | +67.9 |
| Seen 87, mean | −24.3 | −4.5 | +3.1 | +3.8 | −0.3 | +26.0 | +49.7 | +59.7 | +92.1 | +99.9 | +110.0 | +115.2 | +119.0 | +133.2 | +142.4 | +152.7 | +170.4 |
| Share above 0 | 44% | 46% | 40% | 49% | 3% | 77% | 81% | 88% | 96% | 95% | 96% | 94% | 90% | 88% | 86% | 81% | 75% |

(The file's T − 600 s point holds one hop, the only one with a trade exactly at the window's start.)

- **The giveback is a burst.** Half of the first 15 seconds' move comes in the first 0.5 s, three quarters by 2 s.
  By T + 15 s it is 85 bp, and 96% of hops are in the scalp's favour from 2 s on.
- **After T + 15 s there is little left:** +4.7 bp more by T + 60 s and +18.5 by T + 300 s on average, and nothing on
  the 134 unseen hops (−3.8 by T + 60 s).
- **The flow says the same** (`results/flow.csv`; taker quote volume in the scalp's direction a second, in units of
  the hop's mean total taker volume a second over [T − 600 s, T − 60 s)):

  | Seconds after T | −60..−10 | −10..0 | 0..1 | 1..2 | 2..5 | 5..15 | 15..30 | 30..60 | 60..120 | 120..300 | 300..900 |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | Mean | −0.10 | −0.66 | +26.2 | +18.6 | +5.6 | +1.2 | +0.5 | +0.3 | +0.3 | +0.1 | +0.06 |
  | Median | −0.08 | −0.29 | +11.8 | +10.7 | +3.4 | +0.9 | +0.3 | +0.2 | +0.2 | +0.06 | +0.03 |

  In the first two seconds after T, the net taker selling against the receiving longs runs at 19 to 26 times the
  hop's normal total volume. By 15 s it is back near normal.
- **What it fits:** the traders who bought for the lump sell the moment it is paid, within one or two seconds. They
  do not wait out the 15-second deviation. Either they know the snapshot is taken at T in practice, or they accept
  the risk. Nothing public tells which.

## Computed after the run (reported, not decided on)
- **Dose:** the move scales with the lump. By terciles of R354's forecast |e| (medians 33 / 44 / 71 bp):
  - in T + 1 s, out T + 60 s: +22.8 / +39.1 / +75.1 bp gross;
  - the primary (in T + 15 s): −4.4 / −0.2 / +20.7 bp gross. Only the deepest third keeps something after 15 s, and
    +20.7 bp barely covers the 17 bp round trip. This subgroup was chosen after the run and decides nothing.
- **Years:** the primary's gross is +2.4 bp a hop in 2025 (69 hops) and +6.7 in 2026 (152).
- **Coins:** KAITO 36 hops, RIVER 30, 0G 26, BERA 26, AVNT 19, ZORA 12.

## Costs (1x, 2x, 3x)
- **1x:** 8.5 bp a side, R354's Binance API charge. The fills are side-specific trade prices, so part of the spread
  is charged twice: the 1x cost is conservative.
- **2x / 3x:** 17 / 25.5 bp a side. Every decided exit is negative at 2x and 3x. Of the reported early entries, only
  T + 1 s is positive at 2x (+11.7), and none at 3x.
- **At zero cost** the primary would make +5.4 bp a hop with a median of 0. No fee level makes it a strategy.

## What this does and does not show
**It shows,** on Binance ticks at gate 0:
- The post-settlement move R356 saw inside the first minute is real, large and immediate: about 85 bp against the
  receiving side within 15 seconds, most of it within 2.
- The move is also on the 134 hops nobody had read (+64.6 bp by T + 15 s), so it is not R356's sample alone.
- It is done before a position against the receiving side can open safely on Binance. **The Binance seconds scalp
  is closed.**

**It does not show:**
- **When Binance actually charges each account.** The FAQ states a 15-second deviation; the crowd behaves as if the
  snapshot were at T. Testing that needs an account and real positions: the owner's call, not this lab's.
- **Real fills** in the seconds after a settlement. The trade prints approximate the touch; books were not recorded.
- **Other venues.** MEXC and Lighter follow Binance within about a second (R348), so a position held across T there
  would ride the move, paying that venue's own settlement. That is R363's question (Lighter, minute bars) and needs a
  live recorder to answer at the second.
- **Out of sample:** these are R354's hops at gate 0. Against 9,479,100 program trials, nothing here is a proof.

## What changes
- **M267's seconds form on Binance is NULL.** No seconds scalp after the deviation.
- **R363 changes before its freeze** (it was drafted, not frozen, when this ran). Its decided hops, the 134 unseen
  here, are no longer unread on Binance: R363's PREREG must say this lane's path has been read, and that R363 tests
  whether Lighter's minute closes carry the known move net of Lighter's own settlement and book, not whether the move
  exists.
- **A live settlement-tape recorder is still worth having for a Lighter or MEXC route:** books and trades from T − 2
  min to T + 5 min on the venue that holds the position, because the move is in the first seconds and minute bars
  cannot price it.

## Lane details
- **Registry row:** R362, 7 trials.
  - PREREG sha256 `6b0a819d…a250`, frozen 2026-10-28 14:20:40 UTC and pushed in `3410447` before the run.
  - Claimed on #7 (comment 6471157448) before the freeze.
  - All 11 inputs matched, and the 221 tick files matched their provenance before and after the run.
- **Reproduce:** `python scripts/run_settleticks.py` (about 5 seconds, after `scripts/fetch_settle_ticks.py` has
  rebuilt `data/settle_ticks`, 1.23 GB of zips streamed); the log is `run.log`.
  - `results/` holds `summary.json`, `scalps.csv`, `hops.csv.gz`, `path.csv` and `flow.csv`.
  - Everything under "Computed after the run" comes from `results/hops.csv.gz` and R354's `hops.csv.gz`.
- **Read against the program:** trials go from 9,479,093 to 9,479,100 on this branch, or 9,479,117 counting #56's
  R338-R346.
