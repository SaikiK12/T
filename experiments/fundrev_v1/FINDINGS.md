# FINDINGS: fundrev_v1 (R491, M172) — does the within-cycle premium index forecast the next settled funding rate?

**Verdict: NOISE (a clean null, with a mechanism).** The naive within-cycle premium-index mean does **not** beat the
no-change forecast; it is significantly *worse*. Frozen PREREG `79df1757e29c`; one run, one primary estimand.

## What was run
`scripts/run_fundrev.py` on Binance USDT perps: 50 symbols, funding manifest `601d3d955c34`, premium-index manifest
`54acb813841b`, klines manifest `16e6434c8fcd`. 345,759 settlements, 2,462 calendar days. For offset `k` hours before
settlement `T`, the point-in-time forecast is `P_k` = mean of the premium-index bar closes in the cycle with
`h <= T-1-k` (bars closed at or before `T-k`; no look-ahead). Baselines: no-change `r_prev` and (curve) the partial
mean. Primary estimand `k=1`, paired absolute-error difference `d = |r_prev - r_next| - |P_k - r_next|` aggregated to
days and tested with Newey-West (lag 7).

## Result (primary, `k=1`)
| Forecast | MAE vs `r_next` |
|---|---|
| no-change `r_prev` | **1.107 bp** |
| partial premium mean `P_1` | 4.330 bp |
| **paired reduction** | **-3.119 bp** (NW t **-35.1**, n 342,437, 2,462 days) |

The partial premium mean is **3.1 bp worse** than doing nothing, and the sign is overwhelming. Sensitivity curve is
uniformly negative: `k` = 0/-3.35, 1/-3.12, 2/-3.22, 3/-3.32, 4/-3.34, 6/-3.62 bp (all |t| > 24). No offset helps.

## Why (diagnostic on the frozen feature, not a new feature)
- **Level bias.** The signed difference `P_1 - r_next` has mean **-2.72 bp**, median **-4.38 bp** (3-symbol probe).
  The premium index sits above the settled rate on average, so the raw mean is a biased point forecast.
- **Clamp.** **33.9%** of settlements are exactly at the ±1 bp baseline (0.0001), which no-change reproduces for free;
  a continuous premium mean cannot, so it pays the clamp noise on a third of all settlements.
- The two together explain the whole gap: no-change is already within ~1.1 bp, and the premium mean adds a ~2.7 bp
  bias on top of the clamp.

## Null and robustness
Block bootstrap on the daily `d` series (block 7 d, 2,000 replicas, seed 20261114): null 95th-pct t **2.63**,
5th-pct **-1.43**. The observed `k=1` t is **-35.1**, far below the 5th percentile — i.e. the partial-premium
forecast is significantly **worse** than no-change, not merely uninformative. Verdict rule gives **NOISE**.

## Secondary diagnostic (return signal)
The revision `P_1 - r_prev` has a **negative** cross-sectional rank IC vs the next-cycle return: mean **-0.0315**,
NW t **-9.18** (2,457 days, 341,918 pairs). A revision that points *up* is followed by a *lower* next-cycle return —
the opposite sign to the carry thesis. This is diagnostic only; the lane holds no positions.

## Honest limits
- **Mechanism not the last word.** This tests the *naive* premium mean. A de-biased or clamp-aware forecast (subtract
  the trailing level bias, or condition on being off the clamp) is a different, untested feature and would need its
  own frozen PREREG; the raw premium path is not the same as a fitted predictor. Do not read this as "the premium
  index carries no information" — only "this unadjusted use of it does not."
- **Fixed major universe** (current survivors). The estimand is within-coin, so survivorship does not enter the primary
  number, but it bounds external validity to majors.
- **Binance only.** MEXC's current/next-rate display is the venue M172 actually names; this is Binance transfer
  evidence, not a MEXC measurement.
- **No trades, no cost.** None is needed: the estimand is forecast accuracy. There is no P&L claim.
- **One run.** No feature, offset or split changed after the result.

## What this authorizes
Nothing. M172 is closed as tested-and-null. It does **not** support trading the funding revision, does not move
`go_real()`, and authorizes no order, key or money. It informs R220: the *displayed next rate* (not the premium mean)
remains the only plausible revision signal worth a prospective, timestamped capture.

## Reproduction
```
.venv/bin/python -m lab.data build fundingRate --symbols "$(cat /tmp/syms.txt)"
.venv/bin/python -m lab.data build premiumIndexKlines 1h --symbols "$(cat /tmp/syms.txt)"
python -c "import lab.prereg as p; p.freeze('experiments/fundrev_v1/PREREG.md')"   # 79df1757e29c
python scripts/run_fundrev.py                                                      # results/report.json
```
