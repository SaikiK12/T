# FINDINGS: merge_v2 (R187)

**Verdict: FAIL** (the pre-registered word for NULL here). Trade-consistent (episode) cell statistics, shorter windows
and session-aware means do not produce a gross edge out of sample at the primary, and nothing passes at full or half
costs.

- **Registry row:** R187 (trials: 1,008 = runs A, B, C, D x 252 configurations; placebo not counted)
- **Reproduce:** prereg sha f35b8387; `python scripts/run_merge_v2.py --tag A|B|C|D [--train-days 90] [--pooled]
  [--tensors main,clock,flow] [--placebo]`.

## Numbers (2022-01-01 to 2025-06-30; excess, h 24, N 30, k_in 1, fixed thresholds)
| run | gross / yr (t) | net 1x (t) | 2x | 3x | fee-aware 0.5x (t) | gross per year 2022..2025H1 |
|---|---|---|---|---|---|---|
| A 180 d, session-aware (primary) | -1.7% (-0.09) | -62.7% (-3.31) | -124% | -185% | -27.4% (-1.65) | +58, -32, -45, +13% |
| A placebo | +1.4% (0.10) | -43.7% (-3.00) | | | | |
| B 90 d, session-aware | +32.3% (1.93) | -36.4% (-2.08) | -105% | -174% | -21.6% (-1.45) | +66, +19, +25, +4% |
| C 180 d, pooled | +20.8% (1.06) | -17.5% (-0.89) | -56% | -94% | -9.4% (-0.54) | +75, -31, -24, +53% |
| D = A + order flow | +21.0% (1.14) | -44.8% (-2.40) | -111% | -176% | -14.4% (-0.87) | +52, -3, -5, +30% |

Best configuration at 1x per run (all h 4, excess): A Sharpe 0.97 (Deflated Sharpe 0.63), B 0.72 (0.19), C 0.72
(0.48), D 1.17 (0.77). None reaches a Deflated Sharpe of 0.95.

Effects: session means hurt (A vs C: -1.7% vs +20.8% gross); a shorter window helps the gross (B vs A); order flow
helps (D vs A: +21.0% vs -1.7%).

## Cost sensitivity
In the table. No run is positive at 1x, 2x or 3x; LOW-FEE PASS not met.

## What this does not show
Same combiner as merge_v1 (additive cell means, hysteresis trading). Per-trade cell statistics shrink the edges toward
what an entry earns, which is the honest number, but the merge still trades often enough that costs dominate.

## Next
Stop merging many small cells with frequent trading; trade few strong, slow cells as slices (flow72_v2) or gate them by
context (atlas_ctx, atlas_mtf).
