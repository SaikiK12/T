# FINDINGS: squeeze_v1 (R274). A cover cuts the squeeze tail, but it also cuts the median; no covered short pays

**Verdict: NULL (gate 0).** 72 strategies: Binance 2021-26 and MEXC 2025-04..2026-09, at 40/80/120 bp.
- **Registry:** R274, 72 trials. Program trials become 9,477,741.
- **Reproduce:** prereg sha 58e13f44, frozen in commit 598e438 before any return was read. Then run
  `python scripts/qx_run.py experiments/squeeze_v1` at that commit. The run takes about 30 s.
- **Sample:**
  - 7,548 onset legs, 7,521 priced (4,717 Binance, 2,804 MEXC);
  - 27 legs had no trade at the settlement hour;
  - the 20× bar-jump guard dropped none.
- **Reserved coins:** the 87 MEXC-only contracts were not read. Every kind kept at least 206 clusters, so the family
  is the full 72.

## Best strategies by t (1x, one observation per settlement-hour cluster)
| Strategy | n | 1x mean | Median | Hit | t | RC p | Halves | 2x | 3x |
|---|---|---|---|---|---|---|---|---|---|
| mx_neg0.3 short 72h, 10% cover | 1,307 | +0.55% | +1.09% | 53% | 1.35 | 0.94 | +0.90 / +0.19 | +0.15% | -0.25% |
| mx_neg0.3 short 24h, 10% cover | 1,308 | +0.38% | +1.26% | 56% | 1.10 | 0.98 | +0.80 / -0.04 | -0.02% | -0.42% |
| mx_neg0.3 short 168h, 10% cover | 1,301 | +0.40% | -0.32% | 49% | 0.85 | 0.99 | +0.80 / +0.00 | +0.00% | -0.40% |
| mx_neg1 short 168h, 10% cover | 542 | +0.38% | -2.68% | 47% | 0.41 | 1.00 | -0.83 / +1.60 | -0.02% | -0.42% |
| bn_neg0.3 short 168h, 10% cover | 2,278 | +0.11% | -1.04% | 48% | 0.33 | 1.00 | -0.41 / +0.63 | -0.29% | -0.69% |

- **Reality check:** the family's max-t null has its 95th percentile at 4.19. Every strategy has RC p ≥ 0.94, so the
  matched null was not run (it runs only after an RC pass).
- **Full table:** `results/strategies.csv`. `results/SUMMARY.md` is written by the pipeline.

## What the cover does (1x mean / median, %; descriptive)
| Cell | No cover | 10% | 20% | 35% |
|---|---|---|---|---|
| bn_neg0.3 72h | -0.99 / +2.83 | -0.03 / +0.13 | -0.34 / +1.71 | -0.20 / +2.45 |
| bn_neg1 168h | -3.43 / +6.23 | +0.06 / -4.06 | -0.34 / +1.50 | -1.23 / +3.86 |
| bn_neg2 168h | -14.10 / +5.83 | -1.34 / -11.19 | -2.78 / +1.20 | -4.57 / +2.73 |
| mx_neg0.3 72h | -2.22 / +3.41 | +0.55 / +1.09 | +0.04 / +2.28 | +0.09 / +2.99 |
| mx_neg1 72h | -4.73 / +4.80 | -0.10 / +0.05 | -0.63 / +3.60 | -0.67 / +4.08 |
| mx_neg2 72h | -14.68 / +3.51 | -2.95 / -6.96 | -3.19 / +1.88 | -4.39 / +2.45 |

- **The tail is real, and a cover removes most of it.**
  - Without a cover, every negative-onset short loses on average: from -0.42% (mx_neg0.3 24h) to -15.5% (mx_neg2 168h).
  - The median is positive in every cell: +1.45% to +6.82%.
  - A 10% cover moves the means to about zero: bn_neg2 168h goes from -14.10% to -1.34%.
- **The median goes with the tail.**
  - The likely reason: many coins that are lower at the horizon first rise 10% or more, so the cover buys them
    back near the top. This is read from the falling median, not measured on the paths.
  - At 10%, the median falls to about zero, or below it for the deeper onsets (bn_neg2 168h: -11.19%).
  - Wider covers keep more of the median and more of the tail. None of the 54 covered strategies reaches t 2.
- **The shorts pay funding all the way.** At these onsets the short pays the negative rate, which is part of each
  number above.
- **Venues:**
  - With a cover, MEXC onsets do a little better than Binance's.
  - Without a cover, they do worse (mx_neg0.3 72h -2.22% against -0.99%).
  - The best (+0.55%, t 1.35) is within what 72 tries give by chance.

## Reading
- **Against program trials (9,477,741):** nothing here is close. The best t is 1.35, against a family null 95th
  percentile of 4.19.
- **Cost sensitivity:**
  - At 2x (80 bp), the best covered strategy keeps +0.15%.
  - At 3x it loses: -0.25%.
  - A cover fires in a fast market, where spreads are wider than 40 bp. So 1x flatters the covered lines.
- **Pre-committed outcomes (PREREG):**
  - **Forward lane: none.** No covered MEXC strategy has t ≥ 2 (the best is 1.35), so no MEXC forward lane comes from
    this family.
  - **2020 batch:** the covered Binance strategy with the highest t, bn_neg0.3 short 168h with a 10% cover (t 0.33),
    joins the first reserved 2020 batch, as written before the result. It is a weak entry, and the batch PREREG will
    say so.
- **What this closes:** M261 is tested (NULL). A close-based cover does not turn the negative-onset short into an
  edge at 10-35%. R273's long side (neg2 long +72 h, top 3 by t) is already in the 2020 batch.
- **What it leaves open, not tested here:**
  - Sizing by onset depth (the tail grows with the level).
  - An entry after the squeeze, for example a short only once the coin is 20% above the onset close, which waits for
    the tail instead of covering it. That would be a new frozen lane, decided before any of these paths is looked at
    again.
