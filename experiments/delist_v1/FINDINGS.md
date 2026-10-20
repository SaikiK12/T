# FINDINGS: delist_v1 (R267). The delisting-notice short is NULL. Spot notices at +1 h are a forward candidate

**Verdict: NULL (gate 0).** Shorting every Binance "Will Delist" leg at the first hourly open after the notice, and
covering an hour later, earned -0.12% per notice at 1x (t -0.06, 68 notice clusters, 160 legs, 2022-03..2026-09).
- **Gates:** G1 (t >= 2.40), G2 (both halves) and G4 (matched null, p 0.0575) fail. Only G3 (2025+ positive) passes.
- **One logged variant clears G1-G3: spot notices at +1 h**, +4.15% per notice at 1x, t 3.07, n 25. It is one of 8
  logged variants, so it is not a pass. Under the PREREG it is a reason for a new frozen lane (see "Next").
- **Registry:** R267, 8 trials. Program trials become 9,472,080.
- **Reproduce:** prereg sha fe2595ff, frozen in commit 25c8480 before any price was read. Then run
  `python scripts/run_delist.py` (about 30 s).
  - The runner checks the catalog, article and leg hashes, and rebuilds `legs.csv` byte for byte.
- **Execution mode:** API. The entry has to follow the notice within the hour, at any time of day.

## Sample
- **Notices:** 83 notices in the catalog give 259 legs.
  - The archive window with an archive perp keeps 72 notices and 170 legs.
  - 10 legs had no traded perp at t0 (`no_market`).
  - **Priced:** 160 legs in 68 clusters (25 spot, 43 futures).
- **Catalog start:** the catalog begins in 2022-02, so there is no 2020 notice, and no reserved data was read.
- **Coverage:** 2023 has a single cluster. Most 2023 spot-delisted coins had no perp.

## Primary and logged variants (one observation per notice cluster)
| # | Legs | Exit | Line | n | 1x mean | t | 2x mean | 3x mean | Median | Hit | Halves | 2025+ (n) | G1-G3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | all (primary) | +1 h | short | 68 | -0.12% | -0.06 | -0.52% | -0.92% | +1.40% | 65% | -1.38 / +1.14 | +2.22% (43) | fail |
| 2 | all | +24 h | short | 68 | +0.54% | 0.18 | +0.14% | -0.26% | +4.30% | 63% | -5.72 / +6.80 | +4.28% | fail |
| 3 | all | +1 h | BTC-hedged | 68 | -0.29% | -0.14 | -0.79% | -1.29% | +1.28% | 62% | -1.43 / +0.86 | +1.96% | fail |
| 4 | all | +24 h | BTC-hedged | 68 | +0.23% | 0.08 | -0.27% | -0.77% | +4.35% | 65% | -5.96 / +6.42 | +3.88% | fail |
| 5 | **spot** | **+1 h** | short | **25** | **+4.15%** | **3.07** | +3.75% (t 2.78) | +3.35% (t 2.48) | +4.16% | 72% | **+3.90 / +4.38** | **+5.61% (17)** | **pass** |
| 6 | futures | +1 h | short | 43 | -2.60% | -0.82 | -3.00% | -3.40% | +1.19% | 60% | -5.05 / -0.27 | +0.01% | fail |
| 7 | spot | +24 h | short | 25 | +3.58% | 0.93 | +3.18% | +2.78% | +8.90% | 64% | +1.81 / +5.22 | +4.70% | fail |
| 8 | futures | +24 h | short | 43 | -1.23% | -0.30 | -1.63% | -2.03% | +3.02% | 63% | -11.79 / +8.85 | +4.00% | fail |

- **G4 null (primary):**
  - Same perps, same hour of day, on a random day 7-60 days before the notice. All 68 clusters had at least 10
    admissible days.
  - Null mean -0.39%, 95th percentile -0.11%, observed -0.12%, p 0.0575.
- **Costs:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x, with funding settled in the hold. Funding is small at
  +1 h (-0.02% mean) and costs the short 0.64% at +24 h.

## Why the pooled short fails: futures notices squeeze
- **The mean is dragged by squeezes on perps that are themselves being delisted:**
  - ANC (2022-05, LUNA crash): -95% in the hour.
  - SLERF (2025-10): -87% in the hour.
  - LUNA (2022-05): -16%.
- **Without the three 2022 crash notices** (LUNA x2, FTT): +1.69%, t 1.07.
- **Futures notices:** the median leg is positive (+1.19%), but liquidity drains before settlement, and the tail
  belongs to the squeezes.
- **Spot notices:** the perp keeps trading, and the hour after the entry keeps falling in 72% of clusters.

## What the hourly entry misses
- **The move the entry cannot catch:** from the close before the notice's bar to the entry, short sign. +2.49% per
  cluster on average, median +4.21%.
- **For spot notices released in the first minutes of an hour** (19 of 25 clusters), the notice's own hour fell a
  median of 14.9%, with an interquartile range of 8.8-20.7%.
  - One exception went the other way: ALPACA (2025-04) rose 85% in that hour.
- This lane enters after that move. The old session's entry, seconds after the notice, saw a decay within seconds.

## Robustness (not counted)
| Check | n | Mean | t |
|---|---|---|---|
| Primary without the top 3 legs | 68 | -0.34% | -0.16 |
| +24 h without the top 3 legs | 67 | -0.43% | -0.15 |
| Primary without the crash notices | 65 | +1.69% | 1.07 |
| +24 h without the crash notices | 65 | +2.57% | 1.03 |
| Gross only, +1 h | 68 | +0.30% | 0.14 |
| Gross only, +24 h | 68 | +1.58% | 0.54 |

- **Per year (primary, 1x):**

  | Year | n | Mean |
  |---|---|---|
  | 2022 | 11 | -10.16% |
  | 2023 | 1 | -3.68% |
  | 2024 | 13 | +0.89% |
  | 2025 | 25 | +1.96% |
  | 2026 | 18 | +2.59% |

  2022 carries the crash notices.
- **Exits:** 0 stale exits at +1 h. At +24 h, 7 were stale and 6 legs were delisted inside the hold.

## Reading
- **Against program trials (9,472,080):** the primary is a clean null.
  - The spot +1 h variant's t of 3.07 is about one-sided p 0.003 on its own, or about 0.02 after Bonferroni over this
    lane's 8 variants. It is far from a program-wide bar (t of about 5.7).
  - It was picked out of the variants after the run, so only data no one has seen can confirm it.
- **Agreement with the old session:**
  - The old 1 h clustered t was 1.42 (fails). Here it is -0.06.
  - The old 24 h t was 2.01. Here it is 0.18.
  - Neither old horizon replicates with an hourly entry.
  - The spot/futures split was not in the old summary, so it cannot be compared.
- **A null is a result:**
  - The pooled delisting short is not an edge at hourly resolution.
  - For futures notices it is a squeeze risk: a short on a perp that is being delisted can lose almost all of its
    notional in an hour.

## Next
1. **Spot notices forward (new lane, new id):**
   - Tickets come from the notice recorder's `first_seen_utc`, which is point-in-time from 2026-10-20.
   - Short the MEXC perp at the first hourly open after detection, and cover at +1 h.
   - Spot delisting notices with a traded perp run at about 8 a year (7 in 2024, 8 in 2025, 9 in 2026 through
     September).
   - At this variant's per-notice signal-to-noise ratio (about 0.6), roughly 11 notices give an expected t of 2. That
     is about 1.3 years.
   - The hourly recorder sees a notice at about minute 6 of its hour. That matches the archive entry for notices
     released in the first minutes of an hour (19 of the 25 spot clusters). The other 6 would enter one hour later.
   - A faster listener would be a new continuous process and needs the owner's yes.
2. **Futures notices:** no lane. Shorting a perp that is being delisted carries a squeeze tail with no offsetting
   mean.
3. **Not checked:**
   - Whether `release_ms` is the true publication second for older articles.
   - Short restrictions or open-interest caps after a notice.
   - MEXC spreads on these coins after a Binance notice.
   - Upbit or other venues' notices.
