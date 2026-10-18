# PREREG: merge_v2 (R187), trade-consistent, faster, session-aware merge

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R187
- **Owner (single writer):** the session that froze it
- **Code:** `lab/merge.py` (cell_stats_episodes, select_v2, walk_forward_v2, trade), `lab/atlas.py`,
  `scripts/run_merge_v2.py`
- **What the author had seen when freezing:** all atlas_v1 (R185) main+clock results on 2021-2025H1 (discovery and
  validation), all merge_v1 (R186) results for M1, its placebo and M1s, and a diagnostic of one oversold cell
  (ema_ratio[8]@1h/z720 bin 0) by year and by how many symbols were oversold at once. The changes below come from
  those results, so the 2022-2025H1 test span is NOT clean for this lane: it is a development test. Its role is to
  decide whether a configuration earns a one-shot holdout test (a separate lane), not to prove an edge.

## What changes from merge_v1, and why
1. **Trade-consistent cell statistics.** merge_v1 and the atlas averaged each day's cells, and every hour a condition
   persisted counted again. That overweighted quiet days and let a symbol in free fall (a "falling knife") repeat its
   signal for hours. Here a cell counts once per episode (the hour a symbol enters the bin), its score is the
   Newey-West t of the daily SUM of episode returns (a fixed stake per trade), and its mean is per episode.
2. **Faster re-learning.** merge_v1's 180-day sensitivity beat its 365-day primary (gross t 2.68 vs 1.27). Primary
   window here: 180 days; sensitivity: 90 days.
3. **Session-aware means.** The atlas found edges concentrated around the US open and evening. Each cell gets a mean per
   session (asia, europe, us_open, us_afternoon, us_evening, weekend, as in atlas_v1) shrunk toward its pooled mean,
   (n_g m_g + 50 m) / (n_g + 50), n_g = episodes in that session. The forecast uses the mean of the current session.
4. **Order flow** (when its tensor is built): metrics and book-depth views join the candidate cells in run D.

## Procedure (fixed)
Same universe, costs, test span (2022-01-01 to 2025-06-30, 42 monthly refits, 72-hour embargo) and trading rule as
merge_v1. Usable cells: >= 30 episodes in the window, the same sign of the per-episode mean in both halves of the window,
|t| >= 2, excess excludes time-only views. Horizons 4 and 24 hours; raw and excess; N in 10, 30, 100; k_in in 0.5, 1,
1.5; cmult in 0, 0.25, 0.5, 1, 2 with fixed thresholds, plus thresholds scaled by the fee (k_in x cmult) for cmult 0.25
and 0.5. Minimum hold 4 hours, exit when the forecast in the held direction is <= 0, slots 10.

Runs (tensors main + clock unless stated):
- **A** (primary): 180-day window, session-aware. **A placebo**: the same on returns circularly shifted by 24k + 12
  hours inside [2021-01-01, 2025-07-01), seeded by the tag.
- **B**: 90-day window, session-aware. **C**: 180-day window, pooled (no session means), to isolate the session effect.
- **D**: as A with the flow tensor added, only if bins_flow.npy exists when the other runs are done.

## Primary configuration and decision
Primary: run A, excess, h = 24, N = 30, k_in = 1, fixed thresholds.
- **GROSS EDGE** if the primary at cmult 0 has Newey-West t (lag 5, daily) >= 3.
- **NET PASS** if at cmult 1: t >= 2, a positive sum in at least 3 of the 4 periods (2022, 2023, 2024, 2025H1), and
  the A placebo at cmult 1 has t < 1. A NET PASS earns a one-shot holdout lane for the frozen primary; nothing else does.
- **LOW-FEE PASS** if the fee-aware variant at cmult 0.5 meets the same three conditions: evidence for a venue with
  about half the tier costs (MEXC-like taker fees or maker execution), to be confirmed the same way.
- Otherwise FAIL, with break-even cmult reported.
Also reported: the session effect (A vs C), the window effect (A vs B), the flow effect (D vs A), the merge curve over
N, per-year results, and the Deflated Sharpe of the best configuration at cmult 1 against all configurations tried in
the real runs.

## Multiplicity
Trials = trading configurations evaluated in real runs (each run: 2 horizons x 2 measures x 3 N x 3 k_in x 7 cost
variants = 252). Program total read alongside.

## Stop rules
Failing unit tests stop the run. No change after seeing results. The holdout is not read.

## Expectations (written before running)
Moderate: trade-consistent scores should remove some false strength; faster windows and session means should help a
little. A net pass at full tier costs is unlikely; a low-fee pass is possible.
