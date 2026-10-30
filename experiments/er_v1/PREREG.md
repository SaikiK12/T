# PREREG: er_v1 (R293). Can tomorrow's efficiency ratio be forecast, and does skipping predicted chop days improve a trend rule? (M314)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R293 (Claude block R280-R299, claimed on issue #7 before the freeze). R292 stays reserved for
  `dealerflow_v1` (M308). **Method:** M314 (new).
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_effratio.py`, tested on synthetic minute closes in `tests/test_run_effratio.py`:
  - the daily path and features see nothing after the day they describe;
  - the gate for a day uses the forecast made the evening before;
  - a planted persistent trend-day regime is found out of sample, and gating improves the rule;
  - an iid regime is not called predictable.

  It calls `verify()` on this file first and checks every input's sha256 against the block below.
- **Source:** the owner's reel of 2026-10-22 (instagram.com/reel/DeF5_5yPtDb). The trader says:
  - they built a logistic regression on 15 measurements of recent price behaviour that predicts the next day's
    efficiency ratio;
  - on one of their NQ strategies, high-efficiency days performed best and low-efficiency days made about a third of
    the money per trade;
  - a gate that skips predicted low-efficiency days "improved almost every performance metric", and the improvement
    "held on two years of data the model never saw".

  The frames show the 15 features and their weights (listed below). The strategy, the threshold and the numbers are
  not shown.
- **The question:**
  1. Is the next UTC day's efficiency ratio predictable from these 15 measurements on crypto perps, out of sample?
  2. Does a gate on that forecast improve a fixed trend rule out of sample?

  The reel's own strategy is unknown, so one plain trend rule stands in for it. It is fixed here, before any number.
- **Gate:** 0. Every year here was read by earlier lanes. R203 (`itsm_v1`) read first hour against last hour on these
  coins, and R289-R291 read these 1-minute files.

## What the author has seen
- **R203** (`itsm_v1`, NULL):
  - the day's first hour does not predict its last hour on Binance perps;
  - BTC gross was −2.2 bp (2021-23) and +0.7 bp (2024-26) per day, with a lean to reversal on a volume clock.

  The rule below (first hour to the day's close) was not computed there.
- **R289-R291 PREREGs and results** on the same 1-minute files:
  - clock and auction-level trading rules (NULL);
  - VPIN as a volatility forecast (NULL).

  The HAR base in R291 showed strong volatility persistence. No efficiency ratio was computed.
- **The reel,** its 15 feature names and weights, and its claim.
- **The runner on synthetic data only** (the tests).
- **Not computed:** no efficiency ratio, feature, forecast or trend-rule return on real data.

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
966602440c3573e677b7578feed150b5065d2062d84869acd54e79ad58af1706  data/klines_1m/SOLUSDT.parquet
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
e110881032024bc2f52a14511c0d3a70a0a444db5b6f4499e31418e7e93c967e  data/fundingRate/SOLUSDT.parquet
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
2c4e93aa4586f41098ee65e8b097c067d0a368b0d0f49c1c4844628eb176b8f1  scripts/run_vpin.py
5f717e2486dc46b600b53330f2e06653e8d3553f80831d957c9bccb317b49740  scripts/run_effratio.py
```

## Data
- **Coins:** BTCUSDT, ETHUSDT and SOLUSDT, Binance USD-M perpetuals, one third of capital each.
- **Bars:** 1-minute bars opening from 2021-01-01 00:00 UTC to 2026-09-30 23:59 UTC (`run_vpin.load_bars`). Earlier
  rows are dropped on load, because 2020 is reserved.
  - A bar is valid when count > 0 and close > 0. Invalid or missing bars are NaN.
  - P(hh:mm) is the close of the bar that opens one minute earlier.
- **Funding:** Binance funding rates (`data/fundingRate`). A position pays side × rate at every settlement strictly
  after entry and at or before exit (`run_clockflow.funding_paid`).

## The efficiency ratio of a UTC day
- **The path:** P(00:00), then the close of every fifth minute (00:05 … 24:00). That is 288 steps of log return,
  where P(00:00) is the previous day's last close.
- **ER** = |Σ steps| / Σ |steps|, over the defined steps. Defined when at least 270 of the 288 steps are.
- **Realized volatility:** sqrt(Σ steps² × 288 / defined steps).
- **The day's close** is P(24:00). Its high and low are the path's max and min.

## The 15 features (the reel's list), each known at the close of day d

| Group | Feature | Here | Reel's weight |
|---|---|---|---|
| What the market just did | Realized volatility | log RV of day d | −0.204 |
| | Today's efficiency | ER of day d | −0.198 |
| | 20-day efficiency | \|log(C_d / C_{d−20})\| / Σ\|daily log returns\| over the 20 days | −0.036 |
| | Variance ratio | variance of 5-day log returns / (5 × variance of daily log returns), last 60 days (at least 50) | −0.101 |
| | False-breakout rate | share of the last 20 days (at least 15) whose path broke the prior day's high or low and closed back inside that range | +0.182 |
| | Distance from the 50-day | log(C_d / 50-day mean close) (at least 45) | −0.198 |
| What it has done lately | Chop run | consecutive days, up to d, that were chop days | +0.065 |
| | 5-day efficiency | as the 20-day, over 5 days | +0.044 |
| | 10-day efficiency | as the 20-day, over 10 days | +0.013 |
| | 20-day mean efficiency | mean ER of the last 20 days (at least 15) | −0.024 |
| | Yesterday's efficiency | ER of day d−1 | −0.200 |
| | Efficiency 2 days ago | ER of day d−2 | −0.135 |
| | Change in volatility | log RV of day d − log of the mean RV of the last 20 days (at least 15) | −0.119 |
| | Chop share, 5 days | share of chop days in the last 5 (at least 4 defined) | +0.009 |
| | Chop share, 10 days | share of chop days in the last 10 (at least 8 defined) | +0.098 |

- **A chop day** has an ER below the median ER of the last 100 days, that day included (at least 60 defined).
- **Point in time:** each feature at row d uses only bars up to P(24:00) of day d.

## Forecast
- **Target:** day d+1 is efficient when its ER exceeds the median ER of that coin's discovery target days.
- **Windows,** by the target day:
  - discovery (fit): 2021-04-01 .. 2023-12-31;
  - validation (out of sample): 2024-01-01 .. 2026-09-30, with halves 2024-01..2025-06 and 2025-07..2026-09.
- **Rows:** only rows with all 15 features and the target defined.
- **Model:**
  - features z-scored per coin with that coin's discovery mean and standard deviation;
  - one pooled logistic regression over the three coins, fitted once on discovery (Newton steps, ridge 0.001 × n on
    the slopes, not the intercept);
  - fixed for validation.
- **Baseline** (reported): the same model on today's ER and the 20-day mean ER only, which is plain persistence.

## The trend rule, and the gate
- **The rule** (fixed before any number, one trade per coin per day):
  - side = sign(P(01:00) / P(00:00) − 1), skipping a zero or undefined move;
  - enter at P(01:01), exit at P(24:00);
  - funding is charged.
- **Ungated book:** the rule on every day.
- **Gated book:** the rule only on days whose forecast is above 0.5. The forecast for day D is the one made at the
  close of day D−1. A day with no forecast is skipped.
- **Book:** each coin's trade on a third of capital. Daily net = gross − funding − 2 × cost × trades / 3.
- **Cost per side:**
  - manual web: 3 bp at 1x, 6 at 2x, 9 at 3x;
  - MEXC API (8.5 bp) reported.

## Decision
- **Predictable** if both hold:
  - the validation AUC of the 15-feature forecast is at least 0.53;
  - the 2.5% bound of its block-bootstrap CI exceeds 0.5. That is 2,000 resamples of 10-day blocks of target days,
    seed 293, because the three coins on a day move together.
- **The gate passes** (PARTIAL for M314) if all hold:
  - predictable;
  - the gated book's validation Newey-West t (lag 10) at 1x is at least 2.0;
  - its validation net at 2x is above 0;
  - each validation half's net at 1x is above 0;
  - its validation gross per trade exceeds the ungated book's (the gate lifts the rule).
- **The rule alone passes** (also PARTIAL, recorded as a rule finding and not as the reel's claim) if the ungated
  book meets the same four book conditions (t, 2x, halves).
- **Verdict:**
  - **NULL** if neither passes. M314 is then TESTED.
  - Predictability without a tradeable gate is still recorded: it is a usable volatility-regime input for other
    lanes.
- **Trials:** 3 (predictability, the ungated rule, the gated rule).

## Reported (not decided on)
- **Forecast:**
  - AUC in discovery and in validation, per coin, and of the baseline;
  - the base rate;
  - the fitted weights next to the reel's (sign agreement).
- **Books:** gross per trade by forecast tercile (cuts from discovery forecasts), discovery and validation.
- **Both books** at 1x/2x/3x and API, by window and half: trades, gross bp per trade, net bp per day, t.
- **Read against** `registry.program_trials()`.

## Outputs
`experiments/er_v1/results/`:
- `summary.json`;
- `daily.csv` (per day: net of both books at 1x, and each coin's forecast).

FINDINGS.md is written after the run.

## Known limits (written before the result)
- **The reel's strategy and market (NQ futures, US hours) are not ours.** One crypto trend rule stands in for it. A
  NULL here does not show the reel's NQ result is false, only that its method does not carry over to crypto perps
  with this rule.
- **The UTC day is a convention** in a 24-hour market, and R290 found no session anchor more structured than random
  clocks.
- **Feature definitions are ours.** The reel names the features but not their formulas, windows or thresholds.
- **Funding at the 24:00 settlement is charged.** An exit a second earlier would avoid it.
- **One threshold (0.5) and one target cut (the discovery median).** Others are not tried.
