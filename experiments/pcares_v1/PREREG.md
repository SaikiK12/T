# PREREG: pcares_v1 (R287). PCA residual reversion on the top-50 Binance perps, hourly (M298)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R287 (Claude block R280-R299, claimed on issue #7 on 2026-10-21). **Method:** M298.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_pcares.py`. It calls `verify()` on this file first and records every input file's sha256.
- **Source of the idea:** Avellaneda and Lee (2010), "Statistical arbitrage in the US equities market", Quantitative
  Finance 10(7). Raised in the comment dig (`docs/COMMENT_DIG.md`, Quant Stack Exchange): trade the residual of a
  factor model instead of predicting prices.
- **Gate:** 0. Every year read here (2021-01..2026-09) has been read by earlier crypto lanes.
- **Execution mode:** API (hourly decisions, many orders a day). Not tradable by hand.

## What the author has seen
- **R250** pairs (distance and Engle-Granger, top-20/top-50, daily formation, 7-day trading): NULL. Gross was near
  zero, and 59-78% of trades ended at the week end without reverting.
- **R245** 1-day and 7-day cross-sectional reversal in liquidity terciles: NULL.
- **R222** residual momentum (daily, slow): NULL.
- **R263** 5,472 single-coin chart rules on 1 h to 1 d bars, Bollinger and RSI fades included: one strategy goes on
  to batch 1.
- **R246** hourly ICT levels: NULL.
- **R185** gross atlas: short-horizon price views, with no factor residual among them.
- No statistic of a PCA factor residual, its s-score or an eigenportfolio has been computed in this lab. The author
  has not looked at hourly residual returns.

## Data
- **Bars:** `data/klines_1h/<SYMBOL>.parquet` for every file whose name ends in `USDT`. Delisted symbols are included.
  - Rows with open time from 2021-01-01 00:00 UTC to 2026-09-30 23:00 UTC. Earlier rows are dropped on load, because
    2020 is reserved (`docs/GATES.md`).
  - A bar is valid if count > 0 and close > 0.
  - The return of hour h is r(h) = close(h) / close(h−1) − 1 when bars h and h−1 are both valid. Otherwise it is
    missing.
- **Excluded symbols** (not crypto, or not a free-floating coin), fixed before any data was read:
  - every name in `experiments/venue_gap_v1/results/tradfi_symbols.json` (sha256 af7b1a0f…983ea): stocks, ETFs,
    indices, metals and commodities;
  - USDCUSDT, PAXGUSDT, XAUTUSDT, BLUEBIRDUSDT and FOOTBALLUSDT.

  A few memecoins share a ticker with a stock in that file (for example CATUSDT and PENGUSDT), and they are excluded
  with it.
- **Funding:** `data/fundingRate/<SYMBOL>.parquet` (t, rate). A rate settled at time F is charged to the weight held
  over the hour bar that ends at F, rounded to the nearest whole hour. A long pays a positive rate. A symbol without a
  file pays none.

## Model (re-fit once per UTC day d, from data before d)
1. **Window:** W_d is the 1,440 hours (60 days) before d's 00:00.
2. **Universe:** U_d is the 50 symbols with the largest summed quote volume over the 720 hours before d.
   - Only symbols that are not excluded qualify.
   - A symbol also needs a return in every hour of W_d, and a nonzero standard deviation of those returns.
   - Ties go to the alphabetical order of the symbol.
   - If fewer than 50 qualify, U_d is all of them, and the count is reported.
3. **PCA:**
   - Standardize each U_d return series over W_d: subtract its mean and divide by its standard deviation (ddof 1).
   - Take the eigenvectors v_1..v_K of the K largest eigenvalues of their correlation matrix.
   - The eigenportfolio weights are Q_k,i = v_k,i / sd_i.
   - The factor returns are F_k(h) = Σ_{i∈U_d} Q_k,i r_i(h). A missing r_i(h) counts as 0 in F.
4. **Betas:** regress each r_i on [1, F_1..F_K] over W_d by OLS, giving β_i,1..β_i,K. The intercept is fitted and then
   dropped.
5. **Residuals and their sum:**
   - For the hours from d's 00:00 − (L−1) h to d's 23:00, ε_i(h) = r_i(h) − Σ_k β_i,k F_k(h).
   - X_i is the running sum of ε_i over those hours.
6. **s-score at a decision hour h of day d** (the close of bar h):
   - Fit an AR(1) to the L most recent X_i points, ending at h: the L−1 pairs (x, y) = (X(j−1), X(j)).
     - b = cov(x, y) / var(x);
     - a = ȳ − b x̄;
     - ζ = y − a − b x;
     - v = mean(ζ²).
   - If 0 < b < 1 and v > 0, then m = a / (1 − b), σ_eq = sqrt(v / (1 − b²)) and **s = (X(h) − m) / σ_eq**. A shift of
     X by a constant leaves s unchanged.
   - Otherwise s is undefined. It is also undefined if any ε in the L window is missing.
   - **Fast enough to trade:** b < exp(−2 / L). That is, the mean-reversion time −1/ln b is under half the window.

## Rule (per variant)
**Coin state** p_i ∈ {−1, 0, +1}, decided at the close of every hour h from 2021-03-03 00:00 UTC, with the model of
day(h):
1. **Forced exit:** p = 0 if i is not in U_day(h), or if s is undefined.
2. **Exit band:** a long exits (p = 0) when s ≥ −0.5. A short exits when s ≤ +0.5.
3. **Entry:** if p is now 0 and the reversion is fast enough, s ≤ −e opens a long and s ≥ +e opens a short. This can
   happen in the same hour as an exit.

**Book weights** w(h) from p(h). The book does not trade within the hour.
- **dollar:** if longs and shorts are both open, each long gets +1/(2 n_long) and each short −1/(2 n_short).
  Otherwise the book is flat.
- **factor** (Avellaneda-Lee hedge):
  - If any position is open, u = p / Σ|p|.
  - w = u − Σ_k (Σ_i u_i β_i,k) Q_k, with Q_k set to 0 off U_d. This removes the book's exposure to the K
    eigenportfolios.

**P&L of bar h+1:**
- **Gross:** Σ_i w_i(h) r_i(h+1). A missing r counts as 0; that coin's position is closed at the next decision,
  because its s is then undefined.
- **Funding:** the funding settled at the end of bar h+1, charged to the weights w(h).
- **Cost:** c × Σ_i |w_i(h) − w_i(h−1)|, charged when bar h+1 starts. Here c = 7 bp per side at 1x (R275's taker
  fee plus spread), 14 bp at 2x and 21 bp at 3x.

Hours are summed into UTC days. The last bar is 2026-09-30 23:00.

**Variants:**
- K ∈ {1, 3, 5};
- L ∈ {72, 168} hours;
- e ∈ {1.25, 2.0};
- hedge ∈ {factor, dollar}.

The exit band (0.5), N = 50, W = 60 days and the daily re-fit are fixed. **Trials: 3 × 2 × 2 × 2 = 24.**

## Windows
- **Discovery:** 2021-03-03 .. 2023-12-31.
- **Validation:** 2024-01-01 .. 2026-09-30, with halves 2024-01-01 .. 2025-06-30 and 2025-07-01 .. 2026-09-30. The
  second half is the spent holdout, so all of this is gate 0.

## Test
1. **Reality check (White, studentized)** over the 24 discovery series of daily net returns at 1x.
   - Statistic: max_j sqrt(n) mean_j / sd_j.
   - Null: a stationary bootstrap of the demeaned series (block 10 days, B = 2,000, seed 287), as in R263.
   - Gives rc_p.
2. **Selected variant j*:** the largest studentized discovery mean at 1x.
3. **PASS** if all of these hold:
   - rc_p < 0.05;
   - j*'s validation Newey-West t (lag 10, `lab.stats.newey_west_t`) at 1x is ≥ 2.0;
   - j*'s validation mean at 2x is > 0;
   - j*'s mean at 1x is > 0 in both validation halves.

**Verdict:**
- **PARTIAL** on a pass. Gate 0, so j* becomes a candidate for a later reserved batch: 2020, with Jan-Feb as the
  warm-up and 81 symbols. It also earns a forward paper lane with a new id.
- **NULL** otherwise.

**Power:** validation has about 1,004 days. A t of 2 is reached with 80% power at an annual Sharpe of about 1.7
(2.84 / sqrt(1004/365)). Avellaneda and Lee report net Sharpe of about 1.1-1.4 on US equities, falling after 2002.
For a smaller edge this lane is a futility screen.

## Reported (not decided on)
- **Per variant and window:**
  - gross, cost and net per day at 1x/2x/3x in bp;
  - Newey-West t at 1x;
  - annual Sharpe at 1x;
  - turnover and gross exposure per day;
  - positions opened, and mean holding hours;
  - break-even cost per side (gross / turnover);
  - share of positive days.
- **For j*:**
  - net at 1x per calendar year;
  - the five best days' share of the summed net;
  - the five best coins' share of the gross.
- **Read against** `registry.program_trials()`.

## Outputs
`experiments/pcares_v1/results/`:
- `variants.csv` (one row per variant and window);
- `daily.csv.gz` (daily gross, cost, funding and net at 1x per variant);
- `inputs.csv` (every input file's sha256), and `summary.json` (verdict, rc_p, j*, the validation figures, the
  combined input digest);
- `FINDINGS.md` by hand after the run.
