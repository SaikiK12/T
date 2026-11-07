# FINDINGS: cascmkt_v1 (registered R255; the frozen PREREG says R253). Buy the market after hours with many liquidation-cascade triggers

**Verdict: NULL.** The decided read, validation 2024-01..2025-06, failed.
- **Result:** +5.6 bp/day at 1x, NW t 1.03 (t 2 was required).
- **Events:** only 15 cascade hours, all in 2024; none in the first half of 2025.
- **Event-level rebound:** after them the equal-weight market rose +186 bp over 24 h, against -8 bp unconditionally.
  That is the sign the idea predicts, but 15 events cannot carry a book's t.

- **Registry row:** R255 (trials 1). Program trials on this branch after it: 9,472,002 + R256's 29 = 9,472,031.
  Codex's R253 adds 3 when it merges.
- **Id:**
  - The PREREG text declares R253. Codex claimed R253 on issue #7 first, so this lane is registered as R255.
  - `REGISTRY_REASSIGNMENT.json` records the move; the frozen text is unchanged.
- **Gate:** 0.
- **Reproduce:** prereg sha b92f7cc5, frozen in commit 3f350fe before the run. Run `python scripts/run_cascmkt.py`
  (about 1 minute).
- **Origin:** queue M233, from R252's post-hoc diagnostic.

## Numbers (CASC3/24: long the equal-weight market for 24 h after an hour with >= 3 cascade triggers)

| Window | Net bp/day 1x / 2x / 3x | Gross / cost | Hours invested | NW t (1x) | Alpha bp/day (t) | Beta | Trimmed |
|---|---|---|---|---|---|---|---|
| **Validation 2024-01..2025-06 (decided)** | +5.64 / +5.28 / +4.93 | +6.00 / 0.36 | 2.4% | **1.03** | +5.82 (1.08) | 0.02 | +1.77 |
| 2021-23 (post hoc, not decided) | +0.57 / +0.03 / -0.51 | +1.11 / 0.54 | 3.7% | 0.23 | +0.22 (0.09) | 0.03 | +2.30 |

Net per year at 1x:
- Validation: 2024 +8.4, 2025 0.0 (no events).
- Post hoc: 2021 -2.8, 2022 -4.4, 2023 +8.9.

## Cascade hours and the market's mean forward return (bp; equal-weight eligible perps)

| Window | K (coins in the hour) | Hours | 1 h | 4 h | 24 h | Unconditional 1 / 4 / 24 h |
|---|---|---|---|---|---|---|
| Validation | 1 | 38 | +32.2 | +96.7 | +253.6 | -0.3 / -1.2 / -8.2 |
| Validation | 2 | 21 | +31.1 | +145.9 | +293.4 | |
| **Validation** | **3 (decided)** | **15** | -5.2 | +116.3 | +186.4 | |
| Validation | 5 | 14 | -18.9 | +107.1 | +154.5 | |
| 2021-23 | 1 | 119 | +22.5 | +42.9 | +83.7 | +0.6 / +2.3 / +13.8 |
| 2021-23 | 2 | 58 | -0.9 | +19.1 | +60.0 | |
| 2021-23 | 3 | 42 | +12.8 | +42.4 | +56.1 | |
| 2021-23 | 5 | 32 | +18.6 | +47.7 | +40.1 | |

- **Cascade hours cluster.** Consecutive cascade hours restart the same 24 h hold. So the event means count one rebound
  several times, and the book counts it once.
  - 2021-23: the event mean implies about 2.1 bp/day gross; the book made 1.1.
- Only K = 3 was decided. The other rows are descriptive.

## Cost sensitivity
- The book is invested 2-4% of hours, so costs are 0.36-0.54 bp/day at 1x.
- At 3x, validation still nets +4.93 bp/day, and 2021-23 nets -0.51.
- **Costs do not decide the verdict; the event count does.**

## Reading
- **A rebound after mass long liquidations shows in both windows, as event averages.**
  - Excess 24 h market return: about +42 bp in 2021-23 (K = 3) and +194 bp in 2024.
  - 2022 is the exception: there the book lost (-4.4 bp/day). Cascades in a bear market were followed by more selling
    within 24 h often enough to offset the rebounds.
- **It is too rare to prove.**
  - 15 events in 18 months, and none from January to June 2025.
  - At this rate, a forward paper record needs years to reach t 2.
- **What it can still be:** an overlay that buys the market after a cascade cluster, sized small, inside a book that
  exists for other reasons. The lab has no such host book confirmed.
- **Read against the program:** 9,472,031 trials on this branch. A t of 1.03 is not evidence.

## Not checked
- BTC instead of the equal-weight market.
- Other holds (4 h or 72 h), or an exit on the first down hour.
- The short-squeeze mirror (sell the market after mass squeezes).
- The holdout (spent at program level).
