# Map: what is known, and the routes still open

Updated 2026-10-19. Every line points to a lane with a frozen PREREG, a FINDINGS file and a registry row. Splits:
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
7. **Context matters, and mostly as an interaction for market-neutral bets** (R192, R195): the coin's own 4 h / 24 h
   state and its order flow change how its 1 h signals pay; a few hundred market-neutral (signal, context) pairs keep a
   validation edge above 2x costs. Market-wide contexts mostly time the whole market. Clocks switch signals off.
8. **Live data match the archive**: the public endpoints rebuild the flow signals' bins at 99.5-99.98% (R199/R200),
   and a forward paper test of the flow book and of top-vs-crowd runs from 2026-10-01 (R200).
9. **Where money could come from** (R202): if top-vs-crowd holds, a crypto prop challenge (a few hundred dollars for a
   100k account) is worth far more than the same edge on own capital; spot has no candidate (every surviving lead is
   short-side or market-neutral); carry cannot run in a prop account.

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

## 6. Context: when does a signal get stronger? (atlas_ctx R192, atlas_mtf R195)
Lift of every signal inside vs outside a context, discovery 2021-2023, replication 2024-2025H1, placebo-calibrated.
| family | confident lifts | replicate | placebo replicate | excess pairs above cost, 1x / 2x / 3x (placebo 1x) |
|---|---|---|---|---|
| clock (hours, opens, expiries, FOMC) | 17,187 | 50% | 6% | - (directional only: 77 / 56 / 30) |
| crowd (share of coins at extremes) | 408,132 | 85% | 49% (not SIGNAL) | 452 / 153 / 62 (2) |
| market (BTC trend/vol, dispersion, breadth) | 321,432 | 71% | 11% | 93 / 43 / 16 (0) |
| flow (the coin's OI, positioning, taker) | 115,453 | 68% | 9% | 188 / 119 / 66 (0) |
| mtf (the coin's 4 h / 24 h state) | 55,592 | 54% | 7% | 431 / 232 / 131 (2) |
- Market-wide contexts time the market: only ~5% of their raw lifts survive as interactions. Excess (market-neutral)
  lifts are interactions (36-46% replicate vs 3-7% placebo).
- Clocks dampen: 8,208 replicated clock lifts switch a signal off, 353 amplify it.
- Patterns: **exhaustion** (1 h overbought while the 4 h EMA cross is most stretched: the coin trails the market by
  ~100 bp over 24 h); **dip in a strong trend** (1 h oversold, daily RSI top bucket: +117 bp over 4 h); **low leverage
  crowding + 1 h overbought** (-122 bp over 12 h); **crowd most short + price below the day open** (+142 bp over 24 h).
- These are day-weighted means of rare states; ctxslice_v1 (R201) turns the 547 pairs into one slice book.

## 7. Live data and forward paper trading (R199, R200)
- Public endpoints on www.binance.com (fapi.binance.com is geo-blocked) carry the same 5-minute metrics as the
  archive, with snapshots stamped 5 minutes later; taker rows match. With the clock fixed the hourly ratios match to
  3e-6 (top traders) and 3e-5 (all accounts).
- R199 was abandoned at its data gate: the archive lacks metrics for coins with non-ASCII names (4 coins, 0.16% of
  eligible cells, all from 2025-10), and the live filter missed Binance's TradFi perps (oil, gold, NVDA... CLUSDT is
  8th by volume). R200 fixes both: bins match 99.98% / 99.53% / 99.58% on common coverage, top-50 overlap 100%.
- R200 runs books A (flow72 primary) and B (top-vs-crowd alone) from 2026-10-01, hourly, journal committed; decision at
  90 scored days through `lab.gate.go_real` plus NW t >= 2.

## 8. Where money could come from (propfirm_v1 R202)
| route | what it needs | today |
|---|---|---|
| crypto prop challenge (HyroTrader, CFT, Breakout: exchange perps) | an edge whose drawdown fits 5-10% at a size that reaches the target | top-vs-crowd (holdout stream): ~88-95% pass, ~USD 15-19k expected payouts per 100k attempt; flow book ~67%, ~6k; zero edge ~28%, ~1.9k (model optimistic: real buyers ~7% paid) |
| own capital, futures | the same edge at a 10% drawdown budget | top-vs-crowd ~+45%/yr at size 0.63; flow book ~+18%/yr at size 0.21 |
| spot (long-only) | a long-only edge | none: surviving leads are short-side or market-neutral |
| carry | spot leg + perp short | real but ~1%/yr since 2025; not possible in a prop account |
Every number in this table assumes a stream that is not confirmed; R200 is the gate.

## 9. Outside sources (docs/SOURCES.md, docs/CLAIMS.md)
- Tarek El Marhri: sub-5-minute order-book scalping on Eurex/CME index and bond futures; no verifiable record; sells
  EUR 3,900-9,900 courses and promotes a prop firm. Nothing transfers to hourly perps except a daily loss/profit limit
  overlay (C17).
- Verifiable records exist on-chain (Hyperliquid leaderboard, HLP vault) and on platform copy-trading lists (Binance,
  OKX, Bitget). Copy-trading ROI rankings favour tiny accounts; leads can win while copiers lose. Daily snapshots run
  from 2026-10-19 for a forward persistence test (C02, C21, C22).
- Base rates: under 1% of day traders are reliably profitable (Barber et al.); Topstep 16.8% of Combines passed in
  2025; FPFX 7% of 300k accounts paid.
- 22 claims, each with a mechanical rule; tested so far: C13 intraday momentum (itsm_v1 R203): NULL.

## Routes still open
- Forward paper test R200 (books A and B): the only confirmatory evidence the lab can produce; checkpoints at 30, 60,
  90 scored days.
- ctxslice_v1 (R201): the replicated context pairs as one slice book; in-sample filter, then a one-shot holdout.
- Cross-venue top-vs-crowd on Gate (180 days hourly) and OKX (C06), and liquidations from Gate (C07): discovery only on
  the spent window, fresh from 2026-10.
- Copy-trader persistence from forward leaderboard snapshots (C02, C21, C22).
- Carry: forward monitor; reverse carry needs borrow data. High aggregate carry as a crash signal (C08).
- Adaptive selection (battery_v1, R184, planned).

## Known data defects
- The archive has no metrics (order flow) for coins with non-ASCII names; their flow features are missing (0.16% of
  eligible cells). Live data include them.
- Live open interest does not yet line up with the archive hour by hour (OI is not used by the live books).

## Program
Program trials: 9,471,640 after R203 (`registry.program_trials()`), almost all of them context-atlas cells. Read every
t above against that count; only the forward ledger is confirmatory.
