# reserved_batch2 (R391): PASS (gate 0)

- **Family:** 1 books; 28 coins on 2+ venues (dydx 9, kucoin 18, lighter 9, mexc 25).
- **Reality check:** the family's max-t null (blocks of 10 days) has its 95th percentile at 0.85.
- **Survivors (all gates):** kucoin+dydx+lighter+mexc L14d th5% K20.
- **Prereg sha:** 74cfb3e096ca. Costs 7, 14, 21 bp per leg per side at 1x/2x/3x; hurdle 0.0%/yr.

## Venue sets

| Set | Lookback | From | Coins ever eligible | Mean coins per day at or above threshold |
|---|---|---|---|---|
| kucoin+dydx+lighter+mexc | 14 d | 2025-05-12 | 18 | >=5%: 4.8 |

## Top 15 by t (1x)

| Book | From | 1x %/yr | 2x | 3x | Sharpe | t | NW t | RC p | Halves bp/day | 2025+ bp/day | Trimmed | Max DD | Funding share | Held | Trades | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kucoin+dydx+lighter+mexc L14d th5% K20 | 2025-05-12 | +2.48 | +1.93 | +1.38 | +1.67 | +2.01 | +3.90 | 0.0005 | +0.41 / +0.95 | +0.72 | +0.64 | -0.4% | 0.83 | 5.3 | 113 | **yes** |

## Bottom 5 by t (1x)

- kucoin+dydx+lighter+mexc L14d th5% K20: +2.48%/yr, t +2.01

## Books that clear the reality check

- **kucoin+dydx+lighter+mexc L14d th5% K20**: gates {'COST2X': True, 'HALVES': True, 'HURDLE': True, 'NW': True, 'RC': True, 'RECENT': True, 'TRIM': True}
