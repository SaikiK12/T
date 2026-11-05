# PREREG: dvolvrp_v1, Deribit's 30-day implied volatility against the realized volatility that follows

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R411
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); claimed on #7, comment 6669179798
- **Date registered (UTC):** 2026-11-05
- **Method:** M477 (`docs/IMPROVEMENTS_20261105.md`, item 41)

## Question
How large, how often positive and how stable is the 30-day crypto variance risk premium: DVOL at the start of each
day against the realized volatility of the next 30 days, BTC and ETH, 2021-03 to 2026-09?

This is a measurement. It decides nothing and earns nothing. It sizes the premium that a 30-day option sale could
collect, beside R409's weekly one.

## Data (gate 0: both series are seen)
- **DVOL:** `data/deribit/dvol_BTC.parquet` and `dvol_ETH.parquet`, Deribit's hourly OHLC, from 2021-03-24.
  - The value at day d 00:00 UTC is the close of the bar that opens at d − 1 h.
  - Bars before 2021 are dropped on load; 2020 is reserved.
- **Realized volatility:** the Binance USDT perp, 1-minute closes on the hour (`data/klines_1m/BTCUSDT.parquet`,
  `ETHUSDT.parquet`).
  - RV30(d) = √(8760 / 720 · Σ r²) · 100, over the 720 hourly log returns in [d, d + 30 d), with zero mean.
  - A day with any missing hour is skipped.
- **Window:** days d from 2021-01-01 with d + 30 d ≤ 2026-10-01. In practice DVOL starts 2021-03-25.
- **Prior reads:**
  - R209 read DVOL minus the *trailing* 30-day RV as a direction timer: DVOL was above trailing RV on 82% of BTC days,
    by 8.6 vol points on average.
  - R409 read the weekly hold's IV minus RV from option flow.
  - No lane has compared DVOL with the realized volatility that *follows* it.

## Measures (all reported)
- **gap** = DVOL − RV30, in vol points.
- **varswap** = (DVOL² − RV30²) / (2 · DVOL), in vol points: the P&L of a short variance swap struck at DVOL, per unit
  of vega notional.
- **For each measure and coin:**
  - mean, median, share > 0, 5th percentile and minimum;
  - Newey-West t with lag 30 (daily windows overlap);
  - means by half: days 2021 to 2023, and days 2024 to 2026-09.
- **Also:** means of DVOL and RV30, and the gap's mean and share positive by calendar year.

## Costs and trials
- **No costs:** this is not a trade. A variance swap is not listed on Deribit, and the option sale that would collect
  the premium is R409 and R410.
- **Trials:** 0. The registry row is a measurement.

## Inputs frozen with this file
```inputs
bfe549bbfa16e35872dc77f269c936908b29c4e846ed3c62c606f4dfb31460d1  scripts/run_dvolvrp.py
7df0959df85c12323c948e6301b3a5d7f1a05c4464e534197fa546f800a8c665  scripts/run_optflow.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
71d38f83f20280519b2e10ecabaf90ed42d99c7fbb5cdd7e0cded42d49437aee  data/deribit/dvol_BTC.parquet
d966bc0c02c07b8533888eb2f366ea8159b4a9f5fa1d83fdb552fa9d4212575e  data/deribit/dvol_ETH.parquet
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
```
