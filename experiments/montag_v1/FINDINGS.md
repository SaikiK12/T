# FINDINGS: montag_v1 (R269). The Monitoring Tag short is NULL at +1 h. The +24 h variant is a forward candidate

**Verdict: NULL (gate 0).** Shorting the perps of coins Binance adds to its Monitoring Tag at the first hourly open
after the notice, and covering an hour later, earned +0.61% per notice at 1x (t 0.71; 24 notice clusters, 86 legs,
2023-10..2026-09).
- **Gates:** G1 (t >= 2.0) fails. G2 (both halves), G3 (2025+) and G4 (matched null, p 0.0005) pass.
- **Two logged variants clear G1-G3: +24 h unhedged** (+4.36% per notice, t 3.81) **and +24 h BTC-hedged** (+3.86%,
  t 3.26). They are 2 of 6 logged variants, so they are not a pass. Under the PREREG they are a reason for a new
  frozen lane (see "Next").
- **But the effect fades in 2026:**
  - 2026 has 11 of the 24 clusters, and its +24 h mean is only +1.31%.
  - The 5 clusters from 2026-06 average -0.92%.
- **Registry:** R269, 6 trials. Program trials become 9,477,562.
- **Reproduce:** prereg sha 08cb8e4c, frozen in commit e00c871 before any price was read. Then run
  `python scripts/run_montag.py` (about 10 s).
  - The runner checks the catalog and leg hashes, and rebuilds `legs.csv` byte for byte.
- **Execution mode:** API. The entry follows the notice within the hour. The notices so far came out between 02:00
  and 11:00 UTC.

## Sample
- **Notices:** 27 Monitoring Tag notices give 149 legs.
  - The tag sample is 24 notices and 97 legs (archive window, archive perp).
  - 11 legs had no traded perp at t0 (`no_market`).
  - **Priced:** 86 legs in 24 clusters (one notice each).
- **Exits:** none stale and none delisted in the hold, at any horizon.
- **Timing:** the tag started in 2023-07, so there is no 2020 notice, and no reserved data was read.
  - 19 of the 24 clusters are from 2025-26.
  - Most notices are released in the first seconds of an hour (median minute 0).

## Primary and logged variants (one observation per notice cluster, n 24)
| # | Exit | Line | 1x mean | t | 2x mean | 3x mean | Median | Hit | Halves | 2025+ (n 19) | G1-G3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **+1 h (primary)** | short | +0.61% | 0.71 | +0.21% | -0.19% | +0.38% | 62% | +0.11 / +1.11 | +0.72% | fail (G1) |
| 2 | **+24 h** | short | **+4.36%** | **3.81** | +3.96% (t 3.46) | +3.56% (t 3.11) | +2.77% | 75% | +6.82 / +1.90 | +4.31% | **pass** |
| 3 | +72 h | short | +3.66% | 1.29 | +3.26% | +2.86% | +5.44% | 75% | +10.27 / -2.96 | +2.69% | fail |
| 4 | +1 h | BTC-hedged | +0.44% | 0.51 | -0.06% | -0.56% | +0.43% | 58% | -0.13 / +1.00 | +0.61% | fail |
| 5 | **+24 h** | BTC-hedged | **+3.86%** | **3.26** | +3.36% | +2.86% | +2.29% | 71% | +7.00 / +0.73 | +3.61% | **pass** |
| 6 | +72 h | BTC-hedged | +4.33% | 1.54 | +3.83% | +3.33% | +5.42% | 83% | +10.84 / -2.19 | +3.53% | fail |

- **G4 null (primary):**
  - Same perps, same hour of day, on a random day 7-60 days before the notice. All 24 clusters had at least 10
    admissible days.
  - Null mean -0.49%, 95th percentile -0.16%, observed +0.61%, p 0.0005.
  - So the hour after the entry beats an ordinary hour of the same coins. But at +1.01% gross (t 1.18) it is too
    small and too noisy to pay 40 bp.
- **Costs:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x, with funding settled in the hold.
  - Funding is about 0 at +1 h. It costs the short 0.14% at +24 h and 0.49% at +72 h, because shorts crowd into
    tagged coins.

## +24 h by year (1x, reported, not counted)
| Year | Clusters | +1 h | +24 h | +72 h |
|---|---|---|---|---|
| 2023 | 1 | -1.59% | -0.77% | -2.31% |
| 2024 | 4 | +0.63% | +5.86% | +9.72% |
| 2025 | 8 | -0.20% | +8.45% | +11.47% |
| 2026 (to 09) | 11 | +1.39% | +1.31% | -3.69% |

- **2024-25 are strong at +24 h.** Each of their 12 clusters but one was positive, and the best ones gained +11-21%
  (BAL, STMX/TROY, GPS).
- **2026 is weak.** Its clusters are larger (2-9 coins), and its last 5 (2026-06..09) average -0.92% at +24 h.
- **+72 h carries squeezes:**
  - 2026-03-06 (9 coins): -18.6%.
  - 2026-07-03 (SCRT, VANRY): -46.7%.

## Robustness (not counted)
| Check | n | Mean | t |
|---|---|---|---|
| +1 h without the top 3 legs | 24 | +0.39% | 0.50 |
| +24 h without the top 3 legs | 24 | +3.32% | 3.81 |
| +72 h without the top 3 legs | 23 | +1.29% | 0.49 |
| Gross +1 h | 24 | +1.01% | 1.18 |
| Gross +24 h | 24 | +4.90% | 4.14 |
| Gross +72 h | 24 | +4.54% | 1.66 |
| The move the entry cannot catch (close before the notice's bar to the entry, short sign) | 24 | +5.55% | 3.92 |

- **The notice's own hour falls hardest.** Because most notices come out at minute 0, the hourly entry waits about
  an hour, and that hour fell 5.55% on average. A listener that enters within minutes could catch part of it, but
  this archive cannot price that.
- **Post hoc (computed after the run, not a gate, not counted):** R267's matched null at +24 h.
  - Null mean -0.30%, 95th percentile +1.25%, observed +4.36%, p 0.0005 (seed 2691).
  - So the +24 h fall is not the ordinary drift of these coins.
- **Untag notices, long (descriptive):** 5 notices, 5 legs. Gross +1.70% at +1 h, -2.61% at +24 h, -4.07% at +72 h.
  Coins that leave the tag keep falling after the first hour. That is too few to read.

## Reading
- **Against program trials (9,477,562):** a t of 3.81 is far below any program-wide bar. Bonferroni over the 6
  variants alone gives about p 0.003 one-sided. The variant is the best of 6 on a family the lab chose because
  R267's spot notices worked.
- **It is consistent with R267.** Binance's own warning about a coin is followed by a further fall after the first
  hourly open: at +1 h for spot delisting notices (R267), and over +24 h for tag notices (here).
- **The fade in 2026 is the main risk.** The edge may have been learned and arbitraged away (bots that short on the
  notice itself), or 2026's larger batches of tagged coins may simply be noisier. Only forward data can tell.
- **No unread sample can confirm it.** The tag began in 2023-07, inside the archive.
  - The MEXC-only coins are not tagged by Binance (they have no Binance listing).
  - Forward notices are the only clean test.

## Next
- **Forward lane (new id, frozen before its first ticket):** short the MEXC perp of each newly tagged coin at the
  first hourly open after the recorder sees the notice, and cover at +24 h. It is modelled on R268.
  - The notice recorder (`scripts/record_notices.py`) already journals the news catalog every hour with
    `first_seen_utc`.
  - About 10-12 notices a year, so a decision at 12 notices takes about a year.
- **Methods:** M260 (new; Claude's method block is M260-M279, after Codex's M234-M251 in PR #33): the Monitoring Tag
  short, PARTIAL (R269).
