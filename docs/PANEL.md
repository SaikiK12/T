# Panel

Rebuilt 2026-10-29 10:23 UTC by `scripts/panel.py` at the end of each tick. Do not edit by hand.

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
| Ideas in the queue, untested | 49 |
| Ideas partly tested | 48 |
| Ideas blocked (data, download, compute) | 105 |
| Rounds in the registry | 170 (NULL 93, PARTIAL 34, PENDING 29, CONFIRMED 8, DATA_PASS 6) |
| Program trials | 9,479,227 |
| Paper lanes registered RUNNING/ARMED (process activity unverified) | 15 |
| Strict on-time paper days so far | 0 |
| Gate eligibility | not assessed by this panel; see frozen lane evidence and GATES |
| Next decision | observation-count dependent; each frozen lane specifies its looks |

## 2. Forward paper lanes (the only road to money)

Replay, late and on-time observations remain distinct. Lane-native decisions do not establish current gate eligibility.

| lane | scope | observations | on-time 1x | 2x / 3x | decided by | gate |
|---|---|---|---|---|---|---|
| R215 mexc_fwd | flow books A and B, one bar late | 9 / 90 on-time days | +0.2% | -0.0% / -0.2% | R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate | UNASSESSED |
| R218 mexc_fwd_sq | flow book X2 (k squared) | 9 / 90 on-time days | +0.0% | -0.4% / -0.8% | R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate | UNASSESSED |
| R220 carry_fwd | funding carry (R191 rule) | 9 / 90 on-time days | -0.1% | -0.1% / -0.1% | go_real at 90 on-time days | UNASSESSED |
| R200 flow72_fwd2 | flow books A and B | 10 / 90 on-time days | -5.8% | -6.2% / -6.6% | go_real at 90 scored days, NW t >= 2 | UNASSESSED |
| R214 flow72_fwd3 | A and B one bar late (delay check) | 9 / 90 on-time days | -6.0% | -6.3% / -6.6% | same days as R200 | UNASSESSED |
| R225 vt_fwd | volatility target on A, B, X2 | 9 / 365 on-time days | +0.1% | -0.1% / -0.4% | risk-only decision at 365 on-time days; reported beside R215/R218 | UNASSESSED |
| R266 unlocks_fwd | unlock short, D-7 to unlock | 1 / 120 scored tickets | -1.5% | -1.7% / - | pending (1 of 120 scored) | UNASSESSED |
| R268 delist_fwd | spot delisting-notice short +1 h | 0 / 12 scored notices | - | - / - | pending (0 of 12 scored notices) | UNASSESSED |
| R270 montag_fwd | Monitoring Tag short +24 h | 0 / 12 scored notices | - | - / - | pending (0 of 12 scored notices) | UNASSESSED |
| R272 announce_fwd | funding-frequency long 1 h; pre-listing short 168 h | 0 / 12 scored notices per book (least observed book) | - | - / - | FF pending (0 of 12 scored notices); PL pending (0 of 12 scored notices) | UNASSESSED |
| R278 xfund_fwd | cross-venue funding carry, books A, B, C | 2 / 90 on-time days | -0.0% | -0.1% / -0.1% | NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3% | UNASSESSED |
| R279 xfund_kc_fwd | cross-venue funding carry on KuCoin, books A, B | 2 / 90 on-time days | -0.0% | -0.1% / -0.2% | NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3% | UNASSESSED |
| R294 xfund_lt_fwd | cross-venue funding carry on Lighter, book A | 1 / 90 on-time days | -0.0% | -0.0% / -0.0% | NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3% | UNASSESSED |
| R355 settlehop_fwd | settlement hop on the displayed funding rate (MEXC decided, Gate reported) | 0 / 80 scored hops | - | - / - | 0 scored on-time primary hops; interim look at 40, final at 80 or 2028-03-01 | UNASSESSED |
| R364 settlelit_fwd | settlement scalp on Lighter against Binance's deep lump (T - 10 s to T + 60 s) | 0 / 80 scored hops | - | - / - | 0 scored on-time primary hops; interim look at 40, final at 80 or 2027-10-28 | UNASSESSED |
| R371 usopen_fwd | US-open leaders: long 3 strongest, short 3 weakest top-50 perps since 00:00 UTC (10:00 New York to 24:00 UTC) | 0 / 500 scored days | - | - / - | pending (0 of 500 scored) | UNASSESSED |
| R285 xbook_fwd | cross-family derived book | unknown / 180 native final days (strict eligibility unassessed) | - | - / - | 180/365 final-day sequential looks; native and gate decisions remain separate | UNASSESSED |

Processing lag of on-time hours: 225 hours, median 287.76666666666665 min, max 5681.933333333333 min; days with late hours: 2026-10-20, 2026-10-21, 2026-10-22, 2026-10-23, 2026-10-24, 2026-10-25, 2026-10-26, 2026-10-27, 2026-10-28.

### Execution receipts

Process state, declared data checks and statistical eligibility are separate.

| task_id | category | state | data_state | run_id |
|---|---|---|---|---|
| R200 | Prospective paper | SUCCESS | COMPLETE | 20261029T101500_24116 |
| REC_TICKER | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_FUNDING | Market data collection | SUCCESS | COMPLETE | 20261029T101500_24116 |
| REC_DERIBIT | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_LTRADES | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_OPTEXP | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_CPERPS | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_LIGHTER | Market data collection | FAILED | UNVERIFIED | 20261029T101500_24116 |
| REC_DEX | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_WALLETS | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_NOTICES | Market data collection | FAILED | UNVERIFIED | 20261029T101500_24116 |
| REC_UNLOCKS | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_TAPE | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_HFT | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_RAW | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| REC_NEWS | Market data collection | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R268 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R270 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R272 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R214 | Prospective paper | FAILED | UNVERIFIED | 20261029T101500_24116 |
| R215 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R224 | Execution measurement | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R218 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R220 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R221 | Evidence decisions | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R225 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R266 | Prospective paper | SUCCESS | COMPLETE | 20261029T101500_24116 |
| R278 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R279 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R294 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R355 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R364 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R369 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R371 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| R285 | Prospective paper | SUCCESS | UNVERIFIED | 20261029T101500_24116 |
| LAG | Data integrity | BLOCKED | UNVERIFIED | 20261029T101500_24116 |
| PANEL | Reporting | RUNNING | UNVERIFIED | 20261029T101500_24116 |
| CATALOG | Reporting | PENDING | UNVERIFIED | 20261029T101500_24116 |
| DASH | Reporting | PENDING | UNVERIFIED | 20261029T101500_24116 |
| REC_DIGEST | Data integrity | PENDING | UNVERIFIED | 20261029T101500_24116 |

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
| R363 | settlelit_v1 | DONE | PARTIAL | 6 |
| R364 | settlelit_fwd | RUNNING | PENDING | 1 |
| R367 | hftlead_v1 | REGISTERED | PENDING | 16 |
| R368 | eventdrift_v1 | DONE | NULL | 26 |
| R369 | eventlag_fwd | REGISTERED | PENDING | 24 |
| R370 | cmelead_v1 | DONE | PENDING | 16 |
| R371 | usopen_fwd | REGISTERED | PENDING | 2 |
| R257 | mixed_signals_v1 | DONE | NULL | 36 |

Details: [MAP](MAP.md), [EDGE_SCOREBOARD](EDGE_SCOREBOARD.md), [canonical methods registry](../registry/methods.csv), [GATES](GATES.md), [CRITIQUE](CRITIQUE.md), [room #7](https://github.com/SaikiK12/T/issues/7).
