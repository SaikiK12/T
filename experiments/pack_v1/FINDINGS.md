# FINDINGS: pack_v1 (R194)

**Verdict: NULL.** A pack of 252 cells that pay per trade with limit entries is, in a book, a long position in alts:
beta to BTC 1.0 unhedged, and once hedged the BTC short eats the gross. No holdout shot is spent.

- **Registry row:** R194 (trials: 18 books)
- **Reproduce:** prereg sha 64cb4135; `python scripts/run_pack.py`; cells from maker_v1 results.

## Numbers (2021-01-01 to 2025-06-30, limit entries 1 sigma, fee 2 bp, exit at market after h)
252 cells, 247 of them long; horizons h 1: 20, h 4: 61, h 12: 74, h 24: 80, h 72: 17.

| slots | hedge | net / yr 1x | t | max DD | beta to BTC | gross | entry | exit | hedge PnL | hedge cost |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | none | +32.7% | 0.77 | 154% | 1.02 | 48.2% | 3.3% | 12.2% | 0 | 0 |
| 20 | none | +31.5% | 0.80 | 161% | 1.02 | 48.9% | 3.7% | 13.7% | 0 | 0 |
| 40 | none | +22.6% | 0.64 | 165% | 0.93 | 44.4% | 4.7% | 17.1% | 0 | 0 |
| 10 | BTC | -21.4% | -0.73 | 281% | 0.18 | 48.2% | 3.3% | 12.2% | -36.6% | 17.5% |
| 20 | BTC (primary) | -25.4% | -0.98 | 266% | 0.20 | 48.9% | 3.7% | 13.7% | -38.6% | 18.3% |
| 40 | BTC | -33.1% | -1.47 | 256% | 0.20 | 44.4% | 4.7% | 17.1% | -34.5% | 21.2% |

Primary per year (1x): 2021 +141%, 2022 -85%, 2023 -19%, 2024 -61%, 2025H1 -92%. Mean exposure 0.87 long; about 10
fills a day at 20 slots.

Reading: gross 49%/yr with 0.87 net long exposure in a period when BTC's daily returns summed to about 50%/yr. Gross plus
hedge PnL is about +10%/yr, less than the 17%/yr the entries and exits cost, before the hedge's own cost. Against BTC the
pack has no alpha even before costs (gross minus beta x BTC is about -3%/yr).

## Cost sensitivity
Unhedged, slots 20: +31.5% (1x), +17.7% (2x), +4.0% (3x), all with t below 1. Hedged: -25%, -57%, -89%.

## What this does not show
- The priority order (min per-trade net over the two periods) favored long horizons, whose per-trade nets carry market
  drift: the top 20 are almost all h 24 and h 72 longs. A score per holding hour would favor h 1-4.
- The hedge is BTC at beta 1, rebalanced at every close (its cost equals a taker leg per trade); alts' beta to BTC is
  above 1, so some market exposure remains.
- maker_v1's statement that signals add +13 bp per trade over a no-signal limit is per trade and equal-weighted; in a
  book with limited slots it does not show up as alpha.

## Next
The per-trade gains from limit entries in raw cells are market exposure plus the bounce. The alpha question is in excess
terms (long the cell, short the universe), where atlas_v1 found that cross-sectional edges decayed. Context gating
(atlas_ctx, R192) is the remaining route for these cells; a neutral pack would need longs and shorts from the same hour.
