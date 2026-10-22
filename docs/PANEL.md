# Panel

Rebuilt 2026-10-22 03:43 UTC by `scripts/panel.py` at the end of each tick. Do not edit by hand.

**Objective.** The best net PnL from any method in any market the owner can trade: MEXC perpetuals first, then spot, prop challenges, forex and index futures as data allows. Search wide (every method is tested, a null is evidence); trust narrow (only days nobody had seen when the rule was frozen count). Money moves only through the four gates in `docs/GATES.md`, at stakes the owner sets.

## How we proceed (owner-approved direction, 2026-10-20: [DIRECTION](DIRECTION.md))

Every tick:
1. `scripts/forward_all.sh` runs the point-in-time recorders (MEXC funding and ticker, notices, unlock calendar), every forward paper lane, the lag report, this panel and the recorder digests.
2. Background jobs (family runs, downloads) are checked; a finished one gets FINDINGS at 1x/2x/3x of its execution mode's cost and a registry row with its full trial count.
3. Breadth through families: strategies from the queue and the quant literature run as one frozen PREREG per family (all variants, reality check or SPA, random null), in the background. A null is evidence.
4. Family survivors go to scheduled batch reads of the reserved samples (2020 crypto, MEXC-only coins; GATES "Reserved samples"). A batch pass becomes one frozen forward paper lane (gate 1), labelled manual-web or API. Real money only after gates 1-3, placed by the owner (gate 4).
5. Read the room (issue #7), commit and push.

Roles: Claude does all of it, with no subagents and no Workflows (owner, 2026-10-20). Codex has stopped.

## 1. The funnel

Screen (gate 0, exploratory) → research on unseen days (gate 1) → execution on MEXC (gate 2, `go_real` here) → account risk (gate 3) → the owner (gate 4). Rules and dates: [GATES](GATES.md); what the critics found: [CRITIQUE](CRITIQUE.md).

| stage | now |
|---|---|
| Ideas in the queue, untested | 38 |
| Ideas partly tested | 38 |
| Ideas blocked (data, download, compute) | 68 |
| Rounds in the registry | 114 (NULL 73, PENDING 20, PARTIAL 8, CONFIRMED 8, DATA_PASS 5) |
| Program trials | 9,478,593 |
| Forward paper lanes running | 17 |
| Strict on-time paper days so far | 0 |
| Passed gate 1 (unseen days) | none yet |
| Next decision date | 2027-01-18: first 90-on-time-day looks (R215, R218, R220, R221 futility) |

## 2. Forward paper lanes (the only road to money)

Replay days were scored after the freeze on days the archive did not hold; on-time days are the evidence.

| lane | book | replay | on_time | 2x / 3x | decided by |
|---|---|---|---|---|---|
| R215 mexc_fwd | flow book A on MEXC | 19 d +4.6% | 2 d +2.0% | +1.9% / +1.8% | R221 looks at 90 / 182 / 365 on-time days |
| R215 mexc_fwd | top-vs-crowd on MEXC | 19 d -0.1% | 2 d +0.8% | +0.8% / +0.8% | R221 looks at 90 / 182 / 365 on-time days |
| R218 mexc_fwd_sq | flow book X2 (k squared) on MEXC | 19 d +5.9% | 2 d +2.0% | +1.9% / +1.8% | R221 looks at 90 / 182 / 365 on-time days |
| R220 carry_fwd | funding carry, MEXC | 19 d -0.0% | 2 d +0.0% | +0.0% / +0.0% | 90 on-time days through go_real |
| R220 carry_fwd | funding carry, Binance | 19 d +0.0% | 2 d +0.0% | +0.0% / +0.0% | 90 on-time days through go_real |
| R200 flow72_fwd2 | flow book A, Binance | 18 d +22.2% | 3 d +1.6% | +1.4% / +1.2% | 90 scored days through go_real plus NW t >= 2 |
| R200 flow72_fwd2 | top-vs-crowd, Binance | 18 d +9.7% | 3 d +0.5% | +0.5% / +0.4% | 90 scored days through go_real plus NW t >= 2 |
| R214 flow72_fwd3 | A one bar late | 19 d +22.6% | 2 d +1.4% | +1.3% / +1.2% | same days as R200, a delay check |
| R214 flow72_fwd3 | B one bar late | 19 d +9.4% | 2 d +0.8% | +0.7% / +0.7% | same days as R200, a delay check |
| R278 xfund_fwd | cross-venue carry, Gate + Hyperliquid | 61 d +0.5% | 0 d | - | NW t >= 2.5 at 90 / 180 scored days |
| R278 xfund_fwd | cross-venue carry, Binance + MEXC | 61 d +0.9% | 0 d | - | NW t >= 2.5 at 90 / 180 scored days |
| R278 xfund_fwd | cross-venue carry, Gate + MEXC (post hoc) | 61 d +1.4% | 0 d | - | NW t >= 2.5 at 90 / 180 scored days |
| R279 xfund_kc_fwd | cross-venue carry, Gate + KuCoin | 61 d +1.4% | 0 d | - | NW t >= 2.5 at 90 / 180 scored days |
| R279 xfund_kc_fwd | cross-venue carry, Binance + KuCoin | 61 d +1.5% | 0 d | - | NW t >= 2.5 at 90 / 180 scored days |
| R294 xfund_lt_fwd | cross-venue carry, MEXC + Lighter | 61 d +0.7% | 0 d | - | NW t >= 2.5 at 90 / 180 scored days |

Processing lag of on-time hours: 50 hours, median 80.68333333333334 min, max 261.48333333333335 min; days with late hours: 2026-10-20, 2026-10-21.

## 3. Next in the queue

| id | method | data_held | status | cheap | note |
|---|---|---|---|---|---|
| M007 | Conviction-weighted sleeves: score weights clip(z,-2,2) vs equal weights at the same gross | Y flow bins (data/research); daily nets | UNTESTED | 1 | 1/N is hard to beat (DeMiguel et al.). Low prior. |
| M014 | Chan half-life and ADF filter to select mean-reverting coins before a reversal book | Y klines_1h | UNTESTED | 1 | Selection filter. Weak prior. Count its trials. |
| M015 | Listing short with a 14-day stop (MEXC rule 3) | Y klines_1h (listing history) | PARTIAL | 1 | Stop variant untested. Early-drift literature (B) points the other way. Low prior. |
| M016 | Abnormal volume x short constraint (Garfinkel): abnormal volume predicts lower returns where shorting is constrained | P klines_1h; no borrow data (funding/OI as proxy) | PARTIAL | 1 | Volume-alone part is dead. The constraint interaction is open; the constraint is a proxy. |
| M017 | Residual momentum split by liquidity tier (ranks 1-10 vs 11-50), 365 d window, 30 d hold | Y klines_1h | PARTIAL | 1 | Tier split and 365 d window not run. |
| M018 | Realized-variance forecast race: trailing mean vs EWMA vs HAR-RV vs GARCH, QLIKE on next-24 h RV | Y klines_1h (RV from hourly returns) | PARTIAL | 1 | Risk skill, not direction. A win supports sizing, not alpha. |
| M020 | Crowd extreme rule: short coins whose global account L/S is above its 95th pct of 90 d, 72 h hold, hedged | Y metrics_1h (global ratio) | PARTIAL | 1 | CLAIMS: crowd ratio is weaker than top vs crowd. |
| M021 | OI change as a crash/risk-state variable (P of -20% in 30 d), not a direction call | Y metrics_1h OI; klines_1h | PARTIAL | 1 | Claimed OOS AUC 0.677 in one 10-asset study. Risk use only. |
| M022 | Multi-timeframe sign agreement (1 h, 4 h, 24 h same sign) as entry or size filter | Y klines_1h | PARTIAL | 1 | Agreement count never run. Low prior. |
| M023 | BTC clock rules: long BTC 21-23 UTC; month-of-year effects | Y klines_1h | PARTIAL | 1 | Clock family null. Low prior. |
| M024 | OI quadrant model, L/S ratio and top-trader positioning (old F1-F3) | Y metrics_1h | PARTIAL | 1 | Folk quadrant model killed (old). Similar to R196-R198. |
| M025 | Copy-leader ROI vs PnL description: rank corr, share of top-100 ROI with AUM < $10k, copier PnL by ROI decile | P one snapshot (2026-10-19, Binance) | UNTESTED | 1 | Descriptive, one date. Not a trading rule. |

## 4. Waiting on the owner

- Answered 2026-10-20: every public download approved ("we need all data possible"); execution mode both (manual-web and API, labelled per lane); tiny live calibration orders: not yet; R263 runs once offline.
- Install PyTorch CPU and the Kronos-small weights (about 300 MB): R227 Kronos lane (PR #9).
- Rotate the two Coinalyze API keys pasted into the old session's chat (`docs/OLD_SESSION_EDGES.md`, security note).
- Set the stake and max loss for gate 4 (`docs/GATES.md`; the lab only proposes 2% of trading capital per book and a stop at 25% of the stake).
- Merges: Codex's draft PRs #26/#27 (R257) and the second Claude session's PR #25 (retarget to `claude/yo-9a1k5w`).

## 5. Latest rounds

| id | lane | status | verdict | trials |
|---|---|---|---|---|
| R290 | auction_v1 | DONE | NULL | 60 |
| R291 | vpin_v1 | DONE | NULL | 4 |
| R293 | er_v1 | DONE | NULL | 3 |
| R288 | xfund_lt_v1 | DONE | CONFIRMED | 6 |
| R292 | dealerflow_v1 | DONE | NULL | 4 |
| R294 | xfund_lt_fwd | RUNNING | PENDING | 1 |
| R295 | optflow_v1 | DONE | NULL | 15 |
| R296 | charm_expiry_v1 | DONE | NULL | 5 |

Details: [MAP](MAP.md), [EDGE_SCOREBOARD](EDGE_SCOREBOARD.md), [METHODS_QUEUE](METHODS_QUEUE.md), [GATES](GATES.md), [CRITIQUE](CRITIQUE.md), [room #7](https://github.com/SaikiK12/T/issues/7).
