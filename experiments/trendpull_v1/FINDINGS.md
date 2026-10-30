# FINDINGS: trendpull_v1 (R284). Visser's trend pullback adds a little on world indices, not enough to count, and loses on crypto perps

**Verdict: NULL (8 trials, gate 0).** No cell reaches p ≤ 0.05/8 = 0.00625.

**IDX (10 world indices, 2001-2026):**
- All four cells have a positive excess over the asset's average hold: +0.20% to +0.73% per trade.
- t is 0.71 to 1.31; the best p is 0.096.
- Both halves are positive in every cell.
- Being in a rising 200-day trend is worth about nothing by itself here (trend-state excess +0.02% at 63 days, −0.02%
  at 21 days). So the reset entry is what adds the little there is.

**CRYPTO (556 Binance perps with a year of history, 2021-2026):**
- All four cells lose: net −1.7% to −10.2% per trade at 1x, excess −2.4% to −8.2%.
- The typical trade is worse than the mean: median excess −8% to −23%.
- The means are not significantly negative either: t −0.36 to −0.82, because there are only 20 entry quarters and
  coins move together inside a quarter.
- Being above a rising 200-day average is itself a bad sign on perps: the trend-state excess is −9.5% at 90 days and
  −3.5% at 30 days. The reset entry is 1-3% better than that, still below the coin's average day.

**Reproduce**
- prereg sha a73d4940, frozen before the first statistic.
- Run `python scripts/run_trendpull.py`. It takes about 80 s, and its log is in `run.log`.
- `results/inputs.csv` has the sha256 of all 1,466 files read (10 Yahoo index files, 900 hourly kline files and their
  funding files). Their combined digest is in `results/summary.json` (7de6101f29b7…).
- `results/cells.csv` has one row per cell. `results/trades.csv` has one row per trade.
- Tests: `tests/test_trendpull.py` covers the signal, the next-open entry, funding, one position per asset and the
  cluster t, on synthetic data.

## The 8 cells
Costs per round trip at 1x are 2 bp for IDX and 14 bp for CRYPTO; CRYPTO is also net of funding. "Excess" is the
trade's return minus the mean of every eligible day's hold on the same asset. t is clustered by entry quarter (CR1).
The pass bar is p ≤ 0.00625.

| Universe | k | H | Trades | Assets | Net % 1x / 2x / 3x | Excess % | t | p | Hit | Median % | Early / late excess % | Trend-state excess % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IDX | 0.25 | 63 | 368 | 10 | 2.57 / 2.55 / 2.53 | +0.73 | 1.11 | 0.136 | 0.67 | 3.03 | +1.24 / +0.35 | +0.02 |
| IDX | 0.25 | 21 | 761 | 10 | 1.01 / 0.99 / 0.97 | +0.41 | 1.31 | 0.096 | 0.63 | 1.19 | +0.55 / +0.30 | −0.02 |
| IDX | 0.5 | 63 | 486 | 10 | 2.21 / 2.19 / 2.17 | +0.38 | 0.71 | 0.241 | 0.67 | 2.65 | +0.59 / +0.21 | +0.02 |
| IDX | 0.5 | 21 | 1,113 | 10 | 0.80 / 0.78 / 0.76 | +0.20 | 0.79 | 0.216 | 0.61 | 1.13 | +0.33 / +0.10 | −0.02 |
| CRYPTO | 0.25 | 90 | 781 | 286 | −9.00 / −9.14 / −9.28 | −6.62 | −0.52 | 0.70 | 0.28 | −28.4 | −6.05 / −6.79 | −9.54 |
| CRYPTO | 0.25 | 30 | 1,437 | 319 | −1.67 / −1.81 / −1.95 | −2.42 | −0.36 | 0.64 | 0.35 | −8.85 | −5.35 / −1.66 | −3.46 |
| CRYPTO | 0.5 | 90 | 881 | 294 | −10.25 / −10.39 / −10.53 | −8.19 | −0.82 | 0.79 | 0.29 | −28.9 | +2.78 / −12.28 | −9.54 |
| CRYPTO | 0.5 | 30 | 1,823 | 328 | −3.28 / −3.42 / −3.56 | −4.25 | −0.81 | 0.79 | 0.33 | −10.0 | −4.81 / −4.08 | −3.46 |

The halves split at 2014-01-01 for IDX and 2024-01-01 for CRYPTO. Worst trades: −26% to −37% on IDX; −100% to −114%
on CRYPTO (a coin that went to near zero, with funding on top, in unlevered accounting).

**Robustness of the best IDX cell (k 0.25, H 63):**
- Without its five best trades, the excess is +0.40%. Without its five worst, +1.08%. The median excess is +1.16%.
- By index: ^NDX +2.29%, ^GDAXI +2.09%, ^HSI +1.22%, ^GSPC +1.18%, ^DJI +0.84%, ^N225 +0.48%, ^FTSE +0.41%,
  ^AXJO +0.29%, ^RUT −1.07%, ^STOXX50E −1.26%.
- By year, the excess is negative in 2001-02, 2006, 2011, 2015, 2018-20 and 2022: the years a trend broke soon after
  the entry.

**CRYPTO by entry year (k 0.25, H 90):**

| Year | Trades | Mean net % | Median net % | Excess % |
|---|---|---|---|---|
| 2021 | 33 | −35.3 | −34.7 | −30.6 |
| 2022 | 20 | −8.5 | −34.1 | −8.5 |
| 2023 | 131 | +0.6 | −14.7 | +0.5 |
| 2024 | 354 | +1.2 | −25.6 | +5.5 |
| 2025 | 186 | −40.6 | −45.7 | −36.9 |
| 2026 | 57 | +25.7 | −10.7 | +15.1 |

The median is negative every year. The positive years are carried by a few large winners.

## Reading
- **Indices: the direction Visser describes, too small to count.**
  - +0.4% to +0.7% per trade over a random entry at a 3-month hold, +0.2% to +0.4% at 1 month.
  - The best cell has t 1.11 over 82 quarters. Reaching t 2 at the same effect would take about (2/1.11)² ≈ 3.2 times
    as many quarters: about 80 years of index history.
  - These index years were read before (R239, R247), so this is gate 0 anyway.
- **Crypto: a long-horizon trend filter picks the wrong coins.**
  - On perps, being above a rising 200-day average forecasts a below-average next 1-3 months. This agrees with R229
    and R242 (daily trend, NULL net).
  - The reset entry does not fix that. It is 1-3% better than buying any day of the trend, and still 2-8% worse than
    the coin's average.
  - The opposite trade (short the reset) is not supported either: t is −0.36 to −0.82. It would be a new lane with a
    new id, on a sample nobody has read.
- **Against the program:** 8 trials on top of 9,478,412 (`registry.program_trials()`). The best IDX cell, p 0.096,
  is ordinary for a search of this size.

## What happens next
- **No forward lane** (no pass, per the PREREG).
- **No reserved read.** Only a CRYPTO pass would have earned one, and the rule needs a year of history before its
  first signal, so 2020 alone could not test it.
- `docs/VIDEO_DIG.md` and methods row M277 are updated with this result.
