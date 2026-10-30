# FINDINGS: posimpulse_v1 (R234). The change in top-vs-crowd positioning as a spread book

**Verdict: NULL.** All four books failed discovery, so validation and holdout were not computed. The holdout was not
read.

- **Registry row:** R234 (trials 4). Program trials after it: 9,471,897.
- **Gate:** 0 (screen). Nothing here moves towards money.
- **Reproduce:** prereg sha 3275f91f, frozen in commit 8ed92a8 before the run. Run `python scripts/run_posimpulse.py`
  (about 80 seconds).
- **Origin:** queue M001, NEXT_SEARCH_SPACE's first-ranked item.

## Numbers (discovery 2021-01..2023-12; 1x / 2x / 3x costs)

| Book | Net bp/day | NW t (1x) | Residual vs level book, bp/day (t) | Corr with level book | Trimmed mean (1x) | Gross / cost (1x) |
|---|---|---|---|---|---|---|
| imp24/H | +3.5 / -0.4 / -4.3 | 0.87 | +3.5 (0.88) | 0.00 | +2.4 | 7.4 / 3.9 |
| imp24/L | -11.4 / -15.3 / -19.2 | -2.58 | -11.4 (-2.58) | 0.00 | -10.0 | -7.4 / 3.9 |
| imp72/H | +5.2 / +1.0 / -3.1 | 0.90 | +2.8 (0.50) | 0.20 | +2.7 | 9.3 / 4.2 |
| imp72/L | -13.5 / -17.6 / -21.8 | -2.23 | -11.1 (-1.88) | -0.21 | -10.8 | -9.3 / 4.2 |

- H longs the coins whose top traders turned most towards long against the crowd (bin 7) and shorts bin 0. L is the
  reverse.
- The reference is the level book: top_vs_crowd bin 0 short, K 2.418, as R211.

**Per year at 1x (bp/day):**

| Book | 2021 | 2022 | 2023 |
|---|---|---|---|
| imp24/H | -7.2 | -6.1 | +23.8 |
| imp72/H | -7.7 | -2.0 | +25.3 |

**Coverage.** The share of eligible coin-hours with a finite impulse:

| Year | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| Coverage | 9-10% | 11-12% | 99.8% | 99.7% | 99.5% |

## Cost sensitivity
- Gross is 7-9 bp/day against 4 bp/day of cost at 1x.
- The H books are about break-even at 2x and lose at 3x.
- The impulse turns over faster than the level: K is 5.5 slices per hour, against 2.4 for the level book's one side.

## Reading
- **The sign is the expected one, but too weak to pass.** H, which shorts fresh divergence against the crowd, earns.
  L loses by the same amount less costs.
- **The impulse is nearly independent of the level.** Correlation is 0.00 for 24 h and 0.20 for 72 h. So it is not
  the level book in disguise, but on its own it does not reach t 2.
- **The whole discovery result comes from 2023, the only year with full positioning data.**
  - In 2021-22 only about 10% of coin-hours have the ratios. Those books are thin and lose 2-8 bp/day.
  - In 2023 both H books make about +24 bp/day.
  - This split was seen after the run, so it is a description, not a result.
- **Follow-up:** a lane that uses only full-coverage years would be a new id with the 2023 split in view:
  - discovery is 2023 only, already seen, so not a test;
  - the test is validation 2024-01..2025-06, which has never been read for the impulse.
  Queued as M223. Its trials add to the program count.

## Not checked
- Other horizons (4 h, 12 h, 168 h).
- A one-sided short-only impulse book (the level book's form).
- An impulse gate on the level book.
- The holdout, for any book.
