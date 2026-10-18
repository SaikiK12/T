# PREREG: battery_v1 (R184)

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R184
- **Owner (single writer):** the session that froze it
- **Program version:** lab/config.py PROGRAM_VERSION 1

## Question
Strategies work for a time, not forever. Can a process that, at each weekly rebalance, picks the strategies that are
currently performing best (using only past data) out of a library of rules mined on an earlier period, earn more after
costs than a turnover-matched random pick from the same library, out of sample, in liquid Binance USDT perpetuals?
Two supporting questions: does recent performance predict the near future better than the distant past (a regime
signature, as opposed to a fixed edge)? and does the whole search procedure, run on circularly shifted returns, produce
the same results (it must not)?

## Universe and data
- Binance USD-M perpetuals from the public archive (data.binance.vision), all 900 USDT symbols including delisted ones,
  hourly bars 2021-01-01 to 2026-09-30. Manifest hashes: klines_1h edd4faaa2cc1, premiumIndexKlines_1h 3345c95cea2c,
  fundingRate e48e89529786 (first 12 hex characters of each manifest sha256).
- Tradable at hour t: top 50 by trailing 30-day quote volume (point in time). 499 columns ever qualify.
- Clock: hourly. A signal at row t uses bars through t; the position earns the return of bar t+1. Higher timeframes
  (4h, daily) become visible only after their bar closes (tests/test_features.py checks no feature reads the future).
- Holdout: rows from 2025-07-01 are not read by any step of this lane (enforced by `research.eval_rules`).

## Rules searched
- 284 feature views from `lab/features.default_specs()` (EMA ratios/crosses/ribbons, RSI, Bollinger z, Donchian, ATR,
  volume and taker imbalance, premium and funding, momentum, calendar, previous-day levels, Asian range, ICT/SMC
  detectors at 1h/4h/1d, market state), binned with fixed edges or cross-sectional ranks. Names sha256 recorded in
  data/research/meta.json.
- A rule: 1-3 conditions (view, bin range) that must all hold, a direction (long or short), a minimum hold in hours.
  Equal weight 1/max(active, 10). Costs: one-way 6/8/12/20 bp by liquidity rank (<=20/<=50/<=100/beyond) plus exact
  funding settlements; baseline multiplier 1x, sensitivity 2x and 3x.
- Stage 1 all single conditions with support between 0.5% and 40% of eligible cells, both directions, holds 4/24/72.
  Stage 2 AND-pairs of the 250 best distinct conditions (at most 6 per view), holds 24/72. Stage 3 the best 400 pairs
  crossed with the 250 conditions. Every rule evaluated is one trial.

## Folds (expanding discovery, never touching later data)
F1 discovery 2021-01-01..2022-12-31, test 2023. F2 discovery ..2023-12-31, test 2024. F3 discovery ..2024-12-31, test
2025-01-01..2025-06-30.

## Scoring and the library
- Per rule: Newey-West t (lag 3) of the mean daily net return in each calendar half-year of discovery. Score = peak
  (max over eras), so a rule that worked in one era counts.
- Placebo: the full search is re-run on returns circularly shifted inside the discovery window (2 replicas per fold).
  Estimated FDR(tau) = mean placebo count with peak >= tau / real count. tau = smallest value on a 0.25 grid with
  FDR <= 0.25 and at least 30 real rules. No such tau means the fold is NULL and stops.
- Library: rules with peak >= tau, greedy de-duplication at absolute daily-return correlation 0.7, at most 2000.
  The library is frozen before the test period is read.

## Analyses, on the frozen library's test-period daily returns only
1. Locality: share of strategies with an episode (60-day rolling t >= 2 for >= 30 days).
2. Persistence: IC(recent trailing window) - IC(window ending 100 days earlier), trailing 40 days, forward 14 days,
   block-permutation null (500, block 14).
3. Policy: lookback L in {30,60,120}, K in {5,10,20}, rebalance H in {7,14}; empirical-Bayes shrinkage of trailing means;
   switch cost 0.0015 per unit of capital moved; baseline = 500 turnover-matched random selections. Primary configuration
   L=60, K=10, H=7. Report t of the difference vs random (Newey-West lag 10), p_random, and the Deflated Sharpe of the
   best configuration over the 18 tried.
4. Placebo libraries (top-N placebo rules, N = real library size) go through the same analyses with the same code.

## Decision rule (what counts as evidence)
A fold is SIGNAL only if all hold: primary-configuration p_random <= 0.05 and mean net daily return above the random mean;
the same under 2x costs; the placebo analyses do not reject (so the procedure has no leak). The lane is SIGNAL if at
least 2 of 3 folds are SIGNAL and the Stouffer combination of the three primary p_random values is below 0.01.
PARTIAL: some folds signal, or only the persistence test rejects. NULL otherwise. Forward paper tickets and the holdout
are only considered after SIGNAL, in a separately registered lane.

## Multiplicity
Trials this lane will run: about 250,000 rules per search x (1 real + 2 placebo) x 3 folds. Program trials so far:
139,377 (R182). The online FDR ledger receives the Stouffer p-value as one test.

## Stop rules
No new features, folds, thresholds, or analyses after seeing results. A bug fix that changes a number is recorded in
FINDINGS with before and after.
