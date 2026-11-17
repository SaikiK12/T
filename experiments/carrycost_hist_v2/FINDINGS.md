# FINDINGS: carrycost_hist_v2 (R500). C14 at recorded book cost, 2021-07..2026-09

**Verdict: COST_OK.**
- At $1,000 a leg, charged what the books asked at each real entry and exit, the book nets **+7.97%/yr**, above
  R275's 4.13%/yr hurdle.
- The same window at the flat 7 bp nets +9.79%/yr.
- Neither INCOMPLETE flag is raised: 2.9% of events miss a measured Gate leg (limit 20%), 23.0% miss a Binance leg
  (limit 50%).

Run on 2026-11-17 by `scripts/run_carrycost_hist_v2.py run` after the PREREG and its six input hashes verified.
- Results: `results/events.csv` (one row per event, costs only) and `results/report.json`.
- Raw books were never stored. Gate hours were reduced on arrival; Binance samples are derived files under the
  git-ignored `data/carrycost_hist_v2/`.

## Coverage
- **2,544 events** (entries and exits), 2021-07-01..2026-09-30.
- **Gate (exact hour).** 2,525 hour files: 2,457 found, 68 absent from the archive (HTTP 404). Of the events, 2,470
  have a measured Gate cost at $1k.
- **Binance (proxy: first 15 minutes of the event month's 1st).**
  - The pre-registered 4.5 GB transfer cap was reached with 1,473 of 1,896 coin-month streams read; 13 returned
    400.
  - 1,959 events have a measured Binance cost at $1k. The other 585 took the venue's same-year median (rule 5).
- **Data volume.** 4.50 GB transferred. 17 MB kept on disk.

## Costs measured (all-in per leg per side: walk + taker fee)
| Size a leg | Gate mean / median | Binance mean / median | Mean per leg side | × flat 7 bp | Net %/yr |
|---|---|---|---|---|---|
| $250 | 16.7 / 13.6 bp | 7.5 / 6.8 bp | 12.1 bp | 1.73 | **8.56** |
| **$1,000 (primary)** | **20.4 / 15.4 bp** | **8.7 / 7.6 bp** | **14.6 bp** | **2.08** | **7.97** |
| $5,000 | 36.2 / 21.0 bp | 11.9 / 10.0 bp | 24.1 bp | 3.44 | 5.68 |

- **Gate's walk at $1k, before fee:**
  - percentiles: 7.9 bp (median), 13.5 (75th), 21.2 (90th), 86.8 (99th);
  - the worst event was 1,287 bp.
  - The tail is what lifts the mean above the median.
- **Gate's median walk by year (bp):** 12.4 (2021), 10.8 (2022), 7.6 (2023), 7.1 (2024), 6.6 (2025), 8.1 (2026).
  Books got deeper after 2022.
- **Against the one live snapshot.** The fee map's 18.4 bp a leg side at $1k (R495, 2026-11-15) is above the
  historical mean of 14.6 bp. That snapshot was not optimistic.

## Cost sensitivity (primary cell, $1k)
| | Net %/yr |
|---|---|
| Measured walk 1x + fee | 7.97 |
| Measured walk 2x + fee | 5.96 |
| Measured walk 3x + fee | 3.95 (just under the 4.13 hurdle) |
| Flat 7 bp: 1x / 2x / 3x | 9.79 / 8.08 / 6.38 |

Variants are reported, never chosen. At $1k: `snap0` (the 00:00 sample alone) 7.46; `best` (lowest minute, a
patient taker) 8.99.

## By year (primary cell)
| 2021 (from 07-01) | 2022 | 2023 | 2024 | 2025 | 2026 (to 09-30) | 2024-01..2026-09 |
|---|---|---|---|---|---|---|
| 7.10 | 6.46 | 1.22 | 3.84 | 22.62 | 5.52 | 11.13 |

- **2025 carries the result.** Without it, the day-weighted mean of the other years is about +4.5%/yr, barely above
  the hurdle. This is computed here from the table, not a pre-registered cell.
- 2023 and 2024 were below the hurdle at measured cost.

## What this says, and what it does not
- **The book's archive return survives the recorded books at taker execution.** That holds at $250 a leg, which is
  the size for a $10k book: 20 slots × 2 legs × $250.
  - Cost takes about 1.8 points a year at $1k and 1.2 points at $250.
  - The binding risk is the return's concentration in 2025, not cost.
- **What is still open:**
  - funding actually credited;
  - transfers and margin between the two venues;
  - outages and delistings;
  - maker fills (R498 reads 2026-12-01).
- **The Binance leg is a proxy.** It is a different day of the month, and only 15 minutes. Gate is the costlier leg,
  and it is exact.
- **The book is still a selection.** C14 was chosen among R275's books; its forward verdict stays R390's. Blind
  replications on held-out coins earned +0.7 to +2.5%/yr before this cost. A cost of 14.6 bp a leg side would cut those
  further.
- **Time.** This answered in hours, from years of recorded books, what forward paper would have taken months to
  answer for taker cost.

## Lineage and process
- R499 asked the same question and was superseded for disk before any cost was read (see
  `../carrycost_hist_v1/NOTES.md`).
- R500 is registered with 0 trials; it is a measurement.
- Program trials at the freeze: 9,785,313.
