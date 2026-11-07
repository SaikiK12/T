# FINDINGS: delay_v1 (R213), entry delay barely touches the flow books

PREREG sha 73f95bb1. Run 2026-10-19 by `scripts/run_delay.py` (a first run crashed at the panel start before any
statistic was printed; the warm-up was clamped at row 0 and the run repeated). Results in `results/`.

## Result
Opening each 72 h slice 1 or 2 hours after its signal bar costs **1-2% of the books' net**, and nothing for top_vs_crowd
in-sample. The edge is not front-loaded; R200's zero-delay paper accounting is not materially optimistic on this
count. The reading rule's flag (25% loss at d = 1) is **not raised**.

| Book | Window | d = 0 (bp/day, t) | d = 1 | d = 2 | share lost at d = 1 |
|---|---|---|---|---|---|
| A (three cells) | in-sample 2021-01..2025-06 | +12.10, t 3.36 | +11.99, t 3.34 | +11.94, t 3.33 | 0.9% |
| A | holdout 2025-07..2026-09 | +23.11, t 1.24 | +22.66, t 1.21 | +22.63, t 1.21 | 1.9% |
| B (top_vs_crowd) | in-sample | +4.93, t 2.64 | +4.93, t 2.64 | +4.94, t 2.65 | -0.1% |
| B | holdout | +19.62, t 2.73 | +19.38, t 2.69 | +19.20, t 2.66 | 1.2% |

All at 1x costs; book B here uses R200's unit (K 9.316), so its scale is a quarter of R198's top_vs_crowd book.

## Cost sensitivity (in-sample, d = 1)
A: 1x +11.99 (t 3.34), 2x +8.14 (t 2.28), 3x +4.28 (t 1.21) bp/day; gross 15.85, cost 3.86 bp/day at 1x.
B: 1x +4.93 (t 2.64), 2x +4.16 (t 2.23), 3x +3.38 (t 1.82). Holdout d = 1: A 1x/2x/3x +22.7/+17.4/+12.1, B
+19.4/+18.4/+17.5. Delay does not change costs (same turnover, shifted).

## Reading
- A linear guess for the live 12-minute lag is 0.2 x 0.9% = **0.2% of the net**, labelled a guess (hourly data cannot
  measure inside the hour).
- The lag that matters live is R200's actual `run_at`, which has been hours when the loop slept. R214 (flow72_fwd3)
  scores the same signals entered one bar late and reports the run_at lag distribution and a book entered at the
  first bar after run_at.
- Nothing here confirms anything: both windows' zero-delay outcomes were known. Program trials after this lane:
  9,471,709.

## Not checked
Intra-hour timing (no sub-hour prices in the archive); MEXC prices (R215); fills beyond the tier cost model.
