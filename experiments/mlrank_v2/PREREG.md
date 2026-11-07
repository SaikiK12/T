# PREREG: mlrank_v2 (R304). R299's rankers without the features whose coverage leaks survival (M042)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R304, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Method M042:** ML cross-sectional rankers, as in R299 (`experiments/mlrank_v1`).
- **Owner (single writer):** the Claude session that froze it.
- **Why this lane exists.** R299's GBM passed its frozen rule (validation net 1x +55 bp/day, t 4.0), with a daily rank
  IC of 0.155-0.19. The audit then found a survivorship leak in three of its inputs:
  - The KuCoin, Kraken, MEXC, Upbit and Bithumb histories were fetched for markets live at download time, and
    Hyperliquid's for its listed perps. Only Gate and dYdX include delisted contracts.
  - So a coin Binance later delisted has almost none of those venues. Among the top 150 (rows with a close):

    | Year | KuCoin funding: survivors / later delisted | Upbit price | Mean `n_venues` |
    |---|---|---|---|
    | 2021 | 53% / 2% | 42% / 5% | 1.29 / 0.49 |
    | 2022 | 73% / 5% | 40% / 4% | 1.93 / 0.88 |
    | 2023 | 89% / 5% | 40% / 3% | 2.60 / 1.06 |
    | 2024 | 95% / 3% | 39% / 3% | 3.73 / 1.51 |
    | 2025 | 93% / 0% | 42% / 0% | 4.52 / 1.88 |

  - `n_venues`, `fund_gap7` (a mean over six venues' funding gaps) and `kimchi7` (Upbit/Bithumb) therefore tell a model
    which coins will die. A coin usually falls before Binance delists it.
- **This lane:** the same family, code and decision rule, with those three features removed. Plus one diagnostic, the
  GBM on those three features alone, to measure how much the leak can earn.
- **Code:** `scripts/run_mlrank2.py`, tested in `tests/test_run_mlrank2.py`:
  - the feature lists and the trial count;
  - the later-delisted perps and each leg's share of them;
  - on a synthetic panel where only `n_venues` knows who dies, the leak-only model's short leg holds the dying coins
    and the clean model's does not;
  - the plumbing run blanks returns.

  It imports everything else unchanged from `scripts/run_mlrank.py` (R299, frozen): features, targets, universe,
  ranks, models, walk-forward, legs, book, report, windows and `decide`. It calls `verify()` on this file first and
  checks every input's sha256 against the block below.
- **Execution mode: API,** as R299.
- **Gate: 0, on seen data.** R299 read these windows with these 24 features plus the three dropped ones.

## What the author has seen
- **R299's full results:**
  - all 12 books, the per-feature rank ICs and the pick's legs;
  - the GBM books grossed +58 to +66 bp/day in validation, and the ridge and IC books lost (−8.8 to −24.2 bp/day).
- **The coverage table above, and the plumbing run of this script** (counts only, returns blanked):
  - Among the 24 kept features, OI and positioning cover 45-54% of survivors' rows and 25-35% of later-delisted
    coins' (2022-25).
  - The metrics files were fetched for all 900 archive perps, delisted ones included, and the files are missing at
    similar rates (later delisted 50%, survivors 45%). So that gap is in Binance's archive, not in the download list.
    These features are kept.
  - Binance spot (`basis`, `spot_share`) covers 79-99% of survivors and 52-97% of later-delisted coins. A spot
    delisting is public when it happens, so that gap is point-in-time. Kept.
- **R282** read `n_venues_7d` and the Korean premium one at a time (rank IC +0.034 and −0.005); `n_venues_7d` did not
  pass there.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
ee4bbe450e70307481f39d75e86b12e09a792475c2cc4b2f62efd36e799ee403  scripts/run_mlrank2.py
```

## Features
- **Clean set (24):** R299's point-in-time list minus `n_venues`, `fund_gap7` and `kimchi7`:
  - price and volume: rev1, mom7, mom30, mom90, vol30, max7, range7, illiq30, qvol_trend, qvol30, taker7,
    tradesize7, wick30;
  - funding and basis: fund3, fund30, premium, basis, spot_share;
  - OI and positioning: oi_chg7, oi_qvol, top_ls_pos, ls_acc, taker_ls7;
  - age.
- **Leak set (3), diagnostic only:** n_venues, fund_gap7, kimchi7.
- R299's vintage features (size, vol_mcap, oi_mcap) are not used. Their market-cap coverage also differs by survival
  (52-85% against 81-91%).
- Ranks are taken across the day's universe, centred, and a missing value is 0 (R299's `stack`).

## The family (6 trials) and the diagnostic (1)
- **Family:** model {ridge, IC-weighted, GBM} × hold {1 day, 7 days}, on the clean set. These are R299's models,
  holds, hyperparameters and walk-forward, unchanged:
  - monthly refits from 2022-01;
  - training on decisions whose hold ends at least a day before the month starts;
  - the GBM with learning rate 0.05, 200 trees, 15 leaves, at least 1,000 rows a leaf.
- **Diagnostic:** GBM, hold 7 days, leak set only. It is reported and never picked.
- **Trials: 7** (the diagnostic is counted).

## Books, costs and windows
R299's, unchanged:
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
- **Survivorship flag (decided now).** If the pick's short leg holds later-delisted perps at more than twice their
  share of the universe in either window, the verdict is reported as survivorship-suspect, whatever it is.
  - A later-delisted perp is one whose last close is more than 30 days before the panel's last day.
  - A flagged pass earns nothing until the flag is explained.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once. No second pick.
- **What a pass earns:**
  - a place in a reserved batch (2020 rows exist for about 80 perps, so a 2020 read is only partial);
  - a forward paper lane with its own id on MEXC prices.
- **What a NULL means:** R299's PARTIAL came from the leak. M042 is closed for this panel and these features.

## Reported (not decided on)
- **Per book and window,** gross and net at 1x/2x/3x, each with:
  - the mean, bp/day, median, hit rate and annual Sharpe;
  - the mean without the 10 best periods;
  - the legs' means, names per leg and turnover;
  - the daily rank IC with its Newey-West t.
- **Hansen SPA and White's reality check** over the 6 family books per window:
  - each book's net 1x summed onto a 7-day grid from the first prediction day;
  - 2,000 stationary-bootstrap draws, mean block 4 weeks, seed 304.
- **Each book's share of later-delisted perps per leg and window,** against their share of the universe.
- **R299 against R304:** the same model and hold with and without the three features. The difference is what the leak
  earned.

## Outputs
`results/summary.json`, `results/periods.csv`, `results/rank_ic.csv`, `run.log`, and FINDINGS.md with 1x/2x/3x
costs read against `registry.program_trials()`.

## Power
R299's GBM books had validation t of 3.9-5.9 with the leak. Without it, a pick with a true annual net Sharpe of 1.0
has about 37% power at the 2.0 bar over 2.75 years (R302's table).

## Known limits
- **Seen data:** R299 read these windows.
- **Other survivorship.** The OI and positioning gap above is archive-side, and the market-cap features are dropped.
  Other forms of survivorship are not ruled out. The leg shares make the residual visible.
- **Prices:** Binance only; MEXC is not checked here.

## Multiplicity
- **Program trials before this lane:** 9,478,673 in `registry.program_trials()` today (R299-R302 included). With
  R303's 10 (frozen separately) it is 9,478,683.
- **7 trials, one pick, one validation read.** One registry row with 7 trials.
