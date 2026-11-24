# Map of venue design mechanisms (living; revised in place)

- **The class:** the rules of different venues disagree, and the disagreement forces a transfer. Arbitrage is held off
  by a barrier (`docs/reviews/approach_20261124.md`).
- **Each row** is filled from primary sources (venue documentation, rulebooks, APIs) and asks one question: where does
  a rule force someone to pay, behind a barrier we can cross?

| Mechanism | What the rule is, per venue (source) | Who is forced to pay | Barrier | Status |
|---|---|---|---|---|
| Funding formula | Floor venues: P + clamp(0.01% − P, ±0.05%) per 8 h, flat at 0.01% while P is in [−0.04%, +0.06%] (Binance, Gate, KuCoin, Hyperliquid, Aster; `research/intake/library_20261119/deriv.md`). Floorless: Kraken (premium only), Deribit (±0.025% dead zone), Bitfinex (±0.05% dead zone). dYdX: cross markets 0, isolated markets 0.125 bp/h (vote 220; indexer `defaultFundingRate1H`) | longs on floor venues, about 10.95%/yr while P sits in the band | the clamp band shields the floor; the gap closes only from the floorless side, so capacity = floorless depth | proven in sample (R525); forward R509/R520/R524. Liquid pairs ≈ risk premium; thin Kraken coins ≈ capacity rent (reflection 2026-11-24) |
| Mark price and liquidation | Kraken: spot index + EMA30s(impact mid − index), premium capped at 1%, liquidation on the mark (Kraken docs). Deribit: mark kept within bands around the spot index, EMA of the basis (Deribit KB). Hyperliquid: median of {oracle + EMA150s(mid − oracle), median(bid, ask, last), median of Binance/OKX/Bybit/Gate/MEXC perps}; liquidation on the mark (HL docs) | the account whose mark crosses its maintenance | — | 2025-10-10: Kraken's mark low averaged −43.8% over 126 coins (Binance prints −65% to −69%); this sets the leverage of long accounts |
| Margin regimes | Kraken: retail schedules 50%/25% (`dlt`) and 10%/5% (`europa`); the EEA page lists 10x "pro" (2026-11-23). Hyperliquid: maintenance = half of 1/max leverage | over-levered accounts | — | used for the ticket; not yet read for an edge |
| Fees and rebates | Lighter 0/0; others per the fee map | takers | — | partly (`research/intake/fee_map_20261116.md`) |
| Settlement and expiry | CME, Deribit and Binance dated futures | hedgers at expiry | — | partly (settle family, 43% pass share) |
| Listing and delisting | new-listing funding caps; delisting closes | early longs; forced closers | — | partly (R516 dried up) |
| Spot lending against perp funding | Boros fixed funding; CEX and DeFi lending | — | — | partly (R412) |
| Index-fund rolls | GSCI business days 5-9, BCOM 6-10 (CFTC paper) | index funds | none: public, one exchange | NULL (R529): paid first by cheaper capital |
| Incentives and points | per-program | venues buying volume | — | measured small (11-21) |
| Stablecoin mint and redeem | not read | — | — | not mapped |
