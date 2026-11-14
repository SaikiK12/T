# FINDINGS: dvolvrp_v1 (R411). The 30-day crypto variance premium is real but has shrunk to a few vol points

**A measurement, 0 trials, gate 0. No decision and no trade.**

DVOL at the start of each day is compared with the realized volatility of the next 30 days, from the Binance perp's
hourly returns.
- The run: `run.log`, 2026-11-05 20:59 UTC, PREREG `36bc2decce6e`, 8 inputs matched. One run.
- Results: `results/summary.json` and `results/days.csv`.

## DVOL minus the next 30 days' realized volatility (vol points)

| Coin | Days | Mean DVOL | Mean RV30 | Mean gap | Median | NW t (lag 30) | Share > 0 | 5th pct | Worst | 2021-23 / 2024-26 |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 1,897 | 60.0 | 51.9 | **+8.15** | +8.62 | 5.50 | 74% | −17.0 | −51.5 | +12.5 / **+3.8** |
| ETH | 1,927 | 74.1 | 68.6 | **+5.54** | +6.09 | 2.59 | 67% | −26.4 | −98.0 | +9.8 / **+1.1** |

**Short variance swap struck at DVOL**, (DVOL² − RV30²) / (2·DVOL) per unit of vega:

| Coin | Mean | Median | NW t | Share > 0 | Worst | 2021-23 / 2024-26 |
|---|---|---|---|---|---|---|
| BTC | +6.16 | +7.80 | 4.40 | 74% | −69.1 | +9.6 / +2.7 |
| ETH | +2.90 | +5.77 | 1.27 | 67% | −151.9 | +6.1 / −0.4 |

**Mean gap by calendar year:**

| Year | 2021 (from 03-25) | 2022 | 2023 | 2024 | 2025 | 2026 (to 09-01) |
|---|---|---|---|---|---|---|
| BTC | +16.8 | +14.3 | +7.0 | +6.1 | +3.8 | +0.7 |
| ETH | +11.0 | +13.3 | +5.6 | +2.3 | −1.4 | +3.2 |

## Reading
- **The premium exists at the 30-day tenor and is larger than at one week.**
  - DVOL beat the next 30 days' realized volatility on 74% of BTC days (+8.2 vol points) and 67% of ETH days (+5.5).
  - R409's weekly hold had mean IV − RV of +0.85 (BTC) and −1.89 (ETH), and medians of +4.3 and +2.4.
- **It has been shrinking for five years.**
  - BTC fell from about +17 vol points (2021) to +4 (2025) and +1 (2026 to date).
  - In 2024-26 the ETH variance swap is slightly negative (−0.4).
  - Any option-selling lane should expect the recent level, not the full-sample mean.
- **The tails are the risk.** The worst 30-day windows lost 51 (BTC) and 98 (ETH) vol points against DVOL. The ETH
  variance swap's mean is under half its median because of them.
- **It is not a trade by itself.**
  - No variance swap is listed on Deribit.
  - Collecting the premium means selling options and hedging them, with spreads, fees and hedge turnover (R409:
    about 56-59 bp a week at 1x for the weekly straddle).
  - A monthly straddle pays the option-side costs once a month, not every week, and its gamma, and so its hedge
    turnover, is lower. Its gross premium per month at the recent +2 to +4 vol points is roughly 50-90 bp (vega of an
    ATM 30-day straddle ≈ 0.23% of spot per vol point). That is a rough check, not a measured result.
  - This is item 43 (weekly vs monthly). It would be a new lane, gate 0, and its PREREG must use the recent level.
- **Program context.** This round adds no trials. The read is against 9,784,334 program trials, as a description of a
  known economic premium, not a searched pattern.
