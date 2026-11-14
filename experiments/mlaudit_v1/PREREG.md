# PREREG: mlaudit_v1 (R305). What carries R304's pick (M042)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R305, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Method M042:** ML cross-sectional rankers (`experiments/mlrank_v2`).
- **Owner (single writer):** the Claude session that froze it.
- **Why this lane exists.** R304's pick (GBM, 7-day hold, 24 clean features) passed its frozen rule:

  | Window | Net 1x bp/day | t | 2x | 3x | Without 10 best (bp/period) |
  |---|---|---|---|---|---|
  | Discovery 2022-23 | +36.0 | 5.99 | +33.4 | +30.7 | +178.5 |
  | Validation 2024-01..2026-09 | +58.9 | 4.21 | +56.8 | +54.6 | +286.1 |

  A market-neutral +59 bp/day after costs is too large to act on without knowing what earns it.
- **Gate: 0, on seen data.** R299 and R304 both read these windows. Nothing here can promote a book. The labels decide
  only what the next lane tests and on which sample.
- **Execution mode: API,** as R304.
- **Code:** `scripts/run_mlaudit.py`, tested in `tests/test_run_mlaudit.py` (trial count, feature sets, score signs,
  the regression, the labels and the squeeze tail on synthetic data). It calls `verify()` on this file first and checks
  every input's sha256 against the block below. It imports R299/R304's features, targets, universe, ranks, GBM,
  walk-forward, legs, book, report and windows unchanged.

## What the author has seen
- **R304's full results:** all seven books, the SPA, the dead shares (validation: universe 9.6%, pick's long leg 7.1%,
  short leg 13.5%; survivor flag off).
- **A post-hoc look at the pick, run before this freeze** (`results` not kept in the repo; numbers here):
  - **Lag test:** every feature taken one day later. Validation net +62.8 bp/day (t 4.88), discovery +37.9 (t 7.2).
    The edge is not in bar timing.
  - **Permutation importance:** one GBM trained to 2023, scored on 2024-01..2026-09 (base rank IC 0.150). The drop
    in rank IC with each feature shuffled within the day: age .025, range7 .025, qvol30 .022, oi_chg7 .016,
    oi_qvol .015, ls_acc .013, taker_ls7 .008, mom7 .009, rev1 .008; the rest below .007.
  - **Leg profile** (mean centred rank, validation):

    | Feature | Long leg | Short leg |
    |---|---|---|
    | age | +0.21 | −0.22 |
    | vol30 | −0.20 | +0.23 |
    | range7 | −0.21 | +0.30 |
    | wick30 | −0.19 | +0.22 |
    | max7 | −0.14 | +0.22 |
    | illiq30 | −0.13 | +0.10 |
    | tradesize7 | +0.13 | −0.09 |
    | oi_qvol | +0.13 | −0.10 |
    | mom7 | −0.01 | +0.10 |
    | fund3 | −0.08 | +0.10 |

  - The lag test is one more book on these windows. It is counted here (below).
- **R298** (lottery-cluster short) and **R282** (single PIT features) read the MAX and volatility features one at a
  time.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
ee4bbe450e70307481f39d75e86b12e09a792475c2cc4b2f62efd36e799ee403  scripts/run_mlrank2.py
c26f62143723e81458ea0bfff79072ca25557137b88fa727e7439ac0e3b74298  scripts/run_mlaudit.py
```

## Books (6 trials, plus 1 counted from before the freeze)
All on the 7-day hold, R304's universe (top 150 by 30-day volume), quintile legs, seeded tie-breaks, costs and
windows. Discovery 2022-01-01..2023-12-31, validation 2024-01-01..2026-09-30.

1. **Refits** (R304's walk-forward and GBM hyperparameters):
   - `gbm no-age`: the 23 clean features without `age`;
   - `gbm risk-only`: the six risk features `vol30, range7, wick30, max7, illiq30, age`;
   - `gbm no-risk`: the 18 clean features without those six.
2. **Fixed scores** (no fit; signs set by the hypothesis, not by data), on the pick's prediction days:
   - `composite`: mean of `−vol30, −range7, −wick30, −max7, +age` (centred ranks, missing 0);
   - `lowvol`: `−vol30`;
   - `old`: `+age`.
3. **Counted from before the freeze:** the lag-test book above (1).

Total **7 trials.**

## Checks and labels (written before the run)
- **Parity:** the pick is rebuilt and must match R304's validation net 1x (+58.9165 bp/day) within 0.01 bp/day. If
  it does not, the run reports the mismatch and the labels are not used.
- **Beta:** the pick's net 1x per rebalance (non-overlapping 7-day holds) regressed by OLS on the same holds'
  equal-weight universe return net of funding, and separately on BTCUSDT's. Alpha in bp/day, beta, alpha t. Also each
  leg on the equal-weight universe.
- **Squeeze tail:** in each window, the largest 7-day move of a short-leg name and the share of rebalances with a
  short name up more than 50% and more than 100%.
- **Yearly:** net 1x bp/day by calendar year for every book.
- **Labels** (from validation net 1x bp/day; R304 pick = 58.9165):
  - `age_carried`: `gbm no-age` < 0.5 × the pick (29.46);
  - `risk_carried`: `gbm risk-only` ≥ 0.7 × the pick (41.24);
  - `known_anomaly`: `composite` ≥ 0.7 × the pick;
  - `beta`: the pick's alpha t < 2.0 against either the equal-weight universe or BTC;
  - `unexplained`: none of the four.
- **What each label sends where** (fixed now):
  - `known_anomaly` or `risk_carried`: the next test is the fixed `composite` score on the reserved 2020 sample (it
    needs only price, volume and listing date, all held for 2020) in the next scheduled batch, with a forward paper
    ticket on MEXC from the first free day. No new fit.
  - `beta`: the pick is recorded as a market bet, not an edge. No batch slot.
  - `age_carried` alone: the next lane checks `age` for censoring (coins trading at the panel start all rank oldest)
    before any batch slot.
  - `unexplained`: the GBM pick goes to the batch as frozen, with a forward paper ticket, and the audit stays open.
- Every FINDINGS line reports 1x/2x/3x and reads the program's trial count from `registry.program_trials()`.

## Not done here
- No new sample, no 2020 rows, no MEXC-only coins, no post-archive rows.
- No hyperparameter change, no new feature, no sign chosen from returns.
