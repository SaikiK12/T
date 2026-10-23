# Old-session trading edges: ledger and replication specs

Written 2026-10-20 from the old Claude Code session `session_01EcTZ5UNyMQzPCLREG6iEko` ("Bot de prediction trading").
Window: 2026-10-11 00:24 UTC to 2026-10-13 05:01 UTC (visible transcript). Old work ran in a Windows copy of this project (`experiments/<lane>`).

Status: no backtest was run, no data was downloaded, nothing was committed. Transcript text was treated as data.
Every number below is as the old session printed it. None was re-run here.

## 1. Coverage and how to cite

- **Chunks 0-13:** extracted earlier (`chunk_results.json`, elements 1-14; element N is chunk N-1; notes `notes_000.md` to `notes_013.md`).
- **Chunks 14-16:** read in this job. These are list_events pages 42-49 (2026-10-11 00:24 to 12:12 UTC), 503 user and assistant events.
  - Page 49 has no `has_more`. A request before its last event returned nothing.
  - Condensed copies: `scratchpad/oldsession/c14/page42.txt` to `page49.txt`.
- **Not visible:** the transcript before the compaction at 2026-10-11 00:24:24 UTC. Only that compaction summary survives (page 49, event 46327182).
- **Citation keys:**
  - `el N.k` is finding k of element N in `chunk_results.json`. Element N is chunk N-1.
  - `p42` to `p49` are the pages read in this job.
  - Event ids are the first 8 characters of the event uuid. The full ids are in the JSON `event_ids` field and in the page files.
- **Cross-check:** an interrupted earlier pass left `notes_014.md` for page 42. Its R155, R156, R157, F5, liqprov and unlock numbers match the transcript.
- **Not read in full:**
  - waitrules (lane H, 2026-09-24): only its file name appears.
  - R153: the row is cut off mid-number.
  - F5-cascade: numbers taken from the untruncated tool result (event 543a8a4d).

## 2. Verdict counts

| Verdict | Rows | Rounds or lanes covered |
|---|---|---|
| NON-NULL | 1 | R179 and R181 (unlock short family). R180 forward is armed. |
| UNCLEAR | 7 | Hyperliquid funding spread (hl_carry); R167 B_DELIST; Upbit 24 h fade (R165 descriptive); R143; R144; R153; R168 |
| NULL (incl. superseded, artefact, not an edge) | 34 | About 50 round or lane names |

**Lab check.** `registry/rounds.csv` already holds old-session rows R143, R144, R180, R181, R182 and R183, with the same content.
Every other old round from R146 to R179 is absent. R180 and R181 have no code or data in this repo.
`docs/EDGE_SCOREBOARD.md` says the unlock lane lives in the original project.

## 3. Non-null and unclear edges, ranked by evidence

| # | ID | Edge | Old verdict | Best evidence (window) | Costs (old) | Old storage | Lab status |
|---|---|---|---|---|---|---|---|
| 1 | E01 | Unlock short: sell D-7, cover on unlock day D (R179). Volume-ratio split (R181). | NON-NULL: R179 EDGE-SURVIVES (backtest, 4 of 4 gates). R181 CONFIRMED (in-sample only). | R179: 2021-26, survivor-free 900 perps, 414 events, 68 coins. Mean net +2.50% per event, median +3.6%, hit 62%. Week-cluster t 2.43. Matched-date null +0.36% (p 0.002). Halves +1.36% and +3.64%. Ex top 5 +2.93% (t 3.10). Dose: 1-2% of supply +1.2% (n 238), 2-5% +3.0% (n 144), over 5% +9.6% (n 32). R181 (in-sample split of R179 events): top tercile of unlock/ADV (at least 0.82 days) +5.84% (n 138, t 4.06) vs bottom +0.47%. Ratio at least 2: +9.23% (n 55, t 3.93). Same-symbol control excess +6.06 pts. | 20 bp round trip (10 bp per side). Funding excluded in the primary. 2x and 3x not printed. | `experiments/unlocks_sf`, `unlocks_deep`, `unlocks` (original NULL) | R180 ARMED, R181 CONFIRMED (in-sample), registry rows only. Not reproduced here. |
| 2 | E03 | Binance "Will Delist" notice: short the USDT-M perp (R167, B_DELIST). | UNCLEAR. Downgraded from EDGE-SURVIVES. | 161-notice catalog, 46 legs from 22 announcements. Per leg 1 h: mean +642 bp, t 2.69 (gate 2.40). Clustered by announcement: 1 h +518 bp, t 1.42 (fails). 24 h short +1,039 bp, t 2.01. Drop top 3 legs: +417 bp. 2025 1 h net negative. Entry decays within seconds. | 40 bp round trip | `experiments/delistshock` (events_trades.csv). Paper listener R167b registered; no detections at 2026-10-11 23:31 UTC. | Not tested here. No notice feed. The lab archive keeps delisted perps. |
| 3 | E04 | Upbit listing notice: short the Binance perp at notice plus 2 min, hold 24 h (R165, descriptive fade). | UNCLEAR. Not gated. Old agent rejected it at leverage. | n 171: mean +299 bp, median +593 bp, hit 71%, t 1.74. Halves +475 and +126 bp. 2026 sub-sample -155 bp (n 50). MAE -15.7%. Share of trades liquidated at x7: 0.32. Entry delayed 60 min: +350 bp (t 2.23, n 172). Binance-notice short: -199 bp (t -0.35, n 34). | 40 bp embedded | `experiments/listingshock` | Not tested here. R188 and R189 (age-based listing fade on Binance, NULL) use a different trigger. |
| 4 | E02 | Hyperliquid vs Binance funding spread carry (hl_carry). | UNCLEAR. Partially replicates; below hurdle. | Spread real, about 3-4 times the CEX-CEX null. Late-2024 peak claimed +8.5% to +11.4% per year. 2026 year-to-date liquid-20 book +2.05% per year gross, against a 4.13% T-bill hurdle. | Gross only; costs not printed | `experiments/hl_carry`, `experiments/hyperliquid` (103 coins, 2023-05 to 2026-10, 2.15M rows) | Not tested here. carry_v1 (R190) is one venue. carry_fwd (R220) is Binance plus MEXC. |
| 5 | E05 | Funded challenge with the chase_QUANT rule set (R143). R149 paper forward open. | UNCLEAR. PARTIAL, not actionable. | BRK_CLASSIC pass 21.6% vs control median 11.3% (p95 17.2%). Mean +0.001 R per trade. Late split (starts from 2024-10): 13.5% vs control p95 22.3%, fails. HYRO2 late 10.8% vs 7.2% (n 37, overlapping). The simulator is optimistic: no 30-day inactivity, no floating drawdown, no 40% rule. | Not printed | `experiments/funded` | Tested here: R143 PARTIAL (same lane name, no code here). R202 propfirm_v1 is similar. |
| 6 | E06 | Challenge as an option (R144). | UNCLEAR. PARTIAL. O1 fails. | Value per start at fee $100, 80% split, r = 1%: chase_QUANT +$2 vs zero-edge control -$80. hybrid_BASE -$32 vs -$94 (p 0.025). All of chase's gain comes from 2020-22 starts. | Fee, split and r grid in summary.csv | `experiments/challengeoption` | Tested here: R144 PARTIAL. |
| 7 | E07 | R153 xs_disp: does the SCATTERED skip of the chase arm block alpha? | UNCLEAR. No verdict visible. | Row cut off in the transcript after "chase_QUANT earns +0.00984/trade (t=". | - | `experiments/xsdisp_chase_disagree` (other session) | Not tested here. Depends on the old chase rules, which are not in this repo. |
| 8 | E08 | R168 mmprobe: two-sided resting market making on MEXC alt perps (queue-pessimistic sim). | UNCLEAR. Pending; no statistic. | No result. Verdict due after 2026-10-20 (ROADMAP). MEXC survey: maker fee 0 on 545 of 1,089 USDT contracts. | - | `experiments/mmprobe` (live L1 recorder) | Partly covered by maker_v1 (R193) and pack_v1 (R194), both NULL. C05 "covered". R224 records MEXC order books. |

Ranking: E01 first (largest sample, pre-registered backtest, null p 0.002). E03 second (24 h clustered t 2.01, but 1 h fails clustering). E04 and E02 follow. E05 and E06 need no spec: they are already in the registry. E07 and E08 get blocked specs S5 and S6 in section 4.

## 4. Replication specs (E01 to E04 in full; E07 and E08 blocked)

Nothing here has been run. Before any statistic, freeze each spec with `lab.prereg.freeze()`, and count every variant in `registry.program_trials()` (current total 9,471,889).

### S1 (E01) Unlock short

- **Data needed:**
  - Unlock calendar: date, amount, category, max supply per token. The old source was DefiLlama emissions (372 protocol files, 69 mapped to perps). Not in this repo. Needs the owner's explicit yes for the download.
  - Binance USD-M daily close and quote volume, built from `data/klines_1h` (901 parquet files). Delisted perps are kept (`lab/data.py`).
  - Funding from `data/fundingRate`.
- **Universe and window:** archive perps as they traded on each event day. Freeze the token-to-symbol map and the old exclusions (GRAM, ETH, BNB, POL, FTM) before any statistic. Freeze the calendar snapshot with its date. The old session warned that a later correction to the calendar can flatter the edge.
- **Event rule (R179):** category in {insiders, privateSale}; amount at least 1% of max supply; events at least 14 days apart per coin. Entry at the close of day D-7 (00:00 UTC). Exit at the close of unlock day D. Short only.
- **Volume split (R181):** V = unlock USD (tokens times close at D-8) divided by mean daily quote volume over D-37 to D-8. Use the old in-sample cut 0.82 days of ADV as a hypothesis only.
- **Costs:** 20 bp round trip, as the old session used, plus 2x and 3x. Funding as a separate line, since the old primary excluded it.
- **Gates:** carry over R179's G1 to G4: week-cluster t at least 2; matched random-date null (2,000 reps, fixed seed) p below 0.05; both halves positive; still positive without the top 3 symbols.
- **Horizons:** primary D-7 to D. Log only: D-30 to D (old +5.0%, t 2.7) and D to D+7 (old -1.20%).
- **Holdout caveat:** the old session read all of 2021-26 for this family. The lab holdout is therefore not clean for it. Treat R179 as in-sample. Only the forward test is clean.
- **Forward option (MEXC paper):** append-only tickets with `frozen_at`, as in R180. Use the MEXC contract API `Min60` klines and only coins with a live MEXC USDT perp. No stake until a go-real gate passes. The old gate was at least 20 scored events, mean net above 0, hit at least 55%, and no event lost more than 40% unlevered. The owner places any stake.

### S2 (E03) Delisting-notice short (archive version)

- **Data needed:** Binance "Will Delist" announcement times. The old catalog had 161 notices and is not in this repo. Needs the owner's yes to fetch public announcement pages. Prices from the lab's hourly klines, which keep delisted symbols.
- **Limit:** the old fill was the worst print in [t0+1 s, t0+3 s]. Hourly bars cannot test that. Pre-register this as a different, weaker test: entry at the first hourly open after t0, with up to 60 min of lag. The old R167 showed decay within seconds, so expect less.
- **Rule:** short at entry. Exit at +60 min (old primary) and +24 h (old secondary). Report a hedged variant (long BTC) on its own line.
- **Clustering and gate:** one observation per announcement (old: 46 legs from 22 announcements). Gate: announcement-clustered t at least 2.40, both halves positive, and a 2025 split.
- **Costs:** 40 bp round trip (old), plus 2x and 3x.
- **Forward option:** needs a continuous announcement listener, which is a new process and needs owner approval. Old caveats: Binance may restrict shorts after the notice, and borrow and open-interest caps were not counted.
- **Power:** the whole old sample had 22 announcements. A one-year forward window gives only a handful of events.

### S3 (E04) Upbit listing notice, 24 h short

- **Data needed:** Upbit listing notices. The old sample had 268 Upbit and 190 Binance notices (2021-26); 202 Upbit notices had a Binance perp. Not in this repo. Needs owner's yes.
- **Limit:** the old entry was at notice plus 2 min. The archive version enters at the first hourly open after notice plus 60 min. The old 60-minute delay still showed +350 bp (t 2.23, n 172), so the signal may survive the lag. Pre-register this version as the archive test.
- **Rule:** short at entry, hold 24 h. Costs 40 bp round trip, plus 2x and 3x.
- **Gate (R165 family):** mean above 0; announcement-clustered t at least 2.24; median above 0; both halves above 0. Report 2026 separately (old -155 bp, n 50).
- **Overlap:** R188 and R189 are an age-based listing fade on Binance (NULL; holdout NOT CONFIRMED). They use a different trigger and do not test this one.
- **Forward option:** needs an Upbit notice listener, which is a new process and needs owner approval.

### S4 (E02) Hyperliquid vs Binance funding spread

- **Data needed:** Hyperliquid public `/info` `fundingHistory` (hourly since 2023-05, no key). Not in this repo. New venue, so needs owner's yes (the old pull was 103 coins, 91 MB). Binance from `data/fundingRate` and `data/premiumIndexKlines_1h`.
- **Rule:** re-pre-register from scratch, since the old FINDINGS are not in this repo. Proposal: top 20 coins by trailing volume present on both venues. Each funding period, long the perp paying the lower rate and short the one paying the higher. Hold while the gap stays above a fixed threshold. Freeze the threshold and universe.
- **Hurdle:** 4.13% T-bill (old value). Name the source before use.
- **Costs:** 2x and 3x, with exact funding.
- **Gate:** net annualised return at least the hurdle, with NW t at least 2 on daily returns. Report halves.
- **Expectation:** NULL is likely. The old 2026 gross was +2.05% per year. The spec's job is to confirm this on 2023-2026 with the lab's costs.
- **Forward option:** could become a third leg of carry_fwd (R220), but needs its own venue approval.

### S5 (E07) R153 SCATTERED-skip gate on chase_QUANT (blocked)

- **Blocker:** the rule is in the old repo's funded and paper_multi arms, not here. The old row was cut off, so its verdict and t are unknown.
- **Needed before pre-registration:** the exact skip rule, the broad 173-coin universe definition, and the cost basis. The owner decides whether to share the old repo files.
- **Spec once the rule is in hand:** compare trades taken with trades the gate skipped, on the lab's hourly archive. Gate: t at least 2 on the skipped-trade returns. Report 1x, 2x and 3x costs. The chartist arms are excluded (X31).

### S6 (E08) R168 two-sided market making on MEXC (blocked)

- **Blocker:** no result yet. The old verdict was due after 2026-10-20. The simulation needs a live L1 and trade recorder, which is a new continuous process and needs owner approval.
- **Lab overlap:** R193 and R194 (limit entries, NULL), C05 "covered", and R224 (MEXC order-book snapshots from 2026-11-03).
- **Spec once data exists:** two-sided quotes at the best bid and ask on each MEXC contract. Maker fee 0 on web orders, 6 bp on API orders. Fill only on a trade-through. Include inventory and adverse-selection controls. Gate: positive net after adverse selection, t at least 2 on daily PnL, 1x, 2x and 3x costs.

## 5. Null, superseded, or not an edge

| ID | Round | What it was | Old verdict | Key numbers (window) | Cite | Lab |
|---|---|---|---|---|---|---|
| X01 | R152 | 8 AM ET 1-hour range fade (owner's Edgeful claim, alt perps, 1-min data) | NULL | P(both sides) 58.9%, a base rate (rank 7 of 24). Net -0.168 R, t -9.0. Gross +0.034 R at best hour. | p45 605590b4, 04590f87 | Not tested here |
| X02 | R153 (renumbered R154) | Entry timing vs random bar within 90 days (chase, hybrid_BASE, hybrid_FLAG, about 21,500 signals) | NULL | 24 h gain vs random: chase +0.59% (solidity -1.67), hybrid_BASE +0.42% (solidity 1.92), hybrid_FLAG +0.60% (solidity 1.50). After 2025 about zero. | p43 0e8636b6 | Not tested here (R185 atlas asks a different question) |
| X03 | R155 | Pullback limit at half the signal bar vs market entry | NULL | Chase D = -36 bp per signal at 24 h (t 2.18). Fills -3.5% and non-fills +1.8% over 24 h. | p42 059c9a95; notes_014 63843ffd | Not tested here (R193 limit entries similar, NULL) |
| X04 | R156 | Early abort at 50% retrace in bar i+1 | NULL | Chase -22 bp (t -1.13). hybrid_BASE -28 bp (t -3.75). hybrid_FLAG -37 bp (t -3.52). | p42 66d9fb2a; p43 d4c4d91b | Not tested here |
| X05 | R157 | Taker long at a 4H bar where at least 8 of 173 perps fire, 24 h hold | NULL (borderline) | OOS before 2024-09-25: n 221, net +0.82%, t 1.97 vs gate 2.0. IS: n 105, +0.21%, t 0.46. 72 h OOS +1.51%, t 2.27 (secondary only). | el14.9 93825787; p42 2cbc96b6 | Not tested. R206 liq_v1 is a similar idea (NULL). |
| X06 | F5 (futuresnative) | Does pre-cascade positioning separate bounce from continuation? 96 cascades, 71 with positioning | NO SIGNAL (underpowered) | Best cell rho -0.274, raw p 0.023, family-wise p 0.21, DSR 0.49 at N=24. Cascades bounce on average: median-of-15 +1.41% at 24 h (t 3.71), vs unconditional -0.07%. | p42 543a8a4d | Not tested |
| X07 | U4 liqprov | Resting bid ladder during cascades (maker) | TRAP at retail scale | Net -0.84% per rung (4 h exit) to -0.24% (26 h). DSR 0.0000 on 20 configs. The only positive rung (-10%) is beyond the exchange's 5% limit-price cap, so it cannot rest statically. | el8.3 82c4a50d; p42 6556bc98 | Similar to R206 |
| X08 | R158 | Fade extreme daily liquidations (Coinalyze) | NULL | H1 z at least 3: +24.9 bp (t 0.89). H2 z at least 3: -84.4 bp (t -2.18). | el14.8 0cfb2848 | Similar to R206 |
| X09 | R159 | Short 30 days before a 1% cliff unlock | NULL | Mean net -4.25% (t -0.59). Null p 0.92. | el14.7 91c1cbb6 | Not tested |
| X10 | R-unlocks (original) | Short D-7 to D on data_deep survivors only | NULL (superseded by R179) | 182 events, mean +0.85%, t 0.50, null p 0.33. | el4.5 5ea44ec8 | Not tested |
| X11 | R160 | Coinalyze crowding z-score: H2 short-crowded to long next day, H1 the reverse | NULL at gate (t 2.5). H2 recorded as a lead. | H2 z at least 2: +31 bp (t 2.14). z at least 3: +44 bp (t 1.38). | el14.6 6ad47b35 | Similar: R185 atlas flow views (C19 "covered"), not the same rule |
| X12 | R161 | Megascan: 390 cross-sectional cells, 13 features | NULL | 0 of 390 pass discovery. Best 1-day rpos_48: gross 302 bp, holdout -57 bp. | el14.4 1f169609 | Not tested |
| X13 | R162 | Ridge and GBM composite on 13 megascan features | NULL (6 of 6) | Rank IC 0.01 to 0.04. Best net -19 bp per bar. | el14.5 30341cfa | Not tested |
| X14 | R163 and R164 | C1 rpos_48 cross-sectional long-short (data_deep universe) | ARTEFACT (superseded) | R163: +5.6 bp per day, t 2.22. R164 on survivor-free: artefact. The mega24 check returned 0 days. | el13.5 4bfda3bd; el14.0 0193b765 | Not tested |
| X15 | R165 | Upbit and Binance listing notice to long Binance perp; gate t0+2 min to t0+60 min | NULL (both venues) | Upbit n 171: -21 bp, t -0.33. Binance n 34: +319 bp, t 1.06, median +25 bp. | el10.0 087f3852; el13.0 3ce02946 | Similar: R188 and R189 (NULL) |
| X16 | R165 speed residual | Speed-only effect at 1 to 2 s after the notice | Descriptive only | Upbit: +7.8% mean and +1.5% median at +2 s. Gone by about 10 s. Not tradable by a human. | el10.1 087f3852 | Not replicable here (sub-second) |
| X17 | R166 | Bithumb and Bybit spot listing to long Binance perp | NULL | Bithumb n 257: +103 bp, t 2.02 (gate 2.24), median -40 bp. Bybit: -92 bp. | el11.0 f5aa6681 | Not tested |
| X18 | R167 U_DELIST and U_WARN | Upbit delist and warning notices, 1 h short | NULL | U_WARN n 48: +90 bp, t 0.82. | el12.9 8d961462 | Not tested |
| X19 | R169 | xsrev daily reversal, illiquid coins, survivor-free universe | NULL | No numbers in the excerpt. | el3.6; el7.3 | Similar: R185 atlas reversal views |
| X20 | R170 | xsrevmaker: maker-limit version of R169 | NULL | Adverse selection explains the result. | el7.0 to el7.2 | Similar: R193 and R194 |
| X21 | R171 to R173 | Chart patterns: rangebounce, bouncewhen, bruteconf (R175 in ROADMAP) | NULL. Family closed. | 2,671 combinations, 0 pass. | el4.8; el6.0 to el6.3 | Not tested |
| X22 | R174 | recentwin: monthly walk-forward on grandgrid rules | NULL | Persistence about 0. | el3.11; el6.4 | Not tested |
| X23 | R176 | MoksNQ ICT method (video rules) | NULL (A to D) | verdict.json: all four NULL. | el3.3; el4.10 | Similar: R185 ICT detectors |
| X24 | R177 | sessionflow: who enters when (session and volume rules) | NULL | All 5 holdout cells negative after 10 bp. EU prev_down high flips sign: +67.6 bp in discovery, -32.0 bp in holdout. | el3.0; el3.1 | Similar: R185 session views |
| X25 | R178 | Supertrend(10,3) plus RSI14 combo | NULL (6 of 6) | 4 h Supertrend: +238 bp discovery, -5.5 bp holdout. 62,448 trades. | el3.2 f85a06d6 | Not tested |
| X26 | R182 | hypermine: 38-feature 1-to-3 condition search | NULL / NOISE | n_disc 1,777, n_val 2 vs null q95 4. Trials 139,377. | el2.2 9aac49f2 | SAME: R182 in the registry (identical numbers) |
| X27 | F1, F2, F3 (futuresnative) | OI dynamics, L/S ratio, top-trader positioning | NO SIGNAL | F1: folk quadrant model killed. F2 and F3: no effect survives the gate. | p43 c0737392 | Similar: R196 to R198, C19 |
| X28 | U3, B1, U1, U2, U6, carry_oracle, xvenue_carry, vol/VRP | Retail-scale structural ideas | NULL, NOT VIABLE, HELD or CLOSED | xvenue_carry: +22%/yr gross in 2021, +0.9%/yr in 2024-26, below the 4.13% T-bill. U3 DSR 0.92 vs 0.95. | el13.9 87136164; el10.11 to el10.16; el13.8; el13.11 | xvenue ~ R190 (one venue). vol/VRP = R209 (same idea, NULL). |
| X29 | R142 (conscience) | Integrated ML: 50 features, HGB plus isotonic, quarter-Kelly, leverage up to x35 | NULL on holdout. DEV PARTIAL. | Holdout traded R -0.101 (t -1.63). Holdout Spearman -0.002. Paper equity $55. | p49 46327182 | Not tested |
| X30 | grandgrid | 138 frozen chartist and quant rules, 173 alts, 4 H | NULL. 3 rules pass the screen, unverified. | None survive. | el5.8; el7.6 | Not tested |
| X31 | Chartist arms (rules.detect) | chartist_FULL, chartist_NO4H and every chartist-derived number. Lookahead (PREREG A2.3). | INVALID (superseded) | NO4H showed 94% pass vs 0.7% control. That was an artefact. | p48 2c42e099; p48 14949800 | Not tested |
| X32 | Priors and others | smc, candles, mtf_rsi, fib (NULL). onchain (selection-bias artefact). saxanalog (discarded). | NULL | Per summaries; not re-read. | el5.6 to el5.9; el8.7; el8.13 | Not tested |
| X33 | Owner's own MEXC futures record (aggregate only) | Realised trading record | Descriptive. Beta, not edge. | +$3,591 net over 124 fills, 11 pairs. +36% BTC window. Ex top 5 fills: -$39. | el10.17 661a3c11 | Not applicable |
| X34 | Owner's stop test (R137, aggregate only) | 57 trades, no stops, x35 vs stop with x3 on $600 | Descriptive | Worst drawdown -22.6% to -3.9% with stop and x3. Gain +$4,083 to +$93. | p46 e0371755 | Not applicable |

Data and infrastructure rows (R145, R146 to R148, R150, R183) are not edges. R146 (Tardis) stopped at its free quota.

## 6. Owner requests from the old session, still open

Status as of the last visible event, 2026-10-13 05:01 UTC.

| # | Request (paraphrased) | Source | Status |
|---|---|---|---|
| 1 | Positive futures PnL. Standing goal in the 10-minute and hourly ticks. | el1 owner_messages; p42 00ea5ed5 | Open. No live edge found. Forward paper lanes unscored. |
| 2 | Enter at the right moment, and have the best edges. | p44 fc2627cd | Answered NULL (R153 and R154; R155 and R156). A per-signal entry score was offered, not done. |
| 3 | Something better than zero, and free Bloomberg-type data. | p42 00ea5ed5; p43 c87d23c5 | Partly. Free Coinalyze API used (R158 data lane; fetch started, no verdict). Tardis history is an owner decision. Old quotes conflict: 50-900 USD per month vs 350-6,000 USD per month. |
| 4 | Advance the project one year, without prompting each time. | p43 c7bd5ca8 | Open. Three levers were offered: buy history (owner decides, paid); log trades with conviction (20 needed, 1 logged); autonomous mode with a stop date (needs explicit owner yes for recurring tasks). |
| 5 | Trade log with conviction and stops (`bridge.py plan --conviction`). | p43 7eb2277c; p46 e0371755 | Open. Owner action. |
| 6 | Call sheet for MEXC alts with x7 and x35 leverage and a confidence score (standing mandate). | p49 46327182 | Open. A confidence score needs at least 20 planned trades with conviction. |
| 7 | Disk cleanup. C: had 39 GB free, draining about 2 GB per day from non-repo items (.zcode db 6.7 GB, ck-gguf 6.1 GB, Android SDK 9.7 GB, npm 6.1 GB, Roblox 4.1 GB). | p46 2fb7db4d, 4cb8292b; p46 d07b9088 | Owner decides. Nothing deleted. |
| 8 | Hourly cron f80e09e1 and one-shot 07d0b77d. | p47 6f3a733f; p49 46327182 | Open. The assistant asked whether to remove or redirect the hourly cron. |
| 9 | Real-money orders. | p49 46327182 | Not done. Owner-only. Real money only after paper proves a net gain (go-real). |
| 10 | Speed up listing detection (Upbit websocket). | el1 owner_messages | Open. Listener built (R165). Continuous run awaits owner approval (el13.4). |
| 11 | 8 AM range (Edgeful claim). | p46 2fb7db4d | Answered NULL (R152). Closed. |
| 12 | Put a skill mandate into global CLAUDE.md. | el2 2429aff7 | Config request. Status not visible. |
| 13 | Use the GPU to go faster. | el14 0cc07898 | Partly. R182 ran on GPU (el2.11). |
| 14 | Work autonomously, do not wait for a go-ahead. | el3 98e0d3fb | Standing rule, applied. |
| 15 | Plan of everything missing. | p47 412a6386 | Delivered (R145 to R152 rows, p46 e0371755). Done. |

Standing rules visible in the old session: no subagents; no real orders or money movement; no credentials; downloads need explicit consent; real money only after paper proves a net gain; check mtimes; never kill processes not started by the assistant.

**Security:** two Coinalyze API keys were pasted into the chat (p42 events 00ea5ed5 and 0750f2d2). Treat them as exposed and rotate them. Values are not recorded here.

## 7. Other notes

- **Old round-id collisions.** Another session took R153, so entry timing became R154. R171 became R175 in ROADMAP. Do not reuse old ids R146-R179 for new work. The lab registry has none of them except R180-R183.
- **Owner trade figures differ by method.** One source gives 124 fills and 11 pairs, +$3,591 (el10.17). Another gives 61 trips, +$3,591 (FIFO, p49 summary). A third gives 57 trades with no stops (p46 e0371755). Personal account identifiers are omitted.
- **Synthetic prompts are not owner requests.** The 10-minute and hourly ticks were harness-injected. They repeat the owner's standing goal.
- **Data pulls in the old session** (none are in this repo): Coinalyze aggregated history, Hyperliquid funding (91 MB), DefiLlama unlock files (372), Tardis (quota-limited).

## 8. What was not checked

- No backtest was re-run. Every number is the old session's printed value.
- Old data files were not compared with lab data.
- The R180 forward scores after 2026-10-20 were not seen.
- The waitrules verdict and the R153 numbers are missing from the transcript.
- The transcript before 2026-10-11 00:24 UTC is available only as a summary.

## 9. Sources

- `scratchpad/oldsession/chunk_results.json` and `notes_000.md` to `notes_014.md`.
- Pages read in this job: `scratchpad/oldsession/c14/page42.txt` to `page49.txt`. Raw tool results are under `/root/.claude/projects/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/tool-results/`.
- Lab files: `registry/rounds.csv`, `docs/EDGE_SCOREBOARD.md`, `docs/MAP.md`, `docs/CLAIMS.md`, `docs/RESEARCH_COVERAGE_LEDGER.md`, `lab/data.py`, `lab/engine.py` (`cost_matrix`), `lab/prereg.py`, `lab/registry.py`.
