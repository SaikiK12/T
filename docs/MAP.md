# Map: what is known, and the routes still open

Updated 2026-10-18. Every line points to a lane with a frozen PREREG, a FINDINGS file and a registry row. Splits:
discovery 2021-2023, validation 2024-2025H1, holdout 2025-07..2026-09 (read once per lane). "Replicates" = picked on
discovery, same sign and |t| >= 2 on validation. Universe: the 50 most liquid Binance USD-M perps at each hour (499 coins
over time, delisted ones included). Round trip at the tier costs: about 12-16 bp.

## The short version
1. **Before fees, a lot predicts returns, with high confidence**: about half of 1,020 confident cells replicate (placebo
   9%). Mostly directional short-term mean reversion: yesterday's levels, oscillators, range position, ICT-style
   detectors (which say the same as price).
2. **Per trade, almost none of it pays a market order**: the median replicated cell earns 11 bp (discovery) and 5 bp
   (validation) per entry before costs. Merging many cells does not fix it (R186, R187).
3. **Limit entries help a lot per trade, but for directional cells that is market exposure**: in a book they are long
   alts with beta 1 (R193, R194).
4. **The best lead is order flow, traded as a slow neutral book**: short the coins where takers sold most, or top
   traders lean short against the crowd, as overlapping 72 h slices hedged with the market. In-sample +42.6%/yr (t 3.25,
   5/5 years). Holdout +104% over 457 days but t 1.22: positive, not confirmed (R196-R198).
5. **Funding carry is real and regime-bound**: +35% in 2021, ~0 in 2022-23, +8% in 2024, ~1%/yr since (R190, R191).
6. **How you measure decides what you find**: day-weighted, all-hours atlas means overstate what an entry rule earns;
   the same edge can be captured by a book that holds the state (slices), not by one that trades the entry.

## 1. What predicts returns before fees (atlas_v1, R185)
| family | replicates | reading |
|---|---|---|
| previous-day levels (prevday, prevday_raid), day open | 79-100% | price vs yesterday's high/low/close and today's open: mean reversion |
| oscillators (rsi, bbz), ema_ratio, ret z-scores | 56-71% | short-term oversold bounces, overbought fades |
| ICT-style detectors (sweep, fvg, struct) | 41-57% | work, but carry what price features carry |
| donchian, clv, atr% | 55-56% | where the price sits in its range |
| breadth, BTC trend | 26-67% | market timing, directional only |
| cross-sectional selection (taker imbalance, volume z, funding, premium, order blocks) | 0-23% | strong 2021-2023, gone 2024-2025 |
| order flow: OI vs price, after a 24 h rise | 69% | next 12 h -55 to -63 bp in both periods (a price reversal; OI adds little) |
| order flow: taker selling, top traders vs crowd, 72 h | 3 cells | -37 to -57 bp excess over 72 h |
| order-book depth (30 coins, 2023+) | none found | one year of discovery data |

- Raw (directional) cells replicate 64-73% at 1-24 h; excess (long the cell, short the market) 3-15%.
- **Where they hold** (conditional cells): every liquidity tier (72-84%); sessions Europe 60%, US open 49%, Asia 38%,
  weekend 33%, US afternoon 24%, US evening 9%; BTC up and volatile 69%, up and calm 48%, down and calm 15%.
- Market clocks alone (hour, weekday, US/EU/CME opens, FOMC days, expiries) predict nothing.

## 2. Combining them (merge_v1 R186, merge_v2 R187)
Walk-forward composites (monthly refits, cost-threshold trading): no robust net edge. Adding order flow doubles the
gross (+50%/yr, t 2.64, positive in all four years) but at full tier costs it loses 20%/yr (break-even at 0.72x the
costs). Session-specific means overfit. Best Deflated Sharpe 0.77.

## 3. Executing them better (maker_v1 R193, pack_v1 R194)
- Limit entries 1 sigma below the close (filled only on a trade-through) move the median replicated cell from -10 bp
  to +9..11 bp per trade in validation; a no-signal limit gets part of that, the signals add +13 bp on top. Buying dips
  with limits helps; selling rips with limits does not.
- A pack of 252 such cells is long alts (beta 1.0); hedged with BTC it loses 25%/yr. Per-trade gains of directional
  cells are market exposure plus the bounce.

## 4. Order flow as a neutral book (flow72_v1 R196, flow72_v2 R197, flow72_holdout R198)
- Entry-only book (short when a coin enters the bin, hold 72 h): -20%/yr. Per entry the edge is 5-13 bp, under costs.
- Slice book (a slice every hour the coin is in the bin, closed 72 h later; universe hedge): +42.6%/yr net (t 3.25,
  Sharpe 1.54, max DD 27%), 2x costs +26.9%, 3x +11.3%, every year positive.
- Holdout, one shot: +104% over 457 days (+83%/yr, Sharpe 1.05, max DD 47%), t 1.22 < 2: NOT CONFIRMED. Positive at
  every cost level and hedge; much more volatile than in-sample. Top traders short vs the crowd alone: t 2.72, max DD
  16% (reported, not decided).

## 5. Structural ideas
- **Funding carry** (R190, R191): short perp + long spot when trailing funding > 20% APR. Confirmed in-sample and on the
  holdout, size set by the funding regime.
- **New listings** (R188, R189): trail the market in every year (median -9% over 14 days), squeezes (+700%) keep it
  insignificant; the holdout did not confirm.

## 6. Context: when does a signal get stronger? (atlas_ctx R192, atlas_mtf R195, running)
Lift of every signal inside vs outside: market clocks, market-wide crowding (share of coins at extreme lows/highs), BTC
trend and volatility, dispersion, breadth, the coin's own order flow (R192), and the coin's own 4 h / 24 h state: trend,
range, RSI, structure, volatility, volume, funding (R195). For market-wide contexts the raw lift includes the context's
own market timing; an exploratory decomposition separates the interaction.

## Routes still open
- Forward paper test of the flow slice book and of top-vs-crowd alone (the next real evidence; no money before
  `lab.gate.go_real`).
- Context gating, if atlas_ctx / atlas_mtf lifts replicate as interactions.
- Slice books for other slow, cross-sectional cells; the slice construction is the cheap way to hold a state.
- Carry: forward monitor; reverse carry needs borrow data.
- Adaptive selection (battery_v1, R184, planned): does recent performance pick the next winners?

## Program
Program trials: 507,088 after R198 (`registry.program_trials()`), most of them atlas cells. Read every t above against
that count; only the forward ledger is confirmatory.
