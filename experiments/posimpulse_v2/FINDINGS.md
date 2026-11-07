# FINDINGS: posimpulse_v2 (R240). Positioning impulse on 2024-25, the only unseen window it had

**Verdict: NULL.** Neither book passed validation (2024-01..2025-06). imp24/H lost (-0.7 bp/day, t -0.22).
imp72/H made +6.6 bp/day with t 1.33, and lost at 3x costs. The holdout was not read.

- **Registry row:** R240 (trials 2; R234's family, so 6 trials in all). Program trials after it: 9,471,930.
- **Gate:** 0.
- **Reproduce:** prereg sha 5788743c, frozen in commit d99ff9a before the run. Run `python scripts/run_posimpulse_v2.py`
  (about 30 seconds).
- **Origin:** queue M223, the follow-up R234 recorded after seeing 2023.

## Numbers (1x / 2x / 3x; K fixed on 2023: 12.99 for imp24, 12.98 for imp72; level book K 6.0)

| Book | Window | Net bp/day | NW t (1x) | Gross / cost (1x) | Residual vs level book, bp/day (t) | Trimmed (1x) |
|---|---|---|---|---|---|---|
| imp24/H | 2023 (seen) | +10.2 / +6.0 / +1.8 | 2.39 | 14.3 / 4.2 | +10.2 (2.40) | +8.6 |
| imp24/H | **2024-25H1** | -0.7 / -4.9 / -9.1 | **-0.22** | 3.5 / 4.2 | -0.8 (-0.27) | -0.7 |
| imp72/H | 2023 (seen) | +10.6 / +6.2 / +1.8 | 1.62 | 15.1 / 4.4 | +8.2 (1.26) | +7.9 |
| imp72/H | **2024-25H1** | +6.6 / +2.2 / -2.3 | **1.33** | 11.1 / 4.5 | +4.8 (0.97) | +5.1 |

The 2023 numbers are smaller than R234's per-year +24 bp/day because K is now fixed on a full-coverage year, about
2.3 times R234's, which halves the size. The t-statistics do not depend on K.

## Cost sensitivity
These are 72 h books with fast-moving features, so cost is about 4.2-4.5 bp/day at 1x, a third of the gross.
- imp24/H loses at every cost level in 2024-25.
- imp72/H stays positive at 2x (+2.2) and turns negative at 3x (-2.3).

## Reading
- **The 2023 result did not carry forward for imp24.** Its gross fell from +14.3 to +3.5 bp/day, below its cost.
- **imp72/H kept some gross: +11.1 bp/day, t 1.33.**
  - About a fifth of it is the level book (correlation 0.22, residual +4.8 with t 0.97).
  - It is not a pass. A third look at the same family on the next window would be a new lane, and the holdout is
    spent.
- **R234 + R240 close M001/M223:** six trials across two lanes, and nothing at t 2 on an unseen window.

## Not checked
- Other impulse horizons (6 h, 168 h).
- Maker entries, which would remove most of the 4.4 bp/day cost (the gross of imp72/H is about 2.5 times its cost).
- The holdout.
