# False-null audit, 2026-11-10

The owner asked (2026-11-10): if the engine had accounting errors that changed carry's %/yr, why would there not be
other errors, in the code or in how we chose and read tests, that made real edges look like NULLs? This file answers
that question.

**How it was done.**
- Six read-only Haiku auditors each took one area: survivorship on short lanes, the cross-section engine, options and
  cross-asset lanes, the power of every NULL, held data never used, and event-lane timing and costs. Four Opus auditors
  were tried first and stopped on a rate limit.
- Items already in [the 2026-11-04 hidden-edge audit](hidden_edge_audit_20261104.md) are not repeated.
- The auditors' scratch scripts and condensed reports are not in the repository. The figures marked *recomputed* came
  from their re-runs on held data. They are not registered results and decide nothing.
- I re-read the code behind every finding marked **Verified**.

**What this file is.** It is evidence, not a result. No frozen file was edited and no verdict was changed. A corrected
test is a new lane with its own id (AGENTS rules 1-2).

## Headline
- **The engines are mostly clean.** No alignment, sign, unit or double-lag error was found that turns a real signal
  into a NULL. An executed synthetic test of the cross-section engine recovered a planted signal at t 127, and one
  extra row of lag removed it, as it should.
- **Two code issues hide edge, and neither moves a verdict:** the listing cost tier (E1) and R271's unpriced legs (E2).
- **The large error is in process, not code.** Most NULLs could only have detected edges of 30 to 190%/yr. Reading
  them as "no edge" was wrong; they are "not measurable at this sample size". See P1 below.
- **One operational error was mine:** I ran two forward lanes that Codex's GitHub runtime owns (O1).

## Hidden or understated edges in code

| Id | Finding | Where | Status | Effect (recomputed unless noted) |
|---|---|---|---|---|
| E1 | **Listing cost tier.** Liquidity rank averages quote volume after filling pre-listing hours with zero, so a new coin ranks as illiquid and pays the 20 bp tier. | `lab/panel.py:98-104` (`np.nan_to_num` before the 30-day rolling mean) | **Verified** (code) | 78% (discovery) and 91% (validation) of R188/R189 entries pay 20 bp, a 73-77 bp round trip. Ranked over traded hours only, 15-18% do (40-44 bp). Net short R188 discovery 2.98% → 3.27%, validation 4.27% → 4.63%. Gross t is unchanged, so no verdict moves. R189's holdout loses gross (-1.9% at hold 7), so cost does not explain it. |
| E2 | **R271 prices only legs with a Binance market at entry.** 663 of 1,882 non-2020 legs are dropped as `no_market`: spot listings 80%, pre-listings 68%, perp launches 33%. | `engine/src/events.rs:225-237` | **Verified** (code); shares recomputed | A post-hoc 168 h short return from each dropped leg's first traded hour: perp launches median +9.2% (n 133) against +4.4% for included ones (n 15); pre-listings +28.2% (n 26) against +22.0% (n 37). Not like-for-like (other entry, no funding, no costs). The dropped legs are new-listing shorts, which R188/R189 already tested (holdout NULL). |
| E3 | **Delisted or untraded exits are booked at zero.** For a short on a dying coin this hides the gain. | `scripts/run_mlrank.py:132`; `scripts/run_lotcap.py:145,150` | **Verified** (code) | Small. R298 exits at the last traded close in the hold, so a coin booked at zero is one that never traded again after entry. On R298's top-150 universe with 24-168 h holds that is rare. Not quantified. |
| E4 | **R239/R241 read VIX one day late.** The trigger uses VIX(D-1); the PREREG's rationale states the opposite (documentation error). | `scripts/run_fxindex.py:89` | Recomputed | Same-day VIX gives more triggers but a lower 5-day gross on QQQ (+86 against +109 bp). No edge revealed. |

## Inflation risks (gains that may be overstated)
- **R304 presence look-ahead.** `lab/flow.py:74-86` fetches metrics only for days tradable in the next 35 days. It is
  documented in `scripts/run_mlrank3.py:3-9`, and R332 was rebuilt without it.
- **Missing returns are zero-filled with the weight kept** (`lab/engine.py:91,167`; `lab/slices.py:64`). Small.
- **E3 for long legs** inflates rather than hides.

## Immaterial (checked, no effect)
- Bar `t` is the bar's open time in every runner and in the Rust engine; no runner shifts a bar.
- Funding signs are correct in every audited lane (a short receives a positive rate; 99.7% of R223's events check out on
  data).
- R193 starts its funding sum one settlement early (`lab/maker.py:70`): 14.39 → 14.50%/yr.
- R188/R189 credit both boundary settlements: +1.4 / -1.3 bp. R223 adds two simple returns instead of compounding:
  -2.2 / -0.8 bp.
- R271 enters at the close of the notice hour, 37 minutes after the notice on average (up to 60). A reaction inside
  the notice hour is invisible. This is a design limit, already in its PREREG.
- Survivorship on short lanes: `lab/data.py:88-92` lists every USDT perp, delisted ones included. R265, R267, R269,
  R298, R303 and R196 have a low chance of flipping. MEXC history is survivor-only (`docs/DATA_SOURCES.md`).

## Process findings
- **P1. Underpowered NULLs read as "no edge".**
  - On the 18 NULL/PARTIAL rounds with a parseable daily net, the detectable annual edge (t 2.5, 80% power) was mostly
    23-195%/yr. Only the carry rounds (about 2-3%/yr) and R353 could detect a 10%/yr edge. 109 rounds were not computed
    (grid or trade files).
  - Near misses: R229 slow trend (+14.1%/yr, t 1.54, detectable 30.5%), R231 (the same strategy, correlation 0.98),
    R257 mixed signals (+25.8%/yr, t 1.78, detectable 48.3%).
  - Underpowered: R230 (detectable 130%/yr), R232 (189%/yr), R283 VIX panic (QQQ 10-day needs about +244 bp, observed
    +158), R244 weekend link (needs 12-16 bp a trade, observed -1 to -4).
  - Killed by cost, not by gross: R287 (PCA residual) and R435 (stock tug-of-war, gross +18.6 bp/day, net -3.5).
  - NULL decided by a paired test, absolute t large: R281, R382, R309, and R414 (equal weight of 12 in-sample streams
    +32.6%/yr, Sharpe 2.64, max DD -8.4%; the switching rules lost to it).
  - Post hoc, books combining near misses and cost-killed rounds all have negative Sharpe. Pooling does not rescue them.
- **P2. One low-Sharpe directional idea at a time.** A single directional signal at Sharpe 0.5-1 needs years to reach
  t 2.5. Held tradable samples are often under a year (MEXC index perps start 2026-01-29). The tests that did pass are
  structural, high-Sharpe trades: cross-venue carry (t 4.8-11). Directional ideas should be pooled into one registered
  family or run forward, not read one by one.
- **P3. Held data never used to predict anything:** SqueezeMetrics DIX; Cboe VIX1D, VIX1Y, VIX6M, SKEW and VXD; the
  MEXC index perps (NAS100, SPX500, US30) as targets. Queued as M499 (DIX) and M500 (SKEW). On SPX500 overnight the
  detectable move is 12 bp over all nights and about 24 bp on a top-quintile rule, against a 16 bp round trip. DIX's
  publication time is not in the repository and must be verified first.
- **P4. All tradable series end 2026-10-19..22.** Any held-data test misses the last three weeks.

## Operational finding
- **O1. A second writer on Codex's forward lanes.** On 2026-11-10 at 08:14 UTC my local orchestrator batch ran R406
  and R413. Their journals are owned by Codex's hourly GitHub runtime (`quant-paper-priority.yml`), which then failed
  from 09:33 to 12:33 UTC with "journal/raw state diverged" (`lab/runtime_takeover.py:71`).
  - Fixed in 1ec28d2: the six journal files were restored to their canonical prefix.
  - `docs/loop/PROMPT.md` now says never to run R406, R413 or R419 locally.
  - The cause was a wrong belief, not code: I thought every forward lane had stopped on 11-06.

## What was acted on
- **R439 (`experiments/carry5_v1`), CONFIRMED:** R275's all-four carry rule over five venues, adding KuCoin. +18.46%/yr at
  1x, NW t 8.71. KuCoin makes the book steadier (t 4.77 → 8.71, top-10-day share 33% → 18%) but not measurably richer
  (paired +1.48%/yr, t 0.54; level on constant notional).
- **Queue notes:** E1 on M155; DIX and SKEW as M499 and M500 (QUEUED, publication time to verify first).

## Disclosures
- The event-timing auditor printed the first two rows of `data/klines_1h/BTCUSDT.parquet` and
  `data/fundingRate/BTCUSDT.parquet`. Those are reserved 2020 rows. Nothing from them was used.
- The power auditor opened the headers of R392's published result CSVs. No statistic used them.
- No repository file was changed by any auditor.
