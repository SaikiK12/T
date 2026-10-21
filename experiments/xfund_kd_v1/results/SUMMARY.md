# xfund_kd_v1 (R277): PASS (gate 0)

- **Family:** 4 books; 873 coins on 2+ venues (binance 873, dydx 231, gate 860, kucoin 642).
- **Reality check:** the family's max-t null (blocks of 10 days) has its 95th percentile at 2.11.
- **Survivors (all gates):** gate+kucoin L14d th5% K20, binance+kucoin L14d th5% K20.
- **Prereg sha:** d399c923455e. Costs 7, 14, 21 bp per leg per side at 1x/2x/3x; hurdle 4.13%/yr.

## Venue sets

| Set | Lookback | From | Coins ever eligible | Mean coins per day at or above threshold |
|---|---|---|---|---|
| binance+kucoin | 14 d | 2021-01-22 | 617 | >=5%: 130.4 |
| binance+dydx | 14 d | 2023-12-06 | 71 | >=5%: 17.4 |
| gate+kucoin | 14 d | 2021-01-22 | 597 | >=5%: 127.6 |
| kucoin+dydx | 14 d | 2023-12-06 | 66 | >=5%: 17.3 |

## Top 15 by t (1x)

| Book | From | 1x %/yr | 2x | 3x | Sharpe | t | NW t | RC p | Halves bp/day | 2025+ bp/day | Trimmed | Max DD | Funding share | Held | Trades | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gate+kucoin L14d th5% K20 | 2021-01-22 | +11.76 | +10.34 | +8.92 | +6.08 | +14.51 | +11.41 | 0.0005 | +1.64 / +4.80 | +5.93 | +2.99 | -0.7% | 1.02 | 19.6 | 1153 | **yes** |
| binance+kucoin L14d th5% K20 | 2021-01-22 | +10.80 | +9.36 | +7.92 | +5.26 | +12.56 | +11.17 | 0.0005 | +1.40 / +4.52 | +5.68 | +2.75 | -2.3% | 1.04 | 19.6 | 1168 | **yes** |
| kucoin+dydx L14d th5% K20 | 2023-12-06 | +6.78 | +5.61 | +4.44 | +0.69 | +1.16 | +2.13 | 0.2444 | +1.67 / +2.05 | +1.87 | +1.12 | -6.9% | 0.64 | 15.4 | 471 | no |
| binance+dydx L14d th5% K20 | 2023-12-06 | +8.34 | +7.44 | +6.53 | +0.49 | +0.83 | +1.44 | 0.3568 | +1.32 / +3.24 | +2.75 | +0.85 | -11.2% | 0.41 | 15.5 | 364 | no |

## Bottom 5 by t (1x)

- gate+kucoin L14d th5% K20: +11.76%/yr, t +14.51
- binance+kucoin L14d th5% K20: +10.80%/yr, t +12.56
- kucoin+dydx L14d th5% K20: +6.78%/yr, t +1.16
- binance+dydx L14d th5% K20: +8.34%/yr, t +0.83

## Books that clear the reality check

- **gate+kucoin L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': True, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
- **binance+kucoin L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': True, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
