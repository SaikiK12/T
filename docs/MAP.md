# Map: what is known, and the routes still open

Updated 2026-10-18. Every line points to a lane with a frozen PREREG, a FINDINGS file and a registry row. Numbers are
gross (before fees) only where marked; "replicates" means discovery 2021-2023 picked it and validation 2024-2025H1
confirmed it (same sign, |t| >= 2). Holdout = 2025-07 onward, read once per lane.

## 1. What predicts returns before fees (atlas_v1, R185)

Universe: the 50 most liquid Binance USD-M perps at each hour (499 symbols over time, delisted ones included).

| family (examples) | replicates | reading |
|---|---|---|
| previous-day levels (prevday, prevday_raid), day open | 79-100% | price relative to yesterday's high/low/close and today's open: mean reversion |
| oscillators (rsi, bbz), ema_ratio, ret z-scores | 56-71% | short-term oversold bounces, overbought fades |
| ICT-style detectors (sweep, fvg, struct) | 41-57% | work, but carry the same information as the price features |
| donchian, clv, atr% | 55-56% | same family: where the price sits in its recent range |
| breadth, BTC trend (market state) | 26-67% | market timing, raw only |
| cross-sectional selection (taker imbalance tbi, volume z, funding, premium, order blocks) | 0-23% | strong in 2021-2023, gone in 2024-2025 |

- **Directional (raw) edges replicate, cross-sectional (excess) ones do not**: raw cells replicate 64-73% at 1-24 h,
  excess cells 3-15%. Placebo picks replicate 9%.
- **Where**: by liquidity tier the conditional cells replicate 72-84% (robust everywhere); by session, Europe 60%, US
  open 49%, Asia 38%, weekend 33%, US afternoon 24%, US evening 9%; by BTC regime, BTC up and volatile 69%, up and calm
  48%, down and calm 15%. Market clocks on their own (hour, weekday, US/EU/CME opens, FOMC days, expiries) pass nothing.
- **Size**: the day-weighted edges look large (median edge/cost 3.3 in validation), but per trade, counted once per
  episode, the median replicated cell earns 11 bp before costs (discovery) and 5 bp (validation): under the 12-16 bp
  round trip.

## 2. Combining them (merge_v1 R186, merge_v2 R187)
Walk-forward composites of the top cells (monthly refits, cost-threshold trading): no robust net edge. Best gross t
2.68 (+50%/yr gross, break-even at 1.0x cost); every primary loses at 1x. Session-aware merges overfit.

## 3. Executing them better (maker_v1 R193, pack_v1 R194)
- Limit entries 1 sigma below the close (filled only on a trade-through) move the median replicated cell from -10 bp
  to +11 bp per trade (validation, after costs); a no-signal limit gets part of that, the signals add +13 bp on top.
- But in a book, a pack of the 252 cells that pay per trade is a long position in alts (beta to BTC 1.0); hedged with
  BTC it loses (-25%/yr). **The per-trade gains of directional cells are market exposure plus the bounce, not alpha.**

## 4. Structural ideas
- **Funding carry** (R190, R191): short perp + long spot when trailing funding > 20% APR. CONFIRMED in-sample and on
  the holdout, but its size is the funding regime: +35% in 2021, ~0 in 2022-2023, +8% in 2024, ~1%/yr since mid-2025.
- **New listings** (R188, R189): trail the market in every year (median -9% over 14 days), but squeezes (+700%) keep
  it insignificant; the holdout did not confirm.

## 5. Context: when does a signal get stronger? (atlas_ctx, R192, running)
Lift of every signal inside vs outside: market clocks (US/EU/CME opens, data days, expiries), market-wide crowding
(share of coins at extreme lows/highs), BTC trend/volatility, dispersion, breadth, and the symbol's own order flow.

## 6. Order flow (atlas_v1 flow part, running)
Open interest, long/short ratios, taker flow (all symbols, 2021+) and order-book depth (30 symbols, 2023+).

## Routes still open
- Context gating of the replicated cells, if atlas_ctx finds lifts that replicate.
- Order flow as a signal and as a context.
- A neutral pack: longs and shorts from the same hour, so beta cancels without a hedge leg.
- Carry: a forward paper monitor of the frozen rule; reverse carry needs borrow data.
- Confluence: pairs of replicated cells (one as the other's context), with the lift machinery.

## Program
Program trials so far: see `registry.program_trials()`; every row above carries its own count.
