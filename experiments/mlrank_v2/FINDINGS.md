# FINDINGS: mlrank_v2 (R304). Without the leaking columns the GBM ranker still passes; the leak never carried it

**Verdict by the frozen rule: PARTIAL (gate 0, on seen data).** The pick passes all three checks. It is not a
candidate yet. The validation window was read before (R299), and a market-neutral +59 bp/day after costs needs an
explanation before it gets a batch slot or a forward ticket. R305 (`mlaudit_v1`) looked for one and found none
(label `unexplained`; below).
- **Trials:** 7 (6 family books, 1 diagnostic), gate 0.
- **Read:** frozen PREREG 19f56764, frozen and pushed in 811283d before the run. Run 2026-10-22 with
  `scripts/run_mlrank2.py`. All 7 inputs matched their frozen hashes.
- **The pick:** gbm h7 clean. Each week, long the top fifth of a gradient-boosted ranking of 24 point-in-time
  features, and short the bottom fifth, in the top 150 Binance perps by 30-day volume.
- **The three leaking columns did not carry R299.** Without them the pick is +58.9 bp/day in validation, against
  R299's +55.4 with them. The GBM on those three columns alone loses (−20.5 bp/day, rank IC 0.07). R299's FINDINGS
  called its result invalidated by the leak. That was wrong about the size: the leak was real, but it earned nothing.

## Result

**The pick: gbm h7 clean (bp/day; t is Newey-West)**

| Window | Weeks | Gross | Net 1x / 2x / 3x | t at 1x | Without best 10 (bp/week) | Long leg (bp/week) | Short leg (bp/week) | Rank IC |
|---|---|---|---|---|---|---|---|---|
| Discovery 2022-23 | 104 | +38.7 | +36.0 / +33.4 / +30.7 | +5.99 | +178.5 | +133.7 | +136.9 | 0.159 |
| Validation 2024-01..2026-09 | 142 | +61.1 | +58.9 / +56.8 / +54.6 | +4.21 | +286.1 | +310.1 | +117.3 | 0.190 |

- **The checks:** t ≥ 2.0 at 1x (+4.21), a positive 2x mean (+56.8), a positive mean without the 10 best weeks
  (+286 bp/week). All pass.
- **SPA:** p 0.000 in both windows (best book: gbm h7 clean in discovery, gbm h1 clean in validation).
- **Turnover:** 1.76 per week in validation (of 2.0 possible), about 30 names a leg.

**All 7 books (bp/day; t of net 1x)**

| Book | Discovery gross | Discovery net 1x (t) | Validation gross | Validation net 1x / 2x / 3x (t at 1x) | Rank IC disc / valid |
|---|---|---|---|---|---|
| ridge h1 | +19.9 | +7.6 (0.99) | −0.8 | −12.3 / −23.8 / −35.3 (−1.09) | 0.110 / 0.102 |
| ic h1 | +11.0 | +2.4 (0.30) | −15.9 | −22.8 / −29.8 / −36.7 (−1.94) | 0.102 / 0.100 |
| gbm h1 | +39.2 | +24.0 (3.44) | +57.7 | +44.5 / +31.2 / +18.0 (4.73) | 0.124 / 0.121 |
| ridge h7 | +13.0 | +10.6 (1.48) | −15.6 | −17.7 / −19.7 / −21.7 (−1.02) | 0.138 / 0.144 |
| ic h7 | +3.8 | +1.5 (0.19) | −25.6 | −27.4 / −29.2 / −31.0 (−1.56) | 0.125 / 0.143 |
| **gbm h7 (pick)** | +38.7 | +36.0 (5.99) | +61.1 | +58.9 / +56.8 / +54.6 (4.21) | 0.159 / 0.190 |
| gbm h7 leak-only (diagnostic) | −0.7 | −3.3 (−0.90) | −18.4 | −20.5 / −22.7 / −24.8 (−1.42) | 0.013 / 0.074 |

- **Only the GBM earns, as in R299.** The linear books rank well on average (IC 0.10-0.14) and lose at the extremes.
  Their short legs lose most (ridge h7 −118 bp/week in validation, the GBM's +117).
- **Survival:** later-delisted coins are 9.6% of the validation universe. The pick holds 7.1% of them in its long leg
  and 13.5% in its short leg. The survivor flag (short-leg share above twice the universe's) is off in both windows.
  The leak-only book's short leg held 19.5%, and it still lost.

## The audit
**Post-hoc look, before the audit lane** (not a trial; numbers in R305's PREREG):
- **Lag test:** every feature one day later. Validation net +62.8 bp/day (t 4.88), unchanged. The edge is not in bar
  timing. (This book is counted in R305's trials.)
- **Permutation importance** (one GBM trained to 2023, scored on 2024-26): age, range7, qvol30, oi_chg7, oi_qvol
  and ls_acc lead. No single feature carries more than 0.025 of the 0.150 rank IC.
- **Leg profile:** the long leg is old, calm, low-range, with larger trades and high OI per volume. The short leg is
  young, volatile, wicky, with recent momentum and high funding.

**R305 `mlaudit_v1` (frozen 1152e416, 7 trials) tested that reading and rejected it.** Label: `unexplained`.
- Without `age`: +56.1 bp/day (t 4.06). On the six risk features alone: −15.7. Without them: +62.4 (t 5.42).
- A fixed low-risk score with the same signs loses in both windows (−21.3 in validation).
- Alpha against the equal-weight universe +58.4 bp/day (t 4.22), against BTC +58.8 (t 4.11). Not a market bet.
- The long leg holds the alpha: +45.9 bp/day over the equal-weight universe (t 8.81). The short leg adds +14.6
  (t 1.43).
- **The short leg's tail is extreme:** in validation, 49% of weeks had a short name up more than 50% in the week
  and 15.5% one up more than 100%. The worst was COAI, +1,850% in a week (2025-10). At 1/30 of the leg that costs
  about 62% of the leg in one week.
- Details and next steps: `experiments/mlaudit_v1/FINDINGS.md`.

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side on each rebalance's turnover.
- **At 1x/2x/3x** the pick nets +58.9 / +56.8 / +54.6 bp/day in validation, and +36.0 / +33.4 / +30.7 in discovery.
  Weekly turnover is small against the gross, so cost does not decide it. The daily GBM book (gbm h1) falls to +18.0
  at 3x.

## Read against the program
- **Program trials:** 9,478,683 in `registry.program_trials()` before this row. With R304's 7 it is 9,478,690.
- The pick's discovery t of 5.99 just clears a Bonferroni bar over the whole program (5.84 for 9,478,690 trials,
  two-sided 5%, normal approximation), on a window R299 had already read. Validation's 4.21 does not. The SPA p of
  0.000 is over this family only.

## What this does and does not show
- **It shows:** the R299 GBM result does not come from the three survivor-leaking columns. A gradient-boosted
  ranking of 24 point-in-time features earned +59 bp/day net market-neutral in 2024-26 on the top 150 Binance perps,
  with positive years throughout and alpha over both the market and BTC.
- **It does not show** an edge anyone should trade yet:
  - both windows were read before (R299);
  - the short leg carries squeezes that would liquidate a leveraged account;
  - no forward day exists;
  - missingness of the metrics features is untested as a driver.

## Next
- **Forward paper:** the frozen pick, plus two variants chosen from R305 (the long leg against an equal-weight
  hedge; the pick with a protective cover on each short), each as its own frozen lane on MEXC prices.
- **Batch 2:** listed as frozen. The 2020 sample has no metrics (they start 2021), so the batch PREREG must fix how
  rows without them are scored.
- **Audit still open:** missing OI and positioning as a feature (a missing-flag refit, and a refit on rows with
  metrics only).
