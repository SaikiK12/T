# PREREG: mlrank_v1 (R299). Do machine-learned rankings of the daily panel make a tradeable cross-sectional book? (M042)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R299 (Claude block R280-R299, claimed on issue #7 on 2026-10-22 before this freeze).
- **Method M042:** ML cross-sectional rankers (ridge, gradient boosting, a composite) on many features.
  - The old session's version used 13 price features: 0 of 390 megascan cells passed (R161), and a ridge and GBM
    composite had rank IC 0.01-0.04 and lost net (R162).
  - The daily panel adds funding on six venues, OI, positioning, basis, the Korean premium and caps. No lane has
    combined them.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_mlrank.py`, tested on synthetic panels in `tests/test_run_mlrank.py`:
  - features do not change when later rows change;
  - ranks are centred and missing values are neutral;
  - targets: exit at the last close in the hold, funding over the hold, no full hold at the panel's end;
  - each model recovers a planted linear signal;
  - the walk-forward never trains on a target that ends within a day of the month it predicts;
  - legs, with ties broken at random, not by symbol;
  - the book and the window masks;
  - end to end: a planted signal is found and a null is not;
  - the plumbing run blanks returns.

  It calls `verify()` on this file first and checks every input's sha256 against the block below. It reuses
  `costed`, `turnover`, `series_stats` and `weekly_grid` from `scripts/run_lotcap.py` (R298, frozen).
- **Libraries:** scikit-learn 1.9.1 (`HistGradientBoostingRegressor`), installed in the venv on 2026-10-22 for this
  lane. Its version is written into the summary.
- **Execution mode: API.** 30 names a leg, rebalanced daily or weekly.
- **Gate: 0, on seen data.**
  - Most features were read one at a time on these years: R222 (MAX, momentum, premium), R238 (weekly momentum,
    MAX, IVOL, funding slope), R245 (reversal), R276 (funding level), R282 (age, size, vol_mcap, oi_mcap, wicks,
    venue breadth, venue funding gaps, Korean premium) and R211/R234 (positioning).
  - The combination and its out-of-sample rankings are new; the windows are not blind.

## What the author has seen
- **The lanes above in full,** including R282's rank ICs (age +0.053, vol_mcap −0.068, size +0.046, oi_mcap −0.078,
  wick_30d −0.036, n_venues_7d +0.034 at 24 h), its books by year, and R298's result that the lottery cluster's books
  flip sign between 2021-23 and 2024-26.
- **R276's reference:** Binance 3-day funding, rank IC −0.038 at 168 h.
- **Feature coverage in the top 150, by year** (no returns): OI and positioning cover about 44% of rows from 2022
  (5% in 2021); Coin Metrics' free-float cap 66-90%; MEXC funding only from 2025.
- **A plumbing run on the real panel, before this freeze** (`--plumbing`, with returns blanked), which printed counts
  only:
  - 2,098 days, 2021-01-02 to 2026-09-30;
  - a median of 150 names, at least 89 on any day from 2022;
  - 57 prediction months;
  - rebalances: 729 discovery / 1,003 validation days at 1 day, 104 / 142 weeks at 7 days;
  - feature coverage within the universe:
    - 0.97-1.00 for the price, volume, funding, wick, venue and age features;
    - 0.88 for basis and spot share, and 0.93 for the venue funding gap;
    - 0.32-0.39 for OI and positioning, and 0.33 for the Korean premium;
    - 0.83 for size and 0.82 for vol_mcap; oi_mcap 0.33.

  No return, prediction, statistic or model fit was produced.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
```

## Data and timing
- **The panel** (`lab/daily.py`): row D is the decision at 00:00 UTC on day D. It holds the 24 hours that end then.
  - A row exists only when the perp traded.
  - It has no row before 2021-01-02 (2020 is reserved) or after 2026-09-30.
- **The universe on row D:** perps with `rank_qvol30` ≤ 150 that traded on row D.
- **Features** use rows up to D, on a calendar of days (a missing row is a gap in a rolling window).
- **Entry and exit:**
  - Entry is row D's close.
  - A hold of h days exits at the last close in rows D+1..D+h. With none (the perp stopped trading), the return is
    0.
  - It pays (long) or receives (short) the funding settled in rows D+1..D+h.

## Features (27 point-in-time; "all" adds 3)
Each is ranked across the universe on its row into [−0.5, 0.5]. A missing value is set to 0 (neutral).

- **Price:**
  - rev1 (row D's log return);
  - mom7, mom30, mom90 (summed log returns; mom90 needs 60 rows);
  - vol30 (standard deviation);
  - max7 (largest daily return);
  - range7 (mean daily high/low range);
  - illiq30 (mean |return| / quote volume).
- **Volume:**
  - qvol_trend (7- over 30-day mean volume);
  - qvol30 (level);
  - taker7 (taker-buy share − 0.5);
  - tradesize7 (volume per trade).
- **Other single-coin features:**
  - wick30 (mean of the up-wick minus the down-wick against the mark);
  - fund3, fund30 (funding sums);
  - premium (last hour);
  - basis (perp over spot);
  - spot_share (spot over perp volume, 7 days).
- **OI and positioning:**
  - oi_chg7 (log change);
  - oi_qvol (OI over 7-day volume);
  - top_ls_pos and ls_acc (logs, last hour);
  - taker_ls7 (mean log taker buy/sell ratio).
- **Venues:**
  - fund_gap7 (7-day sum of the mean venue-minus-Binance funding gap over Gate, MEXC, dYdX, Hyperliquid, KuCoin,
    Kraken);
  - n_venues;
  - kimchi7 (Upbit's relative premium, 7-day mean).
- **Age:** log(1 + days since the first Binance bar). Coins trading at the panel start share the maximum.
- **"all" only (vintage, Coin Metrics):** size (log free-float cap), vol_mcap (30-day volume over cap), oi_mcap.

## Target and models
- **The target on row D** is the long's net return over the hold (return − funding), ranked across the universe into
  [−0.5, 0.5].
- **Walk-forward fit:**
  - Each month from 2022-01, a model is fit on every universe row with D + h + 1 day ≤ the month's first day
    (purged, one day of embargo, expanding from 2021-01-02).
  - It then predicts every universe row of that month.
  - A month with fewer than 1,000 training rows is skipped. None is expected from 2022.
- **The three models:**
  - **ridge:** least squares with an L2 penalty of 0.01 × (training rows), no intercept.
  - **ic:** each feature weighted by its mean daily correlation with the target over the training days (days with at
    least 30 names).
  - **gbm:** `HistGradientBoostingRegressor` with learning rate 0.05, 200 iterations, 15 leaves, 1,000 rows per leaf,
    L2 1.0, no early stopping, seed 299.

## Books
- **Legs:** at each rebalance, with n ≥ 30 names predicted, k = floor(n / 5):
  - long the k highest predictions, short the k lowest;
  - ties break by a seeded random order (seed 299), never by symbol (R298's lesson).
- **Rebalancing:**
  - h = 1: every day from 2022-01-01;
  - h = 7: every 7th day from 2022-01-01, held 7 days.
- **Weights:** equal within a leg, 1 unit a side.
- **Per period:** gross = mean long (return − funding) + mean short (−return + funding).
- **Costs (API, per side):**
  - 8.5 / 17 / 25.5 bp at 1x / 2x / 3x;
  - charged on turnover from the previous period's end weights;
  - drift inside a period is ignored.

## The family (12 trials)
model {ridge, ic, gbm} × horizon {1 d, 7 d} × feature set {pit, all}.

## Windows (by decision; a period counts only when D + h is inside the window)
- **Training only:** 2021.
- **Discovery:** 2022-01-01..2023-12-31.
- **Validation:** 2024-01-01..2026-09-30.

## Statistics
Per book and window, at 1x / 2x / 3x net and gross:
- the mean per period, bp/day and %/yr, the median and the hit rate;
- the mean without the 10 best periods, and the best 10 periods' share of the sum;
- the annual Sharpe;
- the Newey-West t on a calendar grid of periods, with lag 5 for days and 2 for weeks.

## Decision
- **The pick:** the book with the highest discovery net 1x t, among those with a positive discovery mean.
- **The pick passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best periods is positive.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. One validation read, no second pick.
- **What a pass earns:**
  - **A forward paper lane** with its own id and PREREG. Its model is frozen as fitted at the end of 2026-09, refit
    monthly by the same rule, on MEXC prices where the coins list.
  - **A reserved-batch read** of the same rule, if a later batch can compute its features.
    - The 2020 rows lack OI and positioning, and most venues.
    - The pit set without those features would be the candidate.

## Reported (not decided on)
- **Rank IC:** each book's out-of-sample daily rank correlation of prediction and target, per window (mean and NW t,
  lag max(5, 2h)).
- **All minus pit:** the paired net 1x difference per model and horizon. Does the vintage cap data add anything?
- **The linear models' average weights per feature** (ridge coefficients, IC weights).
- **Per book and window:** the long and short legs' means, names per leg and turnover.
- **Hansen SPA and White's reality check** over the 12 books, per window:
  - net 1x summed onto the weekly grid;
  - stationary bootstrap, 2,000 draws, mean block 4 weeks, seed 299.

## Outputs
- `results/summary.json` (every number above, the inputs' hashes, the scikit-learn version);
- `results/periods.csv` (every book's periods);
- `results/rank_ic.csv` (daily rank IC per book);
- `run.log`, and FINDINGS.md with 1x/2x/3x costs read against `registry.program_trials()`.

## Power (written before the result)
- **Books:** as in R298, with 2.75 years of validation and the 2.0 bar.

  | Annual net Sharpe of the pick | 0.5 | 1.0 | 1.5 | 2.0 |
  |---|---|---|---|---|
  | P(validation t ≥ 2.0) | 12% | 37% | 69% | 91% |

- **Rank IC:** about 150 names a day and 1,003 validation days. A mean daily rank IC of 0.01 with a daily standard
  deviation near 0.1 gives a t of about 3. The IC itself is easy to detect.
- **The binding question** is whether it survives costs and the squeeze days (R282, R298).
- **Turnover:** a daily ML book that replaces a third of its names each day trades 4/3 of a unit and pays about
  11 bp/day at 1x API. The weekly books pay about a seventh of that per day.

## Known limits (written before the result)
- **Seen data.** See the gate above.
- **Vintage.** The "all" set's caps are Coin Metrics' latest vintage. The pit set exists so a result can be read
  without them.
- **Free exits.** A perp that stops trading exits at 0 return for that hold. Its delisting price is unknown.
- **Coverage.** OI and positioning cover a third of the universe. Their weights mix "has metrics" with the metric
  itself.
- **Fixed settings.** The hyperparameters are fixed, not tuned. Tuning would add trials that are not counted here.
- **Prices.** The books use Binance prices and the funding the panel holds; MEXC execution is not checked.
- **Squeezes.** Short legs are not covered. R298 found that covers changed little in 2021-23.

## Multiplicity
- 12 trials, one pick, one validation read. One registry row with 12 trials.
- SPA over the 12 is reported per window.
- The result is read against `registry.program_trials()` in FINDINGS.
