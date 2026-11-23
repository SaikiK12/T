# Frameworks above strategies: one replicating mechanism across many venue pairs, 2026-11-23

- **The owner:** "Voit si les frameworks sont de meilleurs choses que les stratégies ou genre plus haut."
- **Short answer.** A framework multiplies real edges; it does not create one.
  - Grinold-Kahn's fundamental law: information ratio ≈ skill × √(number of independent bets).
  - The lab has seen combinations of nulls stay null: R414 (strategy switching), R228/R253 (mixing one flow family),
    and M3, which adds value only if the combined net beats the best input.
  - So the higher-level move is breadth on the one mechanism that replicates: the funding-design gap.

## Measured on the four design-gap books' in-sample daily nets (1x)
- **Window:** 274 overlapping days, 2025-12-31..2026-09-30.
- **The books:**
  - R507 Bitfinex+Binance;
  - R508 Kraken+Hyperliquid;
  - R511 Kraken+Aster;
  - R519's reported R275 book on Deribit+Hyperliquid, recomputed from its frozen code.
- **Pairwise correlations:** −0.26 to +0.15.

| Book | %/yr | Sharpe | Max drawdown |
|---|---|---|---|
| Bitfinex+Binance | +3.0 | 1.3 | −0.46% |
| Kraken+Hyperliquid | +26.7 | 7.4 | −0.57% |
| Kraken+Aster | +14.0 | 4.2 | −0.57% |
| Deribit+Hyperliquid | +4.1 | 3.1 | −0.36% |
| **Equal weight of the four** | **+11.9** | **8.5** (NW t 10.2) | **−0.19%** |
| Inverse-volatility weights | +9.1 | 8.2 | −0.17% |

- **What the combination does.** It keeps most of the return and cuts the drawdown to a third of the best single book.
  Each book's edge comes from different coins' funding extremes on different venues, so their noise does not add up.
- **What it is worth.** A higher Sharpe at the same drawdown means more leverage for the same risk of ruin. The limit
  then becomes each venue's liquidation and transfer delays (`docs/reviews/stake_dhl_20261123.md`), not the market.
- **Venue risk.** Four venue pairs also spread venue-failure risk.

## The framework, as the lab now runs it
1. **Scan venues for funding designs.**
   - Floorless: Kraken, Bitfinex, Deribit, dYdX (dead).
   - With a 0.01%/8 h floor: Hyperliquid, Binance, OKX, Aster, Lighter, Drift (since its change).
   - Each new floorless venue adds a pair.
2. **One rule on every pair:** R275's book.
   - No per-pair tuning.
   - A sign fixed by design where it is used statically (L011).
3. **Weight pairs by risk,** equal or inverse volatility, and lever the total under `lab/margin.py`'s limits with daily
   rebalancing.
4. **Execution layer:** passive entries where they measured cheaper (R513/R514). Points count as zero.
5. **Evidence layer:** each pair forward on paper (R509, R512, R520). The next useful read is a combined forward read
   across pairs, which reaches significance faster than any one pair.
- **Software frameworks** (NautilusTrader, Hummingbot) belong to step 4's operations later. They are not a source of
  edge.

## Limits
- **In sample, on seen data.** R519's book is a reported secondary.
- **Short window.** 274 days, and correlations can rise in a crash.
- **Different coins.** The books do not trade the same coins, which is why they diversify.
- **Not shown:** the forward correlation, and the operational cost of running five venues.
