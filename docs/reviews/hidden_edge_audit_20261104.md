# Hidden-edge audit, 2026-11-04

The owner asked (2026-11-04): find where we were careless, and anything that could be hiding a real gain. Six
read-only checkers each audited one area of the code and lane records: units, costs, timing, data, statistics and the
qx engine. Each claim was then checked against code or data before it was written here.

**What this file is.** It is evidence, not a result.
- No frozen file was edited and no verdict was changed.
- A corrected test is a new lane with a new id, registered and frozen before it reads anything (AGENTS rules 1-2).
- Numbers marked *recomputed* came from the checkers' read-only re-runs on held data. They are not registered
  results and decide nothing.

**Verification labels.**
- **Verified:** I re-read the code, or recomputed the figure from held data, myself.
- **Codex:** reproduced independently by Codex on #7.
- **Recomputed:** from one checker's re-run only. Plausible, but not reproduced a second time.

## Headline
The audit found more inflated gains than hidden ones.

- **Biggest hidden gain (H1).** An engine rule suppresses most dYdX carry days.
  - With dYdX on daily bars, R277's KuCoin+dYdX book recomputes to +10.5%/yr, NW t 4.75.
  - But more than half of those trades are in coins that trade under $50k a day, and their costs are not measured.
- **Biggest inflated gains:**
  - **F1.** The settlement-hop PASSes R354, R356 and R363 are cost artifacts: each coin's measured Lighter book is
    25-90 bp a side, against the ~1 bp band they were charged.
  - **F5.** R278's live paper gain is mostly one delisting windfall.

## Hidden or understated edges

| Id | Finding | Where | Status | Effect if fixed (recomputed unless noted) |
|---|---|---|---|---|
| H1 | **The engine's freshness rule depends on bar length.** A day counts as "fresh" only if a bar *ends* exactly at the day boundary. An hourly venue therefore needs a trade in the 23:00-24:00 bar; a daily venue needs only one trade that day. Fresh days feed the identity-guard correlation, so thin hourly venues fail the guard on most days. | `engine/src/spread.rs:147-159`; `pair_corr` at 222-233 | **Verified** (code) | About 77% of eligible dYdX coin-days are dropped. R391's 7 dYdX-only coins were never eligible, so dYdX took no trade. With dYdX on daily bars: R277 KuCoin+dYdX +10.52%/yr (t 4.75), Binance+dYdX +10.52%/yr (t 4.47); R288 dYdX+Lighter +7.90%/yr (t 2.79). 54-56% of those trades are in coins under $50k a day, with no measured cost. R277's FINDINGS says dYdX has no oracle prices; its funding files do hold an `oracle` column. |
| H2 | **Constant-notional marking.** Each day the engine marks each leg as if it held constant notional, not a fixed quantity. When the two venues' prices split apart, this creates profit or loss that a held position would not have. | `spread.rs:127-131, 395-403` | Recomputed | With fixed-quantity marking: R277 KuCoin+dYdX +4.13%/yr (t 3.24, passes); Binance+dYdX +2.96%/yr (t 1.80). The sign of the bias is not the same on every book. |
| H3 | **R354 halves Binance's 4 h rate before 2025-09-19.** The predicted-rate formula used m/8 on 4-hour contracts during that period. | `scripts/run_settlehop_pred.py` (frozen) | Recomputed | Corrected: primary hops 87 → 95, t 3.24 → 3.48; MEXC θ 0.5% t 2.36 → 2.61. This does not matter in the end, because of F1. |
| H4 | **R333 decided on day-weighted means.** Per trade it is +11.52 bp at 1x (t about 2.0), but −6.62 bp at 2x, so it would not pass. R306 shows the same pattern and is negative per trade. | R333 / R306 FINDINGS | **Codex** + recomputed | No verdict changes. |
| H5 | **R267 and R269 were weighted by cluster.** Leg means are R267 +1.96% (t 1.78) and R269 +1.46% (t 1.97). | lane runners | Recomputed | Not significant. The NULLs stand. |
| H6 | **Name rules join the wrong contracts:** LUNA2, RAYSOL, 1000CAT, 1MBABYDOGE. | symbol maps | Recomputed | Under 1% of candidate days. |
| H7 | **R300 at R224's measured median web cost** passes validation (t 2.01-2.08). | R300 | Recomputed | Already forward as C17/R371. Nothing new to do. |

## Fake or inflated edges

| Id | Finding | Where | Status | Effect |
|---|---|---|---|---|
| F1 | **Settlement hops are charged a volume-band cost.** Lighter's cost band is keyed on the coin's 24 h volume, and that volume spikes just before a deep settlement. Measured snapshot cost a side for the coins that carry the result: KAITO 33.5, RIVER 33.5, AVNT 89.2, ZORA 51.4, NMR 25.6 bp. The band charged about 1.1 bp. | R354, R356, R363 cost code (frozen) | **Verified** (snapshot costs) | At each coin's own cost: R363 −35.9 bp a hop (t −5.53); R354 −26.2 bp a hop, with all six books negative; R356 −6.6 bp. EDGE_SCOREBOARD still ranks R354 first. The forward lanes R355 and R364 already charge measured live books, so they are the real test. |
| F2 | **R354 credits the T + 1 h Binance payment at an exit priced before it.** | `run_settlehop_pred.py` | Recomputed | Primary +30.9 → +26.2 bp at 1x, 10.4 → 5.8 bp at 2x. |
| F3 | **R336's PARTIAL used MEXC's web fee (0) for fills its PREREG calls API.** | R336 | Recomputed | At the API fee of 8 bp a side: t 0.12, so NULL. The FINDINGS already says the API pays 6-8 bp and dropped the forward lane, but the recorded status is still PARTIAL. |
| F4 | **A delisted leg is valued at its stale last trade.** On ALPACA, one leg's price_pnl is 3.26 leg units. Fake legs of ±100-500% add about +1.1%/yr to K20 books and inflate their variance. | `spread.rs` / `lab/xfund.py` exits (frozen) | **Verified** (ALPACA trade) | Affects R275 and the forward lanes R278, R279, R294 and R390. |
| F5 | **R278's live result is mostly one dead-leg windfall.** PTB is 86% of book B's +0.665%. Without dead legs, book C's NW t falls from 2.65 to 1.18. | R278 journal | Recomputed | R278 must not be read as a forward confirmation of the carry until dead legs are split out. |
| F6 | **Freshness inflates R288's Lighter books by 25-45%** (H1, in the other direction: hourly Lighter is compared with daily venues). | R288 | Recomputed | MEXC+Lighter 6.20 → 3.67 %/yr with daily Lighter bars. R288's rule still passes. |
| F7 | **R288 and R294 price the Lighter leg at 4 bp a side**, while the coins they trade average 14.7 bp a side measured. | R288, R294 | Recomputed | MEXC+Lighter about 5.07%/yr at measured cost. |
| F8 | **The API-mode forward lanes R268, R270 and R272 charge the web taker fee.** That understates cost by 12-16 bp a ticket. | forward runners (frozen) | Recomputed | No ticket has been scored yet, so no verdict is affected. A reported API-fee column is needed before the first decision. |
| F9 | **Flow72 never flags backlog hours as late.** 184 of 359 "on-time" hours were computed more than 6 h late. | `forward_tick.py:110` | Recomputed | Affects R200, R214, R215, R218, R221, R225 and R285. The late hours must be reported apart. |
| F10 | **R285's xbook joins different 24 h windows.** | R285 | Recomputed | NW t 5.00 as run, 4.11 with aligned windows. Still large. |
| F11 | **`lab/inference.spa` over-rejects:** size 0.07 against a nominal 0.05. | `lab/inference.py` | Recomputed | Only R281 decides on it, and R281 is NULL, so nothing changes. |

## Design defects

| Id | Finding | Status | Action |
|---|---|---|---|
| D1 | **R389's scorer trades April-May steps outside its window.** From 2027-03-28 London is UTC+1, so 23:59 London is 22:59 UTC, outside the frozen 23:29-00:30 UTC window. The PREREG says such steps are "reported, never rescued", but the scorer still counts the window as a traded step. | **Verified** (code + PREREG) | It changes the decision only if fewer than 20 November-March steps are traded. Note in `experiments/lighter_roll_fwd/FINDINGS.md`. A DST-aware successor lane (new id) is needed before 2027-03-28. |
| D2 | **R369 can enter after its own exit** (t* + L ≥ T + 60 s). | Recomputed | Low impact. Report such events apart. |
| D3 | **R388's symbol-day clustering does nothing,** and its minimum detectable effect is about 653 bp. | Recomputed | R388 is NULL; it was underpowered as well as negative. |
| D4 | **`registry.program_trials()` counts 6 blank rows as 0:** R143, R144, R180, R181, R183, R184. | Recomputed | The program total is understated by those rounds' trials. Fix the reader so blanks are reported, not dropped. |
| D5 | **Late catch-up runs apply the current contract lists to earlier days.** | Recomputed | Low impact. Record the list date in each run. |

## Checked and found sound
- Lighter funding units and sign.
- Bar timestamps: open-stamped on every venue.
- Funding scale and sign on every venue.
- Formulas: NW, CR1, PSR/DSR, PBO, MCS, LORD++, trimmed mean and leave-two-out.
- The R286 and R391 decision code.
- The carry journals reproduce from the data.

## What changes now, and what does not
- **No verdict is rewritten.** Each lane's FINDINGS gets a dated audit note outside any frozen block. These lanes are
  annotated:
  - R275, R288, R354, R356, R363, R336 and R391;
  - R389 and R278, in new FINDINGS files.
- **`experiments/xfund_kd_v1/FINDINGS.md` (R277) is frozen,** as an input of xfundint_v1, so its notes stay in this
  file (H1, H2 and the oracle column).
- **EDGE_SCOREBOARD's settlement-hop rows** carry an F1 caveat.
- **New queue rows** in `registry/methods.csv`, each a new lane that must be registered before it measures:
  - **M468:** a venue-neutral carry engine (fresh = a trade during the UTC day on every venue, fixed-quantity marks,
    delisted legs closed at mark/index), as a new module or engine v2. The frozen `spread.rs` and `lab/xfund.py` are
    not touched.
  - **M469:** the dYdX/Lighter carry re-test on that engine, at each coin's measured book cost, read once.
  - **M470:** delisting-aware exits for the forward carry lanes, plus a dead-leg split of R278-R390.
  - **M471:** settlement hops re-scored at each coin's own book cost and with the payment timing fixed (F1, F2,
    H3). The forward R355 and R364 already decide on live books; this is the backtest correction.
  - **M472:** an R389 successor with DST-aware windows, frozen before 2027-03-28.
  - **M473:** forward ledger corrections: an API-fee column for R268, R270 and R272, late-hour flags in flow72, and
    blank trial counts reported by `program_trials`.
- **The trial count does not change.** This audit ran no registered trial. Its recomputations are diagnostics
  and decide nothing.
