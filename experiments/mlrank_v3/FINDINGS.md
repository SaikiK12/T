# FINDINGS: mlrank_v3 (R332). On a complete-metrics panel R304's +58.9 bp/day is −16.5, and a rule that only asks "does this row have metrics?" earns +50.3

**Verdict by the frozen rule: NULL (gate 0, on seen data).** The pick fails all three checks. R304's PARTIAL is labelled
`metrics-leak`: the presence book, which holds no model and no feature except whether row D has `oi_usd` on R304's
panel, earns +50.3 bp/day net in validation (t 4.47), about 85% of R304's +58.9.
- **Trials:** 7 (6 family books, 1 diagnostic), gate 0. Program total 9,479,239 + 7 = 9,479,246
  (`registry.program_trials()`); the result does not lean on that count, since the pick loses.
- **Read:** frozen PREREG 7f7118ad, frozen and pushed in 43b3786 before the run. Run 2026-11-02 18:27-18:39 UTC with
  `scripts/run_mlrank3.py` (`run.log`). All 18 inputs matched their frozen hashes. One run; validation read once.
- **The pick:** gbm h7 clean, picked by discovery net 1x t (+1.94), the highest of the six with a positive mean.
- **What changed against R304:** nothing but the metrics columns (`oi_usd`, `top_ls_pos`, `ls_acc`, `taker_ls`). Same
  code, features, models, seeds, windows and costs. On R304's panel a row holds metrics only if the coin was among the
  100 most traded within the following 35 days. This panel holds them for 99-100% of top-150 rows from 2022.

## Result

**The pick: gbm h7 clean (bp/day; t is Newey-West), against R304's**

| Window | Weeks | Gross | Net 1x / 2x / 3x | t at 1x | Without best 10 (bp/week) | Long / short leg (bp/week) | Rank IC | R304 net 1x / 2x / 3x (t) |
|---|---|---|---|---|---|---|---|---|
| Discovery 2022-23 | 104 | +14.6 | +11.9 / +9.3 / +6.7 | +1.94 | +12.3 | +19.3 / +82.6 | 0.131 | +36.0 / +33.4 / +30.7 (+5.99) |
| Validation 2024-01..2026-09 | 142 | −14.4 | −16.5 / −18.7 / −20.8 | −1.02 | −245.7 | −11.7 / −88.9 | 0.151 | +58.9 / +56.8 / +54.6 (+4.21) |

- **The checks:** t ≥ 2.0 at 1x (−1.02: fail), a positive 2x mean (−18.7: fail), a positive mean without the 10 best
  weeks (−245.7 bp/week: fail). The loss grows with cost.
- **The swing is about 75 bp/day** in validation (+58.9 to −16.5) and about 24 bp/day in discovery (+36.0 to +11.9).
- **SPA:** discovery p 0.056 (best book gbm h7), validation p 1.00.
- **Survival flag:** off. Later-delisted coins are 9.6% of the validation universe; the pick's long leg holds 6.7% and
  its short leg 12.7%.
- **The rank IC stays positive** (0.151, Newey-West t 13.7) while the top-fifth/bottom-fifth book loses. The average
  ordering across all 150 names is not what the book trades; this lane did not look at which part of the ranking
  carries the IC.

**All books and the diagnostic (bp/day; t of net 1x)**

| Book | Discovery gross | Discovery net 1x (t) | Validation gross | Validation net 1x / 2x / 3x (t at 1x) | Rank IC disc / valid |
|---|---|---|---|---|---|
| ridge h1 | +14.3 | +1.8 (+0.24) | -3.1 | -14.8 / -26.5 / -38.2 (-1.33) | 0.108 / 0.102 |
| ic h1 | +10.4 | +1.9 (+0.24) | -15.4 | -22.3 / -29.2 / -36.1 (-1.90) | 0.102 / 0.100 |
| gbm h1 | +26.0 | +10.7 (+1.56) | +12.7 | -0.6 / -14.0 / -27.3 (-0.07) | 0.121 / 0.112 |
| ridge h7 | +8.8 | +6.4 (+0.87) | -23.6 | -25.7 / -27.9 / -30.0 (-1.48) | 0.130 / 0.141 |
| ic h7 | +2.2 | -0.1 (-0.01) | -24.8 | -26.7 / -28.6 / -30.5 (-1.55) | 0.122 / 0.141 |
| **gbm h7 (pick)** | +14.6 | +11.9 (+1.94) | -14.4 | -16.5 / -18.7 / -20.8 (-1.02) | 0.131 / 0.151 |
| presence book on R304's panel (diagnostic) | +26.5 | +23.5 (+5.66) | +53.4 | +50.3 / +47.2 / +44.1 (+4.47) | 0.032 / 0.068 |

- **R304's side by side (validation net 1x):** gbm h1 +44.5 → −0.6; gbm h7 +58.9 → −16.5; ridge h1 −12.3 → −14.8;
  ic h1 −22.8 → −22.3; ridge h7 −17.7 → −25.7; ic h7 −27.4 → −26.7. The linear books were losers in both panels. Only the
  GBM books changed, and they changed from large winners to zero or losers.
- **The presence book** (diagnostic, counted, never picked). On R304's panel, hold 7 days, R304's weekly grid: long a
  random fifth of the rows that have `oi_usd`, short a random fifth of those that do not.
  - Validation net 1x +50.3 bp/day (t 4.47), 2x +47.2, 3x +44.1; gross +53.4; the mean without its 10 best weeks is
    +190.6 bp/week. Long leg +202.6 bp/week, short leg +170.9.
  - Discovery net 1x +23.5 (t 5.66), 2x +20.5, 3x +17.5.
  - The frozen rule: validation t ≥ 2, so the look-ahead alone earned money and **R304's result is labelled
    `metrics-leak`.**

## Reading
- **What the data say.** A rule with no model earns 85% of R304's validation net at 1x, and R304's own model, given
  complete metrics, earns nothing. The metrics columns of R304's panel told the model which coins would soon be among
  the most traded, and those coins out-earned the rest. R305's `unexplained` label is now explained.
- **What they do not say.** The presence book is a direct measure of the 35-day rule, but it does not isolate other
  things correlated with having metrics, and it does not show that none of R304's edge came from elsewhere: the
  remaining ~9 bp/day gap (+58.9 against +50.3) is not attributed. What is shown is that, with the leak removed, the
  same model has no net edge on the same days.
- **Power** (as the PREREG): the lane could detect a loss of about half the edge. It found the whole edge gone and a
  small, insignificant loss (t −1.02), so it cannot say the true edge is negative, only that it is not this.
- **Not an edge the other way.** The −16.5 bp/day has t −1.02, which is inside noise, and the mean stays negative
  without the 10 best weeks (−245.7 bp/week). Nothing here suggests trading the opposite side.

## What this changes
- **M042 (ML cross-sectional rankers) is closed on this panel.** R304 gets no forward lane, as the PREREG decided
  before the run. R299 and R304 are explained by the metrics availability, not by features or models.
- **The largest positive in the project was a data leak,** found by a complete refetch and one frozen rerun.
- **Open, not tested here:** every other lane that reads `data/metrics_1h` or the panel's metrics columns inherits the
  same availability rule. How far it reaches depends on how each lane picks rows or coins. The lanes are named in the
  queue row M459; this lane tests none of them.

## Not checked
- Lanes other than R304's family (above).
- Another random seed or feature set for the GBM (R304 and this lane share seed 299).
- The ~9 bp/day gap between R304's pick and the presence book.
- The first rows of 2021, where metrics are thin in both panels.

## Files
- `PREREG.md`, `PREREG.sha256` (frozen), `run.log`
- `results/summary.json`: every book and window, the pick and its checks, SPA, the presence book, the column check,
  both coverage tables, the input hashes and the sklearn version.
- `results/periods.csv`, `results/rank_ic.csv`
- Built for this lane (not in git): `data/metrics_full/metrics_1h/` (`scripts/fetch_metrics_full.py`) and
  `data/daily_v2/` (`scripts/build_daily_v2.py`; manifest sha256 `09ff2747…`).
