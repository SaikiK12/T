# Opt-in gap-aware labels and protected holdout prices

Implementation follow-up revised 2026-10-20 on Claude base `174e1a9`. This changes two shared research functions using invented fixtures; no market outcomes, frozen specifications, registry rows, or journals were changed.

## Historical labels stay the default

`lab.atlas.forward` historically replaced NaNs with zero in the cumulative sum, then masked labels whose starting return was NaN. For `[+1%, NaN, 0%]`, a two-hour label starting at the first row is finite although the second observation is unavailable. That same rule retains observed losses when a coin's history ends. Requiring a full future horizon would instead drop those terminal observations and can select survivors.

The default, `missing="legacy"`, preserves the historical cumulative calculation and missing-start mask, including its old infinity handling. Existing research callers do not opt into a new sample silently. Previously frozen findings keep their original behavior and provenance for their supported horizon ranges.

## Explicit gap-aware policy with terminal prefixes

A new study can preregister `missing="terminal_prefix"`. It uses finite-return sums and a separate count of invalid observations:

- A fully finite horizon is usable.
- An interior NaN invalidates every overlapping label, including a NaN at the horizon's last bar when this symbol resumes later in the selected segment.
- A finite prefix followed only by a terminal NaN suffix stays usable. For `[+1%, -41%, NaN, NaN]`, a four-bar label retains **-40%**, instead of dropping the loss. That retained label also contributes to the eligible cross-sectional benchmark.
- A missing start, an entirely missing symbol or any infinity within the horizon is unavailable. Infinities are not interpreted as a terminal exit. Valid windows after an interior defect recover normally.

"Terminal" is evaluated only inside the supplied `[t0,t1)` segment: neither later prices nor later eligibility are read. This is an observation-boundary convention, not independent proof of a delisting. A feed that stops can look the same. It retains known returns but does not price an unknown final settlement, claim zero subsequent economic loss, infer an executable liquidation or replace a portfolio's lifecycle accounting. A new study must document that assumption and bind its policy/code/data hashes before measurement.

Under both policies, a requested horizon crossing `t1` stays unavailable, even if the symbol's finite prefix ends earlier. A horizon longer than the segment produces all-missing labels; nonpositive horizons and unknown policy names are rejected. F and X remain float32; the cross-sectional mean uses finite labels of symbols eligible at the decision row. No archived findings are revalidated or replaced by this patch.

## A return row depends on the following price

The engine defines `ret[t] = close[t+1] / close[t] - 1` minus funding. Thus evaluating return rows `[t0, t1)` uses the price at row `t1`. Previously `research.eval_rules` blocked `t1 > holdout_row`, but allowed equality. A synthetic panel in which only the first holdout close changes from 100 to 200 proves that the last supposedly pre-holdout return changes by 100 percentage points for a unit long position.

The shared evaluator now requires `allow_holdout=True` when `t1 >= holdout_row` and the panel contains holdout prices. The explicit opt-in still works. Panels ending entirely before the holdout remain usable. Under the existing full-day aggregation, a caller without holdout permission must end at an earlier full-day boundary; the patch rejects the unsafe request instead of silently shortening its dates.

The opt-in is a software guard, not a substitute for preregistration. Direct callers of `engine.run_rules`, `atlas.forward`, and other low-level engines still control their own splits; this patch does not claim to repair every lane-specific boundary. `battery_v1` remains on hold: its final-fold equality case is now rejected by the shared evaluator, but its other pre-registration/code mismatches remain unresolved. No old fold dates or decisions were rewritten.

## Verification

Fixtures cover opt-in behavior, terminal loss inclusion in raw/excess labels, missing starts, all-missing series, interior gaps, both signs of infinity, recovery after defects, requested-segment boundaries and the exact holdout-price dependency. Existing finite-data label and daily/hourly aggregation tests remain in place. These are implementation checks, not a strategy search or evidence of a trading edge.

On 100 seeded synthetic panels, the default F/X arrays match the original Claude function byte for byte, including NaNs and infinities. On another 100 panels, the opt-in policy matches an independently written direct-window oracle, including terminal suffixes, listing starts, varying eligibility and overlong horizons. The archived reference function was extracted directly from `174e1a9`, rather than reconstructed from this patch. The focused forward/evaluator suite passes 17 tests; all **270 repository tests pass** on this branch (NumPy 2.3.5, pandas 2.2.3, numba 0.68.0 and pyarrow 26.0.0). No model weights or historical market archives were downloaded; separate PRs #5/#6/#17 are outside this branch.
