# FINDINGS: tsbattery_v1 (R242). Four crypto time-series rules

**Verdict: NULL.** VOLTREND passed discovery (+6.0 bp/day, t 2.07, alpha t 2.21) and failed validation (+2.0, t 0.52).
WEEKOPEN, FOMC and ETHBTC failed discovery. The holdout was not read.

- **Registry row:** R242 (trials 4). Program trials after it: 9,471,937.
- **Gate:** 0.
- **Reproduce:** prereg sha 63082fdf, frozen in commit 1adb667 before the run. Run `python scripts/run_tsbattery.py`
  (about 30 seconds).
- **Origin:** queue M013, M191, M009, M184.

## Numbers (1x / 2x / 3x; alpha and beta against the equal-weight market)

| Rule | Window | Net bp/day | NW t (1x) | Gross / cost (1x) | Gross / net exposure | Beta | Alpha bp/day (t) | Trimmed |
|---|---|---|---|---|---|---|---|---|
| WEEKOPEN | discovery | +4.4 / +0.5 / -3.4 | 0.54 | 8.2 / 3.9 | 0.85 / -0.04 | -0.20 | +7.1 (0.82) | +4.2 |
| FOMC | discovery | +0.5 / +0.2 / -0.1 | 0.38 | 0.8 / 0.3 | 0.02 / 0.02 | +0.01 | +0.4 (0.27) | 0.0 |
| ETHBTC | discovery | -1.8 / -2.6 / -3.3 | -0.50 | -1.0 / 0.8 | 0.94 / 0.00 | +0.06 | -2.6 (-0.74) | -0.6 |
| VOLTREND | discovery | +6.0 / +5.4 / +4.9 | **2.07** | 6.5 / 0.6 | 0.37 / -0.02 | -0.03 | +6.4 (2.21) | +5.6 |
| VOLTREND | validation | +2.0 / +1.4 / +0.8 | **0.52** | 2.6 / 0.6 | 0.36 / -0.01 | -0.04 | +1.7 (0.43) | +1.2 |

Per year at 1x (bp/day):

| Rule | 2021 | 2022 | 2023 | 2024 | 2025H1 |
|---|---|---|---|---|---|
| WEEKOPEN | +18.6 | -7.6 | +2.1 | | |
| FOMC | +0.7 | +2.4 | -1.6 | | |
| ETHBTC | +7.3 | -9.4 | -3.2 | | |
| VOLTREND | +9.2 | +2.6 | +6.1 | +1.6 | +2.7 |
| Equal-weight market | +51.9 | -36.2 | +25.2 | +6.0 | -34.7 |

FOMC events: 24 in discovery, 12 in validation.

## Cost sensitivity
- **WEEKOPEN** pays 3.9 bp/day at 1x, half its gross, and is negative at 3x.
- **VOLTREND** trades daily but small: 0.6 bp/day at 1x. It kept a positive mean at 3x in both windows, so its
  failure in validation is in the gross (6.5 to 2.6 bp/day).

## Reading
- **VOLTREND is the only rule with a signal.**
  - Positive in all five years, with beta near zero (its long and short books net out).
  - The size is small. At its 0.37 gross exposure, 6 bp/day is about +2%/yr in 2021-23 and +0.7%/yr in 2024-25.
    Scaling exposure up scales the cost too.
  - The validation t of 0.52 is far below 1.5. Like R222 and R229, it says slow trend in crypto perps is weak after
    2023.
- **WEEKOPEN earned only in 2021**, the same pattern as R238's winner tilt.
- **FOMC:** the book is invested about 1 day in 45 and made nothing. 24 events cannot show a small effect either way.
- **ETHBTC:** the alt-season regime was right in 2021 and wrong in 2022-23.

## Not checked
- Other trend lookbacks (7, 90, 180 days) and blends.
- Volatility targets other than 40% per coin.
- FOMC windows after the statement.
- A BTC-only or ETH-only version of any rule.
- The holdout.
