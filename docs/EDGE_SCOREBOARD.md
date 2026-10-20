# Edge scoreboard: the evidence for each edge, and how far it can go

As of 2026-10-20, after R230. Program trials: 9,471,884. Every number comes from the cited lane's FINDINGS or journal.
The draft was checked line by line against the files by a verifier subagent, and its 11 mismatches and 12
overstatements are corrected here.

## How to read this
- **Windows:**
  - **In-sample** is 2021-01..2025-06: discovery 2021-23 plus validation 2024-25H1, where cells were chosen or gated.
    Validation is in-sample here.
  - **Holdout** is 2025-07..2026-09. It is the only out-of-sample window in the archive. It was read once per family
    for that family's decision.
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
  The holdout gave one clear verdict each way: carry confirmed (t 2.07) and the flow book not confirmed (t 1.22).

## Scoreboard

| Edge | Best in-sample (where) | Holdout (out of sample) | Costs 2x / 3x | On the owner's venue (MEXC) | Paper lane now | Verdict |
|---|---|---|---|---|---|---|
| **Funding carry**: short perp + long spot when trailing 72 h funding > 20% APR | Discovery +12.7%/yr, t 3.80; validation +5.9%/yr, t 2.82 (R190) | **+1.45% over 457 d, t 2.07: CONFIRMED** (R191) | Holdout 2x +0.66%, t 1.14 | Funding on MEXC matches Binance (median trailing-APR gap 0.0004 on 40 coins, `experiments/carry_fwd/venue_check.json`). **MEXC lists spot pairs for small alts Binance lacks** (AKE, BR, BTW, Q, USELESS). Replay: MEXC invested 18/18 days, net about 0; Binance 0/18 (R220) | **R220** carry_fwd (Binance and MEXC), decision at 90 on-time days | **The only edge confirmed on a holdout.** Small (about 1%/yr since 2025; "economically small", R191), very low risk (holdout max DD 0.07%). Not usable in a prop account (R202) |
| **Flow book A**: three 72 h order-flow cells, short the crowded coins, universe-hedged | +42.6%/yr, t 3.25, positive all 5 years (R197) | All symbols on Binance: +82.9%/yr (sum +103.8%), **t 1.22: NOT CONFIRMED**, DD 47% (R198). **Crypto only: +22.33 bp/day, t 1.25** (R216) | In-sample 2x +26.9% (t 2.07), 3x +11.3%. Holdout crypto 2x +17.3, 3x +12.3 bp/day | MEXC crypto replay: +4.67% in 18 d, 2x +3.8%, 3x +2.9% (R215). BEAT and LAB carry about 68% of the holdout gross (R216) | **R215** (go_real at 90 d), **R221** (sequential, 365 d) | Strongest in-sample edge. Holdout positive, too noisy to confirm, concentrated in two coins |
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
| **Gate signal, liquidation fade, carry-crash, VRP, Coinbase premium, intraday momentum, daily stop rules** | Liquidation fade h12 t -1.96 (R206). Carry crash reversed, t -2.06 (R207). VRP t 1.06 (R209). Coinbase premium t 0.34 (R210). Intraday momentum net negative (R203). Stops harmful (R208) | VRP +1.1 bp/day, t 0.12; Coinbase premium t 0.88; carry crash -3.0%. The Gate signal's window (t 1.43, vs 2.08 for Binance's own signal on the same coins) lies inside the spent flow holdout (R205) | — | — | none | NULL (stops: HARMFUL) |
| **Unlock short** (original project, R180/R181) | Top tercile +5.84%, n 138, t 4.06 (R181) | Forward tickets armed 2026-10-12 (R180); first score 2026-10-20 | not reported | not stated | lives in the original project; **not in this repo** | Promising in-sample; cannot be checked here |

## The best achievable edges, ranked
1. **Funding carry on MEXC.** It is the only edge confirmed on a holdout, and the MEXC version has more coins to
   carry.
   - **Size:** about 1%/yr in the 2025-26 regime, +8% in 2024, +35% in 2021. It is the safest edge, not the largest.
   - **Falsified by:** R220 failing at 90 on-time days. At 2x costs it was not significant even on the holdout.
   - **To trade it:** a MEXC spot buy plus a perp short of the same size, placed by hand by the owner, only after
     `go_real`.
2. **Flow book A, or X2, on MEXC crypto.**
   - **Size:** the largest returns in the archive, not confirmed. Crypto-only holdout +22.3 bp/day (about +80%/yr
     simple), t 1.25, drawdowns of 47-62% across versions.
   - **Falsified by:** R215 or R218 failing their 90-day screen, or R221's futility stop at day 90.
   - **Evidence needed:** confirmation needs R221's look at 182 or 365 days.
   - **Risk:** two coins carried two thirds of the holdout gross.
3. **top_vs_crowd, crypto only, on MEXC.**
   - **Size:** the best holdout t, 2.74 on crypto only. The all-symbol drawdown was 16%.
   - **Status:** the forward replay is about zero. It is now decided by R221.
4. **Everything else is NULL net of costs.**
   - The gross edges (atlas cells, lead-lag spread) are real but smaller than a taker's cost.
   - The route left open for them is execution: maker orders placed by hand on MEXC at 0 fee, or an overlay on books
     that trade anyway.

## Refinements already measured
| Refinement | Effect | Where |
|---|---|---|
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
