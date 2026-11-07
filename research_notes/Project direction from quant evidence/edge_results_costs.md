# Edge results and costs: what every tested lane found (as of 2026-10-20)

> **Historical review — 2026-10-20.** This document describes an earlier checkout. Its counts, data coverage, calculations and recommendations have not been refreshed or revalidated. The [original revision](https://github.com/SaikiK12/T/blob/ec9029ecdefd5e88f1f335226dd0abbaeda0ebe2/research_notes/Project%20direction%20from%20quant%20evidence/edge_results_costs.md) retains the received text. Use the [current panel](../../docs/PANEL.md), [live queue](../../registry/methods.csv) and linked lane evidence for present decisions. Local links below have been made portable; unavailable source paths are labelled.

Source: per-lane research subagent, returned in its reply. The coordinator saved this text unchanged because the subagent did not write the file. Its figures are unverified by the coordinator, and no lab code, registry row or run script was executed.

**Verdict.** At base cost, two results clear holdout t>=2: carry (t 2.07) and top-trader book B (t 2.72). At 3x, carry is negative and B still clears (t 2.44). Neither has a family-wise test, and B was not the frozen decision.

## Lane table

Paths are /home/user/T/experiments/<lane>/FINDINGS.md. Holdout is 2025-07-01..2026-09-30 (457 days) unless noted. Registry R# in brackets.

| Lane [R#] | Verdict | Killed at | Holdout |
|---|---|---|---|
| allocation_v1 [228] | NULL | validation (Sharpe gain 0.007 vs 0.15) | descriptive only |
| amihud_v1 [236] | NULL | validation (-9.2 bp/d, t -1.07) | unread |
| atlas_v1 [185] | in-sample PASS, gross | none; below per-trade cost | not read |
| atlas_ctx [192] | in-sample PASS, gross | none; excess lifts only | 289 pairs spent (ctxslice_v2) |
| atlas_mtf [195] | in-sample PASS, gross | none | as atlas_ctx |
| carry_v1 [190] | in-sample PASS | none (disc t 3.80, val 2.82) | see R191 |
| carry_holdout [191] | holdout gate PASS, 1x only | fails 2x (t 1.14) | +1.45%, t 2.07 |
| carrycrash_v1 [207] | NULL, sign reversed | discovery (t -2.06) | -3.0%, t -0.54 (7 d) |
| cascmkt_v1 [255] | NULL | validation (t 1.03, 15 events) | spent, not read here |
| cbprem_v1 [210] | NULL | discovery (BTC t 0.34) | +0.7 bp/d, t 0.88 |
| chartist_v1 [243] | NULL | discovery (best t 1.23) | unread |
| chartxm_v1 [247] | NULL | discovery (best t 1.50) | unread |
| ctxslice_v1 [201] | NULL | stage 1 in-sample (-32%/yr, t -1.97) | unread |
| ctxslice_v2 [204] | NULL | holdout | -6.5%/yr, t -0.13 |
| daylimit_v1 [208] | NULL, harmful | in-sample (-22.5 bp/d, t -8.3) | 2nd window -57 bp/d, t -3.7 |
| delay_v1 [213] | NULL (1-2% cost) | n/a | A t 1.21, B t 2.69 (1 h delay) |
| dow_v1 [256] | NULL | discovery (best t 0.84) | unread |
| flow72_fwd [199] | ABANDONED | data-parity gate | none |
| flow72_holdout [198] | NOT CONFIRMED | holdout, A t 1.22 | A +22.7 bp/d; B alone t 2.72 |
| flow72_v1 [196] | NULL | primary (-20%/yr, t -2.73) | n/a |
| flow72_v2 [197] | in-sample PASS | none (t 3.25) | to R198 |
| fxindex_v1 [239] | NULL | discovery (6 rules); VRP passed disc and val | VRP t 1.11 (2020-26) |
| ictlevels_v1 [246] | NULL | discovery (RN_CROSS t -9.93) | unread |
| itsm_v1 [203] | NULL | discovery (gross -2.2 bp, t -0.96) | unread |
| liq_v1 [206] | NULL | primary net (-36 bp/d, t -1.96) | single window |
| listings_holdout [189] | NOT CONFIRMED | holdout | 7 d: -2.6%, t -0.78, n 206 |
| listings_v1 [188] | NULL | primary (abs t below 3) | spent via R189 |
| lmw_v1 [251] | NULL | validation (t -0.18) | crypto unread |
| maker_v1 [193] | NULL | validation (book t 0.18) | spent for choice |
| merge_v1 [186] | NULL | primary (gross t 1.27; net -32.6%/yr) | none |
| merge_v2 [187] | NULL ("FAIL") | primary (gross -1.7%/yr) | none |
| oiwick_v1 [252] | NULL | discovery (t 1.93 vs 2.0) | unread |
| optimizer_v1 [253] | NULL | validation (family p 0.54) | descriptive |
| pack_v1 [194] | NULL | primary (beta 1.0; hedged -25%/yr) | none |
| pairs_v1 [250] | NULL | discovery | unread |
| partial_execution_v1 [231] | NULL | validation | descriptive |
| pivotfade_v1 [248] | NULL | validation (all 4 windows) | unread |
| posfam_v1 [211] | NULL | validation (t 1.31, 0.85) | unread |
| posfam_v2 [212] | NULL | validation (t 1.13, gate 1.5) | unread |
| posimpulse_v1 [234] | NULL | discovery (best t 0.90) | unread |
| posimpulse_v2 [240] | NULL | validation (t 1.33; -2.3 bp/d at 3x) | unread |
| propfirm_v1 [202] | PARTIAL, descriptive | no pass rule | streams only |
| rebalancing_v1 [232] | NULL | validation (Sharpe bar missed) | descriptive |
| regime_v1 [233] | NULL | discovery (no gate selected) | unread |
| rnfade_v1 [249] | NULL as a book | validation (no book t>=2; difference t 2.53) | 2025-07 unread |
| seesaw_v1 [219] | NULL | discovery | unread |
| settle_v1 [223] | NULL | discovery (long leg -38.5 bp/event) | unread |
| sizing_v1 [217] | NULL | discovery and validation (no +0.3 Sharpe rule) | re-read: X2 t 1.70; A t 1.22 |
| slow_trend_v1 [229] | NULL | validation (Sharpe +0.03 vs +0.15) | descriptive |
| tradesize_v1 [226] | NULL | discovery (all 6) | unread |
| tsbattery_v1 [242] | NULL | validation (VOLTREND t 0.52) | unread |
| tsmom_v1 [237] | NULL | discovery (t 1.00) | 2013-26 unread |
| usindex_calendar_v1 [235] | NULL | discovery (max t 1.45) | 2013-26 unread |
| venue_gap_v1 [216] | DATA_PASS (TradFi flag raised) | n/a | B crypto t 2.74; forward replay -0.5% |
| volrisk_v1 [241] | NULL | holdout (SVXY t 1.70) | 2020-26 window |
| vrp_v1 [209] | NULL | holdout (+1.1 bp/d, t 0.12) | read once |
| weekendlink_v1 [244] | NULL | discovery (t -0.14) | 2025-07 spent |
| weekly_rotation_v1 [230] | NULL | validation (Sharpe 0.83 vs 1.11) | descriptive |
| xsalt_v1 [222] | NULL | discovery (best t 1.23) | unread |
| xsbattery_v1 [238] | NULL | discovery (best t 1.77) | unread |
| xsrev_v1 [245] | NULL | discovery (1 d liquid t -3.73) | unread |
| xvenue_v1 [205] | NULL | replication (G t 1.43) | spent; B on Binance t 2.08 (157 d) |

Count of the 62 lanes with FINDINGS: 51 NULL, 5 in-sample PASS, 1 holdout gate pass (carry), 2 NOT CONFIRMED, 1 DATA_PASS, 1 ABANDONED, 1 PARTIAL. Registry rows without a folder: R143, R144, R180-R183.

## Holdout survivors and cost sensitivity

| Candidate | Mean net 1x / 2x / 3x | t 1x / 2x / 3x | Daily hit | Break-even (derived) |
|---|---|---|---|---|
| Carry, R191 (n 457; 25% invested) | +1.45% / +0.66% / about -0.12% total | 2.07 / 1.14 / n.r. | n.r. | about 2.8x |
| B, all symbols, universe hedge, R198 csv | 19.6 / 18.6 / 17.6 bp/d | 2.72 / 2.58 / 2.44 | 57.5% | about 21x |
| B, crypto only, R216 | 18.3 / 17.4 / 16.5 bp/d | 2.74 / 2.60 / 2.47 | n.r. | about 22x |
| A, frozen primary, R198 (fails) | 22.7 / 16.9 / 11.1 bp/d | 1.22 / 0.91 / 0.60 | 54.7% | about 4.9x |

- n.r. means not reported. Carry 3x is the subagent's calculation: (funding + basis - 3 x cost) from carry_holdout/results/holdout.json. Break-evens are linear in the 1x/2x/3x points.
- Daily hit rates and the t values for B and A are the subagent's recomputation from /home/user/T/experiments/sizing_v1/results/daily.npz (B_C0, A_C0; NW lag 10). They match the reported t (A 1.22; B 2.69 vs 2.72).
- Concentration (same file): B's top 10 of 457 days are 47% of its holdout sum; without them t falls to 1.58. A's top 10 days exceed its whole holdout sum (113%); without them t is -0.16.
- Family-wise p: lab/nulls.py defines familywise_p and tests/test_lab.py checks it, but no run script calls it, and no FINDINGS or result carries the CANDIDATE label (lab/config.py FW_P_CANDIDATE). Against registry.program_trials() (9,472,034 by code), a two-sided Bonferroni bar at 0.05 needs |t| of about 5.8. No holdout t in the repo (max 2.74) reaches it. This is conservative because cells are correlated, but no formal test was run.
- In-sample reference: flow72_v2 A is +42.6%/yr at 1x, +26.9% at 2x, +11.3% at 3x (t 3.25, 2.07, 0.87).
- Unlock short (R181, outside this repo): the old session reports +2.50% per event at 20 bp round trip, hit 62%, with 2x and 3x not printed (OLD_SESSION_EDGES.md section 3). If 20 bp is the only cost, 2x is about +2.3% and 3x about +2.1% (derived). Its holdout is not clean.

## Family assessment

- **Atlas and cell search** (17 rows): 9,471,554 of the 9,472,034 registered trials (subagent's sum by family). Gross in-sample edges only; every per-trade or book test fails costs or validation. Exception: raw OI-vs-price reversal replicates gross in 2024-25H1 (-63/-55 bp, atlas_v1 FINDINGS), but not net.
- **Flow and top-trader positioning** (22 rows, 148 trials): A fails its holdout. B passes only as an unfrozen read. Its MEXC crypto forward replay is about zero (-0.1%, 18 days). Crypto replay of A is +4.7% on MEXC.
- **Funding carry** (6 rows): holdout gate at 1x only, about 1.2%/yr in 2025-26. The only frozen holdout pass.
- **Listings and unlocks**: listings fail the holdout (t -0.78). The unlock short is in-sample only and cannot be checked here.
- **Volatility and VRP**: BTC VRP fails its holdout. SVXY contango reaches t 1.70 (fails t 2) with max drawdown 50%.
- **Spot portfolio and sizing**: all NULL at validation; holdout readings are descriptive.
- **Altcoin cross-section, liquidity, pairs**: all NULL before any holdout.
- **Chart/TA and patterns**: all NULL. The round-number mechanism replicates as a difference (t 2.53) but no book passes.
- **Crypto time series, calendar, FX/index**: all NULL before their holdouts.
- **Copy trading**: no lane tested. M063 and M064 are BLOCKED pending a forward collector. copylead_data holds snapshots only; it has no FINDINGS and no registry row.
- **Forward**: no edge has a strict on-time day (/home/user/T/experiments/forward_lag/status.json, strict_ontime_days 0). No go_real ticket has been scored.

## Disagreements

1. Trials: EDGE_SCOREBOARD and cascmkt_v1 FINDINGS (line 90) quote 9,472,031. The registry sums to 9,472,034. The difference of 3 matches R253's trials, which the running totals omit (unverified why).
2. Registry "CONFIRMED" (R181, R185, R190, R192, R195, R197) marks in-sample passes. flow72_v2 FINDINGS says "PASS (in-sample design check)". Only R191 is a holdout pass, and only at 1x.
3. R199 is REGISTERED/PENDING in the registry but ABANDONED in flow72_fwd FINDINGS.
4. R209: registry says "6/8 variants lose on holdout"; vrp_v1 FINDINGS says 7 of 8 (erratum noted).
5. ALTCOIN_LEADS.md says funding, OI vs price, premium, taker and volume were "all dead in 2024-25". atlas_v1 shows funding 0%, taker 1%, volume 3%, premium 23%, but a raw OI-vs-price reversal that replicates.
6. EDGE_SCOREBOARD reports B's "t 1.6 without top 10 days" (confirmed, 1.58) but not A's same test (-0.16).
7. EDGE_SCOREBOARD gives listings "best of 48, t -3.06" without that configuration's validation t of -1.52 (listings_v1 FINDINGS line 17).
8. Holdout definition: FOUNDATION and AGENTS fix it at 2025-07-01. volrisk, fxindex, tsmom, chartxm and usindex use 2020-01-01..2026-10-19 (PREREG files). EDGE_SCOREBOARD calls 2025-07 "the only out-of-sample window in the archive", which overstates it for those lanes.
9. AGENTS rule "3x in every FINDINGS": carry_holdout and carry_v1 give no 3x; listings_holdout gives no cost sensitivity.
10. A's holdout: the subagent's daily replay gives 21.9 bp/d and 99.9% total; R198 csv gives 22.7 bp/d and 103.8%. t matches (1.22). About 4% unexplained.
11. Registry rows R143, R144, R180-R183 point to folders absent here (unlocks_sf, unlocks_deep, hypermine, hypermine_expand, funded, challengeoption). The integrity audit has 0 errors and 12 warnings, with 70 of 71 specs verified. R182's 139,377 trials are in the program total but cannot be audited here.
12. propsim_v1 and forward_lag have no registry row. No ledger.csv exists in any lane; forward state is in journal/tickets.csv and status.json.

## Not checked

- Unlock short forward (R180) and the R179-R181 numbers: taken from registry and old-session text only.
- Family-wise p and daily hit rates for carry, volrisk, vrp and venue_gap: not computed.
- The B holdout was read by at least six lanes (flow72_holdout, venue_gap, delay, sizing, xvenue, daylimit), so it is not a clean holdout.
- Unit tests not run. No lab code, registry or FINDINGS was edited. No run script was executed.
- Did not post to room #7 (read-only brief).
