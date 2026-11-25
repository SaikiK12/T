# Room audit, carry-type families: re-verification with the 2026-11-25 reflections

Auditor: room member "carry". Date: 2026-11-25. Scope: registry rows in families carry, carry_tradfi, settle, vaults, infra
(138 rows after the join with `registry/lane_families.csv`). Read-only audit. Paths below are relative to `/home/user/T`.

Method and limits (stated first):
- Every row with verdict CONFIRMED, PARTIAL, DATA_PASS or NULL was triaged (67 rows). 65 have a FINDINGS.md. R183 and R405
  have none (R405 is ABANDONED and recorded as NULL; see flag below).
- Read in full or in substance: R190, R191, R275, R277, R288, R391, R437, R438, R439, R483, R384, R335, R281, R309, R382,
  R327, R328, R430, R436, R442, R444, R470, R475, R476, R477, R478, R481, R412, R280, R387, R388, R223, R353, R354, R356,
  R362, R363, R450, R452, R484, R486, R487, R497, R401, R402, R391. Plus the three reflections the task names.
- Headers and registry notes only: R262, R264, R312-R326, R373, R403, R407, R321, R183. These are engineering or
  measurement rounds with no economic claim; I did not verify their bodies.
- Not opened, by rule: any `experiments/*/journal/`, any `run_*_fwd.py`, `run_*_fast.py`, R406, R413, R419. RUNNING and
  REGISTERED rows were not triaged (they have verdict PENDING). No downloads, no logins.
- Inference is labelled "inference". Where a claim rests on a FINDINGS sentence, the line is cited.

Key of flags: K1 decay/regime; K2 PnL source; K3 valuation (last-trade, stale legs, constant notional); K4 selection;
K5 owner capacity, access and margin mode; K6 mechanism and control; K7 null-specific (window, sign, instant, cost).

## 1. Report table

| Round | Lane | Verdict (registry) | Flags | Evidence | Suggested action |
|---|---|---|---|---|---|
| R190 | carry_v1 | CONFIRMED (in-sample) | K1: 2021 +35.0%, 2022 -0.1%, 2023 +3.3%, 2024 +8.1%, 2025H1 +0.8%; window ends 2025H1. K3: basis is the premium index, not the traded spread (stated limit). K5: capital is 1.3x the leg notional (spot plus perp margin), no account-access check. K6: no control group. | experiments/carry_v1/FINDINGS.md:15 (by year), 16 (1.3x capital), 23-24 (limits) | re-check: run the cycle-8 regime regression on this book's daily nets. The 2021 result is the only strong year. |
| R191 | carry_holdout | CONFIRMED (one-shot) | K1: +1.2%/yr over 2025-07..2026-09 (t 2.07), mean trailing funding negative in the window. K5: 25% invested. | experiments/carry_holdout/FINDINGS.md:12, 16-17, 20 | none for money. The holdout already shows the decay the reflection describes ("works for a time"). Do not cite as a live edge. |
| R275 | xfund_v1 | PARTIAL (gate 0, 212/560 books pass) | K1: Gate+Hyperliquid by year 2023 +18.6, 2024 +10.1, 2025 +5.0, 2026 +8.4 (1x); Binance+Hyperliquid 2025 +5.2, 2026 +7.9. The 2026 rise does not match the design-gap decay. The regression has not been run on these pairs (inference: the trend reflection's 2026 result was on R525's pairs, not these). K2: direction is stated correctly (long the venue that paid less, short the one that paid more, FINDINGS:21-22). Funding is 96-105% of gross (line 89). K3: daily last-trade closes, constant-notional marks (H2, line 153), stale delisted legs (F4, line 149; NEIROETH -83%, A2Z -140%, YALA -114%, lines 91-100). K4: best of 560 by t (12.70; NW 8.63) still clears the reality-check p95 of 4.27 (lines 109-111). The best-by-return book (gate+mexc L7, +16.3%) was chosen after the run (lines 138-141). K5: returns on total capital including both collateral (line 25). $10k means $250 per leg (line 105). Cross margin per venue is assumed; isolated margin liquidates these books at 1x (see R280). Gate, Binance and MEXC legs need accounts the owner may not have (line 123-124; see R439 note). K6: no control group; the reality check is a permutation of the family, not a placebo entry. | experiments/xfund_v1/FINDINGS.md:3, 21-22, 25, 54-66, 89-91, 98-106, 109-121, 123-124, 138-146, 149-153 | re-check, then retire the "structural floor" reading. First: regression on daily nets (cycle-8 method). Second: re-price the price legs on executable marks. Third: confirm the owner's account and margin modes per venue. |
| R277 | xfund_kd_v1 | PARTIAL (2 of 4 venue sets replicate) | K1 and K3 (dominant): the KuCoin "+20-24%/yr in 2025-26" headline is on pre-scaling 4h rates (see R384). K7: dYdX sets fail on the 2025-10-10 print (lines 50-66). | experiments/xfund_kd_v1/FINDINGS.md:16-17, 34-35, 48-49, 50-66; experiments/xfundint_v1/FINDINGS.md:44-51 | re-check. Do not cite the 2025-26 KuCoin pace as current until R384's point is resolved. |
| R288 | xfund_lt_v1 | CONFIRMED (5 of 6 Lighter sets) | K5: "No Lighter account exists" (line 13); a bridge and an on-chain wallet are needed (line 157-158); the owner's access is for the owner to decide. K3/K7: the audit notes already show MEXC+Lighter falls from 6.20% to 3.67%/yr on daily bars (F6) and to about 5.07% at the measured 14.7 bp cost (F7). Both are below or near the 4.13% hurdle, but they were not applied to the verdict (lines 162-168). K1: every set shrinks from 2025 to 2026 (line 60). K4: the book is R275's pick, so this is replication of a chosen rule, not a new search. | experiments/xfund_lt_v1/FINDINGS.md:13, 46-47, 60, 63-66, 157-158, 162-168 | re-check under F6 and F7. Retire the "CONFIRMED" as a money claim until the venue is accessible to the owner. |
| R391 | reserved_batch2 | PASS (small) | K3: the engine that produced it has the H1 freshness bug (dYdX took no trade, lines 84-88) and the H2/F4 valuation issues. It was never re-run on M468 v2. K7: costs are not measured on these books. The 3x net (+1.38%/yr) is the only cushion (line 64-65). K5: +2.48%/yr on capital is below the T-bill (line 61). K1: 2025 +1.4%, 2026 +3.3%. K4: top 10 days carry 95% of the sum (line 52-53). | experiments/reserved_batch2/FINDINGS.md:3-5, 24-30, 52-53, 61-65, 81-90 | re-check on M468 v2 with measured book costs before any forward lane. The PASS does not move money. |
| R437 | carry_v2_audit_v1 | CONFIRMED (7 books survive v2) | K3: blowout exits add +3.4 pts/yr in the two Binance+Gate books, closed on daily last-trade prints (lines 67-71). Binance+Gate t falls from 5.96 to 3.48. K4: inherits R275's best-of-560 (lines 93-95). K5: fixed-quantity drift is part of the gain (lines 62-66). Post-hoc sensitivity: R390 A's defensible figure is about +9.7%/yr, not +13.4 (line 89). | experiments/carry_v2_audit_v1/FINDINGS.md:3-14, 62-71, 75-89, 93-98 | none for the verdict (gate 0 on seen rows). Use the +9.7% figure, not +13.4%, wherever R390 A is cited. |
| R438 | carry_v2_audit_kc_v1 | CONFIRMED (2 KuCoin books) | K1: its 2025+ figures are on the pre-scaling KuCoin rates (see R384). K3: drift is mostly covariance (line 55-61). K4: the two books are the 2 of 4 that passed R277's rule (lines 95-96). | experiments/carry_v2_audit_kc_v1/FINDINGS.md:55-66, 95-96 | re-check the post-scaling window (R384's 2026-07-25 onward) before citing any KuCoin pace. |
| R439 | carry5_v1 | SURVIVES (CONFIRMED in registry) | K5: "As held, the book is not one the owner can hold from France" (lines 68-71). K3: KuCoin price leg swings from +1.29 (four venues) to -2.14 (five venues) on daily closes (lines 34-39). Paired gain not significant (line 27). K1: KuCoin scaling (see R384). | experiments/carry5_v1/FINDINGS.md:24-27, 34-39, 68-71 | retire as an owner route. Re-check the KuCoin pace. |
| R483 | carryhurdle_v1 | PASS (CONFIRMED) | K5: the benchmark sUSDe "is not offered to EU/EEA residents" (line 123-124). Beating it is not an alternative the owner has. K1: the 2025+ KuCoin book reads 26.3%/yr at 2x (line 89), which is the pre-scaling pace. K3: no cost is charged to the benchmark side (line 128), which favours the benchmark. K4: inherits R275 (lines 113-115). | experiments/carryhurdle_v1/FINDINGS.md:3-9, 52-59, 83-89, 113-115, 119-128 | re-check against the owner's bar (euro cash after tax, not sUSDe). Re-check the KuCoin pace. |
| R384 | xfundint_v1 | PARTIAL (label "robust") | **K1 (decisive):** KuCoin's scaling date is 2026-07-25 (line 21). The pre-scaling 2025-26 pace (+20-24%/yr, shown in R277 and R288) is about double the post-scaling pace (+10.5%/yr gate+kucoin, +10.0% binance+kucoin, 69 days; lines 23-25, 50-51). The 4h contracts carried about two thirds of pre-scaling funding (line 77-78). K7: whether recorded rates equal paid rates is unchecked (line 84-85). The counterfactual rescaling was not run (line 92-93). The interval class is static for 32-33% of position-days (line 86-88). | experiments/xfundint_v1/FINDINGS.md:3-5, 21-25, 44-51, 64-71, 77-81, 84-93 | **re-check, top priority.** Verify each KuCoin contract's paid rate factor before the scaling date. Re-state R277, R288, R438, R439, R483 KuCoin pace on post-scaling rates. |
| R335 | locked_carry_v1 | DATA_PASS ("USEFUL") | K1: the offer is rich in 2021 and 2024 and thin in 2022, 2023 and 2025. It was absent in 2026 to date (lines 11-13, 58-61, 74-76). The offer follows leverage demand, the same mechanism the trend reflection names (line 76). K5: Binance coin-margined; "access by country" (line 122). The "guarantee" holds only while the venue is solvent (lines 113-128). K7: mark-to-market path not measured (line 118). | experiments/locked_carry_v1/FINDINGS.md:3-13, 58-61, 74-76, 108-110, 113-128 | reopen with a new lane: the owner's live offer board (its own proposal, lines 130-134). Check venue eligibility first. Do not describe this as a guarantee; describe it as locked USD value at expiry. |
| R405 | lockcarry_fwd | NULL (registry), ABANDONED | Integrity: a NULL is recorded for a round abandoned before any offer was recorded. No FINDINGS.md exists. The forward test of R335 therefore does not exist. | registry/rounds.csv:191 (notes field) | re-label as ABANDONED in the registry. Reopen the forward test under a new id. |
| R281 | sizecarry_v1 | NULL (30 trials) | K7: the decision is fixed at 2x. At 7 bp or less all six books earn more with the tilt (lines 87-91). That lower-cost test was not registered. K1: the gain is in 2025-26 only (lines 74-78). K5: liquidation of sized legs not modelled (lines 96-99). | experiments/sizecarry_v1/FINDINGS.md:3-6, 74-78, 87-91, 96-99 | reopen with a new lane at maker cost, with a new id and a frozen PREREG. |
| R309 | capital_mix_v1 | NULL | K3: carry keeps stale-leg and constant-notional biases (lines 102-104). K1: window is 457 days, 2025-07..2026-09 only. K5: margin and collateral not verified. | experiments/capital_mix_v1/FINDINGS.md:102-104 | none. The NULL stands on its own gates. Carry-alone Sharpe 5.9 inherits K3. |
| R382 | fundvol_v1 | NULL | K1: second half includes 2026. K4: six variants, chosen on first-half Sharpe; the chosen variant is below the base in that half (4.43 vs 4.46). | experiments/fundvol_v1/FINDINGS.md:8-16 | none. |
| R327 | dated_carry_v1 | PARTIAL (terminal driver failed) | K7: no terminal economic result was persisted. | experiments/dated_carry_v1/FINDINGS.md:1-6, 26-27 | none. This is a failure record. |
| R328 | dated_carry_v2 | PARTIAL | K5: transfer, network and withdrawal costs are an optimistic zero floor (lines 40-41). Fees, debit asset and rounding unknown. K7: 54 of 216 scenarios uncomputed (ETH top-book depth). K1: one snapshot (2026-10-26). BTC control is +1.5 bp of capital over about 60 days. | experiments/dated_carry_v2/FINDINGS.md:24-29, 40-41, 47-51 | none. Do not treat as an edge. |
| R430 | okxcarry_v1 | NULL | K7: the cross-section annualization is wrong for 118 of 167 instruments that settle every 4 h. The corrected median is about 10.4%/yr (lines 56-61). BTC and ETH verdict is unchanged. K1: one 95-day regime (line 78). K5: France access taken from a 2026-11-06 report, not checked against registers (line 81). | experiments/okxcarry_v1/FINDINGS.md:9-24, 56-61, 78, 81 | re-check the cross-section only, as M490 (a new lane with a point-in-time rule). BTC and ETH NULL stands. |
| R436 | stock_carry_v1 | NULL | K7: taker costs (MEXC 8 bp API, 1x excess -1.76). Maker not tested. K3: universe is 381 survivor-only contracts (line 31). K6 (inference): selection on trailing funding decays from 55%/yr at entry to 15%/yr while held (lines 6-8). R275 also selects on trailing spread; the same decay could apply there. | experiments/stock_carry_v1/FINDINGS.md:6-8, 31 | re-check at maker cost in a new lane. Test R275's selection on hold-period funding. |
| R442 | xperp_stock_v1 | NULL (stop) | K7: 50 bp round trip at 1x (line 31). Maker orders and 0-commission brokers not tested (lines 44-45 region). K1: 83 days only. | experiments/xperp_stock_v1/FINDINGS.md:6, 31, 43 | reopen only with a maker-cost lane (new id). |
| R444 | hlspot_carry_v1 | NULL (stop at gate 0) | K7: the NULL is a capital-use result. 6 of 10 slots sit idle (lines 35-39). Per held slot the book earns about +6.7%/yr, +2.7 points over the hurdle. K5: portfolio margin reading is an upper bound only and changes capital, not trades (lines 57-72). | experiments/hlspot_carry_v1/FINDINGS.md:35-39, 57-72 | reopen with a new lane: fully deployed slots or a lower entry band, against the same frozen gate. |
| R470 | xvfund_v1 | NULL | K1: xyz funding changed on 2025-12-19. The post-change window reads +3.0%/yr (line 56). K7: "too thin even at zero cost" (lines 4-8). | experiments/xvfund_v1/FINDINGS.md:4-8, 55-56 | none for this rule. A post-change lane would need a new id. |
| R475 | hip3stock_v1 | PARTIAL (PASS recorded PARTIAL) | K1: all in 2026 (27 weeks). "Large effects in the first months of stock-perp venues, flat afterwards" (lines 58-61). K5/K6: half of A's excess is one isolated-margin liquidation day (lines 35-43). The payoff is a call option only for a trader who does not top up. K3: mark mismatch, 4-hour liquidation check (lines 91-92). K7: the frozen identity check returns NaN for markets with fewer than 60 marks and drops valid pairs (lines 63-71). | experiments/hip3stock_v1/FINDINGS.md:3-10, 35-43, 58-61, 63-71, 91-92 | re-check: fix the NaN and re-run. Retire liquidation-driven gains from any money case. The forward design must state its margin rule (lines 99-102). |
| R476 | hip3other_v1 | PARTIAL | K1: six of nine trades ended when a deployer shut down (lines 11-13, 47-50). The A venues no longer exist. K7: eight names dropped only by the NaN bug. K3: the exit-day price leg is booked at the last 20:00 UTC mark (lines 56-58). | experiments/hip3other_v1/FINDINGS.md:11-13, 47-58, NaN section | re-check the NaN. Forward on Paragon only (live). |
| R477 | xyztwin_v1 | PARTIAL | K7: NaN bug drops TLT in B (lines 55-64). K3: a 30-minute timing gap and a price leg that swamps carry (lines 75-78). K5: an EUR owner bears EUR/USD on the book (lines 83-86). t = 0.50 in A. | experiments/xyztwin_v1/FINDINGS.md:55-64, 75-78, 83-86 | re-check with the NaN fix. No money claim. |
| R478 | rollcarry_v1 | PARTIAL | K1: funding halved on xyz since 2025-12-19 (line 74). Margin shrank in the second half (lines 66-70). K5: UNG, USO and BNO are not buyable by a French account (line 92). K3: marks from a 4-hour fallback (lines 20-21). | experiments/rollcarry_v1/FINDINGS.md:9-12, 20-21, 66-70, 74, 92 | re-check. A forward lane needs a French-held hedge (CME futures via broker, or a UCITS ETC), as the FINDINGS says. |
| R481 | ltroll_v1 | NULL | K1: documented July-October months negative (-5.78 pts, t -2.27). K7: 7-8 missing prints per market. | experiments/ltroll_v1/FINDINGS.md:3-8, 26-33 | none. The arbitrage held on Lighter. |
| R412 | boroslock_v1 | DATA_PASS ("LOCK_HOLDS") | K1: locked rate 10.2% (2025-09), 3.0% (2026-04), 7.9% (2026-09) (lines 59-63). K7: indicative carry after round trip is negative at 1x, below the T-bill on average (lines 65-78, 93). The runner's Binance label is wrong (lines 9-11). K5: Boros/Pendle access not checked. | experiments/boroslock_v1/FINDINGS.md:9-11, 56-63, 65-78, 93 | none for money. The lock mechanism holds. The carry at 1x does not beat the T-bill. |
| R450 | hlvaultsel_v1 | NULL (-27 pts, t -2.26) | K4: the rule picked steady-record vaults; three blow-ups in October 2025. K1: 2026 steady vaults earned +8.2% while the book lost 31%. | experiments/hlvaultsel_v1/FINDINGS.md:3-5, 13, 27-35 | none. |
| R452 | litpoolsel_v1 | NULL | K7: the rule mostly picked dormant pools, a design flaw (lines 6-10). K4: one month carries the result (line 34). | experiments/litpoolsel_v1/FINDINGS.md:6-10, 34 | re-check only if the rule is re-specified under a new id. |
| R484 | llphouse_v1 | NULL (both books) | K7: one hourly settlement missing from the last trade day, judged immaterial (FINDINGS "Window and events"). | experiments/llphouse_v1/FINDINGS.md:1-10, 18-22 | none. |
| R486 | litbuyback_v1 | NULL | K4: two trials. The correlation sits inside its null (p 0.154). | experiments/litbuyback_v1/FINDINGS.md:3-6 | none. |
| R487 | adlstress_v1 | PARTIAL (a bound) | K5: Hyperliquid-leg books are exposed: R278 A's S1 bound is 29.35% of book capital at 2x (lines 3-6). Under S2 all nine books are exposed (21-55%). | experiments/adlstress_v1/FINDINGS.md:3-8 | keep as a risk. Hyperliquid-leg books (R278 A, R475) need an ADL stop in any money case. |
| R223 | settle_v1 | NULL (discovery only) | K1: discovery 2021-2023 only; holdout unread. K7: validation not run. | experiments/settle_v1/FINDINGS.md (head) | reopen with the 2024-26 holdout under a frozen rule. The NULL is valid for 2021-23. |
| R353 | settlehop_v1 | NULL | K7: 20.1 bp round trip at 1x, measured as four sides (line 89). The Lighter leg is 0-fee; re-check the cost split with measured Lighter and MEXC book costs. | experiments/settlehop_v1/FINDINGS.md:10, 89 | re-check cost sensitivity. The NULL stands at the frozen costs. |
| R354 | settlehop_pred_v1 | PARTIAL (PASS recorded PARTIAL) | K3: the entry sits at a Binance perp 2.8% under its index, on a last trade (line 8). K4: six trials. K5: Binance leg not accessible to a French retail client (inference from R439's access note). K1: 86 of 87 hops are the same direction. | experiments/settlehop_pred_v1/FINDINGS.md:3-12, 127 | re-check the valuation. Check the owner's access for the Binance leg before any claim. |
| R356 | settlehop_exit_v1 | PARTIAL | K1/K4: +15.2 of the +19.6 bp gain is a funding hour, so the exit is a timing variant of R354, not new evidence. | experiments/settlehop_exit_v1/FINDINGS.md:3-9 | none beyond R354. |
| R362 | settleticks_v1 | NULL | K7: the decided instant (T+15 s) could hide an effect at T+1 s. That variant reads +28.7 bp at 1x, t 1.90, reported not decided (line 36, 49). K5: a T+1 s taker entry is not executable for a retail owner (inference). | experiments/settleticks_v1/FINDINGS.md:36, 49 | none for the owner. Reopen the instant only as a measurement. |
| R363 | settlelit_v1 | PARTIAL | K3: minute-close last trades. 18 of 134 entries are stale (line 31). K4: the "unseen" hops had their Binance seconds read by R362 (lines 4-6). K5: Lighter is on-chain. | experiments/settlelit_v1/FINDINGS.md:4-10, 31 | re-check the stale-entry rule. Confirm Binance-leg access. |
| R387 | settlelit_1h_v1 | NULL (CR1 t 1.64) | K7: a near-miss. Net is positive at 2x (+6.4) and 3x (+3.5). The 1h-class sample is 222 events, 9 coins (lines 12-22). K1: window 2025-10..2026-09. | experiments/settlelit_1h_v1/FINDINGS.md:12-22 | none now. Re-test when more events accrue, under the same frozen rule. |
| R388 | forcedswitch_v1 | NULL | K4: tail-driven. The median 1x net is -174 bp; the five best events are 175% of the total (lines 21-35). | experiments/forcedswitch_v1/FINDINGS.md:21-35 | none. |
| R280 | levcarry_v1 | DATA_PASS (measurement) | K5 (central to the owner): isolated margin per leg liquidates every book at 1x. Cross margin per venue is needed. The 2025-10-11 crash takes Gate accounts at 2x (lines 6-9, 23-29, 80-88, 95-105). | experiments/levcarry_v1/FINDINGS.md:6-9, 23-29, 80-88, 95-105 | re-check every R275-family 1x figure against the owner's margin mode. Either confirm cross margin on each venue or retire the figure. |
| R401 | carry_cost_qualification_v1 | PARTIAL (incomplete source) | K7: cost of the R391 pairs unknown; body reached a 2 MiB cap; no decode (lines 1-20). | experiments/carry_cost_qualification_v1/FINDINGS.md:1-20 | a new frozen protocol is needed to measure book costs. |
| R402 | carry_targeted_costs_v1 | PARTIAL (overrun, no economics) | K7: 19th request overran its reservation. Dispatch is blocked. No cost or return measured (lines 3-27). | experiments/carry_targeted_costs_v1/FINDINGS.md:3-27 | none. This consumed protocol must not be resumed. |
| R497 | gatemaker_v1 | DATA_PASS (LEVER_HOLDS) | K7: the rule counts every trade at the touch as a fill. Queue position and time to fill are not measured (lines 4-6). This matters for every maker-cost re-check in this table. | experiments/gatemaker_v1/FINDINGS.md:1-6 | use as the basis for maker-cost re-checks (R281, R436, R442), only after a queue measurement. |
| R321 | dependent_null_v1 | NULL (infra, synthetic) | None for carry economics. Synthetic Monte Carlo; no market PnL. | experiments/dependent_null_v1/FINDINGS.md (head) | none. |
| R183, R262, R264, R403, R407 | infra (data, impact, accounting checks) | DATA_PASS | None for economics. Registry notes state coverage or a tier check only. R262 says impact is 0.4-1.4% of validation net at $10k (registry note). | registry/rounds.csv (notes) | none. |
| R312-R319, R322-R326, R373 | infra (measurement, PARTIAL) | PARTIAL | None for economics. Headers read only. | experiments/<lane>/FINDINGS.md (head) | none. |

## 2. Ranked: the five most important findings for real money

1. **The KuCoin 2025-26 pace is pre-scaling, and the lab's carry headlines rest on it (K1, K7).**
   - R384 shows KuCoin scaled its funding on 2026-07-25 (experiments/xfundint_v1/FINDINGS.md:21). Post-scaling, the books
     earn +10.5%/yr (gate+kucoin) and +10.0%/yr (binance+kucoin) over 69 days (lines 23-25).
   - R277's "+20-24%/yr in 2025-26" (experiments/xfund_kd_v1/FINDINGS.md:34-35) and R288's comparison "3-4 times any
     Lighter set" (experiments/xfund_lt_v1/FINDINGS.md:63-66) are on the pre-scaling rates. So are R438, R439 and the
     KuCoin "BEATS" in R483 (experiments/carryhurdle_v1/FINDINGS.md:89).
   - Paid rates versus recorded rates is unchecked (experiments/xfundint_v1/FINDINGS.md:84-85). Inference: the
     2021-24 KuCoin average (about 8%/yr) is about the post-scaling level, so the inflation is in the 2025-26 pace.
   - Action: verify the paid rate factor per contract before any figure goes into a money plan.

2. **Almost nothing in the carry family is yet a route the owner can hold from France (K5).**
   - R439 says the five-venue book "is not one the owner can hold from France" (experiments/carry5_v1/FINDINGS.md:68-71).
   - R288 has no Lighter account (experiments/xfund_lt_v1/FINDINGS.md:13). R275's Gate+Hyperliquid and Binance+Hyperliquid
     books need a non-French CEX leg (experiments/xfund_v1/FINDINGS.md:123-124).
   - R483's sUSDe benchmark is "not offered to EU/EEA residents" (experiments/carryhurdle_v1/FINDINGS.md:123-124).
   - The one French-eligible carry screen, OKX Europe, is NULL (experiments/okxcarry_v1/FINDINGS.md:69-75). Kraken (R418)
     and Coinbase CDE (R424) also failed on the lab's own record (same file, lines 73-74).
   - Action: map every book in this table to a venue the owner can open, using `docs/reviews/venue_access_fr_20261110.md`.
     Until a two-leg route exists, no carry round is a money claim.

3. **The 1x figures of the funding-carry books assume cross margin per venue (K5).**
   - Under isolated margin per leg, every R278/R279 book has legs liquidated at 1x on 155 days, mostly on short-leg pumps
     (experiments/levcarry_v1/FINDINGS.md:6-9, 48-51). Only cross margin keeps 1x intact (line 8-9).
   - The HIP-3 result R475 is half one isolated-margin liquidation day (experiments/hip3stock_v1/FINDINGS.md:35-43). Trade.xyz
     books are mostly isolated (docs/reviews/reflection_20261125_power.md:177).
   - Inference: the owner's default margin mode on each venue decides which figure applies. Nothing in the lab records it.
   - Action: confirm the margin mode on each venue before using any 1x figure. Cross-only figures carry a label.

4. **Last-trade valuation misstates the price legs of the same books (K3).**
   - The R275 family values price legs on daily last-trade closes with constant notional (experiments/xfund_v1/FINDINGS.md:153-154).
     It carries stale delisted legs (lines 91-100; NEIROETH -83%, A2Z -140%, YALA -114%).
   - The v2 blowout exits add +3.4 pts/yr on the Binance+Gate books, closed on last prints (experiments/carry_v2_audit_v1/FINDINGS.md:67-71).
   - KuCoin's price leg moves from +1.29 to -2.14 on the five-venue book (experiments/carry5_v1/FINDINGS.md:34-39).
   - The convergence reflection found last-trade valuation on thin coins misstates price PnL by about 0.2-0.3% a trade
     (docs/reviews/reflection_20261124_convergence.md:66-69, 74-75). Inference: the same bias applies here.
   - Action: re-value the books on executable marks (Kraken or Hyperliquid hourly mark or mid, as the convergence reflection did)
     before any capital is set.

5. **Decay and regime are real in this family, and the replications were never re-run on the corrected engine (K1, K7).**
   - R190 earned +35% in 2021 and about 0 in 2022-23 (experiments/carry_v1/FINDINGS.md:15). The holdout earns +1.2%/yr
     (experiments/carry_holdout/FINDINGS.md:12, 20). R335's locked offer was absent in 2026 (experiments/locked_carry_v1/FINDINGS.md:13).
   - The xyz funding halved on 2025-12-19 (experiments/rollcarry_v1/FINDINGS.md:74; experiments/xvfund_v1/FINDINGS.md:55-56).
   - R288 (Lighter) and R391 (reserved batch) are on the v1 engine. R288's own audit notes already put MEXC+Lighter at
     3.67%/yr on daily bars, below the 4.13% hurdle (experiments/xfund_lt_v1/FINDINGS.md:162-164), and were not applied.
   - The trend reflection's regression has not been run on R275's own pairs. Inference: R275's Gate+Hyperliquid 2026 (+8.4%)
     is not the decay pattern of R525's non-Kraken pairs, so the reflection's 2026 "~0" conclusion may not transfer.
   - Action: run the cycle-8 regression on the daily nets of R275's books. Re-audit R288 and R391 on M468 v2 before citing them.

## 3. Answers to the checklist, in brief

- **K1 (decay/regime):** the design-gap decay is not tested on the R275 pairs. The KuCoin pace is inflated by a scaling
  change (R384). Several rounds (R190/R191, R335, R470, R478, R412) show regime dependence.
- **K2 (PnL source):** R275's FINDINGS describes the funding difference correctly (line 21-22, 89-90). Its direction is
  sign-agnostic by design. The FINDINGS does not report PnL split by sign of spread over time. R288 and R277 report which leg
  is long (experiments/xfund_lt_v1/FINDINGS.md:46-47; experiments/xfund_kd_v1/FINDINGS.md:49), which is not the same thing.
- **K3 (valuation):** yes, for the R275 family and the settle family (R354, R363). The stale-entry count is reported in R363
  (line 31). The R275 family's audit (H2, F4) changed returns by up to 3 pts/yr.
- **K4 (selection):** R275's headline t survives its own null (560 books, p95 4.27), so the selection threat is to the magnitude,
  not the sign (inference). The post-hoc best-by-return book (gate+mexc, +16.3%) is the case to discount.
- **K5 (owner):** dominant. Access, margin mode and capital (R275: $250 per leg; R439 access note; R280 margin).
- **K6 (mechanism and control):** no round in this family has a placebo control. R483 and R390 use passive benchmarks, which
  are the nearest thing. R335's offer-follows-leverage mechanism matches the reflection's regime argument.
- **K7 (nulls):** the nulls that could be cost-driven: R281, R436, R442 (maker not tested; R497 is the lever). The null
  driven by idle capital: R444. The near-miss: R387 (t 1.64). The null from a mis-specified rule: R452.

## 4. Items for the owner (not decided here)

- The owner's margin mode on each venue (cross or isolated) and whether a French account can open each leg.
- Which venues the owner can open. This is the owner's act (AGENTS.md rule 5), so the room records it and does not decide it.

No file other than this one was written. No commit was made. No journal was opened, and no forward or fast script was run.
