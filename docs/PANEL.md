# Panel

Rebuilt 2026-10-20 07:29 UTC by `scripts/panel.py` at the end of each tick. Do not edit by hand.

**Objective.** The best net PnL from any method in any market the owner can trade: MEXC perpetuals first, then spot, prop challenges, forex and index futures as data allows. Search wide (every method is tested, a null is evidence); trust narrow (only days nobody had seen when the rule was frozen count). Money moves only through the four gates in `docs/GATES.md`, at stakes the owner sets.

## How we proceed: one item at a time

Every 30-minute tick:
1. `scripts/forward_all.sh` runs every forward paper lane, the lag report and this panel.
2. Read the room (issue #7) and answer Codex.
3. Take the top `UNTESTED` method in `registry/methods.csv` that runs on data we hold. Write its PREREG, freeze it, run it (`lab/screen.py` for a cross-sectional feature), write FINDINGS at 1x/2x/3x costs, append the registry row and mark the method tested. Finish it before starting another. A bad-looking idea is still tested: a null is evidence.
4. A method that passes its screen becomes one frozen forward paper lane under a new id (gate 1). Real money only after gates 1-3, placed by the owner (gate 4).
5. Commit and push.

Roles: Claude runs the lanes and the forward pipeline; Codex reviews and drafts on `codex/` branches; subagents (Haiku preferred) read, extract and critique (at most 3 at a time). No Workflows.

## 1. The funnel

Screen (gate 0, exploratory) → research on unseen days (gate 1) → execution on MEXC (gate 2, `go_real` here) → account risk (gate 3) → the owner (gate 4). Rules and dates: [GATES](GATES.md); what the critics found: [CRITIQUE](CRITIQUE.md).

| stage | now |
|---|---|
| Ideas in the queue, untested | 35 |
| Ideas partly tested | 31 |
| Ideas blocked (data, download, compute) | 74 |
| Rounds in the registry | 72 (NULL 49, PENDING 11, CONFIRMED 7, PARTIAL 3, DATA_PASS 2) |
| Program trials | 9,471,991 |
| Forward paper lanes running | 8 |
| Strict on-time paper days so far | 0 |
| Passed gate 1 (unseen days) | none yet |
| Next decision date | 2027-01-18: first 90-on-time-day looks (R215, R218, R220, R221 futility) |

## 2. Forward paper lanes (the only road to money)

Replay days were scored after the freeze on days the archive did not hold; on-time days are the evidence.

| lane | book | replay | on_time | 2x / 3x | decided by |
|---|---|---|---|---|---|
| R215 mexc_fwd | flow book A on MEXC | 19 d +4.6% | 0 d | - | R221 looks at 90 / 182 / 365 on-time days |
| R215 mexc_fwd | top-vs-crowd on MEXC | 19 d -0.1% | 0 d | - | R221 looks at 90 / 182 / 365 on-time days |
| R218 mexc_fwd_sq | flow book X2 (k squared) on MEXC | 19 d +5.9% | 0 d | - | R221 looks at 90 / 182 / 365 on-time days |
| R220 carry_fwd | funding carry, MEXC | 19 d -0.0% | 0 d | - | 90 on-time days through go_real |
| R220 carry_fwd | funding carry, Binance | 19 d +0.0% | 0 d | - | 90 on-time days through go_real |
| R200 flow72_fwd2 | flow book A, Binance | 18 d +22.2% | 1 d +0.1% | -0.0% / -0.1% | 90 scored days through go_real plus NW t >= 2 |
| R200 flow72_fwd2 | top-vs-crowd, Binance | 18 d +9.7% | 1 d -0.3% | -0.3% / -0.3% | 90 scored days through go_real plus NW t >= 2 |
| R214 flow72_fwd3 | A one bar late | 19 d +22.6% | 0 d | - | same days as R200, a delay check |
| R214 flow72_fwd3 | B one bar late | 19 d +9.4% | 0 d | - | same days as R200, a delay check |

Processing lag of on-time hours: 6 hours, median 109.88333333333333 min, max 259.8833333333333 min; days with late hours: 2026-10-20.

## 3. Next in the queue

| id | method | data_held | status | cheap | note |
|---|---|---|---|---|---|
| M003 | Dispersion or breadth gate on flow books: gate A/B/X2 when 30 d dispersion is in top tercile and alt index 90 d return < 0 | Y klines_1h (dispersion views in R185) | UNTESTED | 1 | R233 tested trend x vol only. Few crash episodes: low power. |
| M004 | TradFi commodity/equity perps (CL, XAU, NVDA...) 1 h return leads the crypto cross-section, next 1-24 h | Y klines_1h (TradFi perps present) | UNTESTED | 1 | Transfer test of R216's TradFi gross. A proxy for the news claim, not the claim. |
| M006 | Square-root impact cost at target size (Donier & Bonart) to size books against the tier cost | Y klines_1h (quote_volume) | UNTESTED | 1 | Cost realism, not an edge. MEXC book-walk version is R224 (running). |
| M007 | Conviction-weighted sleeves: score weights clip(z,-2,2) vs equal weights at the same gross | Y flow bins (data/research); daily nets | UNTESTED | 1 | 1/N is hard to beat (DeMiguel et al.). Low prior. |
| M014 | Chan half-life and ADF filter to select mean-reverting coins before a reversal book | Y klines_1h | UNTESTED | 1 | Selection filter. Weak prior. Count its trials. |
| M015 | Listing short with a 14-day stop (MEXC rule 3) | Y klines_1h (listing history) | PARTIAL | 1 | Stop variant untested. Early-drift literature (B) points the other way. Low prior. |
| M016 | Abnormal volume x short constraint (Garfinkel): abnormal volume predicts lower returns where shorting is constrained | P klines_1h; no borrow data (funding/OI as proxy) | PARTIAL | 1 | Volume-alone part is dead. The constraint interaction is open; the constraint is a proxy. |
| M017 | Residual momentum split by liquidity tier (ranks 1-10 vs 11-50), 365 d window, 30 d hold | Y klines_1h | PARTIAL | 1 | Tier split and 365 d window not run. |
| M018 | Realized-variance forecast race: trailing mean vs EWMA vs HAR-RV vs GARCH, QLIKE on next-24 h RV | Y klines_1h (RV from hourly returns) | PARTIAL | 1 | Risk skill, not direction. A win supports sizing, not alpha. |
| M020 | Crowd extreme rule: short coins whose global account L/S is above its 95th pct of 90 d, 72 h hold, hedged | Y metrics_1h (global ratio) | PARTIAL | 1 | CLAIMS: crowd ratio is weaker than top vs crowd. |
| M021 | OI change as a crash/risk-state variable (P of -20% in 30 d), not a direction call | Y metrics_1h OI; klines_1h | PARTIAL | 1 | Claimed OOS AUC 0.677 in one 10-asset study. Risk use only. |
| M022 | Multi-timeframe sign agreement (1 h, 4 h, 24 h same sign) as entry or size filter | Y klines_1h | PARTIAL | 1 | Agreement count never run. Low prior. |

## 4. Waiting on the owner

- Download MEXC public history (about 9.4k requests, `scripts/fetch_mexc_history.py`): carry on MEXC-only coins.
- Install PyTorch CPU and the Kronos-small weights (about 300 MB): R227 Kronos lane (PR #9).
- Download the DefiLlama unlock calendar (old source: 372 protocol files): replicates the old session's unlock short (E01, R179/R181, +2.5% per event), the strongest edge in `docs/OLD_SESSION_EDGES.md`.
- Rotate the two Coinalyze API keys pasted into the old session's chat (`docs/OLD_SESSION_EDGES.md`, security note).
- Yes or no: 20-30 tiny live MEXC orders placed by the owner to measure real fills against paper (a carve-out from rule 6; `docs/CRITIQUE.md`).
- Set the stake and max loss for gate 4 (`docs/GATES.md`; the lab only proposes 2% of trading capital per book and a stop at 25% of the stake).

## 5. Latest rounds

| id | lane | status | verdict | trials |
|---|---|---|---|---|
| R243 | chartist_v1 | DONE | NULL | 14 |
| R244 | weekendlink_v1 | DONE | NULL | 2 |
| R245 | xsrev_v1 | DONE | NULL | 4 |
| R246 | ictlevels_v1 | DONE | NULL | 8 |
| R247 | chartxm_v1 | DONE | NULL | 14 |
| R248 | pivotfade_v1 | DONE | NULL | 4 |
| R249 | rnfade_v1 | DONE | NULL | 4 |
| R250 | pairs_v1 | DONE | NULL | 4 |

Details: [MAP](MAP.md), [EDGE_SCOREBOARD](EDGE_SCOREBOARD.md), [METHODS_QUEUE](METHODS_QUEUE.md), [GATES](GATES.md), [CRITIQUE](CRITIQUE.md), [room #7](https://github.com/SaikiK12/T/issues/7).
