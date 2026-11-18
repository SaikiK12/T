# FINDINGS: cmeterm_grid_v1 (R506). 432 cost- and confidence-aware variants of CME commodity carry, walk-forward

**Verdict: GRID_WEAK.**
- The walk-forward strategy nets **+2.42%/yr** at 1x costs over 2014-01..2026-10, with a Newey-West t of only 0.79.
  It stays positive at 2x (+1.99) and 3x (+1.56).
- Hansen's SPA over the 432 variants gives p = 0.133: the best variant does not beat zero once the search is counted.
- No forward paper lane and no capital study are earned. The PREREG reserves them for GRID_PASS.

- **Registry row:** R506 (trials: 432). Program trials at the read: 9,785,747.
- **Reproduce:**
  - PREREG sha256 `54b727e3…`;
  - code commit `77a143c` (`scripts/run_cmeterm_grid.py`; data loaded by R505's frozen `load()`);
  - data: R505's `data/databento/cmeterm_v3/manifest.csv` sha256 `cb4368c1…`.
- Run on 2026-11-18 by `scripts/run_cmeterm_grid.py run` (41 s), after R505's run. The PREREG and its five input
  hashes were verified first.
- Results: `results/report.json`, `results/grid.csv` (one row per variant), `results/walk_forward_daily.csv`.

## Primary read: walk-forward, 2014-01..2026-10 (12.8 years)
| Costs | Net %/yr | NW t | Sharpe | Max drawdown |
|---|---|---|---|---|
| 1x | **+2.42** | 0.79 | 0.21 | −57.6% |
| 2x | +1.99 | 0.65 | 0.17 | −61.2% |
| 3x | +1.56 | 0.51 | 0.14 | −64.9% |

- Gross is 2.85%/yr, so the 1x cost is about 0.43%/yr. The break-even cost multiple is 6.6: costs are not what limits
  this book.
- Drawdowns are on the running sum of daily returns (R503's engine), not compounded.
- The PREREG's power note applies: over 12.8 years, a true Sharpe of 0.4 gives t ≈ 1.4. A WEAK is weak evidence either
  way.

### By year, with the variant the past picked
| Year | Net %/yr | NW t | Pick (signal / roots per leg / weights / frequency / band / gate) |
|---|---|---|---|
| 2014 | **−28.0** | −2.47 | carry / 2 / ivol / quarterly / off / on |
| 2015 | −0.5 | −0.24 | combo / 3 / ew / two weeks / on / on |
| 2016 | −8.5 | −0.82 | carry / third / ivol / monthly / off / on |
| 2017 | 10.7 | 1.75 | same |
| 2018 | **−18.5** | −1.28 | same |
| 2019 | 3.4 | 0.29 | carry12 / third / ew / two weeks / on / on |
| 2020 | −3.0 | −0.31 | same |
| 2021 | −3.7 | −0.58 | same |
| 2022 | **32.6** | 1.89 | combo / third / ivol / quarterly / off / off |
| 2023 | 6.5 | 0.76 | same |
| 2024 | 14.2 | 1.70 | same |
| 2025 | 10.9 | 1.34 | same |
| 2026 (to 10-30) | 18.4 | 1.53 | same |

- The selection switched five times in its first six years and lost through 2021. From 2022 it settled on the
  quarterly carry-plus-momentum combo and earned in every year.
- 2014 and 2018 hold most of the losses, as in R505: long backwardated energy into the oil collapses.

### Where the walk-forward's gross sits (%/yr)
- **By leg:** long +4.00, short −1.15. The short leg (the most contangoed roots) loses money.
- **By root:** best HO +0.97, SI +0.94, ZW +0.71, NG +0.51, GC +0.50; worst HE −1.46, PL −0.14, CL −0.09, ZC −0.09.

## Across the grid (reported, never chosen)
- **Share of variants with a positive net:** 69% at 1x, 63% at 2x. Costs barely separate variants.
- **R503's own rule** (carry / third / ivol / monthly / off / off) is −0.76%/yr, R505's number, near the bottom.

**Each dimension's levels, mean over every variant at 1x:**
| Dimension | Level: mean net %/yr (share positive) |
|---|---|
| Signal | carry 1.15 (55%); **carry12 3.70 (100%)**; mom12 0.97 (49%); combo 2.08 (74%) |
| Roots per leg | 2: 2.21 (67%); 3: 2.07 (72%); a third: 1.64 (70%) |
| Weights | ivol 1.85 (72%); ew 2.14 (74%); conf 1.93 (63%) |
| Frequency | two weeks 0.96 (61%); monthly 0.54 (47%); **quarterly 4.43 (100%)** |
| Band | off 1.98 (65%); on 1.97 (74%) |
| Cost gate | off 1.85 (66%); on 2.10 (73%) |

- **Confidence weighting did not help.** `conf` (size by how extreme the signal is) has the lowest share of positive
  variants and deeper drawdowns than ivol.
- **The cost gate and the band help a little.** They raise the share of positive variants by 7-9 points and barely
  move the mean, as expected when costs are about 0.4%/yr.
- **The two big levers are slow signals.** The de-seasoned carry (carry12) is positive in all 108 variants. Quarterly
  rebalancing is positive in all 144.

**Is the quarterly lever real, or the calendar?** Exploratory check, run after the read on the same data. It is not a
registered cell, and any later lane must count these 288 extra runs as seen.
- The grid's quarterly signal dates are fixed in March, June, September and December. Rerunning the 144 quarterly
  variants with the other two phases gave:

| Signal months | Mean net %/yr | Share positive | carry | carry12 | mom12 | combo |
|---|---|---|---|---|---|---|
| Mar, Jun, Sep, Dec (the grid) | 4.42 | 100% | 4.81 | 3.46 | 4.07 | 5.36 |
| Jan, Apr, Jul, Oct | 1.73 | 67% | 3.58 | 4.51 | −2.65 | 1.47 |
| Feb, May, Aug, Nov | 2.14 | 80% | 2.58 | 4.75 | −0.80 | 2.01 |

- The registered phase reproduces the grid's 4.42 exactly, and it is the luckiest of the three. About half of the
  quarterly advantage is calendar phase.
- What survives every phase is the de-seasoned carry: 3.5-4.8%/yr. Quarterly plain carry also stays positive
  (2.6-4.8). Momentum does not.

### Best and worst variants (full sample, in-sample by construction)
| Variant | Net %/yr | NW t | 2x | Max drawdown |
|---|---|---|---|---|
| combo / third / ivol / quarterly / off / off (best Sharpe, 0.62) | 6.57 | 2.57 | 6.19 | −26.1% |
| combo / third / ew / quarterly / off / off | 7.18 | 2.61 | 6.81 | −24.7% |
| mom12 / 2 / conf / quarterly / off / off | 8.44 | 2.10 | 8.05 | −53.7% |
| carry / 2 / conf / two weeks / off / off (worst) | −4.32 | −1.21 | −5.05 | −144.7% |

- **Deflated Sharpe of the best variant, deflated by 432 trials: 0.34.** That is the probability that its Sharpe beats
  the best of 432 trials drawn by chance. It is far from 0.95.
- **PBO (CSCV, 16 blocks, monthly nets): 0.42.** Reported only. The PREREG notes that near-twin variants push PBO up
  even when an edge is real.
- **SPA:** consistent and upper p both 0.133. Its best variant was combo / third / ew / quarterly / off / off.
- The ten best variants are all quarterly, and nine of them use the combo.

## What this says, and what it does not
- **Managing costs is not the missing piece.** At 0.4%/yr of cost, every cost lever moves the result by fractions of a
  point. The gross is what decides, and the gross depends on the signal and the calendar.
- **The selection is fragile.** The walk-forward lost 2014-2021 and won 2022-2026. Picking by past Sharpe chased the
  last good variant in the early years. The SPA says the best of 432 is not clearly above zero.
- **A slow, de-seasoned carry is the one pattern that holds across the grid and the calendar.**
  - It is still only 3-5%/yr at about 10% volatility, in sample.
  - Its walk-forward pick (2019-2021) lost money.
  - It is a hypothesis for a new lane, not a finding.
- **The owner cannot hold this book.** R505's minimum capital is about $1M in whole contracts. Micro contracts exist
  for CL, GC, SI and HG only.
- **Not checked:**
  - measured CME spreads (one tick assumed);
  - integer contracts per variant;
  - a broader universe (softs, more metals and energies);
  - the 1990s-2000s, where the published carry edge mostly lives.
- **Days, not months.** The 432 variants ran in 41 s on data that cost about $2.9.

## Next
- No forward lane from this grid.
- **Any follow-up is a new lane**, with these runs and the 288 exploratory phase runs counted as seen:
  - a de-seasoned (12-month) carry read on data nobody has read: earlier years (1990-2010 settlements) or a broader
    universe;
  - with the quarterly phase averaged over, never chosen.
- **It competes for attention with the crypto books.** Those have larger out-of-sample edges and are reachable by the
  owner (`docs/reviews/lane_scan_20261117.md`).
