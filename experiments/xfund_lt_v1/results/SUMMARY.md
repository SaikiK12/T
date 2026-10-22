# xfund_lt_v1 (R288): PASS (gate 0)

- **Family:** 6 books; 195 coins on 2+ venues (binance 195, dydx 91, gate 194, hyperliquid 100, kucoin 186, lighter 195, mexc 117).
- **Reality check:** the family's max-t null (blocks of 10 days) has its 95th percentile at 2.00.
- **Survivors (all gates):** mexc+lighter L14d th5% K20, gate+lighter L14d th5% K20, kucoin+lighter L14d th5% K20, binance+lighter L14d th5% K20.
- **Prereg sha:** 80e6023d9a6c. Costs 6, 11, 16 bp per leg per side at 1x/2x/3x; hurdle 4.13%/yr.

## Venue sets

| Set | Lookback | From | Coins ever eligible | Mean coins per day at or above threshold |
|---|---|---|---|---|
| binance+lighter | 14 d | 2025-02-07 | 152 | >=5%: 40.1 |
| gate+lighter | 14 d | 2025-02-07 | 150 | >=5%: 41.2 |
| hyperliquid+lighter | 14 d | 2025-02-07 | 97 | >=5%: 30.5 |
| mexc+lighter | 14 d | 2025-05-12 | 106 | >=5%: 39.5 |
| kucoin+lighter | 14 d | 2025-02-07 | 150 | >=5%: 47.0 |
| dydx+lighter | 14 d | 2025-02-07 | 36 | >=5%: 9.4 |

## Top 15 by t (1x)

| Book | From | 1x %/yr | 2x | 3x | Sharpe | t | NW t | RC p | Halves bp/day | 2025+ bp/day | Trimmed | Max DD | Funding share | Held | Trades | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mexc+lighter L14d th5% K20 | 2025-05-12 | +6.20 | +5.00 | +3.79 | +5.83 | +6.88 | +6.77 | 0.0005 | +1.94 / +1.46 | +1.70 | +1.60 | -0.2% | 0.94 | 20.0 | 305 | **yes** |
| gate+lighter L14d th5% K20 | 2025-02-07 | +4.78 | +3.57 | +2.35 | +5.11 | +6.56 | +7.62 | 0.0005 | +1.65 / +0.97 | +1.31 | +1.32 | -0.4% | 1.04 | 19.8 | 364 | **yes** |
| kucoin+lighter L14d th5% K20 | 2025-02-07 | +5.57 | +4.20 | +2.84 | +4.90 | +6.28 | +6.71 | 0.0005 | +1.68 / +1.37 | +1.52 | +1.51 | -0.5% | 1.04 | 19.8 | 408 | **yes** |
| binance+lighter L14d th5% K20 | 2025-02-07 | +4.53 | +3.32 | +2.11 | +4.33 | +5.55 | +6.55 | 0.0005 | +1.45 / +1.04 | +1.24 | +1.24 | -0.9% | 1.03 | 19.8 | 363 | **yes** |
| hyperliquid+lighter L14d th5% K20 | 2025-02-07 | +3.53 | +2.01 | +0.49 | +3.65 | +4.69 | +7.34 | 0.0005 | +1.01 / +0.93 | +0.97 | +0.96 | -0.3% | 0.97 | 19.5 | 455 | no |
| dydx+lighter L14d th5% K20 | 2025-02-07 | +2.65 | +1.96 | +1.27 | +0.26 | +0.34 | +1.11 | 0.7041 | +1.11 / +0.35 | +0.73 | +0.70 | -9.0% | 0.90 | 12.9 | 207 | no |

## Bottom 5 by t (1x)

- gate+lighter L14d th5% K20: +4.78%/yr, t +6.56
- kucoin+lighter L14d th5% K20: +5.57%/yr, t +6.28
- binance+lighter L14d th5% K20: +4.53%/yr, t +5.55
- hyperliquid+lighter L14d th5% K20: +3.53%/yr, t +4.69
- dydx+lighter L14d th5% K20: +2.65%/yr, t +0.34

## Books that clear the reality check

- **mexc+lighter L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': True, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
- **gate+lighter L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': True, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
- **kucoin+lighter L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': True, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
- **binance+lighter L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': True, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
- **hyperliquid+lighter L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': False, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
