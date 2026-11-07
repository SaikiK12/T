# FINDINGS: fundext_v1 (R273). Extreme-funding onsets: no strategy passes; the typical coin falls, the squeeze tail decides

**Verdict: NULL (gate 0).** 40 strategies, 2021-01-04..2026-09, 40/80/120 bp.
- **Strategies:** 5 kinds × long/short × +1/8/24/72 h.
- **Registry:** R273, 40 trials. Program trials become 9,477,667.
- **Reproduce:** prereg sha 34cc54eb, frozen in commit bc6027d before any price was read. Then run
  `python scripts/qx_run.py experiments/fundext_v1` at that commit. The whole family takes about 2 s on qx.
- **Sample:** 5,515 onset legs, 5,488 priced on the Binance perp, 27 with no trade at the settlement hour. No leg was
  dropped by the 20× bar-jump guard.

## Deviation from the PREREG text (the frozen rule decides)
- The PREREG table said all six kinds have at least 10 clusters. That count was taken before pricing.
- qx applies `min_clusters = 10` to priced clusters, and pos2 has 9 (3 of its 12 settlement hours had no trade at r0).
- So pos2 is out of the family by the frozen rule. The family is 40 strategies, and 40 trials are registered.

## Top 8 by t (1x, one observation per settlement-hour cluster)
| Strategy | n | 1x mean | Median | Hit | t | RC p | Halves | 2025+ (n) | 2x | 3x |
|---|---|---|---|---|---|---|---|---|---|---|
| neg2 long +72 h | 350 | +7.32% | -4.95% | 42% | 2.39 | 0.87 | +8.91 / +5.72 | +10.17% (270) | +6.92% | +6.52% |
| neg2 long +24 h | 350 | +4.60% | -3.94% | 40% | 2.03 | 0.99 | +5.48 / +3.71 | +6.28% (270) | +4.20% | +3.80% |
| neg1 long +24 h | 860 | +1.26% | -2.80% | 40% | 1.16 | 1.00 | +3.99 / -1.48 | +1.69% (681) | +0.86% | +0.46% |
| neg1 long +72 h | 859 | +1.45% | -4.66% | 39% | 1.08 | 1.00 | +3.80 / -0.90 | +1.61% (680) | +1.05% | +0.65% |
| pos0.3 short +8 h | 310 | +0.73% | -0.18% | 47% | 0.94 | 0.89 | +0.92 / +0.54 | +0.83% (230) | +0.33% | -0.07% |
| pos1 long +1 h | 22 | +1.90% | -0.40% | 32% | 0.75 | 1.00 | +3.62 / +0.18 | +1.90% (22) | +1.50% | +1.10% |
| neg2 long +8 h | 350 | +0.80% | -1.70% | 40% | 0.60 | 1.00 | -0.29 / +1.88 | +1.29% (270) | +0.40% | -0.00% |
| pos1 short +72 h | 22 | +5.02% | +7.15% | 68% | 0.54 | 1.00 | -2.48 / +12.51 | +5.02% (22) | +4.62% | +4.22% |

- The full table is `results/strategies.csv`; `results/SUMMARY.md` is written by the pipeline.
- **The only strategy that clears the reality check is neg0.3 short +72 h** (RC p 0.031, on winsorized observations).
  It fails every other gate:
  - raw mean -0.99%, t -1.45, both halves negative, 2025+ -1.18%;
  - matched null p 0.14.

## What the data show (descriptive, not gates)
- **After a negative-funding onset, the typical coin keeps falling.**
  - neg0.3 short +72 h has a median of +2.83% net and wins 59% of clusters.
  - neg1 short +72 h has a median of +3.86%; neg2 short +72 h, +4.15%.
- **A few squeezes are larger than all the wins.**
  - The same shorts lose on average: -0.99%, -2.25% and -8.12%.
  - The longs mirror this: neg2 long +72 h has mean +7.32% and median -4.95%.
  - The worst 5% of clusters carry the sign. Clipped at the 5th and 95th percentiles, neg0.3 short +72 h has a
    t high enough to clear the reality check (p 0.031). Raw, it loses.
- **The first hour after the settlement is already taken.**
  - The move in the settlement hour, in the short direction, is +0.74% (t 7.5).
  - From the entry one hour later, the +1 h short makes -0.37% net (t -4.1), roughly zero gross.
- **Positive-funding onsets (longs paying) show nothing.** Every pos strategy has |t| < 1.

## Reading
- **Against program trials (9,477,667):** nothing here is close. The best raw t (2.39) is below what 40 tries give by
  chance (null 95th percentile 3.52).
- **Pre-committed:** none passed, so the top 3 by t go to the first reserved 2020 batch: neg2 long +72 h, neg2 long
  +24 h and neg1 long +24 h.
  - 2020 funding rarely went below -1%: 2021 has 1 such onset. These may have too few 2020 events to read, and the
    batch PREREG will say so before reading.
- **A new idea (post hoc, queued as M261, not tested):** shorting after a negative-funding onset has a positive median
  and a negative mean. A version with a protective cover could keep the median and cut the tail; for example, cover
  at the first close 15% above entry, or size by funding level.
  - R208 found stops harmful on daily books. Here the loss is a squeeze tail, which is the case a stop is built for.
  - It needs its own frozen lane, and the tail decides.
- **R271's fund_freq long +1 h does not reappear** in the data-defined version: neg1 long +1 h is -0.60% (t -2.81) and
  neg2 long +1 h -0.06%.
  - The notice effect, if real, was in the notice itself, which comes before or with the frequency change.
