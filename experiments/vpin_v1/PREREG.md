# PREREG: vpin_v1 (R291). Does order-flow toxicity (VPIN) forecast crypto volatility beyond volume and past volatility? (M085)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R291 (Claude block R280-R299, claimed on issue #7 before the freeze). **Method:** M085.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_vpin.py`, tested on synthetic minute bars in `tests/test_run_vpin.py`:
  - no look-ahead in the hourly features;
  - a planted toxicity-to-volatility link is found out of sample;
  - a null link is not.

  It calls `verify()` on this file first and checks every input's sha256 against the block below.
- **Source:** the owner's reel of 2026-10-21 (instagram.com/reel/DevaMerNUk_, "toxic order flow"). It says market
  makers track VPIN to detect informed traders and pull their quotes before a crash or a spike.
- **The question:** VPIN (Easley, López de Prado and O'Hara 2011, 2012) is said to rise before liquidity crises.
  Andersen and Bondarenko (2014, 2015) answered that on the E-mini, once trades are classified perfectly, VPIN has no
  incremental power for future volatility. They traced its apparent power to bulk volume classification (BVC)
  errors that track volume and volatility.
  - Binance's 1-minute bars carry the taker-buy volume, so crypto lets us run their test with the exchange's own
    trade sides, and with BVC as the contrast.
  - If exact VPIN adds nothing, it is volume and volatility repackaged, and M085 leaves the queue.
  - If it adds, it earns a use as a filter: when to stop resting maker orders, for M227 and M264.
- **Gate:** 0. This lane does no trading. Every year here was read by earlier lanes, and R289 and R290 read these
  1-minute files.

## What the author has seen
- **The 1-minute files:** R289's and R290's PREREGs and results. Those are clock and auction-level trading rules, with
  no volatility forecast and no VPIN.
- **The literature claims above,** and the reel.
- **The runner on synthetic data only** (the tests).
- **Not computed:** no VPIN, bucket, BVC share or volatility forecast on real data.
- **Related lab work:**
  - R209 (`vrp_v1`): implied minus realized volatility as a timing signal, NULL;
  - `docs/VOLATILITY_AND_TAIL_RISK_FORECASTS.md` (literature: HAR is a serious baseline).

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
966602440c3573e677b7578feed150b5065d2062d84869acd54e79ad58af1706  data/klines_1m/SOLUSDT.parquet
097ec5cd95aecea45497c68319d11a4ff2508c980a83c373b5afb4c61e90da13  lab/orderflow.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
2c4e93aa4586f41098ee65e8b097c067d0a368b0d0f49c1c4844628eb176b8f1  scripts/run_vpin.py
```

## Data
- **Coins:** BTCUSDT, ETHUSDT and SOLUSDT, Binance USD-M perpetuals.
- **Bars:** 1-minute bars opening from 2021-01-01 00:00 UTC to 2026-09-30 23:59 UTC. Earlier rows are dropped on load,
  because 2020 is reserved.
  - A bar is valid when count > 0 and close > 0. Invalid or missing bars carry no volume.
- **1-minute return:** log(close_i / close_{i−1}), undefined when either bar is missing.

## VPIN (`lab/orderflow.py`)
- **Volume clock:**
  - The bucket size for every bar of UTC day d is the mean volume of the previous 30 days, over 50. Only days with
    at least 1,200 valid bars count, and at least 20 such days are needed.
  - Bars fill buckets in order, and a bar that straddles a boundary is split in proportion to its volume
    (`volume_buckets`).
  - A bucket is known at the close of the bar in which it fills.
- **Bucket buy share:**
  - exact: the taker-buy volume;
  - BVC: v × Φ(r / σ), where σ is the standard deviation of 1-minute returns over the previous UTC day (at least
    1,000 bars). Neutral (v / 2) where r or σ is undefined.
- **VPIN:** the mean of |2 × share − 1| over the last 50 buckets (`vpin`).
- **At an hour boundary h:** VPIN is the value of the last bucket filled in a bar before h. It is missing when that
  bucket filled more than 1,440 bars before h.

## Hourly forecast set
One row per coin and UTC hour h.

**Target:** realized variance (RV), the sum of squared 1-minute returns scaled to 60 (at least 50 valid).
- **H1:** log RV of hour h.
- **H24:** log of the mean hourly RV over hours h..h+23 (at least 20 defined).

**Base model (HAR with volume and seasonality)**, all from bars before h:
- log RV of hour h−1;
- log mean RV of the last 24 hours (at least 20 defined);
- log mean RV of the last 168 hours (at least 140 defined);
- log of hour h−1's quote volume over the mean hourly quote volume of the previous 720 hours (at least 600 defined);
- log of the last 24 hours' mean quote volume over that same reference;
- 23 hour-of-day dummies and a weekend dummy, plus a constant.

**VPIN models:** the base model plus VPIN at h, exact or BVC.

**Rows:** only rows where the target, every base feature and both VPINs are defined. All models are compared on the
same rows.

## Windows
- **Discovery** (fit): 2021-04-01 .. 2023-12-31.
- **Validation** (out of sample): 2024-01-01 .. 2026-09-30.
- A row belongs to a window only if every target hour lies inside it. Models are fitted once, by OLS, on discovery
  per coin, and the coefficients are fixed for validation.

## Test
- **Loss:** squared error of the log-RV forecast.
- **Per coin and validation hour:** d = e²(base) − e²(base + VPIN).
- **Pooled:** the mean of d across the coins defined at that hour. DM t is the Newey-West t of its mean (lags 24 for
  H1, 48 for H24, in calendar hours; `lab/stats.newey_west_t`).
- **MSE cut:** 1 − Σ e²(VPIN) / Σ e²(base), summed over coins' validation rows.
- **Primary, exact VPIN at H1. INFORMATIVE if all hold:**
  - the discovery VPIN coefficient is positive in all three coins;
  - pooled validation DM t ≥ 2.0;
  - MSE cut ≥ 1%.
- **Verdict:**
  - **PARTIAL** if the primary is INFORMATIVE. That would queue VPIN as a maker-entry filter lane (new id) on the
    recorded tape.
  - **NULL** otherwise. M085 is then TESTED and leaves the queue: exact-side VPIN carries nothing beyond volume and
    volatility, as Andersen and Bondarenko found.
- **Trials:** 4 (exact or BVC × H1 or H24). The other three are reported with the same rule, not decided on.
- **Power:** validation has about 24,000 hours per coin. A 1% MSE cut is the economic floor, set because with that
  many hours a negligible gain can reach t 2.

## Reported (not decided on)
- **Per coin:** the discovery VPIN coefficient and its Newey-West t (same lags), validation DM t, MSE cut, and
  validation R² of each model.
- **Discovery correlations** of exact and BVC VPIN with log relative volume, log RV, and each other.
- **Crash table:** the share of hours whose |log return| exceeds 4 trailing standard deviations (720 h, at least
  600), by decile of exact VPIN at the hour's start, against the same table by decile of relative 24 h volume. Decile
  edges come from discovery per coin; counts are pooled.
- **Read against** `registry.program_trials()`.
- **Costs at 1x/2x/3x:** not applicable, because there are no trades. Any use of VPIN as a filter is costed in its
  own lane.

## Outputs
`experiments/vpin_v1/results/`:
- `summary.json`;
- `hourly.csv.gz` (per coin and hour: the features, both VPINs and the targets).

FINDINGS.md is written after the run.

## Known limits (written before the result)
- **The trade sides are bar totals.** The order of trades inside a minute is lost, so a bucket's split is exact only
  at minute resolution. The 1 s tape is too short to use yet.
- **One reading of VPIN:** 50 buckets a day and n = 50, as in the original papers. Other sizes are not tested.
- **The crash claim is checked only descriptively** (the table). The reel's mechanism (market makers pull quotes)
  needs quote data. Depth history was not kept, and the recorders are weeks old.
- **Volatility, not direction.** VPIN is unsigned. Signed taker imbalance as a direction signal is already covered
  by the atlas (R185) and M264.
