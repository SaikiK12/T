# Critic on reflection_20261126_maps.md (2026-11-26)

Method: §1 table first, each row against its source; then the prose. Scripts run, nothing edited, no journal opened.

## 1. Table check

| Row | Verdict | Finding |
|---|---|---|
| 1-3 | ok | Frame f_070: 72 + 124 + 831 = 1,027; 72/196 = 36.7%; break-even 50.2%; interval 30.3-43.7%; net +$10,128; window 2021-11-29 to 2026-11-24. "Peak near $40k" is read off the chart. |
| 4 | error (label) | Arithmetic ok: 2,314 / 4,630 = 50.0%; × $50 = $115,700; ÷ $10,128 = 11.4. "Same window" is false: the panel ends 2026-11-24, row 4 ends 2026-11-20. The frame's Nov 24 chart shows ES near 7,217; (7,217 − 4,630) × 50 ≈ $129,000, about 13 times. `data/databento/es_1h` ends 2026-11-21 (exclusive). |
| 5 | ok | `registry/methods.csv:12`: "RN_CROSS -84.8 t -9.93 (gross -17.7, cost 67.1)". Exact. |
| 6 | ok (numbers) | R249 notes: "+0.2 bp/day t 0.03"; "+4.8 t 2.53", one of several books (F4). |
| 7 | ok, incomplete | `methods.csv:204`: "1d -14.5 bp/day t -1.99". Same row has R247 (indices t -4.16) (F9). |
| 8 | ok | R206: "net -36 bp/day t-1.96 (gross +4, cost 40)". |
| 9 | ok, incomplete | R252 "ALL/24 +2.0 bp/day t 1.93" matches. Omits "effectively 2022-23: OI covers 10% of 2021" (F15). |
| 10 | numbers ok, wrong family | micro 0 / 6 / 6 = 0%. None of the five §3 rounds is micro (F1). |
| 11 | ok, partly | BENCHMARK.md:120 matches; MAP.md 793 lines. EDGE_MAP "generated from registry" not checked. |
| 12 | ok | Last folder 2026-11-06; no workflow mentions funding_board. "Ran in a container": no source (F13). |
| 13 | error (count) | 12 High entries match. "About 75 papers": §1 has 84 entries; 75 appears nowhere. |
| 14 | ok, one generous | Baltussen: §3.6 says "I did not isolate the equity number", so "partly match" overstates. |
| 15 | ok | Quote matches the room file; NBER not re-fetched. |
| 16 | error (cite) | `STRATEGY_BOOK.md:66` is the "Règle" row. "t 2,95" is on line 67. |

## 2. Prose findings

**F1. error. §3 "The family's record is 0 of 6 (row 10)." §4 "The micro family is at 0% (row 10)."**
`lane_families.csv`: liq_v1 and oiwick_v1 (R206, R252) are `flow` (2 pass, 10 fail: 17%; Laplace 21%). chartist_v1, ictlevels_v1, rnfade_v1 (R243, R246, R249) are `charts` (0 of 15: 0%). Micro is vpin, minflow, tapelag and others. The wrong family lowers the prior for R206/R252 (0% against 17%): the cleaner direction.
Fix: cite flow and charts for these rounds; the §4 prior is flow's 17%, with small n.

**F2. error. §3 "The visual map would have shown us the same data."**
The reel's map is a level-3 CME book (line 36). The lab holds ES hourly OHLCV only. The sentence removes a real data gap.
Fix: "The map needs a level-3 book the lab does not hold; the tests used proxies."

**F3. error. §4 "The overshoot is largest when the need is known and the predators are few."**
`vince_quant_papers.md:166` lists "predation fiercest when predators are few" under "Not verified".
Fix: label it as the video's unverified claim.

**F4. error (status word). §3 "R249 found the mechanism real as a difference, but too small to pay its cost (row 6)."**
R249's verdict is NULL. The +4.8 (t 2.53) is one of several grids and holds. R246's 2021-23 post hoc is t −3.30 (`methods.csv:12`); the sign history is not reconciled.
Fix: "R249 saw +4.8 bp/day (t 2.53) in one of several variants on 2024-25; not a confirmed mechanism. Sign against R246 unresolved."

**F5. error (status before the deciding observation). §6 "A3 was already outside money (December decision), so no rule moves. The card now says it."**
`STRATEGY_BOOK.md:63-67`: A3's decision is "90 et 180 jours notés, à partir du 25-11-2026". No "outside money". `grep -i harvey|hurdle|3,0` on the book: no hit. The card does not say it.
Fix: delete "outside money"; add the HLZ line to the card, or drop "the card now says it".

**F6. weak (unlike comparison). §6 "Harvey, Liu and Zhu's t > 3.0 ... puts A3 (t 2.95) below the multiple-testing hurdle."**
HLZ's 3.0 is a bar for a new factor among 313 published candidates. A3 is one card on another sample (2021-01..2026-09, engine R525). Fix: call it an analogy; test on the lab's own grid.

**F7. error (unlike comparison). §2 "about eleven times more (row 4, unadjusted for rolls and margin)" and "the tool itself showed it."**
Buy-and-hold gross against a net intraday rule: no costs, no drawdown, different exposure, a volume-rolled series, a different end date (F-row 4). The panel's net per trade is $10,128 / 1,027 = $9.86, under one ES tick ($12.50), so a one-tick cost decides the sign. The page never states the cost.
Fix: same window, net against net, max drawdown for each, cost assumption written out.

**F8. weak. §2 "The +$10,128 comes from the 831 trades that hit neither".**
The frame does not split P&L by exit. The reading is fair on arithmetic: with a 1:1 bracket (the 50.2% break-even implies about one after costs), the 196 decided trades net negative, so the 831 carry the net. That needs about +$44 per neither-trade, against drift of about $92 per session (2,314 × $50 / 1,254).
Fix: "With a 1:1 bracket, the neither trades carry the net. The panel does not split P&L by exit."

**F9. weak. §3 "Pivots: R243 lost (row 7)."** `methods.csv:204` also has R247 ("breaks lose in three markets", indices t −4.16). Cite it too.

**F10. weak (overstated). §4 "which makes HL a natural experiment of the theory."**
Liquidation levels on HL are observed, not assigned; this is an observational test, not a natural experiment. "The lab's proxies (R206 on Gate, R252) never saw the actual levels": R206 used measured Gate "liquidation spikes"; whether it saw levels is not in the row.
Fix: "an observational test on observed levels"; check liq_v1 inputs before "never saw".

**F11. weak. §4 "JELLY ... was predation on a forced holder (HLP)."**
`hl_incidents.md:22`: HLP held a short; validators delisted and force-settled; loss up to about $13.5M. No predation. Fix: "a forced settlement that hurt a short holder; predation is our reading."

**F12. weak. §4 "Every position, and so every liquidation price, is public on-chain."** No source. Label assumed or cite the HL API docs.

**F13. weak (cause not in record). §5 "when its container ended (row 12)."** Row 12 gives only the last folder. Fix: "stopped after 2026-11-06; cause not in the record."

**F14. weak. §6 "The lab already knew about half".** No count in any row. Count per name (grep) or drop "about half".

**F15. weak. §1 row 9 and §3 "OI drop with a wick (R252, row 9): NULL."** The discovery window is effectively 2022-23. Add it.

**F16. weak (sources missing). §5 "in text or on a local page the owner cannot open from a phone"; "The owner reads the lab through my French messages".** No source. Cite or remove.

**F17. weak. §1 row 1 "(scratchpad)".** Give the full absolute path.

## 3. The two questions

**§2 panel reading fair?** Yes on arithmetic (F8). Gaps: the 1:1 bracket is not stated, and the net is under one tick per trade (F7), so the sign depends on costs. Keep "lose" for the 196 target-or-stop trades only.

**§4 "natural experiment" overstated?** Yes (F10). It is an observational test on observed levels.

## 4. Direction
F1-F5 all move toward the cleaner story (lower prior, lab has the data, a settled mechanism, a book already updated). F7 flatters the beta story the page tells.
