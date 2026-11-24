# Is dYdX a fourth floorless venue? A premise check before any lane, 2026-11-24

- **Question.** R525's design gap pays on every floorless × floor pair. My notes listed dYdX ("cross markets have a 0%
  default rate") as a possible fourth floorless venue next to Kraken, Bitfinex and Deribit. Before registering a
  lane (M469 is queued), does the premise hold?
- **This is descriptive.** No strategy statistic was computed. The funding series were read before by R277/R288 and
  the 2026-11-04 audit.

## What the venue says (public indexer, 2026-11-24)
- **296 markets: 116 cross, 180 isolated** (`https://indexer.dydx.trade/v4/perpetualMarkets`, field
  `defaultFundingRate1H`).
  - Cross markets carry 0, except 2. That is premium-only, a floorless design, and dYdX's docs say the same.
  - Isolated markets carry 0.0000125 an hour. That is the 0.125 bp/h floor of governance vote 220, i.e. 10.95%/yr:
    a floor, like Binance's.
- **Volume:** $42M in 24 h across all 296 markets. Only 3 markets trade more than $1M a day, and the median market
  trades about nothing.

## Funding against Binance on the coins both list (`data/dydx_hist/open`, `data/fundingRate`)
Median per coin, %/yr:

| Type | Year | Coins | dYdX | Binance | dYdX − Binance (median) | Share of coins where dYdX is lower |
|---|---|---|---|---|---|---|
| cross | 2024 | 83 | +6.0 | +13.3 | −6.1 | 66% |
| cross | 2025 | 106 | 0.0 | +2.1 | −0.1 | 50% |
| cross | 2026 | 107 | +0.3 | +0.3 | +3.7 | 40% |
| isolated | 2025 | 113 | +9.1 | −6.9 | +14.4 | 7% |
| isolated | 2026 | 109 | +11.0 | −2.7 | +13.7 | 6% |

- On BTC, ETH and SOL, dYdX funding ran above Binance's in 2024-25 (BTC +22.2 against +11.9 in 2024). Retail long
  demand on dYdX outweighed the missing floor.

## Conclusion
- **Not a usable fourth floorless venue.**
  - The cross markets are floorless by design, but their gap to Binance is near zero in 2025-26.
  - The isolated markets have a floor.
  - Above all, the venue trades $42M a day in total, so costs and capacity rule it out for a book.
- **M469** (re-test of the dYdX carry sets) stays queued only for its Lighter part. Its dYdX part needs measured books
  first, and the volume says they will be thin.
- **The other side.** The isolated markets' floor against negative Binance funding on the same alts (2025-26: +14%/yr
  median gap) is the design gap seen from the other side: a floor venue against a venue whose premium runs
  negative. On these volumes it is not tradable.

## Not checked
- Order books on dYdX: no snapshots were taken.
- Whether the cross-market default ever changed: dYdX's docs and a search found only the open-source default, and
  vote 220 for isolated markets.
