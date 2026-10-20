# Panel

Rebuilt 2026-10-20 06:29 UTC by `scripts/panel.py` at the end of each tick. Do not edit by hand.

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
| Ideas in the queue, untested | 65 |
| Ideas partly tested | 24 |
| Ideas blocked (data, download, compute) | 72 |
| Rounds in the registry | 55 (NULL 32, PENDING 11, CONFIRMED 7, PARTIAL 3, DATA_PASS 2) |
| Program trials | 9,471,893 |
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
| M001 | Positioning impulse: 24 h change in top_vs_crowd (log top_ls_sum - log ls_count), top vs bottom quintile, 72 h hold, dollar-neutral; test increment over the frozen level book | Y metrics_1h (99% coverage from 2023) | UNTESTED | 1 | NEXT's ranked #1. Control: R197 level book. 2023-25H1 is exploratory; holdout spent. |
| M002 | Amihud illiquidity sort: abs(daily return) / quote volume, long illiquid vs liquid, 7-30 d hold, universe-hedged | Y klines_1h (quote_volume) | UNTESTED | 1 | Literature puts alpha in small, illiquid coins. Not in R185 or R222. |
| M003 | Dispersion or breadth gate on flow books: gate A/B/X2 when 30 d dispersion is in top tercile and alt index 90 d return < 0 | Y klines_1h (dispersion views in R185) | UNTESTED | 1 | R233 tested trend x vol only. Few crash episodes: low power. |
| M004 | TradFi commodity/equity perps (CL, XAU, NVDA...) 1 h return leads the crypto cross-section, next 1-24 h | Y klines_1h (TradFi perps present) | UNTESTED | 1 | Transfer test of R216's TradFi gross. A proxy for the news claim, not the claim. |
| M005 | Supertrend(10,3) plus RSI14 on 4 h bars (old combo) | Y klines_1h (resample to 4 h) | UNTESTED | 1 | Old discovery looked good, holdout did not. A re-run needs a frozen spec. |
| M006 | Square-root impact cost at target size (Donier & Bonart) to size books against the tier cost | Y klines_1h (quote_volume) | UNTESTED | 1 | Cost realism, not an edge. MEXC book-walk version is R224 (running). |
| M007 | Conviction-weighted sleeves: score weights clip(z,-2,2) vs equal weights at the same gross | Y flow bins (data/research); daily nets | UNTESTED | 1 | 1/N is hard to beat (DeMiguel et al.). Low prior. |
| M008 | Daily reversal in illiquid coins (xsrev) and its maker-limit version (xsrevmaker) | Y klines_1h | UNTESTED | 1 | Old excerpt has no numbers. Re-run from a frozen spec. |
| M009 | ETH/BTC 60 d log change sets alts vs BTC (alt-season regime) | Y klines_1h (BTC, ETH) | UNTESTED | 1 | Practitioner source (D). Proxy problem. Low prior. |
| M010 | 8 AM ET one-hour range fade (owner's Edgeful claim), on the hourly bar | P klines_1h (old used 1-min data) | UNTESTED | 1 | Base rate: both sides hit 58.9%. Hourly bars cannot match 1-min fills. Low prior. |
| M011 | Round-number levels as stop-run magnets: distance to .00 levels, fade or follow | Y klines_1h | UNTESTED | 1 | FX evidence only (one bank, 1999-2000). Low prior. |
| M012 | SMT divergence: a coin makes a new high or low that BTC or ETH does not; trade reversal or continuation | Y klines_1h | UNTESTED | 1 | ICT, no independent study. Low prior. |

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
| R225 | vt_fwd | RUNNING | PENDING | 3 |
| R226 | tradesize_v1 | DONE | NULL | 6 |
| R228 | allocation_v1 | DONE | NULL | 30 |
| R229 | slow_trend_v1 | DONE | NULL | 2 |
| R230 | weekly_rotation_v1 | DONE | NULL | 96 |
| R231 | partial_execution_v1 | DONE | NULL | 2 |
| R232 | rebalancing_v1 | DONE | NULL | 3 |
| R233 | regime_v1 | DONE | NULL | 4 |

Details: [MAP](MAP.md), [EDGE_SCOREBOARD](EDGE_SCOREBOARD.md), [METHODS_QUEUE](METHODS_QUEUE.md), [GATES](GATES.md), [CRITIQUE](CRITIQUE.md), [room #7](https://github.com/SaikiK12/T/issues/7).
