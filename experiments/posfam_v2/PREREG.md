# PREREG: posfam_v2 (R212), top accounts' headcount as a contrarian signal

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R212
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_posfam.py --lane posfam_v2`, `lab/slices.py`

## What the author had seen
posfam_v1 (R211) on discovery (2021-01..2023-12, mostly 2023 by data coverage): the top-account ratio
top_acct = log(top_ls_count), xs8, lost in both tails as a with-the-top-accounts book: bin 0 short -47.6 bp/day (t -2.99,
gross -45.5), bin 7 long -13.6 (t -2.51); residual against the top_vs_crowd book -32.2 (t -2.43) and -3.9 (t -0.98).
This lane takes the **reverse** of both, chosen on those discovery numbers. Nothing from 2024 on has been computed for
top_acct. top_vs_crowd's holdout result is known (+71%/yr as a book), and top_acct's books correlate with it (-0.50
and -0.75 in discovery), so the holdout is not clean: the residual against top_vs_crowd is reported.

## Books (72 h slices, universe hedge, tier costs, funding; as R197 and R211)
- **C (primary):** top_acct bin 0 opens **long** slices and bin 7 opens **short** slices, positions summed before
  costs; size 1 / (72 x K), K = the mean over the two parts of slices opened per hour on 2021-01..2023-12, times 2.
- L: bin 0 long alone; S: bin 7 short alone (each with its own K).
- Reference (reported, counted as a trial): crowd_ls xs8 (archive bins) bin 0 long + bin 7 short, same
  construction: is top_acct's reversal just the crowd's?

## Stages
1. **Validation** 2024-01-01..2025-06-30: C passes if its 1x daily mean is positive with NW t (lag 10) >= 1.5.
2. **Holdout** 2025-07-01..2026-09-30, one shot, only if C passed: **CONFIRMED** if C's 1x mean is positive with NW t
   >= 2. L, S and the reference are computed on the holdout only if C passed.

## Reported
2x and 3x; gross and cost; correlation with and residual against the top_vs_crowd short book; discovery numbers of C
(not used for the decision).

## Multiplicity
Trials = 4 (C, L, S, crowd reference). Program trials before: 9,471,701.

## Expectations
Discovery effects shrink out of sample; the reversal could be the crowd-contrarian effect atlas_v1 already scanned
(crowd_ls views), in which case C and the reference move together. Guess: validation mean positive, t near 1.
