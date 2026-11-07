# PREREG: brute5k_v1 (R263). 5,472 chart strategies on the top-20 perps, and whether what works now keeps working

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R263 (claimed on issue #7)
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_brute5k.py`
- **Origin:** the owner's request of 2026-10-20:
  - brute-force about 5k strategies, with leverage multipliers;
  - mix in Fibonacci and Monte Carlo;
  - explain why a strategy works now and not before or after, staying close to the charts.

  It also covers queue M204 (Fibonacci), M205-like breakout rules and M228 (stop overlays), and the room's Ask 2 (one
  round with the full trial count).
- **Gate:** 0.

## What the author has seen
- R243 (7 classic rules on 4 h and 1 d bars, all coins): best Supertrend+RSI 1 d t 1.23; fades lost.
- R247/R248: chart rules on FX and indices, NULL. R238: crypto momentum and volatility features paid only in 2021.
- No result for this grammar, this universe or walk-forward selection over chart rules.
- Before writing: data plumbing only, with no returns computed. That covered the regular hourly grid, the top-20
  membership count, and 29 member cells with a missing next return over 2021-2026.

## Universe and accounting
- **Members:** coin s on day d is a member if, at the day's first row, it has `u.rank` <= 20, is in `u.elig`, and is
  not in R216's `tradfi_symbols.json`.
  - A member stays one for the whole day, while still eligible at each row.
  - This uses the daily rank, not the hourly one, so membership does not churn within the day.
- **Weights:** each member coin's position is (rule position in {-1, 0, +1}) / 20. Gross exposure is at most 1.
- **Hourly net:** sum of P x ret minus cmult x sum of |dP| x cmat. That is `slices.run` with `hedge=False` and
  `missing="legacy"`. Three strategies are checked against `slices.run` to 1e-9.
- **Costs:** tier costs at 1x/2x/3x (members are top-20, so 6 bp one-way).
- **Disclosed:** member cells with a missing next return count as 0 (legacy). The run log reports how many are
  exposed.

## Bars
- **Timeframes:** k in {1 h, 4 h, 12 h, 1 d}, UTC-aligned.
  - Bar j covers hourly rows jk..jk+k-1.
  - Its close is the close of the last row. Open, high and low come from the block; volume is the sum of quote volume.
- **A bar's position** is decided at its close and held over rows (j+1)k-1 .. (j+2)k-2, so the first hour earned is
  the one after the close.
- **Indicators:**
  - pandas `ewm(adjust=False)` for EMAs, and Wilder smoothing (alpha 1/n) for ATR and RSI.
  - Rolling windows are in bars.
  - Every rule reads only bars up to the current one.

## Base rules (76 per timeframe)
1. **EMA cross** (9): sign(EMA_f - EMA_s), f in {5, 10, 20}, s in {50, 100, 200}.
2. **Donchian** (3), N in {20, 55, 100}:
   - long on a close above the prior N bars' high, short on a close below their low;
   - exit a long below the prior N/2 bars' low, and a short above their high.
3. **RSI** (9), period in {2, 7, 14}, thresholds (lo, 100 - lo) with lo in {10, 20, 30}:
   - long when RSI < lo, until RSI >= 50;
   - short when RSI > 100 - lo, until RSI <= 50.
4. **Bollinger** (12), z = (close - SMA_n) / SD_n, n in {20, 50}, k in {1.5, 2, 2.5}:
   - fade: long when z < -k until z >= 0, short when z > k until z <= 0;
   - follow: long when z > k until z <= 0, short when z < -k until z >= 0.
5. **Supertrend** (6): the standard rule, ATR period in {10, 14}, multiplier in {2, 3, 4}.
6. **Fibonacci retracement** (18): a close-based zigzag with swing threshold k x ATR(14), k in {2, 3, 5}.
   - When a swing (low L to high H) is confirmed, a long setup is armed.
   - The first close at or below H - e x (H - L), but above H - 0.786 x (H - L), enters long (e in {0.382, 0.5,
     0.618}).
   - The stop is a close below the 0.786 level. The target is a close at or above H + (t - 1)(H - L), t in
     {1.0, 1.272}.
   - Down swings mirror it. A close below the stop level before entry cancels the setup. A newer swing replaces an
     unused setup.
7. **Time-series momentum** (4): sign of the close over n bars ago, n in {12, 24, 72, 168}.
8. **MACD** (3): sign(MACD - signal) with (fast, slow, signal) = (6, 13, 5), (12, 26, 9) and (24, 52, 18).
9. **VWAP band** (12): rolling VWAP of the close weighted by quote volume over n bars, n in {24, 72, 168}.
   - dev = close / VWAP - 1, and z = dev / its rolling SD over n.
   - k in {1, 2}, fade or follow, with the same entries and exits as Bollinger.

## Variants per base rule (72 per base rule, applied in this order)
- **Direction (3):** both; long-only (the positive part); short-only (the negative part).
- **Filter (3):** the filter zeroes a position on bars where it fails.
  - none;
  - trend: longs only when the bar close is above the EMA200 of daily closes as of the last completed day, shorts
    only when below;
  - calm: only when ATR(14)/close is below its median over the prior 180 days of bars.
- **Stop (2):**
  - none;
  - a 2 x ATR(14) trailing stop on closes from the peak (long) or trough (short). Once stopped, the position stays
    flat until the rule's position changes.
- **Total strategies:** 76 x 4 timeframes x 3 x 3 x 2 = **5,472**.

## Walk-forward selection ("what works now")
- At the start of each month, rank strategies by their Sharpe of daily 1x net over the previous L months. Keep the
  top K = 20 with a positive trailing mean, weighted 1/K each, for that month. Fewer than K leaves the rest in cash.
- **Switching cost:** on the month's first day, (1/K) x the sum over added and dropped strategies of their gross
  exposure at the previous month's last row x 6 bp x cmult.
- **L in {3, 6, 12}:** L = 6 is decided; 3 and 12 are reported.
- **Decided out-of-sample window:** 2021-07..2025-06. Every month's selection uses only earlier days.
- **Random-selection null:** 1,000 runs of the same procedure picking K strategies uniformly at random each month.
- **Exploratory, not decided:** 2025-07..2026-09 (spent holdout) and the current selection as of 2026-09-30.

## Decisions
- **Primary (the walk-forward stream, L = 6) passes if all hold over 2021-07..2025-06:**
  - 1x NW t (lag 10) >= 2;
  - 2x mean > 0;
  - 1x mean above the 95th percentile of the random-selection null.

  A pass queues a forward paper lane (new id) for the walk-forward stream. Nothing more.
- **Secondary (the best single strategy):** the strategy with the highest 1x NW t in 2021-07..2023-12. It passes if:
  - White's reality check gives p < 0.05. That uses a stationary bootstrap (mean block 10 days, 500 draws) of
    demeaned daily nets; the statistic is the max over strategies of sqrt(n) x mean / SD.
  - In validation (2024-01..2025-06), 1x NW t >= 1.5 and the 2x mean > 0.

## Monte Carlo on leverage (reported, not decided)
- **Inputs:** the walk-forward stream (L = 6) and the best single strategy, each over its decided window.
- **Method:** stationary bootstrap (mean block 20 days), 10,000 one-year paths. Leverage in {1, 2, 3, 5, 10}
  multiplies daily returns. A day with L x r <= -1 is ruin.
- **Reported:**
  - median and 5th percentile terminal wealth;
  - P(max drawdown >= 50%), P(ruin) and P(year ends below 1);
  - the growth-optimal leverage, which maximizes the median log terminal wealth over 0.5..20 in steps of 0.5.
- **Caveat:** daily, not intraday, so liquidation inside a day is not modelled.

## "Why now" (reported)
- **Persistence:** each month, the Spearman correlation across strategies between trailing 6-month Sharpe and that
  month's mean net (an information coefficient). Reported as the mean IC with NW t over months.
- **Families:** per half-year, the mean net of each family's strategies. Per year, each family's share of the
  walk-forward picks.
- **Regime:** monthly correlation of each family's mean net with BTC's monthly return, its absolute value, and BTC's
  monthly realized volatility.

## Multiplicity
- Trials = 5,472 strategies + 3 selection lookbacks = **5,475**. Leverage is sizing, not a trial.
- Program trials before: 9,472,061 (after R262).

## Expectations
- **Most single strategies lose after cost.** The 1 h ones turn over too fast.
- **The best of 5,472 will show a t near 3-4 in discovery by luck alone.** The reality check should not reject.
- **The walk-forward:** chart-rule performance does rotate with regimes (trend in 2021 and late 2024, mean reversion
  in 2022-23 chop). But one month of persistence after a 6-month look is a weak signal. Most likely NULL, or a pass
  on t that fails the random-selection null.
