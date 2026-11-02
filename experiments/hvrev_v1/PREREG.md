# PREREG: hvrev_v1 (R380). 8-10 week reversal inside the high-volatility tercile, with and without the high-volatility / winner tilt removed (M457)

Frozen with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R380
- **Method M457:** medium-horizon reversal in high-volatility tokens, residualised against the tilt of R238 / M225.
- **Owner (single writer):** the Claude lane worker that froze it. Date registered (UTC): 2026-11-02.
- **Execution mode: API,** as R299.
- **Gate: 0, on seen data.** Every window below was read by R238, R299, R304, R305 and R332 with other features.

## Question
Does a weekly-rebalanced book that is long the 8-10 week losers and short the 8-10 week winners inside the
highest-volatility tercile of the top-150 Binance perps earn a positive net return at API costs in validation, and does
it survive when the part of its score explained by the high-volatility / winner tilt (7-day return, 7-day max, 30-day
volatility) is removed?

## Why this lane (what it can and cannot say)
- M457's source is a 2026 preprint (not read by us; its cost results come from a coauthor synopsis) that reports stronger
  8-10 week reversal in high-volatility tokens. Nothing here tests that paper; it tests the stated mechanism on our panel.
- R238 found rev28, MAX, IVOL and skew books were one high-volatility/winner tilt that paid in 2021 and about nothing in
  2022-23, and R222 found slow cross-sections too small after cost. This lane starts at 2022, so 2021's tilt payoff is
  not in either window.
- The 2021-26 archive holdout is already spent: validation here is seen data and cannot count as a fresh test.

## Universe and data
- `data/daily/panel.parquet` (sha256 in the inputs block), columns `day, perp, close, ret, fund, rank_qvol30` only. No
  metrics column (`oi_usd`, long/short ratios, taker ratio) is read, so R332's metrics look-ahead does not apply. The
  panel starts 2021-01-02 and ends 2026-09-30; no 2020 row, no MEXC-only coin, no reserved folder is read.
- Universe on decision row D: perps with a close on row D and `rank_qvol30 <= 150` (point in time, as R299). Delisted
  perps are in the panel while they traded. A name whose exit close is missing for the whole hold is credited 0 by R299's
  `targets()`; the count of such names per leg is reported (it favours a long leg of losers).
- Row D holds the 24 h that end at 00:00 UTC of day D. Features read rows up to D only; entry is row D's close; exit is
  the last close in rows D+1..D+7; funding settled in those rows is paid by longs and received by shorts.

## Feature lineage (all point in time, computed from rows up to D)
| Feature | Parent fields | Definition | Missing rule |
|---|---|---|---|
| vol30 | ret | std of log1p(ret) over 30 rows | needs >= 21 rows, else the name drops out |
| mom7 | ret | sum of log1p(ret) over 7 rows | needs >= 4 |
| max7 | ret | max of ret over 7 rows | needs >= 4 |
| momL, L in {56, 63, 70} | ret | sum of log1p(ret) over L rows (8, 9, 10 weeks) | needs >= 39, 44, 49 rows |

A name missing any of the four inputs on row D is not in that book's group. A missing value is never read as zero.

## The family (6 books) and two controls (2 books): 8 trials
- **Family:** lookback L in {8, 9, 10} weeks x {raw, residualised}, all inside the high-volatility gate.
- **Controls** (reported, counted, never picked): lookback 9 weeks, no gate (whole eligible universe), raw and residualised.
  They exist to read "stronger in high-volatility tokens" as a difference.
- **Gate (hv):** among the eligible names on row D (n of them), keep the n // 3 with the highest vol30 (ties by the seeded
  random order, seed 299).
- **Score:** -momL, ranked across the group into (-0.5, 0.5) with average ties (high = long, i.e. a loser).
- **Residualised books:** within the same group and row, regress that rank on a constant and the ranks of vol30, mom7 and
  max7 by OLS; the score is the residual. The R^2 of each row's regression is reported.
- **Legs:** long the top fifth and short the bottom fifth of the score, floor(n_group / 5) names each, equal weights, ties by
  R299's seeded random order (seed 299). A rebalance with fewer than 30 names in the group is skipped (R299's
  `MIN_NAMES`, via `legs()`). The plumbing count (no return read) shows 2 of 248 rebalance days where the hv group is
  below 30; those weeks are skipped for the hv books.
- **Rebalance:** every 7th day from 2022-01-01 (R299's weekly grid), hold 7 days.

## Splits and cost
- Discovery 2022-01-01..2023-12-31, validation 2024-01-01..2026-09-30 (R299's). A period counts only when its hold ends
  inside the window. Validation is read once.
- Cost: API 8.5 / 17 / 25.5 bp per side (1x / 2x / 3x) on each rebalance's turnover, from R298's `costed()` and
  `turnover()` (`scripts/run_lotcap.py`, unchanged). Statistics from its `series_stats()` (Newey-West t, lag 2 on a weekly
  grid; mean without the 10 best periods). Windows and legs from `scripts/run_mlrank.py`, unchanged.

## Decision (frozen before any statistic)
- **The pick:** the family book (not a control) with the highest discovery net 1x Newey-West t among those with a positive
  discovery net 1x mean (R299's `decide`). If no family book has a positive discovery mean there is no pick and the
  verdict is NULL.
- **It passes** only if, in validation, all three hold:
  1. net 1x t >= 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best periods is positive.
- **Verdict:** PARTIAL (gate 0, seen data) if the pick passes, else NULL. No second pick, no other book can substitute.
- **Reading of a PARTIAL:** if the pick is a raw book, the residualised book with the same lookback is shown beside it,
  and the pass is not attributed to reversal beyond the tilt unless that twin's validation net 1x mean is positive. This
  changes no verdict.
- **What a PARTIAL earns:** a forward paper lane may be registered; nothing is traded and no gate beyond 0 is claimed.
- **What a NULL means:** these six books are closed on this panel; M457 is not reopened by a variation of lookback, gate
  width or tilt set.

## Reported, not decided on
Per book and window: gross and net at 1x/2x/3x with the mean, bp/day, median, hit rate, annual Sharpe and mean without the
10 best periods; leg means; names per leg; turnover per rebalance; mean group size; mean R^2 of the residualisation;
zero-exit names per leg; net 1x bp/day by calendar year. Across books: Hansen SPA over the 6 family books per window; the
paired difference (hv minus ungated control) at 9 weeks, raw and residualised; the correlation of each raw book's weekly
net with its residualised twin.

## Multiplicity
8 books in this lane (6 family + 2 controls), all counted. Program trials before this lane: 9,479,246 (`registry.program_trials()`
on 2026-11-02); the raw sum is bookkeeping, not an independent-test count. FINDINGS reads the
result against it.

## Evidence lineage
- Canonical method id: M457. Parents: R238 (the tilt), R222, M225 (residualisation), R299 (helpers, grid, windows),
  R332 (R299's panel without metrics look-ahead).
- Decision group this signal feeds: weekly cross-sectional crypto perp spread books (R238 / R299 family).
- Samples seen by any parent: all of 2022-01-01..2026-09-30 on this panel. Proposed fresh sample: none. Exact overlap: total.
- `docs/GATES.md` sha256 e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. This lane meets gate 0 only; it
  has no dependent-null calibration, strict on-time clock, leave-two-coins-out or power calculation, and no across-family
  selection control, so any PARTIAL stays exploratory.

## What the author has seen
- R238's FINDINGS (the tilt and its 2021 payoff), M457's queue row and R332's PREREG.
- The plumbing count of `scripts/run_hvrev.py --plumbing` (eligible names per rebalance, hv group sizes: eligible median
  138-139, minimum 88; hv group minimum 29; 2 of 248 rebalances below 30), with returns replaced by presence flags.
- The synthetic-noise unit tests (`tests/test_run_hvrev.py`): gate, residual orthogonality, no look-ahead, pipeline.
- Never computed before the freeze: a return, a statistic or a rank IC of any book of this lane on the real panel.

## Known limits
- Seen data throughout; validation cannot be a fresh test (Gate 0).
- The source paper's definition (volatility measure, reversal window skip, weighting) is not known; this lane's choices
  are fixed here and are not tuned. The tilt set (mom7, max7, vol30) is the closest panel-only version of R238's
  (mom7, maxd, ivol): total vol30 stands in for idiosyncratic vol.
- About 50 names per group and 10 per leg; 142 validation weeks give about t 2 only for roughly +30 bp/day.
- Two skipped hv rebalances in 2022; zero-exit credit of delisted names (reported); funding is the panel's `fund`.

## Stop rules
The lane ends when the run, FINDINGS and the one registry row are written. After the results: no new lookback, gate, tilt
set, cost, split or pick. A changed idea is a new lane with a new id.

## Outputs
`results/summary.json`, `results/periods.csv`, `run.log`, `FINDINGS.md` (1x/2x/3x table for both windows, read against
`registry.program_trials()`).

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
6bf67388c8acf013941ed48d92963cfee04611ca3a82c12aaeede6776ad8ea67  data/daily/manifest.json
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe  lab/data.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
d98e791aa78d677f0ba4d66cba55fc4bf74c20d13136b39026881873b328d05b  scripts/run_hvrev.py
```
