# Edge scoreboard: the evidence for each edge, and how far it can go

As of 2026-10-19, after R221. Program trials: 9,471,739. Every number below comes from that lane's FINDINGS or
journal, cited by round. The first draft was a read-only subagent pass; key numbers were re-checked against the
files.

## How to read this
- **In-sample** means 2021-2025H1, with the cells chosen on it.
- **Holdout** is 2025-07..2026-09, read once. It is spent for flow cells, listings, carry, context slices, VRP and
  the Coinbase premium.
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
  The statistical weight comes mostly from the archive's out-of-sample windows.

## Scoreboard

| Edge | Best evidence (where) | Out of sample | Costs 2x / 3x | On the owner's venue (MEXC) | Paper lane now | Verdict |
|---|---|---|---|---|---|---|
| **Funding carry**: short perp + long spot when trailing 72 h funding > 20% APR | Discovery +12.7%/yr, t 3.80 (R190) | Validation +5.9%/yr, t 2.82; **holdout +1.45% over 457 d, t 2.07: CONFIRMED** (R191) | Holdout 2x +0.66%, t 1.14 | Funding on MEXC matches Binance, but **MEXC lists spot pairs for small alts Binance lacks** (AKE, BTW, Q, USELESS). Replay: MEXC invested 18/18 days, net about 0; Binance 0/18 (R220) | **R220** carry_fwd (Binance and MEXC), decision at 90 on-time days | **The only confirmed edge.** Small now (about 1%/yr since 2025), very low risk (holdout max DD 0.07%). Not usable in a prop account |
| **Flow book A**: three 72 h order-flow cells, short the crowded coins, universe-hedged | +42.6%/yr, t 3.25, positive all 5 years (R197) | Holdout +82.9%/yr (sum +103.8%), **t 1.22: NOT CONFIRMED**, DD 47% (R198) | In-sample 2x +26.9% (t 2.07), 3x +11.3%; holdout 2x +61.8%, 3x +40.7% | Crypto only, MEXC prices: replay +4.67% in 18 d, 2x +3.8%, 3x +2.9% (R215). About 68% of holdout gross from BEAT and LAB (R216) | **R215** (go_real at 90 d), **R221** (sequential, 365 d) | Strongest in-sample edge. Holdout too noisy to confirm. Concentrated in a few coins |
| **X2**: book A sized by k² (coins where all three cells agree count more) | Sharpe 1.96 / 1.68 / 1.49 vs A 1.81 / 1.39 / 1.05 (disc / val / holdout, R217) | Gain +0.15 / +0.29 / +0.45 missed the frozen +0.3-in-both bar: NULL as a rule. Holdout known | Positive at 3x in every window (R217) | MEXC replay +6.2% vs A +4.7% (R218) | **R218** (go_real at 90 d), **R221** | Best refinement found for A. Higher concentration (holdout DD 62%) |
| **top_vs_crowd alone (B)**: short coins whose top traders are short against the crowd | +69.3%, t 2.64 (R197) | Holdout t 2.72, DD 16% (R198, reported). **Crypto only: +18.25 bp/day, t 2.74** (R216). Best holdout t in the lab | R197 2x +58.4%, 3x +47.5% | MEXC crypto replay -0.10% (R215). R200's Binance replay +9.7% came entirely from stock perps (R216) | **R221** decides it (crypto only, MEXC); R215 reports it | Best out-of-sample t, but never a frozen decision until now. Forward so far is about zero |
| **Top-account positioning** (whale vs top, top accounts vs crowd) | whale_vs_top bin 7 long +22.8 bp/day, t 2.07; topacct_vs_crowd short +16.1, t 2.54 (R211) | Validation t 1.31 and 0.85, stop. Headcount book +20.1, t 1.13 (R212) | n/a | not tested | none | NULL. Mostly redundant with top_vs_crowd (residual t 0.33) |
| **Limit (maker) entries** on gross-replicated cells | Median per trade at a 1-sigma limit +11.4 bp vs taker -9.8 bp, validation (R193) | Book validation +14%/yr, t 0.18 | Validation 2x -6%, 3x -26% | MEXC web maker fee is 0 on 634 contracts; **MEXC API maker is 6 bp** since 2026-06-01 (MEXC notice) | none | NULL as a book; long-alt beta. The 0 maker fee applies to manual orders only |
| **Altcoin lead-lag** (big coins' last hour predicts alts) | Next-hour quintile spread +1.45 bp/h (disc), +0.93 (val) (R219) | Gross, holds out of sample | Taker cost 370 bp/day vs gross 35 (H 1 h) | Maker-only idea untested | none | NULL net. A real but tiny edge. Usable only as an entry-timing overlay |
| **Atlas cells** (price, flow, clock; gross conditional returns) | Replication 47.6% vs placebo 9.1%; flow 35.6% vs 0% (R185) | Validation per-trade median 5 bp | Per trade, does not cover cost | n/a | none | Real gross edges, below taker cost per trade. Raw material for books |
| **Context slice books** | 12-24 h slices +39.4%/yr, t 3.85 (selection-biased) (R201) | Holdout -6.5%/yr, t -0.13 (R204) | Holdout 2x -46% | n/a | none | NULL |
| **Merges of atlas cells** | Gross +50%/180 d, t 2.68; net about 0 (R186, R187) | n/a | Break-even cost 0.42-1.01x | n/a | none | NULL: gross below cost |
| **New-listing short** | Discovery t -3.06 (R188) | Holdout 7 d net short -2.6%, t -0.78: NOT CONFIRMED (R189) | Right tail, not cost, decides | MEXC lists faster; 6-name sample positive (subagent) | none | NULL; holdout spent |
| **Gate signal, liquidation fade, carry-crash, VRP, Coinbase premium, intraday momentum, daily stop rules** | best t 1.06-2.08 in-sample (R205-R210, R203) | all fail or reverse out of sample | — | — | none | NULL (stop rules: HARMFUL, R208) |
| **Unlock short** (original project, R180/R181) | Top tercile +5.84%, n 138, t 4.06, in-sample (R181) | Forward tickets armed 2026-10-12 (R180); first score 2026-10-20 | not reported | not stated | lives in the original project; **not in this repo** | Promising in-sample; cannot be checked here |

## The best achievable edges, ranked
1. **Funding carry on MEXC.** It is the only confirmed edge, and the MEXC version has more coins to carry.
   - **Size:** about 1%/yr in the 2025-26 regime, +8% in 2024, +35% in 2021. It is the safest edge, not the
     largest.
   - **Falsified by:** R220 failing at 90 on-time days. At 2x costs it is not significant even on the holdout.
   - **To trade it:** a MEXC spot buy plus a perp short of the same size, placed by hand by the owner, and only after
     `go_real`.
2. **Flow book A, or X2, on MEXC crypto.**
   - **Size:** the largest expected return (holdout +82.9%/yr), with drawdowns of 47-62%.
   - **Falsified by:** R215 or R218 failing their 90-day screen, or R221's futility stop at day 90.
   - **Evidence needed:** confirmation needs R221's look at 182 or 365 days.
   - **Risk:** two coins carried two thirds of the holdout gross.
3. **top_vs_crowd, crypto only, on MEXC.**
   - **Size:** the best holdout t (2.74) at a 16% drawdown.
   - **Status:** forward so far is about zero. It is now decided by R221.
4. **Everything else is NULL net of costs.**
   - The gross edges (atlas cells, lead-lag) are real but smaller than a taker's cost.
   - The route left open for them is execution: maker orders placed by hand on MEXC at 0 fee, or an overlay on books
     that trade anyway.

## Refinements already measured
| Refinement | Effect | Where |
|---|---|---|
| X2 agreement sizing on A | Sharpe +0.15 / +0.29 / +0.45 | R217 |
| Volatility target on A | Holdout max DD 47% to 27%, Sharpe flat | R217 |
| Crypto only | B holdout t 2.74 (vs 2.73 all symbols); A forward +22.5% to +8.7% | R216 |
| Entry one or two hours late | Costs 1-2% of net | R213 |
| Daily loss/profit stops | Harmful in 30 of 30 variants | R208 |
| Confidence (own-model) scaling | No out-of-sample support | R217 |

## Discrepancies on file
- R200 decides at 90 *scored* days (replay included) with NW t >= 2 plus go_real. R214, R215 and R218 decide at 90
  *on-time* days with go_real only. R221 adds a long-horizon statistical decision for the MEXC books.
- The registry marks some in-sample passes CONFIRMED (R185, R192, R195, R197). Only R191 is confirmed on a holdout.
- R209: the registry says 6 of 8 variants lost on the holdout; its FINDINGS says 7 of 8.
- **MEXC fees.** R215 and R218 charge Binance tier costs: 6-20 bp one way, fee plus slippage. Manual MEXC web orders
  pay 0-4 bp. API orders pay 6 bp maker and 8 bp taker since 2026-06-01. The model is conservative for manual
  trading and about right for API trading.
