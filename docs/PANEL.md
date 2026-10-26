# Panel

Rebuilt 2026-10-26 05:30 UTC by `scripts/panel.py` at the end of each tick. Do not edit by hand.

**Objective.** Net executable MEXC altcoin-perpetual strategies, followed by genuinely new prospective paper evidence. Independent research axes share the canonical methods queue, provenance and gates. Real-money decisions remain with the owner.

## How we proceed (owner-approved direction, 2026-10-20: [DIRECTION](DIRECTION.md))

Configured workflow (actual completion is reported separately):
1. `scripts/forward_all.sh` delegates to `scripts/orchestrate_forward.py` with the shared catalog in `lab/operations.py`: point-in-time recorders (MEXC funding and ticker, notices, unlock calendar), every forward paper lane, the lag report, this panel and the recorder digests.
2. Background jobs (family runs, downloads) are checked; a finished one gets FINDINGS at 1x/2x/3x of its execution mode's cost and a registry row with its full trial count.
3. Breadth through families: strategies from the queue and the quant literature run as one frozen PREREG per family (all variants, reality check or SPA, random null), in the background. A null is evidence.
4. Family survivors go to scheduled batch reads of the reserved samples (2020 crypto, MEXC-only coins; GATES "Reserved samples"). A batch pass becomes one frozen forward paper lane (gate 1), labelled manual-web or API. Real money only after gates 1-3, placed by the owner (gate 4).
5. Read the room (issue #7), commit and push.

Writers: fresh claims in [room #7](https://github.com/SaikiK12/T/issues/7) determine ownership. A registry status or running process does not establish complete prospective evidence.

## 1. The funnel

Screen (gate 0, exploratory) → research on unseen days (gate 1) → execution on MEXC (gate 2, `go_real` here) → account risk (gate 3) → the owner (gate 4). Rules and dates: [GATES](GATES.md); what the critics found: [CRITIQUE](CRITIQUE.md).

| stage | now |
|---|---|
| Ideas in the queue, untested | 33 |
| Ideas partly tested | 42 |
| Ideas blocked (data, download, compute) | 97 |
| Rounds in the registry | 144 (NULL 85, PARTIAL 24, PENDING 22, CONFIRMED 8, DATA_PASS 5) |
| Program trials | 9,478,970 |
| Paper lanes registered RUNNING/ARMED (process activity unverified) | 13 |
| Strict on-time paper days so far | 0 |
| Gate eligibility | not assessed by this panel; see frozen lane evidence and GATES |
| Next decision | observation-count dependent; each frozen lane specifies its looks |

## 2. Forward paper lanes (the only road to money)

Replay, late and on-time observations remain distinct. Lane-native decisions do not establish current gate eligibility.

| lane | scope | observations | on-time 1x | 2x / 3x | decided by | gate |
|---|---|---|---|---|---|---|
| R215 mexc_fwd | flow books A and B, one bar late | 2 / 90 on-time days | +1.4% | +1.4% / +1.3% | R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate | UNASSESSED |
| R218 mexc_fwd_sq | flow book X2 (k squared) | 2 / 90 on-time days | +2.0% | +1.9% / +1.8% | R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate | UNASSESSED |
| R220 carry_fwd | funding carry (R191 rule) | 2 / 90 on-time days | +0.0% | +0.0% / +0.0% | go_real at 90 on-time days | UNASSESSED |
| R200 flow72_fwd2 | flow books A and B | 3 / 90 on-time days | +1.1% | +0.9% / +0.8% | go_real at 90 scored days, NW t >= 2 | UNASSESSED |
| R214 flow72_fwd3 | A and B one bar late (delay check) | 2 / 90 on-time days | +1.1% | +1.0% / +0.9% | same days as R200 | UNASSESSED |
| R225 vt_fwd | volatility target on A, B, X2 | 2 / 365 on-time days | +1.2% | +1.1% / +1.1% | risk-only decision at 365 on-time days; reported beside R215/R218 | UNASSESSED |
| R266 unlocks_fwd | unlock short, D-7 to unlock | 0 / 120 scored tickets | - | - / - | pending (0 of 120 scored) | UNASSESSED |
| R268 delist_fwd | spot delisting-notice short +1 h | 0 / 12 scored notices | - | - / - | pending (0 of 12 scored notices) | UNASSESSED |
| R270 montag_fwd | Monitoring Tag short +24 h | 0 / 12 scored notices | - | - / - | pending (0 of 12 scored notices) | UNASSESSED |
| R272 announce_fwd | funding-frequency long 1 h; pre-listing short 168 h | 0 / 12 scored notices per book (least observed book) | - | - / - | FF pending (0 of 12 scored notices); PL pending (0 of 12 scored notices) | UNASSESSED |
| R278 xfund_fwd | cross-venue funding carry, books A, B, C | 0 / 90 on-time days | - | - / - | NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3% | UNASSESSED |
| R279 xfund_kc_fwd | cross-venue funding carry on KuCoin, books A, B | 0 / 90 on-time days | - | - / - | NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3% | UNASSESSED |
| R294 xfund_lt_fwd | cross-venue funding carry on Lighter, book A | 0 / 90 on-time days | - | - / - | NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3% | UNASSESSED |
| R285 xbook_fwd | cross-family derived book | unknown / 180 native final days (strict eligibility unassessed) | - | - / - | 180/365 final-day sequential looks; native and gate decisions remain separate | UNASSESSED |

Processing lag of on-time hours: 64 hours, median 79.44166666666666 min, max 261.48333333333335 min; days with late hours: 2026-10-20, 2026-10-21, 2026-10-22.

### Execution receipts

Process state, declared data checks and statistical eligibility are separate.

| task_id | category | state | data_state | run_id |
|---|---|---|---|---|
| REC_TICKER | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_FUNDING | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_DERIBIT | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_LIGHTER | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_DEX | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_WALLETS | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_NOTICES | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_UNLOCKS | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_TAPE | Market data collection | UNKNOWN | UNVERIFIED | None |
| REC_NEWS | Market data collection | UNKNOWN | UNVERIFIED | None |
| R268 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R270 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R272 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R200 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R214 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R215 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R224 | Execution measurement | UNKNOWN | UNVERIFIED | None |
| R218 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R220 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R221 | Evidence decisions | UNKNOWN | UNVERIFIED | None |
| R225 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R266 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R278 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R279 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R294 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| R285 | Prospective paper | UNKNOWN | UNVERIFIED | None |
| LAG | Data integrity | UNKNOWN | UNVERIFIED | None |
| PANEL | Reporting | UNKNOWN | UNVERIFIED | None |
| CATALOG | Reporting | UNKNOWN | UNVERIFIED | None |
| DASH | Reporting | UNKNOWN | UNVERIFIED | None |
| REC_DIGEST | Data integrity | UNKNOWN | UNVERIFIED | None |

## 3. Open methods

The canonical queue is [`registry/methods.csv`](../registry/methods.csv). This view shows its first 12 open rows in registry order; the queue does not encode a priority ranking.

| id | method | data_held | status | cheap | note |
|---|---|---|---|---|---|
| M007 | Conviction-weighted sleeves: score weights clip(z,-2,2) vs equal weights at the same gross | Y flow bins (data/research); daily nets | UNTESTED | 1 | 1/N is hard to beat (DeMiguel et al.). Low prior. |
| M014 | Chan half-life and ADF filter to select mean-reverting coins before a reversal book | Y klines_1h | UNTESTED | 1 | Selection filter. Weak prior. Count its trials. |
| M015 | Listing short with a 14-day stop (MEXC rule 3) | Y klines_1h (listing history) | PARTIAL | 1 | Stop variant untested. Early-drift literature (B) points the other way. Low prior. |
| M016 | Abnormal volume x short constraint (Garfinkel): abnormal volume predicts lower returns where shorting is constrained | P klines_1h; no borrow data (funding/OI as proxy) | PARTIAL | 1 | Volume-alone part is dead. The constraint interaction is open; the constraint is a proxy. |
| M017 | Residual momentum split by liquidity tier (ranks 1-10 vs 11-50), 365 d window, 30 d hold | Y klines_1h | PARTIAL | 1 | Tier split and 365 d window not run. |
| M018 | Realized-variance forecast race: trailing mean vs EWMA vs HAR-RV vs GARCH, QLIKE on next-24 h RV | Y klines_1h (RV from hourly returns) | PARTIAL | 1 | Risk skill, not direction. A win supports sizing, not alpha. arch_har_forecast_contract_20261023 records HAR mean-vs-residual-variance and origin/target/horizon distinctions; no forecast race run. R320 separately tested fixed1/7/30day mean RV and the existing univariate168h/72h-EWMA on already-seen BTC,273/273common2026validation days. EWMA−mean7QLIKE -0.0086701,intervals include0;7/14day dependent-null calibration gives12/10percent family false exclusions versus5percent nominal. No skill/significance or alpha validated; HAR/GARCH and PIT basket remain open. R321NULL inference-control diagnostic only:all4procedures fail full predeclared acceptance;calibratedOBM point family errors<=3percent but adjusted exact upper6.31percent>unchanged5percent.5000independent held-out noise paths,152diagnostic cells;no market forecast/PnL rerun,selection or old-result reclassification. Small-effect power remains low;unknown-market calibration unproved. |
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
- Review and integration: [current open PRs](https://github.com/SaikiK12/T/pulls); check each dependency and blocker.

## 5. Latest rounds

| id | lane | status | verdict | trials |
|---|---|---|---|---|
| R317 | fee_routes_v1 | DONE | PARTIAL | 0 |
| R318 | paper_account_v1 | DONE | PARTIAL | 0 |
| R319 | paired_execution_v1 | DONE | PARTIAL | 0 |
| R320 | owner_acceptance_v1 | DONE | PARTIAL | 4 |
| R321 | dependent_null_v1 | DONE | NULL | 152 |
| R322 | funding_prefix_v1 | DONE | PARTIAL | 0 |
| R323 | continuation_control_v1 | DONE | PARTIAL | 32 |
| R324 | spot_perp_inputs_v1 | DONE | PARTIAL | 0 |

Details: [MAP](MAP.md), [EDGE_SCOREBOARD](EDGE_SCOREBOARD.md), [canonical methods registry](../registry/methods.csv), [GATES](GATES.md), [CRITIQUE](CRITIQUE.md), [room #7](https://github.com/SaikiK12/T/issues/7).
