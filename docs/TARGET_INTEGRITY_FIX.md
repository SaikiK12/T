# Complete forward labels and protected holdout prices

Implementation follow-up dated 2026-10-19, based on `babe092`. This change repairs two shared research functions using synthetic fixtures; no market outcomes, frozen specifications, registry rows, or journals were changed.

## Missing observations inside an outcome

Previously, `lab.atlas.forward` replaced unavailable returns with zero before taking cumulative sums, then checked only the first return in each window. For `[+1%, NaN, 0%]`, its two-hour label at the first row was finite even though the second return was unavailable. Infinities could also overflow into later labels.

The repaired implementation keeps cumulative sums of finite returns and a separate count of nonfinite observations. A horizon label is available only when every return in its window is finite. The eligible cross-sectional benchmark uses that same complete-window mask. An invalid interval therefore removes both its raw and excess target without contaminating valid windows after it. Horizons longer than the requested segment produce all-missing labels; nonpositive horizons are rejected.

This changes the target sample when raw histories contain gaps or infinities. Archived atlas findings are not revalidated by the patch and must retain their original provenance. Before a new market-data run, freeze the corrected code and data hashes in the new lane; do not substitute rerun outputs into an old experiment.

## A return row depends on the following price

The engine defines `ret[t] = close[t+1] / close[t] - 1` minus funding. Thus evaluating return rows `[t0, t1)` uses the price at row `t1`. Previously `research.eval_rules` blocked `t1 > holdout_row`, but allowed equality. A synthetic panel in which only the first holdout close changes from 100 to 200 proves that the last supposedly pre-holdout return changes by 100 percentage points for a unit long position.

The shared evaluator now requires `allow_holdout=True` when `t1 >= holdout_row` and the panel contains holdout prices. The explicit opt-in still works. Panels ending entirely before the holdout remain usable. Under the existing full-day aggregation, a caller without holdout permission must end at an earlier full-day boundary; the patch rejects the unsafe request instead of silently shortening its dates.

The opt-in is a software guard, not a substitute for preregistration. Direct callers of `engine.run_rules`, `atlas.forward`, and other low-level engines still control their own splits; this patch does not claim to repair every lane-specific boundary. `battery_v1` remains on hold: its final-fold equality case is now rejected by the shared evaluator, but its other pre-registration/code mismatches remain unresolved. No old fold dates or decisions were rewritten.

## Verification

The new fixtures first reproduced the old failures, then passed after the patch. They cover NaN and both signs of infinity at every position within a horizon, recovery after an invalid interval, requested-segment boundaries, horizons exceeding the segment, and the exact holdout-price dependency. Existing finite-data label and daily/hourly aggregation tests remain in place. These are implementation tests with invented inputs, not a new strategy search or evidence of a trading edge.

The full repository suite passed: 154 tests (`NUMBA_NUM_THREADS=2`). A separate direct-window oracle matched both raw and excess labels on 30 seeded synthetic panels with nonfinite returns, varying eligibility, and horizons exceeding the segment. The isolated environment used NumPy 2.3.5, pandas 2.2.3, numba 0.68.0 and pyarrow 26.0.0. No model weights or historical market archives were downloaded. Stacked PRs #5/#6 are not part of this branch or that test count.
