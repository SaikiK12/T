# FINDINGS: merge_v1 (R186)

**Verdict: NULL.** Walk-forward composites of the atlas's confident cells do not reach a gross t of 3 out of sample at
the primary, and none pays at the tier costs. Adding order flow (M2) doubles the gross edge, which then holds in every
year, but costs still exceed it.

- **Registry row:** R186 (trials: 3,564 = M1, M1s, M2 x 1,188 configurations; placebos not counted)
- **Reproduce:** prereg sha ce5ac5ef; `python scripts/run_merge.py --tag M1|M1s|M2 [--tensors main,clock,flow]
  [--train-days 180] [--placebo]`. Note: the M2 placebo was run as `--tag M2_placebo --placebo`, so its files are named
  M2_placebo_placebo_*.

## Numbers (test span 2022-01-01 to 2025-06-30, 42 monthly refits; excess, h 24, N 30, k_in 1, fixed thresholds)
| run | gross / yr (t) | net 1x (t) | 2x | 3x | break-even cost | gross per year 2022..2025H1 |
|---|---|---|---|---|---|---|
| M1 main+clock, 365 d (primary) | +23.6% (1.27) | -32.6% (-1.77) | -88.9% | -145% | 0.42x | +60, -57, +35, +44% |
| M1 placebo | -15.4% (-1.04) | -40.9% (-2.75) | | | | |
| M1s 180 d window | +50.3% (2.68) | +0.5% (0.02) | -49.4% | -99% | 1.01x | +95, +25, +30, +26% |
| M2 + order flow | +50.1% (2.64) | -19.7% (-1.04) | -89.4% | -159% | 0.72x | +71, +46, +38, +20% |
| M2 placebo | -8.3% (-0.63) | -36.0% (-2.68) | | | | |

Fee-aware thresholds (a trader paying a quarter of the tier costs): M2 +36.8%/yr (t 2.34), M1s +21.5% (t 1.35), M1
+17.3% (t 1.12). Best configuration at 1x in M2: excess, h 4, N 3, k_in 2 (Sharpe 0.39, Deflated Sharpe 0.00003).

## Cost sensitivity
In the table: every run is negative at 2x and 3x. Break-even multiples 0.42x (M1), 1.01x (M1s), 0.72x (M2).

## What this does not show
- The merge sums cell means (additive, no interactions) and trades a 24 h forecast with hysteresis; other combiners
  (per-trade weights, slices as in flow72_v2) were not tried here.
- Cells are selected from day-weighted statistics, which overstate per-entry edges (see flow72_v1).

## Next
The flow effect is the useful finding: M2's gross is positive in all four years. The slice construction of flow72_v2
is the cheaper way to trade the strongest flow cells.
