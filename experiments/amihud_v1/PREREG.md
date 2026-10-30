# PREREG: amihud_v1 (R236). Amihud illiquidity as a one-week spread book on the perp cross-section

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R236
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_amihud.py`, `lab/screen.py`, `lab/flowfeat.load`
- **Queue:** M002 in `registry/methods.csv`
- **Gate:** 0 (screen)

## Why
The crypto literature puts much of its cross-sectional alpha in small, illiquid coins (Cakici 2024; Zaremba 2021). The
lab has not tested a price-impact measure:
- R226 tested 24 h quote volume, level and change: NULL; qv_lvl was -1.4 bp/day, t -0.31.
- R185 and R222 have no Amihud view.

## What the author has seen
- R226's quote-volume books (NULL) and every flow and atlas result.
- No statistic of |return| / volume in this universe.

## Feature (per coin and hour t)
- `illiq[t] = mean(|r|, last 720 h) / mean(quote_volume, last 720 h)`, from hourly returns and klines quote volume.
  This is a 30-day Amihud price-impact ratio.
- It is NaN unless all 720 hours are present.
- It is ranked on `log(illiq)`; the log does not change bins.

## Books (lab/screen.py, hold 168 h)
- xs8 bins among eligible coins (top 50).
- **H** opens long one-week slices in bin 7 (most illiquid) and short slices in bin 0. **L** is the reverse.
- Size 1 / (168 x K), with K = mean slices opened per hour over discovery.
- Universe hedge, tier costs, funding.
- Two books (trials): illiq/H and illiq/L.

## Stages
1. **Discovery** 2021-01-01..2023-12-31. Pass if both hold:
   - 1x NW t (lag 10) >= 2;
   - 2x mean > 0.
2. **Validation** 2024-01-01..2025-06-30, for discovery passers only. Pass if the 1x mean is > 0 with t >= 1.5.
3. **Holdout:** not read (spent at program level, `docs/GATES.md`). A validation passer becomes a candidate for a forward
   paper lane under a new id.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean, NW t, Sharpe, max drawdown, gross and cost;
  - per year;
  - trimmed mean (10 best and 10 worst days removed).
- Correlation with, and residual against, R226's `qv_lvl` H book (long high volume), built the same way with a 168 h
  hold. This shows whether Amihud adds anything beyond inverse volume.

## Multiplicity
- Trials = 2.
- Program trials before: 9,471,901 (after R235).

## Expectations
- **Most likely NULL.**
  - Within the top 50 by volume, illiquidity differences are small.
  - R226 found no volume-level premium.
- **If anything, H earns.** The illiquid coins earn a premium, and short-side borrow is free on perps.
- Risk: illiquid coins are the squeeze-prone ones, so the drawdown matters as much as the mean.
