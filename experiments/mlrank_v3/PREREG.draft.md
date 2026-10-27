# PREREG: mlrank_v3 (R332). R304's rankers on a panel whose metrics were fetched without a look-ahead (M042)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

Draft: this file becomes `PREREG.md` at the freeze. Until then `python -m lab integrity` would read an unfrozen
`PREREG.md` without a registry row as an error (SIDECAR_MISSING).

- **Registry id:** R332
- **Id history:** drafted as R309 in the Claude block R300-R319 claimed on issue #7 on 2026-10-22; Codex's
  rounds took R309-R331 on its branch first, so this lane takes the next free id after the merge.
- **Method M042:** ML cross-sectional rankers, as in R299 and R304.
- **Owner (single writer):** the Claude session that froze it.
- **Why this lane exists.** R304's weekly GBM passed its rule (validation net 1x +58.9 bp/day, t 4.21), and R305 could
  not explain it. Building its forward lane, the author found how the panel's metrics columns were fetched:
  - `data/metrics_1h` (open interest, top-trader and all-account long/short ratios, taker buy/sell ratio) was built by
    `lab/flow.py` with `needed_days()`. A coin's day was fetched only when the coin was in the old research set's top
    100 by volume at some hour of that day or of the next 35 days.
  - So in the panel, a row with metrics says that the coin will be among the most traded within 35 days. That is a
    look-ahead. In R304's universe (top 150 by `rank_qvol30`), 2022-26:

    | Rank band | Rows with `oi_usd` |
    |---|---|
    | 1-50 | 98-100% |
    | 51-100 | 24-28% |
    | 101-150 | 6-9% |

  - Binance's archive has the files: the daily metrics folders of ETCUSDT, AAVEUSDT and SOLUSDT run without a gap from
    2025-09-02 to 2026-10-21, while `data/metrics_1h` stops at 2025-09-13 (ETC) and 2026-09-22 (AAVE).
  - **A correction.** R304's PREREG said the metrics gaps were "in Binance's archive, not in the download list". That
    was wrong. The gaps are in the download list.
- **This lane:** R304's family, code and decision rule on a panel rebuilt with complete metrics. Plus one diagnostic:
  the presence book on R304's panel, which measures what the look-ahead alone earns.
- **Code:**
  - `scripts/fetch_metrics_full.py`: Binance's daily metrics files for every day a universe row reads. For each row D in
    the top 150 by `rank_qvol30` (computed from klines only), that is days D-10..D-1, because row D holds day D-1 and
    the features read up to seven rows back. Reduced to hours by `lab.flow.reduce_metrics`, unchanged, into
    `data/metrics_full/metrics_1h/`.
  - `scripts/build_daily_v2.py`: `lab/daily.py`'s `build`, unchanged, on a shadow root that links every folder of
    `data/` except `metrics_1h`, which links to the complete one. It writes `data/daily_v2/panel.parquet`.
  - `scripts/run_mlrank3.py`: imports R304's `build`, `analyze`, `STRATS` and `label` (`scripts/run_mlrank2.py`, frozen)
    and R299's helpers (`scripts/run_mlrank.py`, frozen), unchanged. It adds the presence book, the column check and
    the coverage table. It calls `verify()` on this file first and checks every input's sha256 against the block below.
  - Tested in `tests/test_run_mlrank3.py`:
    - the fetch plan's ten-day window;
    - the shadow root;
    - the presence book reads row D only, and starts on the first prediction day;
    - the column check and the coverage bands.
- **Execution mode: API,** as R299 and R304.
- **Gate: 0, on seen data.** R299, R304 and R305 read these windows with these features.

## What the author has seen
- **R299, R304 and R305's full results:**
  - R304's pick, `gbm h7 clean`, made +58.9 bp/day net in validation, with a long leg of +310 bp/week and a short leg
    of +117.
  - R305 found it is not age, the risk features or beta.
- **The coverage table above.**
- **The fetch's counts** (`data/metrics_full/metrics_1h/manifest.json`): days needed, listed in the archive, used,
  missing from the archive, and failed.
- **The plumbing run of this script** (column check and coverage only; no return read). [Filled in at the freeze.]
- **The fetch's test on two coins:** for ETCUSDT the complete fetch holds 42,134 hours against 27,350 before. On every
  hour both hold, `oi_value`, `top_ls_sum`, `ls_count` and `taker_ls_vol` are identical.
- **Never computed before the freeze:**
  - a return of any book on `data/daily_v2`;
  - the presence book's return;
  - any statistic that splits returns by whether a row has metrics.

## Inputs (frozen)

```inputs
[filled in at the freeze]
```

## The family (6 trials) and the diagnostic (1)
- **Family:** R304's, unchanged, on `data/daily_v2/panel.parquet`:
  - model {ridge, IC-weighted, GBM} × hold {1 day, 7 days};
  - its 24 clean features: rev1, mom7, mom30, mom90, vol30, max7, range7, illiq30, qvol_trend, qvol30, taker7,
    tradesize7, wick30, fund3, fund30, premium, basis, spot_share, oi_chg7, oi_qvol, top_ls_pos, ls_acc, taker_ls7 and
    age;
  - monthly refits from 2022-01; training on decisions whose hold ends at least a day before the month starts;
  - the GBM with learning rate 0.05, 200 trees, 15 leaves, at least 1,000 rows a leaf, random state 299.
- **The presence book** (diagnostic, reported, counted, never picked):
  - on R304's panel (`data/daily/panel.parquet`), hold 7 days, on R304's weekly grid from 2022-01-01;
  - the score of a universe row is 1 when row D has `oi_usd`, else 0;
  - long the top fifth and short the bottom fifth, with ties in R299's seeded random order. So the long leg is a random
    fifth of the rows with metrics, and the short leg a random fifth of the rows without (when each group holds a
    fifth).
- **Trials: 7.**

## Books, costs and windows
R299's and R304's, unchanged:
- **Universe:** the top 150 Binance perps by trailing 30-day volume with a close on row D.
- **Legs:** long the top fifth of the prediction, short the bottom fifth, equal weights, seeded random ties.
- **Entry and exit:** entry at row D's close; exit at the last close in the hold (none: 0); funding over the hold.
- **Costs:** API 8.5 / 17 / 25.5 bp per side on each rebalance's turnover.
- **Windows:** discovery 2022-01-01..2023-12-31, validation 2024-01-01..2026-09-30. A period counts only when its hold
  ends inside the window.

## Decision
- **The pick:** the family book with the highest discovery net 1x t, among those with a positive discovery mean
  (R299's `decide`).
- **It passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best periods is positive.
- **Survivorship flag:** R304's, unchanged.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once. No second pick.
- **What a PARTIAL earns:** R304's forward lane, built on this panel's code path. Its model is fit on
  `data/daily_v2` and fed live metrics, which are complete like this panel's. It also earns a place in reserved
  batch 2.
- **What a NULL means:** R304's PARTIAL came from the metrics look-ahead or from chance. M042 is closed on this panel.
  R304 gets no forward lane.
- **How the presence book is read** (decided now, reported only): if its validation net 1x t is ≥ 2, the look-ahead
  alone earned money, and R304's result is labelled `metrics-leak` whatever this lane's verdict.

## Reported (not decided on)
- **Per book and window:** R304's report, unchanged.
  - gross and net at 1x/2x/3x, each with the mean, bp/day, median, hit rate and annual Sharpe;
  - the mean without the 10 best periods;
  - the legs' means, names per leg and turnover;
  - the daily rank IC with its Newey-West t.
- **Hansen SPA and White's reality check** over the 6 family books, per window, as R304.
- **The columns that differ** between the two panels (NaN-aware, on the rows both hold). The design expects only
  `oi_usd`, `top_ls_pos`, `top_ls_acc`, `ls_acc` and `taker_ls`.
- **The coverage** of `oi_usd` by year and rank band, in both panels.
- **Side by side:** each family book's validation net 1x against R304's.

## Power
As R304's, from its own run:
- About 1,000 validation days, or 142 weekly periods for hold 7.
- A weekly book with the pick's validation spread (t 4.21 at +58.9 bp/day) would show t ≈ 2 at about +28 bp/day.
- The lane detects a loss of about half the edge. It cannot tell a small loss from none.

## Known limits
- **Seen data:** every window was read by R299, R304 and R305.
- **2021:** Binance's metrics start in December 2021 for most coins. The 2021 training rows have few metrics in both
  panels.
- **Gaps left in the archive:** days missing from Binance's archive stay missing (the fetch's counts). They do not
  depend on the future.
- **Other columns:** the column check shows whether any column besides the five metrics ones changed.

## Outputs
- `results/summary.json`: every book and window, the pick and checks, SPA, the presence book, the column check, both
  coverage tables, the input hashes and the sklearn version.
- `results/periods.csv`: every book's periods (gross, legs, names).
- `results/rank_ic.csv`: the daily rank IC per book.
- `run.log`
- `FINDINGS.md`, with 1x/2x/3x costs, read against `registry.program_trials()`.
