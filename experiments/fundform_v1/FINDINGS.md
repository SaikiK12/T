# FINDINGS: fundform_v1 (R492, M172) — the funding-formula forecast is NOISE; the hourly premium sample is too coarse

**Verdict: NOISE.** Using Binance's actual funding formula `F = P + clip(I - P, -0.05%, +0.05%)` (`I = 0.01%`) on the
point-in-time partial-cycle premium average does **not** beat the no-change forecast at any early offset. Frozen PREREG
`7ad06effd111`; one run, one primary estimand. This closes M172.

## What was run
`scripts/run_fundform.py`, same 50-perp panel and manifests as R491 (`54acb813841b`, `601d3d955c34`). 345,759
settlements, 2,462 days. At offset `k` h before settlement `T`, `F_k = P_k + clip(I - P_k, -0.05%, +0.05%)` with
`P_k` = mean of premium-index bar closes in the cycle with `h <= T-1-k`. Primary `k=1`.

## Result (primary, `k=1`)
| Forecast | MAE vs `r_next` |
|---|---|
| no-change `r_prev` | 1.107 bp |
| funding formula `F_1` | **1.046 bp** |
| **paired reduction** | **+0.118 bp** (NW t **+1.42**, n 342,437, 2,462 days) |

Below the discovery gate (needs t >= 3.0) and below the null 95th pct (t **3.11**). Curve: `k` = 0/-0.10 (t -0.82),
2/-0.04 (t -0.49), 3/-0.22 (t -2.78), 4/-0.26 (t -3.43), 6/-0.75 (t -9.37). Only `k=1` is positive, and only trivially.

## Why (the mechanism, and it is not the naive-mean bias)
R491 showed the naive premium **mean** is 3.1 bp worse than no-change, driven by a +2.7 bp level bias and the clamp.
This lane isolates the two causes:
- **The clamp is real and the formula fixes the bias.** On the full cycle (all 8 bars), the formula's residual bias is
  **-0.72 bp** (vs -2.77 bp for the naive mean). So the settled rate is indeed `avg + clip(...)`; the naive mean was
  simply the wrong object.
- **But the formula still misses by ~1.4 bp even with the full cycle** (`full_cycle_formula_mae_bp = 1.406`). The
  premium index moves ~4 bp hour to hour; an 8-point hourly sample of it has a standard error of ~4/sqrt(8) ~ 1.4 bp.
  That sampling noise is **larger than funding's own no-change MAE (1.1 bp)**, so no early-interval forecast built
  from *hourly* premium data can beat no-change. `k=1` (+0.12 bp, t 1.42) is that noise, not signal.

In one line: the settled rate is predictable (no-change MAE 1.1 bp, because funding is persistent and clamped), and the
premium index is *too coarsely sampled* to improve on that. A finer premium sample (per-minute, a different source) is
the only way this idea could be revisited; the hourly archive cannot carry it.

## Null
Block bootstrap on the daily `d` series (block 7 d, 2,000 replicas, seed 20261114): null 95th-pct t **3.11**,
5th-pct t **-1.35**. The observed `k=1` t (+1.42) is inside the null. Verdict rule gives **NOISE**.

## Cost sensitivity
Not applicable: the lane holds no positions and makes no fill claim. There is no P&L to cost. (Stated explicitly per
the lab rule; cost sensitivity belongs to the return lanes, not to a forecast-accuracy test.)

## Honest limits
- **Fixed major universe** (current survivors); within-coin estimand, so survivorship does not enter the number, but
  it bounds external validity to majors.
- **Binance only**, and **hourly** premium. MEXC's displayed next rate is the venue M172 names; this is Binance
  transfer evidence, and the coarse sampling is the binding limit.
- **Constants not fitted.** `I = 0.01%` and the `±0.05%` clamp are Binance's documented parameters; if they changed
  over 2021-2026 the residuals would show it, and the -0.72 bp residual suggests the formula is close but not exact
  (sub-hourly premium averaging, tick rounding).
- **One run.** No feature, offset or split changed after the result.

## What this authorizes
Nothing. M172 is closed on this data after two rounds (R491 naive mean, R492 formula), both NOISE. It does not support
trading the funding revision, does not move `go_real()`, and authorizes no order, key or money. The carry family's
remaining plausible revision signal is the *displayed next rate* captured prospectively, not the hourly premium path.

## Reproduction
```
python -c "import lab.prereg as p; p.freeze('experiments/fundform_v1/PREREG.md')"   # 7ad06effd111
.venv/bin/python scripts/run_fundform.py                                            # results/report.json
```
