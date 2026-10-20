# Edge scoreboard: the evidence for each edge, and how far it can go

As of 2026-10-20, after R269. Program trials: 9,477,562 on this branch. Every number comes from the cited lane's FINDINGS or journal.
The draft was checked line by line against the files by a verifier subagent, and its 11 mismatches and 12
overstatements are corrected here.

## How to read this
- **Windows:**
  - **In-sample** is 2021-01..2025-06: discovery 2021-23 plus validation 2024-25H1, where cells were chosen or gated.
    Validation is in-sample here.
  - **Holdout** is 2025-07..2026-09. It was the only out-of-sample window in the archive. More than ten lanes read it
    (R189-R233), and what they saw shaped later choices (X2, book B, R218). As of 2026-10-20 it is **spent at program
    level**: every holdout number below is exploratory, not a confirmation (`docs/CRITIQUE.md`).
    - It is spent for flow cells, listings, carry, context slices, VRP and the Coinbase premium.
    - The flow books' holdout was re-read later for descriptions (R213, R216, R217).
  - **Forward** is paper on live data from 2026-10-01.
    - Days 10-01..18 were replayed on 2026-10-19 from endpoint history.
    - On-time days start 2026-10-20.
    - **No edge has an on-time forward day yet.**
- Totals are sums of daily returns, not compounded.
- **What paper trading can prove.** With about 90 days of data, a one-sided 5% test reliably (80% power) detects only
  an annual Sharpe of about 5. A Sharpe-1.5 book needs about 1,000 days for 80% power (`docs/PAPER_REFINEMENT.md`).
  Forward paper here therefore does three things:
  1. it checks that the live signal, fills and costs match the archive;
  2. it catches a book that fails;
  3. it adds evidence slowly.
  On the holdout, carry passed a single test at 1x costs (t 2.07, about 1%/yr; t 1.14 at 2x) and the flow book did
  not (t 1.22).

## Scoreboard

| Edge | Best in-sample (where) | Holdout (out of sample) | Costs 2x / 3x | On the owner's venue (MEXC) | Paper lane now | Verdict |
|---|---|---|---|---|---|---|
| **Funding carry**: short perp + long spot when trailing 72 h funding > 20% APR | Discovery +12.7%/yr, t 3.80; validation +5.9%/yr, t 2.82 (R190) | **+1.45% over 457 d, t 2.07: passed at 1x only** (R191) | Holdout 2x +0.66%, t 1.14 | Funding on MEXC matches Binance (median trailing-APR gap 0.0004 on 40 coins, `experiments/carry_fwd/venue_check.json`). **MEXC lists spot pairs for small alts Binance lacks** (AKE, BR, BTW, Q, USELESS). Replay: MEXC invested 18/18 days, net about 0; Binance 0/18 (R220) | **R220** carry_fwd (Binance and MEXC), decision at 90 on-time days | **The only edge confirmed on a holdout.** Small (about 1%/yr since 2025; "economically small", R191), very low risk (holdout max DD 0.07%). Not usable in a prop account (R202) |
| **Flow book A**: three 72 h order-flow cells, short the crowded coins, universe-hedged | +42.6%/yr, t 3.25, positive all 5 years (R197); cells were chosen on these years, so this is selection-contaminated | All symbols on Binance: +82.9%/yr (sum +103.8%), **t 1.22: NOT CONFIRMED**, DD 47% (R198). **Crypto only: +22.33 bp/day, t 1.25** (R216) | In-sample 2x +26.9% (t 2.07), 3x +11.3%. Holdout crypto 2x +17.3, 3x +12.3 bp/day | MEXC crypto replay: +4.67% in 18 d, 2x +3.8%, 3x +2.9% (R215). BEAT and LAB carry about 68% of the holdout gross (R216) | **R215** (go_real at 90 d), **R221** (sequential, 365 d) | Strongest in-sample edge. Holdout positive, too noisy to confirm, concentrated in two coins |
| **X2**: book A sized by k² (coins where all three cells agree count more) | Sharpe 1.96 / 1.68 vs A 1.81 / 1.39 (disc / val, R217) | Sharpe 1.49 vs 1.05, DD 62% (R217; holdout already known) | Positive at 3x in every window (R217) | MEXC replay +6.2% vs A +4.7% (R218) | **R218** (go_real at 90 d), **R221** | **NULL by R217's frozen bar** (+0.15 / +0.29 missed +0.3 in both). Chosen afterwards to run forward as a hypothesis. Concentrated |
| **top_vs_crowd alone (B)**: short coins whose top traders are short against the crowd | +69.3%, t 2.64 (R197) | All symbols: t 2.72, DD 16% (R198, reported, not decided). **Crypto only: +18.25 bp/day, t 2.74** (R216; crypto-only DD not computed). Best holdout t in the lab | R197 2x +58.4%, 3x +47.5%; holdout crypto 2x +17.4, 3x +16.5 bp/day | MEXC crypto replay -0.10% (R215). R200's Binance replay +9.7% came entirely from TradFi (stock and commodity) perps (R216) | **R221** decides it (crypto only, MEXC); R215 reports it | Best holdout t, but never decided until R221. Forward replay is about zero |
| **Top-account positioning** (whale vs top, top accounts vs crowd, headcount) | Discovery: whale_vs_top bin 7 long +22.8 bp/day, t 2.07; topacct_vs_crowd short +16.1, t 2.54 (R211) | Not read. Validation t 1.31 and 0.85, stop (R211). Headcount book validation +20.1 bp/day, t 1.13 (R212) | R212 validation 2x +15.8, 3x +11.5 | not tested | none | NULL. The headcount book is mostly top_vs_crowd (residual +5.6, t 0.33, R212) |
| **Limit (maker) entries** on gross-replicated cells | Per trade at a 1-sigma limit, median +11.4 bp vs taker -9.8 bp (validation; +23.5 vs -3.4 in discovery) (R193) | Not read. Book validation +14%/yr, t 0.18 | Validation 2x -6%, 3x -26% | Web maker 0 on 1,106 of 1,200 MEXC contracts; **API maker 6 bp** since 2026-06-01 (MEXC notice) | none | NULL as a book: long-alt beta. The 0 maker fee applies to manual orders only |
| **Altcoin lead-lag** (big coins' last hour predicts alts) | Next-hour quintile spread +1.45 bp/h, discovery (R219) | Not read. The spread is still +0.93 in validation; no book passed discovery | Taker cost 370 bp/day vs gross 35 (H 1 h) | Maker-only version untested | none | NULL net. The spread persists but is far below cost. Usable only as an entry-timing overlay |
| **Atlas cells** (price, flow, clock; gross conditional returns) | Replication 47.6% vs placebo 9.1%; flow 35.6% vs 0% (R185) | Not read. Validation per-trade median 5 bp | Per trade, does not cover cost | n/a | none | Real gross edges, below taker cost per trade |
| **Context slice books** | 12-24 h slices +39.4%/yr, t 3.85 (selection-biased) (R201) | -6.5%/yr, t -0.13 (R204) | Holdout 2x -46% | n/a | none | NULL |
| **Merges of atlas cells** | Primary M1: gross +23.6%/yr (t 1.27), net -32.6%. Best variant (180 d window): gross +50.3% (t 2.68), net +0.5% (R186). R187: FAIL | Not read | Break-even cost 0.42x (primary), 1.01x (best) | n/a | none | NULL: gross below cost |
| **New-listing short** | Primary discovery t -1.94. Best of 48 configurations t -3.06 (R188) | 7 d net short -2.6%, t -0.78: NOT CONFIRMED (R189) | The right tail decides, not cost | MEXC lists faster; a 6-name sample was positive (subagent) | none | NULL; holdout spent |
| **Slow altcoin cross-sections** (low beta, residual momentum, MAX, premium net of funding) | Plain 30 d momentum +7.7 bp/day, alpha t 1.23 (R222) | Not read | Costs only 0.6-2.9 bp/day | n/a | none | NULL: the gross is too small |
| **Funding-settlement capture** (hold across a settlement at ±0.20%) | Funding +47.6 bp collected per event, price -72.3 (R223) | Not read | Net 1x -38.5 bp per event | MEXC rates match Binance, so it is closed there too | none | NULL: the price moves against the payment by more than it pays |
| **Trade count and mean print size** (activity, not signed flow; Codex's call) | count surge +6.1 bp/day, t 1.13, but corr 0.99 with quote volume; residual +0.3 (R226) | Not read | Costs 1.4-2.9 bp/day | MEXC klines have no trade count | none | NULL: count is quote volume in disguise |
| **Static allocation among flow books A/B/X2** (Codex) | Discovery picks 30% B / 70% X2; validation Sharpe 1.688 vs 1.681 for X2 alone, interval spans zero (R228) | Already viewed, descriptive only: mixture +35.2 bp/day vs X2 +42.5 | Not the deciding factor | n/a | none | NULL: mixing adds nothing over X2 |
| **Slow spot trend ensemble, six major coins** (Codex) | Validation Sharpe 1.261 vs 1.227 risk-matched passive (needs +0.15); drawdown 9.7% vs 7.2% (R229) | Already viewed, descriptive only: -0.51 bp/day | Validation positive at 2x | Spot only | none | NULL: fails risk-matched passive Sharpe and drawdown |
| **Weekly spot rotation, 96 rules** (Codex) | Selected 28 d momentum top 3 with BTC gate; validation Sharpe 0.83 vs 1.11 passive, family p = 1 (R230) | Already viewed, descriptive only: also loses | 2x mean +13.4 bp/day, market exposure | Spot only | none | NULL |
| **Execution and rebalancing of six-coin spot books** (Codex) | R231: half-step toward the R229 target, validation Sharpe 1.246 vs 1.261. R232: monthly equal-weight reset, validation Sharpe 1.053 vs 0.965 buy-and-hold (needs +0.15), paired interval spans zero | Already viewed, descriptive only | R231 saves 30% of cost but loses more gross | Spot only | none | NULL |
| **Regime gate on the flow books** (MacroHFT: trend x volatility sub-agents and a mixing hyper-agent) | No gate selected: A, B and X2 positive at 2x in all 4 regimes. Mix: validation Sharpe 1.80 vs 1.68 for X2 (bar +0.15) (R233) | Not read | Mix trails X2 by 0.7-1.5 bp/day at 2x-3x | Same books as R215/R218 | none | NULL |
| **Positioning impulse** (24 h / 72 h change in top-vs-crowd, queue M001) | All 4 fail discovery: best imp72/H +5.2 bp/day, t 0.90; residual vs level +2.8 (R234). 2023 alone about +24 bp/day (seen after the run) | Not read | imp72/H +1.0 at 2x, -3.1 at 3x | Same data as R215's B | none | NULL; follow-up M223 |
| **US index calendar** (turn-of-month, overnight drift; SPY/QQQ, first non-crypto lane) | Discovery 2000-12: TOM alpha +1.2 to +1.7 bp/day, t 1.2-1.5; QQQ overnight +1.8, t 1.36 (R235) | 2013-2026 not read | TOM alpha +1.0 at 3x; overnight negative at 2x | not on MEXC (ETFs or index futures) | none | NULL |
| **Amihud illiquidity** (long illiquid / short liquid, one-week hold, queue M002) | Discovery +11.9 bp/day, t 2.28; validation -9.2, t -1.07 (R236) | Not read | Costs 0.8 bp/day; loss is gross | MEXC lists more illiquid coins (untested there) | none | NULL |
| **Cross-asset trend** (12-month TSMOM, 23 ETF/FX/metal/bond series, queue M194) | Discovery 2001-12: Sharpe 0.28, t 1.00 (R237) | 2013-2026 not read | Costs 0.03-0.1 bp/day | not on MEXC | none | NULL |
| **Crypto cross-sectional battery** (weekly momentum and 28 d, daily MAX, IVOL, skew, 52-week high, funding slope, Abdi-Ranaldo spread; queue M034/M171/M178/M180/M182) | All 16 books fail discovery; best mom7/H +9.0 bp/day, t 1.77; five features are one high-volatility/winner tilt that paid in 2021 (R238) | Not read | Costs 0.6-1.8 bp/day; no verdict changes at 3x | Same coins on MEXC | none | NULL |
| **Forex and index battery** (G10 spot momentum, dollar trend, VIX reversal, Halloween, pre-holiday; queue M193/M216/M218/M219) | Discovery 2001-12: VIXREV-QQQ alpha +2.9 bp/day, t 1.94; FXMOM t 1.20; Halloween t 1.32; others below t 0.5 (R239) | 2013-2026 not read | Costs at most 0.2 bp/day | not on MEXC (ETFs, FX) | none | NULL; VIXREV-QQQ follow-up M226 |
| **Short volatility in contango** (long SVXY when VIX < VIX3M; queue M224/M214) | Discovery 2011-16 +21.6 bp/day, t 2.39; validation 2017-19 +15.2, t 1.82, decided by one exit on 2018-02-05 (R241) | Holdout 2020-26 +7.5 bp/day (+19%/yr), t 1.70; max drawdown 50%, worst day -21.5% | Costs 0.15 bp/day | not on MEXC; US ETF | none: fails gate 1, and its drawdown fails gate 3 | NULL (closest cross-market result) |
| **Positioning impulse, follow-up** (queue M223) | 2024-25 only: imp24/H -0.7 bp/day; imp72/H +6.6, t 1.33 (R240) | Not read | imp72/H -2.3 at 3x | Same data as R215's B | none | NULL; family closed at 6 trials |
| **Crypto time-series rules** (week-open bias, pre-FOMC drift, ETH/BTC regime, vol-managed trend; queue M013/M191/M009/M184) | Vol-managed trend +6.0 bp/day, t 2.07, beta -0.03 at 0.37 gross exposure; the other three t <= 0.54 (R242) | Not read; trend validation +2.0, t 0.52 | Trend costs 0.6 bp/day; week-open loses at 3x | Same coins on MEXC | none | NULL |
| **Classic chart rules** (Supertrend+RSI, MACD, Stochastic, CCI, Bollinger, Ichimoku, pivots; 4 h and 1 d; queue M005/M200/M202/M203) | All 14 fail discovery; best Supertrend+RSI 1d +11.3 bp/day, t 1.23; fades and pivot breaks lose (R243) | Not read | 4 h trend rules lose to 6-9 bp/day cost | Same coins on MEXC | none | NULL |
| **BTC weekend move to US equities** (queue M198) | Correlation +0.46 with the QQQ opening gap (priced), +0.07 with the session; rule t -0.14 (R244) | Not read | 2 bp per trade | ETFs, not MEXC | none | NULL |
| **Reversal by liquidity tercile** (1 d and 7 d; queue M008/M181) | 1 d books -13.6 to -17.5 bp/day (cost 9-12); 7 d illiquid 0.0, liquid -6.2 (R245) | Not read | A 24 h hold costs more than any gross | Same coins on MEXC | none | NULL |
| **ICT levels** (round-number crosses and rejections, SMT divergence vs BTC, 8 AM New York range; queue M010-M012) | All 8 fail discovery; SMT fade 24 h +2.0 bp/day (gross +11.3), t 0.29; round-number books -40 to -85 (R246) | Not read | Round-number books cost 31-67 bp/day; none positive at 2x | Same coins on MEXC | none | NULL; post-hoc round-vs-shifted-grid reversal (t -3.30) queued as M230 |
| **Chart rules on forex and world indices** (R243's seven rules, daily, 11 FX pairs and 10 indices; queue M210/M200/M202/M203) | All 14 fail discovery 2001-12; best CCI fade on indices alpha +1.5 bp/day, t 1.50; FX nothing above t 1; pivot breaks lose (FX t -2.49, indices t -4.16) (R247) | 2013-2026 not read | Costs 0.1-0.8 bp/day; CFD spreads would be 2-5x | FX and index CFDs at prop firms, not MEXC | none | NULL; pivot fade queued as M231 |
| **Pivot fade** (mirror of PIVOT_BREAK, post hoc from R247; queue M231) | Discovery spent (R247: break alpha t -4.16 on indices 2001-12) | Validation: indices 2013-19 alpha -0.57, t -0.62; forex +0.46, t 0.98; crypto 2024-25 4 h -9.9, 1 d -8.3 bp/day, gross negative (R248) | Costs 0.7 bp/day (forex, indices) take most of the gross | FX/index CFDs | none: failed gate 1 | NULL; family closed |
| **Round-number fade** (first close through a level per coin-day, vs a half-step-shifted grid; queue M230/M011) | Post hoc in 2021-23 (R246): crosses of round levels reverse 10.8 bp/day more than shifted levels, t -3.30 | Validation 2024-25: round minus shifted +4.8 bp/day, t 2.53 (mechanism replicates); best book RN2SF/24 +8.8, t 0.88 (R249) | Taker cost 10-13.5 bp/day equals the gross; nothing positive at 3x | Same coins on MEXC; maker version M232 | none | NULL as a book; mechanism confirmed gross |
| **Pairs trading** (distance and Engle-Granger, weekly 30-day formation; queue M045) | All 4 fail discovery; gross -1.6 to +2.5 bp/day; 59-78% of trades end unreverted at week end (R250) | Not read | Costs 1.1-2.0 bp/day; gross is the problem | Same coins on MEXC | none | NULL |
| **Brute-force chart strategies** (5,472: EMA, Donchian, RSI, Bollinger, Supertrend, Fibonacci, TS momentum, MACD, VWAP x 1 h/4 h/12 h/1 d x direction/filter/stop; walk-forward 'what works now'; queue M204/M228) | Walk-forward (6 m lookback) +1.18 bp/day, t 0.96, 2021-07..2025-06; beats random picks (p 0.001), but the pool averages -1.02. Best single: discovery t 3.11, reality check p 0.334 (R263) | Best single in validation (2024-01..2025-06): t 0.02. Spent window, walk-forward +1.01 bp/day | Walk-forward 2x +0.29, 3x -0.61 bp/day | Not run | None. Best single and walk-forward stream pre-committed to the first 2020 batch | NULL. 1 h rules lose to costs; trend families track the size of BTC's move, which the trailing 6 months do not predict |
| **Kernel chart patterns** (Lo-Mamaysky-Wang HS, broadening, triangles, rectangles; daily crypto, FX, indices; queue M201) | HS-only on indices alpha t 2.27 (2001-12); others below t 1.5 (R251) | Indices 2013-19: alpha -0.02, t -0.18 | Costs below 0.1 bp/day | FX/index CFDs; crypto on MEXC | none: failed validation | NULL |
| **Liquidation-cascade fade** (hourly OI drop >= 3% plus a >= 3 ATR wick; queue M176) | All 4 fail discovery (effectively 2022-23); best ALL/24 +2.0 bp/day, t 1.93; squeeze-only t 1.03. Both sides revert raw, but the long-side bounce is mostly the market's: +23 bp market-adjusted over 24 h, post hoc (R252) | Not read | Costs 0.04-0.21 bp/day | Same coins on MEXC | none | NULL; cascade-count market timing queued as M233 |
| **Cascade-count market timing** (long the EW market 24 h after hours with >= 3 cascade triggers; queue M233) | Post hoc from R252; 2021-23 book t 0.23 | Validation 2024-25: +5.6 bp/day, t 1.03; 15 events, all in 2024; market +186 bp over 24 h after them (R255) | Costs 0.4-0.5 bp/day | EW perps on MEXC | none | NULL: too rare to prove |
| **Day of week** (SPY, world indices, USD, BTC, crypto; one weekday selected per market; queue M219) | All 5 picks fail discovery; best crypto Monday short alpha t 0.84 (R256) | Not read | Weekly round trips cost 0.4-2.1 bp/day, more than any weekday alpha | Any | none | NULL |
| **TradFi perps lead crypto** (gold/oil and US equity perps' last hour -> crypto market or beta cross-section, 1-24 h; queue M004) | All 12 selected books fail discovery 2026-01..05; best EQ/TS/24 -0.1 bp/day, t -0.08. Same-hour corr +0.34 (EQ), next-hour corr -0.007 (R261) | Not read (2026-06..09 unread) | 1-4 h holds pay 10-116 bp/day; 24 h cost exceeds gross | Any | none | NULL |
| **Variance risk premium, S&P 500** (measurement; queue M215) | VIX² minus next-month realised variance: +116 %², t 2.55; validation +70, t 5.71 (R239) | Holdout +82, t 1.11 (2020 loss) | Not tradeable with free data before 2011 | not on MEXC | none | Measured, not a book; short-vol lane M224 |
| **Gate signal, liquidation fade, carry-crash, VRP, Coinbase premium, intraday momentum, daily stop rules** | Liquidation fade h12 t -1.96 (R206). Carry crash reversed, t -2.06 (R207). VRP t 1.06 (R209). Coinbase premium t 0.34 (R210). Intraday momentum net negative (R203). Stops harmful (R208) | VRP +1.1 bp/day, t 0.12; Coinbase premium t 0.88; carry crash -3.0%. The Gate signal's window (t 1.43, vs 2.08 for Binance's own signal on the same coins) lies inside the spent flow holdout (R205) | — | — | none | NULL (stops: HARMFUL) |
| **Unlock short**: short at the close of D-7, cover at the close of an insider/private-sale cliff unlock of at least 1% of max supply (old R179/R181) | **Replicated here, gate 0: +3.24% net per event, week-cluster t 3.19, null p 0.0005, 422 events 2021-26** (R265). Codex's daily-bar run gives +3.26%, t 3.20 (R258, PR #29). Dose: >=5% of supply +9.9%; unlock >= 0.82 days of ADV +6.3% | None clean: the old session read 2021-26 and the calendar is today's snapshot. Reserved: 30 events in 2020, 41 MEXC-only, 15 after the archive | 2x +3.04% (t 2.99), 3x +2.84% (t 2.79). Funding -0.43% per event; Codex bounds it at 23-82 bp (R259) | 367 of 437 calendar events from 2026-10-21 have a MEXC contract | **R266** unlocks_fwd (MEXC, point-in-time calendar), decision at 120 scored tickets; first ticket RESOLV (2026-10-27) | **Largest per-event edge on file, in-sample only.** Tail: six closes lost over 40% (RIVER -132%); intraday highs far worse (STO +1,623%, R258). Needs a frozen sizing and protective model before any stake |
| **Delisting-notice short**: short the USD-M perp at the first hourly open after a Binance "Will Delist" notice, cover +1 h / +24 h (old E03) | Gate 0, NULL: +1 h -0.12% per notice, t -0.06 (68 clusters, 2022-26; R267). Spot notices alone at +1 h: +4.15%, t 3.07, n 25 (logged variant, 1 of 8) | None clean: the old session read 2022-26. No reserved notices (the catalog starts in 2022) | Primary 2x -0.52%, 3x -0.92%. Spot +1 h: 2x +3.75%, 3x +3.35% | Not checked: MEXC spreads after a Binance notice | **R268** delist_fwd (spot notices, MEXC, from 2026-10-20 18:00 UTC), decision at 12 scored notices | Futures notices carry a squeeze tail (ANC -95%, SLERF -87% in an hour). Spot +1 h was picked after the run |
| **Monitoring Tag short**: short the perp at the first hourly open after Binance extends its Monitoring Tag to the coin, cover +1 h / +24 h / +72 h (queue M260) | Gate 0, NULL: +1 h +0.61% per notice, t 0.71 (24 clusters, 2023-26; R269). +24 h: +4.36%, t 3.81; BTC-hedged +3.86%, t 3.26 (logged variants, 2 of 6). 2026: +1.31% (n 11), last 5 -0.92% | None clean: the tag began in 2023-07, inside the archive. No reserved notices | +24 h 2x +3.96% (t 3.46), 3x +3.56% (t 3.11). Funding -0.14% per notice at +24 h | Not checked: MEXC spreads after a tag notice | Forward lane candidate (+24 h on MEXC, new id) | NULL (primary); forward candidate |

## The best achievable edges, ranked
1. **Funding carry on MEXC.** It is the only edge that passed its holdout test (t 2.07 at 1x costs, about 1%/yr;
   not significant at 2x), and the MEXC version has more coins to carry.
   - **Size:** about 1%/yr in the 2025-26 regime, +8% in 2024, +35% in 2021. It is the safest edge, not the largest.
   - **Falsified by:** R220 failing at 90 on-time days. At 2x costs it was not significant even on the holdout.
   - **To trade it:** a MEXC spot buy plus a perp short of the same size, placed by hand by the owner, only after
     `go_real`.
2. **Unlock short on MEXC (new, 2026-10-20).** It replicates at gate 0 with the largest per-event edge in the lab:
   +3.24% net per event, t 3.19 (R265), and Codex's independent daily-bar run agrees (R258).
   - **Size:** about 150 events a year in 2025-26. At 10% of capital per event that is roughly +45%/yr before tail
     losses. This is in-sample arithmetic, not a forecast.
   - **Falsified by:** R266 failing at 120 scored tickets (futility check at 60), or the reserved batch (2020,
     MEXC-only coins, post-archive events).
   - **Risk:** short squeezes. Six of 422 closes lost over 40%, and intraday highs were far worse. A liquidation at
     2x would have hit several events. Sizing and protection must be frozen before any stake.
3. **Flow book A, or X2, on MEXC crypto.**
   - **Size:** the largest returns in the archive, not confirmed. Crypto-only holdout +22.3 bp/day (about +80%/yr
     simple), t 1.25, drawdowns of 47-62% across versions.
   - **Falsified by:** R215 or R218 failing their 90-day screen, or R221's futility stop at day 90.
   - **Evidence needed:** confirmation needs R221's look at 182 or 365 days.
   - **Risk:** two coins carried two thirds of the holdout gross.
4. **top_vs_crowd, crypto only, on MEXC.**
   - **Size:** holdout t 2.74 on crypto only, but it is the best of 7 series reported after the holdout was read.
     Without its 10 best days of 457 it falls to t 1.6, and its MEXC replay is -0.6 bp/day. The all-symbol drawdown was 16%.
   - **Status:** the forward replay is about zero. It is now decided by R221.
5. **Everything else is NULL net of costs.**
   - The gross edges (atlas cells, lead-lag spread) are real but smaller than a taker's cost.
   - The route left open for them is execution: maker orders placed by hand on MEXC at 0 fee, or an overlay on books
     that trade anyway.

## Refinements already measured
| Refinement | Effect | Where |
|---|---|---|
| Dispersion x alt-bear half-size gate on A/B/X2 (momentum-crash rule) | Sharpe -0.05 / -0.00 / -0.05 in discovery, -0.05 / -0.02 / -0.04 in validation; the gated days were good days for the books | R260 |
| Bridging zero-filled gaps (PR #25 audit item 4) | No change: no held position meets a gap in discovery or validation for A, B or X2 | R264 |
| Square-root impact at size (Binance volumes) | Under 1.5% of net at $10k; A/X2 keep half their net up to about $12M, B up to $129M | R262 |
| X2 agreement sizing on A | Sharpe +0.15 / +0.29 / +0.45 (disc / val / holdout); misses the frozen bar | R217 |
| Volatility target on A | Holdout max DD 47% to 27%, Sharpe flat. Now runs forward on A, B and X2 (R225); today's multiplier A 0.69, X2 0.63, B 0.99 | R217, R225 |
| Crypto only | B holdout t 2.74 (vs 2.73 all symbols). A's 18-day replay drops from +22.5% to +8.7% | R216 |
| Entry one or two hours late | Costs 1-2% of net | R213 |
| Daily loss/profit stops | Harmful in 30 of 30 variants | R208 |
| Confidence (own-model) scaling | No support out of sample | R217 |

## Discrepancies on file
- **Decision rules differ.**
  - R200 decides at 90 *scored* days (replay included) with NW t >= 2 plus go_real.
  - R214, R215 and R218 decide at 90 *on-time* days with go_real only. R214's PREREG line 29 says "same gate as
    R200", but its operative rule is go_real.
  - R221 adds a long-horizon statistical decision for the MEXC books.
- **Registry "CONFIRMED" mixes in-sample and holdout.** The registry marks in-sample passes CONFIRMED: R181, R185,
  R190, R192, R195 and R197. Only R191 is confirmed on a holdout.
- **R209:** the registry says 6 of 8 variants lost on the holdout; its FINDINGS says 7 of 8.
- **MEXC fees.** R215 and R218 charge Binance tier costs: 6-20 bp one way, fee plus slippage.
  - Manual MEXC web orders pay 0-4 bp maker and 0-10 bp taker (2 bp on most contracts).
  - API orders pay 6 bp maker and 8 bp taker since 2026-06-01.
  - The model is conservative for manual trading and about right for API trading.
  - **R224 now measures this from MEXC's order book at every tick.** The first snapshot (32 crypto contracts) gives a
    median one-way cost for a $10k order of 2.5 bp on the web and 9.6 bp through the API, against 8 bp assumed. The
    report starts 2026-11-03.
- **Forward pipeline audit (2026-10-19).** Fixes and the journal rows they leave behind are in each lane's
  `DEVIATIONS.md`: partial newest hours, XAU traded as crypto on MEXC, a forming-bar risk and a lag-unit bug.
