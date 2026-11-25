# FINDINGS: carry_meta_v1 (R531). An ML meta-label filter does not improve the design-gap carry book: FAIL (NULL)

**Verdict: FAIL** by the frozen rule. One trial.
- The run: `run.log`, 2026-11-26, PREREG `1dbea223` (frozen in fd85d439 before the run), one run.
- Results: `results/report.json` and `results/trades_unfiltered.csv` (6,760 trades of the unfiltered books).
- 12 quarterly models; first test day 2024-01-01; 1,004 test days.

## The decision (test days 2024-01..2026-09, equal-weight portfolio of R525's 12 pairs)
| Cost | Frozen rule %/yr | ML filter %/yr | Difference %/yr | NW t of the difference | Difference 2024 / 2025 / 2026 |
|---|---|---|---|---|---|
| 1x (7 bp a leg) | +6.49 | +5.32 | −1.17 | −3.40 | −1.35 / −0.42 / −1.94 |
| **2x (decided)** | **+5.19** | **+4.84** | **−0.35** | **−0.97** | −0.91 / +0.55 / −0.79 |
| 3x | +3.89 | +4.37 | +0.48 | +1.27 | −0.48 / +1.53 / +0.36 |

- **Checks at 2x:**
  - t ≥ 2.5: no (−0.97);
  - positive every year: no;
  - the meta book positive: yes (+4.84%/yr).
- **The ML book by year at 2x:** +6.61 (2024), +1.27 (2025), +7.25 (2026 to Sep).
- **After the 31.4% flat tax, against euro cash** (about 1.5%/yr after tax):
  - the frozen rule at 2x is +5.19 → 3.56%, **about +2.1%/yr over cash**;
  - the ML book is +4.84 → 3.32%, about +1.8%.
  - Both are in-sample for the primary rule. Only the filter is out of sample.

## What the model did
- **It is very selective.** It kept 5,465 of 169,782 scored candidate-days (3.2%), because only 44% of the rule's
  trades pay at 2x over their life. With a base rate under 0.5, a calibrated logistic model rarely reaches 0.5.
- **So the ML book traded less.** It saved turnover cost, which is why it beats the rule at 3x (+0.48%/yr, t 1.27),
  but it gave up carry, which is why it loses at 1x (−1.17%/yr, t −3.40).
- **Why it cannot pick winners (post hoc, descriptive, from `trades_unfiltered.csv`):**
  - The rule's trades are skewed: median −18 bp, mean +151 bp at 2x.
  - 10th / 90th percentile: −161 / +528 bp.
  - The best 10% of trades earn 123% of the total net.
  - The book is paid by a minority of long-lived wide spreads, and the entry features do not separate those from the
    many small losers.

## What it means
- **For money:** keep the frozen rule. The filter's only gain is lower turnover at high cost. If the live costs
  measured in R509 come out at 3x or more, a turnover rule (a higher entry threshold or a longer minimum hold) is the
  cheaper way to get that gain, and it is a one-parameter question, not ML.
- **For the lab:**
  - **ML on entries does not beat a rule whose profit comes from a fat right tail.** The next ML question, if any,
    is about holding: predicting which open trades will keep paying (the exit side), where the tail is.
  - This is the lab's first ML round on a payer family. It now sits with the cross-sectional ML rounds (R299, R304,
    R332): 0 of 4 decided ML rounds pass.
- **Forecast:** written P(PASS) 0.07 (ledger R531-pass); resolved 0.

## What could invalidate this
- **The primary rule is in sample** (R525's panel). The filter's comparison is fair, but both levels are optimistic.
- **The 0.5 threshold, set by the meta-labeling convention, is the decided trial.** With a 44% base rate, a lower
  threshold would keep more trades. It was not run, and doing so now would be a new, post-hoc trial.
- **Seven features, one model.** A richer model could do better. The lab's prior for that is low (0 of 4 ML rounds).
- **Costs are flat per leg,** not measured per coin. The 3x row is the closest to R508's real costs.
