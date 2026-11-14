# FINDINGS: fundvol_v1 (R382, M455 sizing half). Verdict NULL

Frozen PREREG sha256 `a2a43b41b68ada0da57e6c3375df9079fbcd2c3d67a899c271f0ca768dd35706`; `run.log`, `results/`.
Gate 0, on seen data. Saved series only (R277's `gate+kucoin L14d th5% K20` daily net, 1x/2x/3x = 7/14/21 bp per leg per
side); no engine re-run, no download, no order.

## Verdict by the frozen rule: NULL
- **Choice (first half, 2021-05-03..2024-01-16, net 1x Sharpe):** `btc30_gate` 4.43; the others: own30_scale 4.38,
  btc30_scale 4.30, btc7_gate 4.20, own7_scale 3.11, btc7_scale 2.86. The base's own first-half 1x Sharpe is 4.46, so no
  variant beat the unscaled book even on the half that chose it.
- **Test (second half, 2024-01-17..2026-10-01, net 2x):** all three conditions fail.
  - Sharpe 6.37 against the base's 6.88 (difference -0.51).
  - Mean 4.07 against 4.41 bp/day (14.9 against 16.1 %/yr).
  - Block-bootstrap p = 0.935 (one-sided, 5000 stationary resamples, mean block 10, seed 382).
- **Trials:** 6 variants (the whole family). Read against `registry.program_trials()`: 9,479,246 before this round,
  9,479,252 after. A NULL needs no deflation.

## Cost sensitivity (net, annualised Sharpe and bp/day), chosen variant against the base
| Half | Book | 1x Sharpe | 1x bp/day | 2x Sharpe | 2x bp/day | 3x Sharpe | 3x bp/day |
|---|---|---|---|---|---|---|---|
| first | base | 4.46 | 1.75 | 3.31 | 1.33 | 2.20 | 0.90 |
| first | btc30_gate | 4.43 | 1.64 | 3.07 | 1.17 | 1.77 | 0.70 |
| second | base | 7.43 | 4.75 | 6.88 | 4.41 | 6.32 | 4.07 |
| second | btc30_gate | 6.99 | 4.44 | 6.37 | 4.07 | 5.73 | 3.70 |

The gate was off on 5.3% of first-half and 3.9% of second-half days (weight turnover 1.0% and 0.6% of days). Every
other variant, both halves, all three multiples: `results/variants.csv`. For information only (not chosen, not tested):
`btc30_scale` had the highest second-half mean (5.19 bp/day at 2x against 4.41) at a lower Sharpe (6.56 against 6.88)
with mean exposure 1.30x the base, so its mean gain is leverage, not a better ratio, and it carries no financing cost
here. The 7-day scale variants lost money at 2x in the first half (-0.02 and -0.05 bp/day) because exposure changes
on most days and each change is charged at the base's per-leg cost.

## Reading
- The expected result: the base's net volatility is small and stable (10 bp/day sd), so there was little for a
  volatility signal to act on. Interpretation, not tested here: the gate dropped days that on average earn carry
  (second-half mean fell 0.34 bp/day at 2x), and scaling mostly changed leverage or paid exposure-change cost.
- This closes only this form: trailing own-series or BTC volatility sizing of this one carry book at the base's
  cost. It does not test M455's HAR-with-funding volatility forecast, and it says nothing about directional books.
- 1 BTC day after warm-up had no volatility value (an incomplete UTC day); that date's weight was 1.

## Not checked
- M455's actual question (HAR forecast with funding level/change, QLIKE with a paired interval, perp/spot volume split,
  the top perps); neither cited paper was read.
- Any other book (binance+kucoin, R288's lighter books, R302); own-series gate variants (dropped to stay at 6).
- Financing or borrow on leverage above 1x, margin limits, and slippage on exposure changes beyond the base's per-leg
  cost; the date-label convention of the base series (a two-day lag was used instead of deriving it).
- Anything out of sample or forward: gate 0 on seen data, one book, one sample.

## Reproduce
`.venv/bin/python scripts/run_fundvol.py` (calls `prereg.verify` and `check_inputs` first); test:
`.venv/bin/python -m unittest tests.test_run_fundvol`.
