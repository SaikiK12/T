# Map: what is known, and the routes still open

Updated 2026-10-20. Historical entries below retain their reported evidence; new exploratory rounds R228–R232 are linked separately. Splits:
original discovery 2021-2023, validation 2024-2025H1, historical holdout 2025-07..2026-09 (now spent at program level). New studies declare their own splits. "Replicates" = picked on
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
   5/5 years; the cells were chosen on these years). Holdout +104% over 457 days but t 1.22: positive, not confirmed (R196-R198).
5. **Funding carry is real and regime-bound**: +35% in 2021, ~0 in 2022-23, +8% in 2024, ~1%/yr since (R190, R191).
6. **How you measure decides what you find**: day-weighted, all-hours atlas means overstate what an entry rule earns;
   the same edge can be captured by a book that holds the state (slices), not by one that trades the entry.
7. **Context matters before fees, not as a book** (R192, R195, R201, R204): the coin's own 4 h / 24 h state and its
   order flow change how its 1 h signals pay, and hundreds of market-neutral pairs replicate above 2x costs from 2021-23
   to 2024-25H1; but as a slice book the slow pairs lose on the holdout (-6.5%/yr) and the fast ones lose to costs.
8. **Live data match the archive**: the public endpoints rebuild the flow signals' bins at 99.5-99.98% (R199/R200),
   and a forward paper test of the flow book and of top-vs-crowd runs from 2026-10-01 (R200).
9. **Where money could come from** (R202, scenario illustrations only: an unconfirmed stream, a daily-step simulator,
   and real challenge buyers are about 7% paid): if top-vs-crowd holds, a crypto prop challenge (a few hundred dollars
   for a 100k account) is worth more than the same edge on own capital; spot has no candidate (every surviving lead is
   short-side or market-neutral); carry cannot run in a prop account.
10. **On the owner's venue, the forward lead is much smaller** (R213-R216):
    - Entering one or two hours late costs only 1-2% of the books' net.
    - MEXC's prices and funding track Binance's on the same coins.
    - But half of the forward replay's profit came from Binance stock and commodity perps. Book B's whole +9.7% is
      stocks. The crypto book that can trade on MEXC made +4.7% over the 18 replayed days, not +22%.
    - The archive holdout is crypto: top-vs-crowd crypto-only has t 2.74. It is concentrated in two coins.
11. **Every edge's evidence in one table**: `docs/EDGE_SCOREBOARD.md`.
    - Only funding carry passed its holdout test (R191: t 2.07 at 1x, about 1%/yr; t 1.14 at 2x). It now runs forward on MEXC, where spot pairs exist for
      small alts that Binance lacks (R220).
    - Cross-venue funding carry (R275) is the strongest gate-0 result: 212 of 560 books pass, best NW t 8.63, about
      5-10%/yr on capital in 2025-26. It runs forward from 2026-10-22 (R278).
    - Paper days alone confirm slowly. At 90 days the gate only detects an annual Sharpe of about 5; a Sharpe of 1.5
      has a 19% chance to pass R221's frozen test by day 365 (`docs/PAPER_REFINEMENT.md`).

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
- **As books they do not pay out of sample.** All 547 pairs as one slice book lose in-sample (-32%/yr: the fast 1-4 h
  pairs earn 1-2 bp/day gross against 14-16 bp of costs; R201). The slow 12-24 h pairs made +39%/yr in-sample (t 3.85)
  but -6.5%/yr on the holdout (t -0.13; gross 7 bp/day against 8 bp of costs; R204).

## 7. Live data and forward paper trading (R199, R200)
- Public endpoints on www.binance.com (fapi.binance.com is geo-blocked) carry the same 5-minute metrics as the
  archive, with snapshots stamped 5 minutes later; taker rows match. With the clock fixed the hourly ratios match to
  3e-6 (top traders) and 3e-5 (all accounts).
- R199 was abandoned at its data gate: the archive lacks metrics for coins with non-ASCII names (4 coins, 0.16% of
  eligible cells, all from 2025-10), and the live filter missed Binance's TradFi perps (oil, gold, NVDA... CLUSDT is
  8th by volume). R200 fixes both: bins match 99.98% / 99.53% / 99.58% on common coverage, top-50 overlap 100%.
- R200 runs books A (flow72 primary) and B (top-vs-crowd alone) from 2026-10-01, hourly, journal committed; decision at
  90 scored days through `lab.gate.go_real` plus NW t >= 2.
- First 18 scored days (2026-10-01..18, scored on 2026-10-19; not decisive): book A +22.2% at 1x (2x +21.0%, 3x
  +19.8%; top-10 hedge +26.6%, BTC hedge +46.5%), book B +9.7%. The only failing go_real check is the number of days.
  **These 18 days are a replay**: they were rebuilt on 2026-10-19 from about 28 days of endpoint history (tagged `late`),
  not observed in real time.
- **Codex review** (`docs/CONFIDENCE_REVIEW.md`, `docs/IMPLEMENTATION_INTEGRITY_REVIEW.md`, merged 2026-10-19) found
  that R200 credits a slice from the close of its signal bar, while the signal is ready 12 minutes or more later
  (`run_at` shows hours when the loop slept).
- **R213 (delay_v1):** a 1-2 h later entry costs 1-2% of the net (A in-sample +12.10 → +11.99 bp/day; holdout
  23.1 → 22.7), so the edge is not front-loaded.
- **R214 (flow72_fwd3):** scores R200's signals entered one bar late. Replay: A +22.5%, B +9.7%. Decision at 90
  on-time days from 2026-10-20.
- **R215 (mexc_fwd):** trades the same signals on MEXC hourly closes and MEXC funding (`lab/mexc.py`, public endpoints).
  Replay: A +4.7%, B -0.1%. Coverage is 56% / 33%, because Binance's stock perps have no MEXC crypto contract.
- **R216 (venue_gap_v1)** splits the R215 gap:
  - Stock and commodity perps (KORU, SOXL, SNDK, SK Hynix, ...) carried 49% of A's replay gross and all of B's.
  - Crypto-only on Binance: A +8.7%, B -0.5%.
  - The MEXC-mapped crypto book makes +4.66% on Binance prices and +4.67% on MEXC prices.
  - In the archive, TradFi is about 0% of the holdout: crypto-only top-vs-crowd makes +18.3 bp/day, t 2.74. But BEAT
    and LAB carry about 68% of book A's holdout gross.
  - **Reference for the owner: R215, crypto on MEXC.**
- **R217 (sizing_v1)**, the confidence multiplier, run on crypto-only books entered one bar late. The verdict is
  NULL against the frozen bar (+0.3 Sharpe in both discovery and validation). Two patterns stand out:
  - **Across coins, more agreement → more size works.** A coin flagged by k of the three flow cells gets k² slices
    instead of k, at the same gross. Sharpe rises from 1.81 / 1.39 / 1.05 to 1.96 / 1.68 / 1.49 (discovery /
    validation / holdout), and one slice per flagged coin is worse everywhere. The cost is concentration: holdout max
    DD is 62%.
  - **Over time, scaling by the book's own confidence hurts.** Shrunk Kelly and "size up after gains" lower Sharpe
    everywhere. A volatility target keeps Sharpe about flat and nearly halves drawdowns (A holdout 47% → 27%): use it
    for live size.
- **R218 (mexc_fwd_sq)** runs the k² book forward on MEXC next to R215. Replay: +6.2% against A's +4.7%.
- `scripts/forward_all.sh` runs one forward tick: R200, then R214, R215, R218, R220, R221.
- **R219 (seesaw_v1)** asked whether the 5 biggest coins' last hour predicts the alts ranked 6-50. It does, by +1.45 bp
  per hour in 2021-23 and +0.93 in 2024-25H1 (top-minus-bottom quintile). But hourly taker trading costs 370 bp/day
  against 35 bp/day of gross, so it is NULL as a book. A slower catch-up version decays to zero. The only routes
  left are maker-only entries (MEXC lists a 0 maker fee) or using it as an overlay.
- **R220 (carry_fwd)** runs the confirmed carry rule (R191) forward on paper, entered one bar late, as two books:
  - Binance: funding, premium index and spot.
  - MEXC: funding, last/index basis and spot.
  - Funding agrees across the venues: median gap in trailing APR 0.0004 over 40 mapped coins
    (`experiments/carry_fwd/venue_check.json`).
  - The coins with carry above 20% APR in October are small alts (AKE, BTW, Q, USELESS). Binance has no spot pair for
    them; MEXC does.
  - Replay 10-01..18: the Binance book never held a position. The MEXC book held 1-2 on every day: funding +0.10%,
    basis -0.01%, costs -0.09%, net about 0 (2x -0.09%).
  - Decision at 90 on-time days: PASS needs total > 0, t >= 2 and go_real on invested days. Under 20 invested days it
    is INCONCLUSIVE.
- **R221 (mexc_seq)** adds a frozen sequential test to the MEXC books A, X2 and crypto-only B, which the 90-day
  go_real screen cannot provide.
  - Looks: futility at 90 on-time days (stop if t <= -2); efficacy at 182 (z >= 3.558) and 365 (z >= 2.397), with
    the 2x total > 0; Bonferroni over 3.
  - Power by day 365: 19% at annual Sharpe 1.5, 73% at 3.
  - It is the first frozen decision on crypto-only top-vs-crowd, the highest holdout t of 7 series read after the holdout (exploratory).
- **R222 (xsalt_v1)** tested four slow altcoin cross-sections from `docs/ALTCOIN_LEADS.md`: low beta, residual
  momentum, MAX and premium net of funding. Weekly or monthly holds cost only 0.6-2.9 bp/day, but none earns gross.
  All six variants fail discovery on BTC-adjusted alpha t (best: plain 30-day momentum +7.7 bp/day, t 1.23).
  Residual momentum does worse than plain momentum.
- **R223 (settle_v1)** held across a funding settlement when the last rate was beyond ±0.20%. The payment arrives,
  but the price moves against the holder by 1.5-2.3 times it (top 50: long -38.5 bp per event, short -43.4). Funding
  capture is closed on Binance, and on MEXC, whose rates match.
- MEXC fees (`docs/MEXC_EDGES.md`):
  - Manual web orders pay 0-4 bp maker and 0-10 bp taker (2 bp on most contracts). 1,106 of 1,200 contracts have
    0 maker.
  - API orders pay 6 bp maker and 8 bp taker since 2026-06-01.
  - The books' tier costs (6-20 bp one way) are conservative for orders placed by hand.
- **R224 (mexc_costs)** snapshots MEXC's order book at every tick for the coins the forward books can trade. It
  measures the one-way taker cost (fee plus walking the book) at $1k, $10k and $50k, and compares it with the tier
  cost. First snapshot, 32 crypto contracts, $10k order: median 2.5 bp on the web, 9.6 bp via the API, 8 bp
  assumed. A $50k order already empties the shown book on AKE. The report starts 2026-11-03.
- **R225 (vt_fwd)** runs R217's volatility target forward on the MEXC books, warmed up on the archive's daily nets.
  Its multiplier reproduces R217's exactly. Today it says to run A at 0.69 of base size, X2 at 0.63 and B at 0.99.
  In the replay it cut A's drawdown from 2.7% to 1.6%, and its total from +4.7% to +2.8%. It decides at 365
  on-time days whether it keeps the lower drawdown at a similar Sharpe.
- **Processing lag** (`experiments/forward_lag`, a report, not a lane). The frozen lanes call a day on time by
  its date. This report adds how long after each bar closed R200 computed the hour (from R200's own `run_at`). A day is
  *strict on time* when all 24 hours were computed within 60 minutes. FINDINGS report the strict subset beside each
  frozen decision, which stays unchanged. It also checks that day tickets were appended in order without gaps
  (Codex's R225 note on #7). On 2026-10-19 (replay), 19 hours were backfilled late after the session paused.
- **R226 (tradesize_v1)** tested Codex's call that trade count and mean print size rank returns beyond quote volume
  (`NEXT_SEARCH_SPACE.md` block C). All 6 spread books fail discovery.
  - The count surge correlates 0.99 with the quote-volume surge, with a residual of +0.3 bp/day.
  - Mean print size against its own month gains +3.3 bp/day (t 0.77), and all of it is quote volume.
  - Unsigned activity carries no direction. Signed print size would need the aggTrades archive.
- **R228 (allocation_v1)** tested 30 static allocations among the archived A/B/X2 flow books. Discovery selected
  30% B / 70% X2, but validation Sharpe improved only 0.007 versus X2; its confidence interval spans zero. NULL.
  The mixture's validation drawdown was worse than a discovery-risk-scaled X2 control. [Findings](../experiments/allocation_v1/FINDINGS.md).
- **R229 (slow_trend_v1)** tested one literature-fixed daily spot trend ensemble and an unscaled diagnostic on six
  surviving major coins. Validation net remains positive at 2x costs, but the primary fails its risk-matched passive
  Sharpe, drawdown and paired-mean requirements. NULL. This is a bounded adaptation, not all trend following.
  [Findings and source limits](../experiments/slow_trend_v1/FINDINGS.md).
- **R230 (weekly_rotation_v1)** searched 96 frozen weekly spot rotation rules on the same six-coin cache. Discovery
  selects 28-day momentum/top3/BTC56 gate/full adjustment. Validation Sharpe 0.833 versus 1.105 passive, drawdown
  53.63% versus 36.13%, paired excess interval spans zero, family diagnostic p=1. NULL. This does not close C14's
  broader point-in-time long/short universe. [Findings](../experiments/weekly_rotation_v1/FINDINGS.md).
- **R231 (partial_execution_v1)** tests half/quarter daily adjustment toward the unchanged R229 trend target.
  Discovery chooses half adjustment. It saves validation costs but loses more gross return at 1x/2x; paired excess
  -0.090 bp/day, interval [-0.412,+0.226]. NULL. All 5,202 full-control rows reproduce R229 exactly.
  [Findings](../experiments/partial_execution_v1/FINDINGS.md). The raw-flow version remains a separate input-dependent question.
- **R232 (rebalancing_v1)** tests daily/weekly/monthly equal-weight spot resets against fixed-unit buy-and-hold.
  Discovery selects monthly; validation paired gain +0.965 bp/day, interval [-2.350,+4.764], Sharpe gain +0.088
  below +0.15. NULL. [Findings](../experiments/rebalancing_v1/FINDINGS.md). The source's full-universe long/short
  construction remains untested; monthly's previous use as R229's comparator is disclosed.
- **R233 (regime_v1)** tested MacroHFT's idea on the flow books: trade them only in some trend x volatility
  regimes, or switch book by regime. No gate was selected, because A, B and X2 each earned at 2x costs in all four
  regimes in discovery. The regime-wise mix raised validation Sharpe by 0.12 against X2 (bar 0.15), and trailed it at
  2x-3x. NULL. Described, not tested: B (top-vs-crowd) earns almost only in falling low-volatility markets (t 3.68).
  [Findings](../experiments/regime_v1/FINDINGS.md).
- **R234 (posimpulse_v1)** tested queue M001: the 24 h and 72 h *change* in top-vs-crowd as spread books. All four
  books failed discovery. The best was imp72/H at +5.2 bp/day (t 0.90; +2.8 after the level book). The impulse is
  nearly uncorrelated with the level (0.00-0.20). Discovery is effectively 2023, because positioning covers about 10%
  of coin-hours in 2021-22. In 2023 the H books made about +24 bp/day, which was seen after the run and is queued as
  M223. NULL. [Findings](../experiments/posimpulse_v1/FINDINGS.md).
- **R235 (usindex_calendar_v1)** was the first lane outside crypto. It tested turn-of-month and overnight drift on
  SPY and QQQ (2000-2012), as alpha against buy-and-hold. Both effects show the expected sign but fall short of
  t 2:
  - turn-of-month: +1.2 to +1.7 bp/day of alpha, t 1.2-1.5;
  - QQQ overnight: +1.8 bp/day at 1x, -0.2 at 2x.
  NULL. 2013-2026 stays unread. [Findings](../experiments/usindex_calendar_v1/FINDINGS.md).
- **R236 (amihud_v1)** tested queue M002, a one-week Amihud illiquidity spread book. Long illiquid / short liquid
  passed discovery: +11.9 bp/day, t 2.28, every year positive. It then lost in validation: -9.2 bp/day, with 2025H1 at
  -19.4. Most of the book is inverse volume (corr -0.52). NULL. [Findings](../experiments/amihud_v1/FINDINGS.md).
- **R237 (tsmom_v1)** tested queue M194, cross-asset time-series momentum on 23 equity-ETF, FX, metal and bond
  series. Discovery 2001-2012 gave Sharpe 0.28 (t 1.00), with 2008 the only big year. FX (spot only) and bonds
  (unadjusted futures) added nothing. NULL. [Findings](../experiments/tsmom_v1/FINDINGS.md).
- **R238 (xsbattery_v1)** was the owner's brute-force crypto pass: eight untested cross-sectional features (weekly
  momentum, 28-day "reversal", daily MAX, IVOL, skew, 52-week-high nearness, funding slope, Abdi-Ranaldo spread) as
  one-week spread books, 16 trials. None reached t 2 in discovery. The best was mom7/H, +9.0 bp/day with t 1.77.
  Five of the features are one bet, long the recent winners and high-volatility coins, and it paid only in 2021. NULL.
  [Findings](../experiments/xsbattery_v1/FINDINGS.md).
- **R239 (fxindex_v1)** was a forex and US-index battery with 7 trials. Discovery 2001-2012 results:
  - VIX reversal on QQQ: +2.9 bp/day of alpha, t 1.94 (a near miss).
  - G10 spot momentum: t 1.20.
  - Halloween: t 1.32.
  - Dollar trend and pre-holiday: nothing.

  The variance risk premium (a measurement, not a book) was positive on 82-85% of days in every window. Its t was
  2.55 in discovery and 5.71 in validation, but 1.11 on the 2020-26 holdout, because of March 2020. NULL; follow-ups
  M224-M226. [Findings](../experiments/fxindex_v1/FINDINGS.md).
- **R240 (posimpulse_v2)** tested R234's positioning-impulse books on 2024-25, the only window that 2023's after-the-fact
  result had not seen. imp24/H: -0.7 bp/day. imp72/H: +6.6, t 1.33, negative at 3x. NULL; M001/M223 closed after 6
  trials. [Findings](../experiments/posimpulse_v2/FINDINGS.md).
- **R241 (volrisk_v1)** timed short volatility: long SVXY when VIX is below VIX3M.
  - It passed discovery 2011-16 (+54%/yr, t 2.39) and validation 2017-19 (t 1.82). Validation was decided by
    exiting at the open of 2018-02-05, after a 0.28-point term-structure cross the session before.
  - The 2020-26 holdout gave +19%/yr at t 1.70, short of t 2, with drawdowns of 45-66% and a worst day of -21.5%.
  - The calm-VIX filter failed discovery, and R239's VIX reversal had no alpha in 2013-19.
  - NULL. It is the closest cross-market result, and it is a crash-risk premium, not a prop-compatible book.
  [Findings](../experiments/volrisk_v1/FINDINGS.md).
- **R242 (tsbattery_v1)** tested four crypto time-series rules on the top-50 perps: week-open bias, pre-FOMC drift,
  the ETH/BTC alt-season regime and vol-managed trend.
  - Vol-managed trend passed discovery (+6.0 bp/day, t 2.07, beta near 0), but at 0.37 gross exposure that is about
    2%/yr. It failed validation (t 0.52).
  - The other three failed discovery.
  - NULL. [Findings](../experiments/tsbattery_v1/FINDINGS.md).
- **Queue import (Codex PR #20):** 164 source-method records were mapped onto `registry/methods.csv`.
  - 132 are aliases of existing rows and 27 are context (`registry/methods_aliases.csv`).
  - 3 are new rows, M227-M229.
  - ALT1's negative-sign seesaw rule is the mirror of R219 F1, so it loses about 35 bp/day before costs.
- **R243 (chartist_v1)** tested seven classic chart rules on 4 h and daily bars of the top-50 perps, 14 trials:
  Supertrend+RSI, MACD, Stochastic, CCI and Bollinger fades, Ichimoku and pivot breaks.
  - None reached t 2. Daily trend rules were right in sign but weak (Supertrend+RSI +11.3 bp/day, t 1.23).
  - On 4 h bars, costs of 6-9 bp/day ate the trend rules.
  - The overbought/oversold fades lost (Stochastic 4 h alpha t -2.07), and so did pivot breakouts.
  - NULL. [Findings](../experiments/chartist_v1/FINDINGS.md).
- **R244 (weekendlink_v1)** asked whether BTC's weekend move sets the direction of QQQ/SPY for the week's first
  session. It goes with the opening gap (correlation +0.46), which is already priced, but not with the session after
  the open (+0.07). Trading it lost slightly. NULL. [Findings](../experiments/weekendlink_v1/FINDINGS.md).
- **R245 (xsrev_v1)** tested short-term reversal inside the liquid and illiquid thirds of the top 50.
  - The 1-day books lost 13-17 bp/day, mostly to 9-12 bp/day of cost.
  - At 7 days the literature's pattern appears (illiquid coins reverse a little, liquid ones continue), too weakly to
    trade.
  - NULL. [Findings](../experiments/xsrev_v1/FINDINGS.md).
- **R246 (ictlevels_v1)** tested ICT-style levels on hourly bars, 8 trials:
  - round-number crosses and rejections;
  - SMT divergence against BTC (24 h and 168 h, fade and follow);
  - the 8 AM New York range (fade and follow).

  Results:
  - The round-number books turn over all day and lose 40-85 bp/day.
  - SMT fade at 24 h grosses +11.3 bp/day but nets +2.0 (t 0.29).
  - The 8 AM range lost both ways.
  - Post hoc: closes through round numbers reverse 10.8 bp/day more than closes through a half-step-shifted grid
    (t -3.30, every year). This is queued as M230 with a pre-registered control.
  - NULL. [Findings](../experiments/ictlevels_v1/FINDINGS.md).
- **R247 (chartxm_v1)** ran R243's seven chart rules on daily bars of 11 forex pairs and 10 world equity indices,
  14 trials, discovery 2001-12.
  - Nothing passed.
  - On indices, the fades and trend rules were mildly positive (best CCI fade, alpha t 1.50). On forex, nothing
    reached t 1.
  - Pivot breakouts lost in both groups (forex t -2.49, indices t -4.16), as on crypto in R243. Their mirror, a pivot
    fade, is queued as M231, with the 2013-19 decade as its first unseen window.
  - A start-day bug in the first run was fixed to the PREREG text and disclosed; no verdict changed.
  - NULL. [Findings](../experiments/chartxm_v1/FINDINGS.md).
- **R248 (pivotfade_v1)** took R247's post-hoc lead, fading closes beyond the prior day's R1/S1, to windows nobody
  had seen.
  - It failed everywhere: indices 2013-19 alpha -0.57 bp/day (t -0.62); forex +0.46 (t 0.98, negative at 2x); crypto
    2024-25 lost before costs.
  - The 2001-12 index reversal did not survive 2012. The pivot family is closed.
  - NULL. [Findings](../experiments/pivotfade_v1/FINDINGS.md).
- **R249 (rnfade_v1)** took R246's post-hoc round-number lead to crypto validation 2024-25, with one fade per coin
  per day against a half-step-shifted grid.
  - **The mechanism replicated:** the first close through a two-significant-figure level reverses +4.8 bp/day more
    than through a shifted level (t 2.53, 4 h hold).
  - **The books did not pass:** the best was +8.8 bp/day at t 0.88, and taker cost (10-13.5 bp/day) equals the gross.
  - A maker version is queued as M232.
  - NULL. [Findings](../experiments/rnfade_v1/FINDINGS.md).
- **R250 (pairs_v1)** tested classic pairs trading on the top-20 and top-50 perps: distance and Engle-Granger
  selection, weekly 30-day formation, z-score entry 2 and exit 0.
  - Gross was near zero in all four books (-1.6 to +2.5 bp/day).
  - 59-78% of trades ended at the week's end without reverting: one-week idiosyncratic moves in crypto drift rather
    than mean-revert.
  - NULL. [Findings](../experiments/pairs_v1/FINDINGS.md).
- **R251 (lmw_v1)** ran Lo-Mamaysky-Wang kernel chart patterns (head-and-shoulders, broadening, triangles,
  rectangles) on daily crypto, forex and world indices.
  - Head-and-shoulders on indices predicted in 2001-12 (-82 bp over 5 days after an HS, book alpha t 2.27). It earned
    nothing in 2013-19 (t -0.18).
  - Crypto and forex books were flat.
  - NULL. [Findings](../experiments/lmw_v1/FINDINGS.md).
- **R252 (oiwick_v1)** faded liquidation-cascade proxies on the top-50 perps: an hourly open-interest drop of 3% or more
  plus a wick of at least 3 ATR (lower wick: buy; upper wick: sell), held 4 h or 24 h.
  - Both sides reverted in raw price terms (long cascades +143 bp over 24 h, 658 cases; squeezes -391 bp, 166 cases).
  - The best book, ALL/24, reached t 1.93 in discovery, which is effectively 2022-23 because OI data covers little of
    2021.
  - Post hoc, the long-side bounce is mostly the whole market's (+23 bp market-adjusted). A cascade-count market-timing
    rule is queued as M233.
  - NULL. [Findings](../experiments/oiwick_v1/FINDINGS.md).
- **R255 (cascmkt_v1)** bought the equal-weight market for 24 h after hours in which three or more coins showed R252's
  cascade trigger. It was decided on 2024-25 only.
  - The market rose +186 bp over the next 24 h after the 15 cascade hours (all in 2024), but the book reached only
    t 1.03. Too rare to prove.
  - Its frozen PREREG says R253; Codex claimed that id first (see `REGISTRY_REASSIGNMENT.json`).
  - NULL. [Findings](../experiments/cascmkt_v1/FINDINGS.md).
- **R256 (dow_v1)** tested day-of-week effects on SPY, world indices, the US dollar, BTC and crypto. Discovery picked
  one weekday per market.
  - No pick reached alpha t 1 after its sign was set. The Friday-short alpha on indices comes from 2001 and 2010.
  - Weekly round trips cost 0.4 bp/day (Yahoo) to 2 bp/day (crypto), which is more than any weekday alpha.
  - Its frozen PREREG says R254 (reassigned the same way).
  - NULL. [Findings](../experiments/dow_v1/FINDINGS.md).
- **R260 (dispgate_v1)** halved flow books A, B and X2 on days when 30-day cross-sectional dispersion was in its top
  tercile and the alt index had fallen over 90 days (the momentum-crash rule, SIZING_EVIDENCE #7).
  - Every book lost 0.00-0.05 Sharpe in both windows.
  - The gate fired after LUNA (May-June 2022), when books A and X2 earned 3.4-4.2 times their usual mean, and in
    February-May 2025, when they still earned 67-82% of it.
  - Crowd-fading short books profit from the stress that hurts momentum, so the rule removes profit.
  - NULL. [Findings](../experiments/dispgate_v1/FINDINGS.md).
- **R261 (tradlead_v1)** asked whether the last hour of TradFi perps (gold, silver, oil; US equity perps such as QQQ and
  NVDA) leads crypto. It tested a market-timing book and a beta cross-section, held 1, 4 or 24 h.
  - The data starts in 2025-12, so the whole read lies in the spent holdout.
  - Equity perps and crypto move together within the hour (correlation +0.34), with no lead into the next hour
    (-0.007).
  - All 12 selected books fail discovery. The best is -0.1 bp/day at 24 h; the 1-4 h books lose to costs.
  - NULL. [Findings](../experiments/tradlead_v1/FINDINGS.md).
- **R262 (impact_v1)** measured square-root market impact on books A, B and X2 at $1k-$10M (a measurement, 0
  trials).
  - At $10k, impact is under 1.5% of the validation net, so the tier cost model holds at the owner's scale.
  - A and X2 lose half their net near $12M and all of it near $50M. That uses Binance volumes; MEXC capacity is lower
    in proportion to its volume.
  - DATA_PASS. [Findings](../experiments/impact_v1/FINDINGS.md).
- **R263 (brute5k_v1)** brute-forced 5,472 chart strategies on the top-20 perps.
  - The families are EMA, Donchian, RSI, Bollinger, Supertrend, Fibonacci, TS momentum, MACD and VWAP bands, on
    1 h/4 h/12 h/1 d bars with direction, filter and stop variants.
  - **Walk-forward "what worked in the last 6 months":** +1.18 / +0.29 / -0.61 bp a day at 1x/2x/3x, NW t 0.96
    (2021-07..2025-06). It beats 99.9% of random monthly picks, but the pool averages -1.02 bp/day.
  - **Best single strategy** (RSI 14/10, 1 h, long): discovery t 3.11. The reality check gives p 0.334, and its
    validation t is 0.02.
  - 1 h rules lose to costs. Trend families earn when BTC moves a lot, whatever the direction. Leverage above 3x
    mostly buys drawdown.
  - NULL. [Findings](../experiments/brute5k_v1/FINDINGS.md).
- **R264 (accounting_v1)** checked whether the legacy zero-fill of a missing next return inflates books A, B and X2 (a
  measurement, 0 trials; PR #25 audit item 4).
  - No held position meets a gap in discovery or validation, so bridged and legacy nets are identical at 1x/2x/3x.
  - The only held gaps are the archive's last row in the spent window (35 / 4 / 35 positions).
  - Wider universes and event lanes near delistings are not covered; they must use `missing="raise"` or bridge.
  - DATA_PASS. [Findings](../experiments/accounting_v1/FINDINGS.md).
- **R265 (unlocks_v1)** replicated the old session's unlock short (E01): short at the close of D-7, cover at the close
  of an insider or private-sale cliff unlock of at least 1% of max supply.
  - 422 events on 69 Binance perps, 2021-26: +3.24% / +3.04% / +2.84% net per event at 1x/2x/3x, week-cluster t
    3.19. Matched-date null p 0.0005; both halves positive; positive without the top 3.
  - Dose-response is monotone. The tail is heavy: six squeezes lost over 40%.
  - Gate 0 only: the old session read these years, and the calendar is not point-in-time. Codex's daily-bar check
    (R258, PR #29) agrees.
  - PARTIAL (frozen verdict REPLICATES). [Findings](../experiments/unlocks_v1/FINDINGS.md).
- **R266 (unlocks_fwd)** runs the same rule forward on MEXC paper from 2026-10-21.
  - Events come from the daily calendar snapshot recorded since 2026-10-20, and each ticket is frozen before its
    entry bar.
  - Decision at 120 scored tickets. RUNNING. [PREREG](../experiments/unlocks_fwd/PREREG.md).
- **R267 (delist_v1)** tested the old delisting-notice short (E03): short the USD-M perp at the first hourly open after
  a Binance "Will Delist" notice, and cover at +1 h (primary) or +24 h.
  - The events are 68 notice clusters and 160 legs, 2022-26, from the notice catalog plus article text.
  - **Primary:** -0.12% / -0.52% / -0.92% at 1x/2x/3x, t -0.06. The matched same-hour null gives p 0.0575.
  - Squeezes on perps that are themselves being delisted dominate the mean (ANC -95%, SLERF -87% in an hour).
  - **Logged variant:** spot notices at +1 h, +4.15%, t 3.07 (n 25), with both halves positive. It is 1 of 8 variants,
    so it is a forward candidate, not a pass.
  - NULL. [Findings](../experiments/delist_v1/FINDINGS.md).
- **R268 (delist_fwd)** runs R267's spot-notice variant forward on MEXC paper.
  - Tickets come from the notice recorder's `first_seen_utc` (from 2026-10-20 18:00 UTC).
  - Short at the first hourly open after detection, and cover 1 h later (+24 h logged).
  - Futures notices are not traded.
  - Decision at 12 scored notices (about 1.5 years). RUNNING. [PREREG](../experiments/delist_fwd/PREREG.md).
- **R269 (montag_v1)** tested a Monitoring Tag short: short the perp of each coin Binance adds to its Monitoring Tag at
  the first hourly open after the notice, and cover at +1 h (primary), +24 h or +72 h.
  - The events are 24 notice clusters and 86 priced legs, 2023-10..2026-09 (the tag began in 2023-07).
  - **Primary:** +0.61% / +0.21% / -0.19% at 1x/2x/3x, t 0.71. The matched same-hour null gives p 0.0005, but the
    hour is too small to pay 40 bp.
  - **Logged variant:** +24 h, +4.36% at 1x (t 3.81; 2x +3.96%, 3x +3.56%), with both halves positive. The BTC-hedged
    +24 h line also clears G1-G3. They are 2 of 6 variants, so a forward candidate, not a pass.
  - **It fades in 2026:** +1.31% over 11 clusters, and -0.92% over the last 5.
  - NULL. [Findings](../experiments/montag_v1/FINDINGS.md).
- **R270 (montag_fwd)** runs R269's +24 h variant forward on MEXC paper.
  - Tickets come from the notice recorder's `first_seen_utc` (from 2026-10-20 19:00 UTC), with R268's ticket rules.
  - Short at the first hourly open after detection, and cover 24 hours later (+1 h logged).
  - Decision at 12 scored notices (about a year). At 2026's level the expected t is under 1. RUNNING.
    [PREREG](../experiments/montag_fwd/PREREG.md).
- **R271 (announce_v1)** tested every Binance announcement type as one family on the qx engine: long and short at
  +1 / 24 / 72 / 168 h, 64 strategies, one reality check.
  - Best: funding-frequency change long +1 h, +3.59% per notice, t 3.31 (n 35); pre-listing short +168 h, +11.48%,
    median +18.05%, t 2.03 (n 45). Neither clears the family reality check.
  - NULL. [Findings](../experiments/announce_v1/FINDINGS.md).
- **R272 (announce_fwd)** runs R271's two best forward on MEXC paper: FF (funding-frequency long 1 h) and PL
  (pre-listing short 168 h), from notices first seen at 2026-10-20 19:00 UTC.
  - A 5-minute notice loop (`scripts/notice_loop.sh`) writes tickets within minutes.
  - Bonferroni t >= 2.2 at 12 scored notices per book. RUNNING. [PREREG](../experiments/announce_fwd/PREREG.md).
- **R273 (fundext_v1)** tested the onset of extreme funding on every Binance perp (|rate| >= 0.3 / 1 / 2%, no
  same-sign hit in the prior 72 h), long and short at +1 / 8 / 24 / 72 h: 40 strategies.
  - Best neg2 long +72 h +7.32%, median -4.95%, t 2.39 (RC p 0.87).
  - After a negative onset the median coin keeps falling, but a few squeezes outweigh the wins.
  - NULL. [Findings](../experiments/fundext_v1/FINDINGS.md).
- **R274 (squeeze_v1)** tested the short after a negative-funding onset with a close-based cover (10 / 20 / 35%), on
  Binance 2021-26 and on MEXC's own funding 2025-26 (MEXC-only coins not read): 72 strategies.
  - The cover cuts the tail and the median with it. Best mx_neg0.3 short 72 h with a 10% cover, +0.55%, t 1.35.
  - NULL. No forward lane (the pre-committed rule needed t >= 2).
    [Findings](../experiments/squeeze_v1/FINDINGS.md).
- **R275 (xfund_v1)** tested cross-venue funding carry on Binance, Gate, Hyperliquid and MEXC (qx spread): the same
  coin on two venues, long where trailing funding is lower and short where it is higher. 560 books.
  - **PARTIAL: 212 books pass every gate**, the first family in the program far above its reality-check null.
  - Best gate+hyperliquid L14d th5% K20: +9.73 / +8.51 / +7.28 %/yr at 1x / 2x / 3x, NW t 8.63, every year
    positive.
  - The Hyperliquid books decay from 17-19%/yr (2023) to 5-8%/yr (2025-26).
  - [Findings](../experiments/xfund_v1/FINDINGS.md).
- **R276 (xvfac_v1)** tested what Gate and Hyperliquid say about a Binance perp's next days (qx factors, 18 series).
  - NULL: the best cross-venue factor has RC p 0.124.
  - Only the reference (Binance funding alone) passes, and it gets no follow-up (queued as M263).
  - [Findings](../experiments/xvfac_v1/FINDINGS.md).
- **R277 (xfund_kd_v1)** replicated R275's best book unchanged on KuCoin and dYdX, which R275 never read.
  - PARTIAL, 2 of 4 sets: gate+kucoin +11.76%/yr (NW t 11.41) and binance+kucoin +10.80%/yr (NW t 11.17), both
    positive every year at 1x and 2x.
  - The dYdX sets fail: dYdX's crash prints of 2025-10-11/12 dominate them.
  - [Findings](../experiments/xfund_kd_v1/FINDINGS.md).
- **R278 (xfund_fwd)** runs R275's books forward on paper with live fills:
  - A gate+hyperliquid and B binance+mexc, as pre-committed;
  - C gate+mexc, post hoc.
  - On-time from 2026-10-22; NW t >= 2.5 at 90 / 180 scored days.
  - `lab/xfund.py` reproduces R275's trades exactly (`scripts/xfund_parity.py`).
- **R279 (xfund_kc_fwd)** runs R277's two KuCoin books forward on paper:
  - the same rule, accounting and decision as R278;
  - entries on contracts missing from a venue's live list are blocked, which R278 does not do
    ([R278 notes](../experiments/xfund_fwd/NOTES.md));
  - it runs on `lab/carrylane.py`, R278's lane for any venues, whose journals match R278's script in a test.
- **R280 (levcarry_v1), done: the books stay at 1x, on cross margin per venue.** It measured how much leverage these
  five books can carry before an intraday move liquidates a leg, under 3 margin policies and 2 maintenance margins
  (0 trials).
  - Isolated margin per leg is liquidated even at 1x on every book: 155 short-leg days with a pump of about 95% or
    more, 149 of them real on other venues.
  - One cross account per venue is safe at 1x on every book, at 2x only on binance+mexc and binance+kucoin, and at
    3x on none. The 2025-10-11 crash wipes a one-sided venue account at 2x.
  - [FINDINGS](../experiments/levcarry_v1/FINDINGS.md).
- **R281 (sizecarry_v1), NULL: the books stay equal-weighted.** It sized each open pair of the six carry books by
  confidence (spread, persistence, inverse leg volatility and their products, weights capped at 3 slots) against equal
  slots (30 trials).
  - No book passes its SPA bar (p ≤ 0.0083 at 2x). The closest is R279 A spread_persist, p 0.026.
  - Tilting to the widest spreads adds +1.3 to +8.7 %/yr at 1x, but it doubles the trading and cuts the NW t by up to
    half. The gain comes only from 2025-26, the years of R280's short-leg pumps.
  - [FINDINGS](../experiments/sizecarry_v1/FINDINGS.md).
- **R282 (pitfac_v1), PARTIAL by its frozen rule, but no book is evidence.** It tested nine factors from the daily
  point-in-time panel (`lab/daily.py`) on qx `factors`, top 150 Binance perps, 2021-26 (27 trials).
  - The factors: Korean premium, print-wick days, size, volume/cap, fee yield, OI/cap, venue breadth, multi-venue
    funding gap and age.
  - 18 series beat the reality check. Age and vol_mcap also have a positive daily book at 1x and 2x: +3.9 and
    +1.6 bp/day at 1x.
  - Those books have NW t 0.68 and 0.39, and their 10 best days are their whole sum.
  - The real finding is a median effect. Young, small, high-turnover coins drift down on a typical day, and rare
    squeezes cancel it in the mean.
  - The Korean premium, fee yield and funding gap are NULL. M276 (cap the squeezes) is queued.
  - [FINDINGS](../experiments/pitfac_v1/FINDINGS.md).
- **R283 (vixpanic_v1), NULL** (27 cells, the owner's TikTok claim, M278). VIX above VIX3M with VVIX in its top 5%
  leads SPY and QQQ up over 5-10 days (best QQQ 10 d +158 bp over random dates, p 0.005), but no cell clears
  p ≤ 0.00185. BTC has too few onsets. [FINDINGS](../experiments/vixpanic_v1/FINDINGS.md).
- **R284 (trendpull_v1), NULL** (8 cells, M277). The trend-pullback entry adds +0.2 to +0.7% per trade on world
  indices (t ≤ 1.31) and loses on crypto perps. [FINDINGS](../experiments/trendpull_v1/FINDINGS.md).
- **R285 (xbook_fwd), running.** The cross-family forward book (M281): carry, flow and event lanes at equal weight,
  decided at 180 and 365 forward days.
- **R286 (reserved_batch1), frozen; runs on or after 2026-11-03.** Ten pre-committed candidates, read once on 2020,
  Gate 2020 and the MEXC-only coins, with a weighted Bonferroni.
- **R287 (pcares_v1), NULL** (24 variants, M298). Hourly PCA residuals revert a little (gross up to +19 bp/day), but
  hourly trading costs several times that; break-even is at most 3.5 bp per side.
  [FINDINGS](../experiments/pcares_v1/FINDINGS.md).
- **R288 (xfund_lt_v1), reserved.** Lighter carry replication; frozen once Lighter's funding history is fetched.
- **R289 (clockflow_v1), NULL** (40 variants, M301 and M303 from `docs/TRADER_TALKS.md`, 1-minute bars).
  - The US cash-open flush fade won in 2022 (mostly SOL) and lost in 2024-26 (t −0.48).
  - On Fridays, a move inside Deribit's 07:30-08:00 UTC settlement window reverses by about +20 bp gross per trade
    in both windows and all three coins. On the book it is +0.38 bp/day at 2x, t 1.37: not enough.
- **R290 (auction_v1), NULL** (60 variants, M305 from the owner's term list, 1-minute bars, `docs/AUCTION_AND_FLOW.md`).
  - Five auction rules (value-area re-entry, IB and opening-range break, VWAP ±2 SD, naked POC) from 00:00 UTC, the
    New York open and the London open, against 8 random clocks.
  - Real session starts are no more structured than random clocks: rank-permutation p 0.36.
- **R291 (vpin_v1), NULL** (4 variants, M085 from the owner's reel on toxic order flow, `docs/QUANTDATA.md`).
  - VPIN from Binance's exact taker split worsens 1-hour volatility forecasts out of sample (DM t −12.5 against
    a HAR with relative volume); the bulk-classified VPIN of the papers is mostly volume (corr 0.53-0.59).
  - Plain relative volume flags hours with moves over 4 sd about 40x top against bottom decile; VPIN 3x.
  - The discovery pick (follow VWAP-band breaks after the New York open) lost in 2024-26 (t −0.96).
  - Placebos, post hoc: the 09:30 New York fade is cleaner on days the US market is shut, and moves after 10:30 New
    York continue. They are seeds for a lane on unread data.
  - [FINDINGS](../experiments/clockflow_v1/FINDINGS.md).

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
- 22 claims, each with a mechanical rule. Tested so far, all NULL:
  - C13 intraday momentum (itsm_v1 R203).
  - C06 top-vs-crowd on Gate (xvenue_v1 R205): same gross as Binance's (+25 bp/day over 157 days) but t 1.43 and 3x
    the drawdown; Gate-only coins earn nothing. Weak support that the signal is market-wide; Gate adds nothing.
  - C07 liquidation fade (liq_v1 R206): long cascades *continue* (buying after them loses before costs at 4-72 h);
    short squeezes revert +10-26 bp/day gross at 4-24 h, below taker costs.
  - C08 carry as a crash signal (carrycrash_v1 R207): reversed. Top-decile market carry was followed by no -20% BTC
    crash in 138 signal days (base rate 16%); shorting BTC on it lost -74% in-sample (t -2.06). High carry marked the
    2023-2024 rallies.
  - C17 daily loss/profit limits (daylimit_v1 R208): harmful. All 30 stop rules on the flow books lose against the
    unfiltered book in both windows (primary -22.5 bp/day, t -8.3); the books' hourly results are uncorrelated and
    each stop pays a round trip. Meet a prop firm's daily limit by sizing, not by an intraday kill switch.
  - C23 volatility risk premium (vrp_v1 R209, Deribit DVOL): BTC +7.5 bp/day in-sample (t 1.06), +1.1 on the
    holdout; 7 of 8 variants lose on the holdout.
  - C18 Coinbase premium (cbprem_v1 R210): book +0.2 bp/day (t 0.34) in-sample; the gross 24 h spread after +/-2 z
    extremes has the claimed sign in both windows (BTC +28 bp in, +57 out) but the signal is rare and noisy.
  - Pattern: one- or two-asset timing rules (C08, C13, C18, C23) cannot reach t 2 in five years at daily frequency;
    every lead the lab has comes from a cross-section of many coins.

### Inside top-vs-crowd (posfam_v1 R211, posfam_v2 R212)
- top_vs_crowd = (top traders' positions vs their headcount) + (top traders' headcount vs the crowd). The first half
  *is* the signal (its short book correlates 0.96 with top_vs_crowd's); the second half fails validation (t 0.85).
  A few large positions leaning short against the other top accounts is what pays; headcounts are crowd-like.
- The top-account ratio alone is contrarian in discovery (t -3.0); reversed, it keeps its sign on validation
  (+20 bp/day) but t 1.13, and its residual over top_vs_crowd is ~0. Three Binance positioning ratios, one story.
- Data coverage: Binance's archived positioning ratios cover 10-13% of eligible coin-hours in 2021-2022 and 99% from
  2023, so every top-trader result's "discovery" is mostly 2023.

## Routes still open
- Forward paper tests:
  - R215 (crypto on MEXC prices, one bar late) is the one that matches the owner's venue. R200 (frozen, Binance,
    includes stock perps) and R214 (R200 one bar late) run beside it.
  - Checkpoints are at 30, 60 and 90 days, with per-coin contributions reported (two coins carried the archive
    holdout).
  - R221 judges the MEXC books at 90/182/365 days. R220 runs carry forward.
- MEXC-specific lanes to pre-register (`docs/MEXC_EDGES.md`):
  - maker-dip entries on zero-maker contracts (paper fills only on trade-through);
  - a MEXC open-interest recorder (needs a process that runs continuously).
- Altcoin leads (`docs/ALTCOIN_LEADS.md`) 1-5 are run (R219, R222): all NULL. R222's 24 h spreads are not pursued:
  a literature check found no prior for either sign.
- Confidence-scaled sizing (`docs/SIZING_EVIDENCE.md`): R217 already tested the specified Kelly/own-performance
  overlays without meeting its bar. Do not repeat them unchanged. A volatility overlay needs a training-fixed
  constant-risk/exposure comparator before attributing lower drawdown to timing skill or confidence.
- The old 93k-cell grammar is not a current run plan. Use the [coverage ledger](RESEARCH_COVERAGE_LEDGER.md) to
  distinguish tested cells from open mechanisms. R226 closes six unsigned activity variants; R228 closes its fixed
  allocation grid; R229/R230 close their registered six-coin spot adaptations. Positioning changes, a flow context
  gate, partial execution on flow targets and the broader weekly C14 remain separate questions with specific input requirements. R231
  closes its two fixed adjustments on the R229 spot target. R222's MOM signal is a
  150-day formation window skipping the latest 30 days, not the weekly C14 portfolio.
- Context as a gate for the flow book (does top-vs-crowd pay more in some contexts?), the one use of R192/R195 left.
- Gate data from 2026-10 on are unseen (Gate keeps 180 days; refetch before 2027-03): a forward score of Gate's
  top-vs-crowd and of the long-cascade continuation / short-squeeze fade (both chosen after R206, so new lanes).
- Copy-trader persistence from forward leaderboard snapshots (C02, C21, C22), and on-chain whales (C04): daily
  Hyperliquid leaderboard (accounts >= USD 1M, about 7k rows) and hourly positions of 87 picks (top 50 by month and by
  all-time PnL) from 2026-10-19, as a change log (`scripts/scrape_hyperliquid.py`).
- Carry: forward monitor running (R220); reverse carry needs borrow data.
- Adaptive selection (battery_v1, R184): **held**. Its draft PREREG and code disagree on 10 points, including no
  decision code, no 2x costs and a holdout-boundary read (`experiments/battery_v1/REVIEW.md`).

## Known data defects
- **Forward pipeline audit (2026-10-19).** The fixes are recorded in each lane's `DEVIATIONS.md`.
  - Before about 15:30 UTC, the newest hour of each tick was averaged over 11 of its 12 five-minute rows: all coins
    at 10-19 08:00, 09:00 and 13:00. Hours now wait until complete.
  - XAUUSDT was traded as crypto on MEXC in R215 and R218's replay tickets. It is excluded from 10-19 on.
  - MEXC days could have closed on a forming bar; no ticket was affected.
  - R214's realized-lag book used the wrong time unit; no ticket was affected.
  - A failed fetch now aborts the tick instead of scoring a zero.
  - Production bins (all coins) agree with the archive's 87-93%. The 99% gate tested only the coins common to both.
- The archive has no metrics (order flow) for coins with non-ASCII names; their flow features are missing (0.16% of
  eligible cells). Live data include them.
- Live open interest does not yet line up with the archive hour by hour (OI is not used by the live books).
- Multi-hour labels (`lab/atlas.forward`) count a missing return inside the window as zero.
  - 0.12% of eligible 72 h windows contain one (0.04% at 24 h), on 69 symbols.
  - There are no infinite returns.
  - Resampled 4 h / 24 h bars can be partial: 0 of the eligible 4 h blocks are, and 2 of the 24 h blocks.
  - Both were found by the Codex review and measured on 2026-10-19. They are too rare to move any result, and kept for
    reproducibility.
- Returns are Binance traded-close to traded-close minus funding. They are not mark-price, index or fill PnL.
- **Dead tails (measured 2026-10-21).** After a delisting, Binance's kline archive keeps writing no-trade bars at a
  frozen close.
  - Since 2021 that is 1.29M hourly bars on 148 perps, 8.3% of all bars. BTCST runs from 2021 to 2026, and RAY, FTT
    and SC run for years.
  - `lab/panel.py` keeps them as prices, so a delisted coin shows a return of 0. It stays eligible while its trailing
    30-day volume still ranks it in the top 100.
  - This is the mechanism behind the integrity audit's "coins that leave the universe exit for free". Its effect on
    the hourly books is not measured here.
  - `lab/daily.py` drops every bar without a trade.
- Binance public-data issue #491 reports a 2026-06-25 change in the metrics `create_time` convention (cited by the
  Codex review). We checked SOLUSDT archive files for 06-10, 06-23..27 and 09-15:
  - Each day has 288 rows, with no duplicate midnight stamps.
  - The taker ratio matches the 5-minute kline that opens at the same stamp (correlation 1.000 at lag 0, about 0.15
    at ±1) on every day, before and after the date.
  - The ratio and OI snapshots have no independent archive to check against; they are unverified.

## Program
Program trials: 9,478,559 after R291 on this branch (`registry.program_trials()`), mostly correlated context-atlas cells. This raw
bookkeeping total is not a count of independent hypotheses. R228–R232 use previously viewed dates and are
exploratory; future confirmation requires outcomes collected after a frozen decision.
