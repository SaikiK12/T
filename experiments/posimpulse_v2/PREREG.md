# PREREG: posimpulse_v2 (R240). Positioning impulse on the full-coverage years: a validation-only test

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R240
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_posimpulse_v2.py`, `scripts/run_posimpulse.py` (features, imported unchanged), `lab/screen.py`
- **Queue:** M223 (follow-up of R234)
- **Gate:** 0 (screen).

## Why, and what the author has seen
- R234 tested imp24 and imp72 (the 24 h and 72 h change in top_vs_crowd) as 72 h spread books on 2021-2023. All four
  books failed discovery.
- Positioning data covers about 10-13% of eligible coin-hours in 2021-22 and about all of them from 2023. After the
  run, the author saw that imp24/H and imp72/H earned about +24 and +25 bp/day in 2023 alone (R234 FINDINGS, per-year
  table). That year is selected after the fact, so it is not evidence.
- No statistic of these books after 2023-12-31 has been computed. The holdout is spent at program level and is not
  read.

## Books (as R234, two of them)
- imp24/H and imp72/H: features built by `run_posimpulse.build` unchanged; xs8 bins among eligible coins; long 72 h
  slices in bin 7, short in bin 0; universe hedge, tier costs, funding.
- **One change from R234:** K (slices per hour, which sets size 1 / (72 x K)) is fixed on 2023 instead of 2021-2023,
  because the sparse 2021-22 coverage made R234's K too small for a full-coverage year. K does not change t.
- Reference: R234's level book (top_vs_crowd bin 0 short, K fixed on 2023). The residual is reported.

## Stages
1. **2023-01-01..2023-12-31: seen, reported only.** No decision.
2. **Validation 2024-01-01..2025-06-30: the test.** A book passes if all hold:
   - 1x mean > 0 with NW t (lag 10) >= 2;
   - 2x mean > 0.
   The bar is t 2, not R234's validation bar of 1.5, because nothing passed a frozen discovery stage first.
3. **Holdout: not read.** A passer becomes a candidate for a forward paper lane under a new id (R200 journals the
   live ratios hourly).

## Reported (not decided on)
- Per window, at 1x, 2x and 3x: mean, NW t, Sharpe, max drawdown, gross and cost, per year.
- Correlation, beta and residual against the level book.
- Trimmed mean at 1x (10 best and 10 worst days removed).

## Multiplicity
- Trials = 2.
- Program trials before: 9,471,928 (after R239).
- These books are R234's family looked at again, so R234's 4 trials and these 2 belong to one family.

## Expectations
- 2023's +24 bp/day was one year after a null discovery. Regression to the mean is the likeliest outcome. Most likely
  NULL; a pass would be the first positioning-change edge and would go to forward paper, not to money.
