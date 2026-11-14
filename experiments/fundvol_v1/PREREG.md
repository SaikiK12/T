# PREREG: fundvol_v1 (R382). M455 reduced to its smallest honest test: volatility sizing of a saved funding-carry book

Frozen with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R382
- **Method M455:** funding x volatility sizing. M455 as written asks for a HAR volatility forecast with funding features
  and a QLIKE comparison; this lane does not do that. It asks only the sizing half, on a saved book (below).
- **Owner (single writer):** the Claude lane worker that froze it. Date registered (UTC): 2026-11-02.
- **Execution mode:** none. Saved daily series only; the base lane's engine is not re-run; no download, no order.
- **Gate: 0, on seen data.** R277's summary and daily series were read to choose the base book and its cost model.

## Question
Does scaling or gating R277's funding-carry book by trailing volatility improve its net return at the base lane's own
executable cost, out of sample, by a rule chosen on the first half of the sample?

## Plain note on the expected outcome
A carry book earns a small, steady daily amount, so its volatility is low (base net: about 3.2 bp/day mean, 10 bp/day
sd) and a sizing rule has little to act on. A NULL is the expected and acceptable outcome. It closes only this form
(sizing a saved carry book by trailing BTC or own-series volatility); it says nothing about the HAR-with-funding
forecast of M455, which is not tested here.

## Base book
`gate+kucoin L14d th5% K20` from `experiments/xfund_kd_v1/results/daily.csv` (R277, PASS gate 0): R277's best book by t
and the longest saved sample (2021-01-23..2026-10-01, 2078 contiguous days, 1x/2x/3x costs of 7/14/21 bp per leg per
side). R288's book (2025-02 onward) is too short for a half-split; R302 saves no daily series. Columns used: `net`
(each cost multiple), `held`. The `gross`/`net` columns recover the base's paid cost exactly: gross - net = legs x
(1/(2K)) x cost, K = 20.

## The six variants (the whole family, trials = 6)
Volatility `v(D)` is the sample standard deviation (ddof 1) of the W daily returns that END TWO DAYS BEFORE date D
(window days D-1-W..D-2; the extra day of lag is deliberate, because the engine's date-label convention was not
re-derived). `own`: the base's saved 1x net series. `btc`: BTCUSDT daily log returns from `data/klines_1h` (UTC day
close = last of 24 hourly bars, an incomplete day has no close; only rows from 2021-01-01 are read).

| Variant | Source | W | Rule |
|---|---|---|---|
| own7_scale | own | 7 | inverse-vol scaling |
| own30_scale | own | 30 | inverse-vol scaling |
| btc7_scale | btc | 7 | inverse-vol scaling |
| btc30_scale | btc | 30 | inverse-vol scaling |
| btc7_gate | btc | 7 | high-vol gate |
| btc30_gate | btc | 30 | high-vol gate |

Own-series gate variants are dropped to stay at 6.
- **Scale:** `w(D) = clip(median_D / v(D), 0, 2)`, `median_D` the expanding median of `v` over the base dates up to and
  including D (needs 60 observations). `v(D) = 0` gives `w = 2`. A cap of 2 means the exposure can reach 2x the base;
  leverage is reported (mean w), not hidden.
- **Gate:** `w(D) = 0` if `v(D)` is above the expanding 80th percentile of `v` through D (60 observations needed), else 1.
- Any `w` whose inputs are missing is 1 (neutral). Weights do not depend on the cost multiple.

## Sized net, cost of changing exposure
`net_variant(D, m) = w(D) * net_base(D, m) - |w(D) - w(D-1)| * (held(D) / 20) * 0.0007 * m`, m = 1, 2, 3. The base's own
costs are scaled by w (its trades happen at the sized exposure); the second term charges the exposure change itself
at the base's per-leg cost (a full book of 20 held pairs is 20 x 2 legs x 1/40 = 1.0 of capital per side). This
charges slightly twice on days the base itself trades while the exposure changes, which is conservative. No funding
or borrow is charged on leverage above 1 (not modelled; the cap makes it matter only for the scale variants and it
favours them; stated, not corrected).

## Evaluation sample and halves
The first 100 base dates (2021-01-23..2021-05-02) are warm-up and never evaluated (every variant needs at most 92 days).
The remaining 1978 dates are split by count: first half = first 989, second half = last 989. Sharpe is the mean over the
standard deviation of daily net, times sqrt(365). Mean is daily net (bp/day and %/yr = x 365).

## Decision rule (written before any statistic)
1. **Choice, first half only:** the variant with the highest net 1x Sharpe on the first half.
2. **Test, second half only:** the chosen variant against the unscaled base (same dates, same cost multiple):
   - net 2x Sharpe of the variant > net 2x Sharpe of the base (strict),
   - net 2x mean of the variant > net 2x mean of the base (strict),
   - paired stationary block bootstrap (Politis-Romano, mean block 10 days, 5000 resamples, seed 382, resampling the
     (variant, base) pairs of days together) one-sided p <= 0.05 for the 2x Sharpe difference, p = share of resamples
     whose centred difference (resample minus observed) is at least the observed difference.
3. **Verdict:** PARTIAL if all three hold, else NULL. Never above PARTIAL (gate 0, saved series, one book, one
   sample). The 1x/3x tables, both halves and every variant are reported, but only rule 2 decides.

Nothing else is a selection: the base book, W, the cap, the quantile and the bootstrap settings are fixed here.

## What the author has seen
- R277's SUMMARY (the top book's headline: +11.76 %/yr at 1x, Sharpe +6.08, halves +1.64 / +4.80 bp/day, max drawdown
  -0.7%) and the column layout, dates and mean/sd of the base's 1x series.
- Nothing about BTC volatility, any variant's weights or any sized series.

## What this lane does not do
- No HAR forecast, no funding feature, no QLIKE, no perp/spot volume split (M455's actual question).
- No other book (binance+kucoin and R288's lighter books are not tested; R302 has no saved daily series).
- No re-run of any engine; no volatility target on capital beyond the cap; no financing on leverage; no live check.

## Inputs (frozen)

```inputs
0ab7db847cb9e0e51c93d59ad205a64888664a067fb8255a4093494c48d6b7ab  experiments/xfund_kd_v1/results/daily.csv
c626c79d3eaa8b3309ddc307731929892d766638ebaa0806ccf72ce15413d8d8  experiments/xfund_kd_v1/PREREG.sha256
ee2577fa45bdbb6b8582ab86c63958bf53717db638ae2fe4a76d32000f45cb3b  data/klines_1h/BTCUSDT.parquet
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
a2d87278873ca6737d3cc71ed628e6519511973ae380041d62a941c258cc1613  scripts/run_fundvol.py
0b6b5e9c5ef2a94d42924033af979890b10fcee0155afe2239ddfe455a9efbd0  tests/test_run_fundvol.py
```

## Outputs
`results/variants.csv` (every variant x half x cost multiple: n, mean, Sharpe, mean w, share off, weight turnover),
`results/summary.json`, `results/pick_daily.csv`, `run.log`, `FINDINGS.md` (1x/2x/3x table, read against
`registry.program_trials()`).
