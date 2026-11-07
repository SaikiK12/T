# FINDINGS: unlocks_v1 (R265). The unlock short replicates here, at gate 0

**Verdict: REPLICATES (gate 0).** Shorting at the close of D-7 and covering at the close of an insider or
private-sale cliff unlock (at least 1% of max supply) earned +3.24% net per event at 1x. That is over 422 events on 69
Binance perps, 2021-02..2026-09. All four of the old session's gates pass.
- **Why only gate 0:** the old session read 2021-26 for this family, and the calendar is today's snapshot, not
  point-in-time. **This is not a confirmation.** Clean evidence must come from the reserved events and forward tickets
  (see "Next").
- **Registry:** R265, 10 trials. Program trials become 9,472,071. The registry has no REPLICATES verdict, so the row
  reads PARTIAL (passes its gate-0 rule, not confirmed out of sample).
- **Reproduce:** prereg sha 4c630003, frozen in commit 83554e1 before any return. Then run
  `python scripts/run_unlocks.py` (about 1 minute).
  - The runner first rebuilds the event list and symbol map from the snapshot and checks them byte for byte against
    the frozen files.
- **Execution mode:** manual-web. Two orders per event, about 2 events open on an average day since 2023, 9 at most.

## Primary (funding excluded, as in the old R179 primary)
| Cost (round trip) | Mean net per event | Median | Hit | Week-cluster t |
|---|---|---|---|---|
| 1x (20 bp) | +3.24% | +4.61% | 63.5% | 3.19 |
| 2x (40 bp) | +3.04% | +4.41% | 63.0% | 2.99 |
| 3x (60 bp) | +2.84% | +4.21% | 62.1% | 2.79 |

- **Sample:** 422 priced events, 170 weeks.
  - 108 of the 530 candidates had no market at entry, because the perp was not yet listed: 66 of them in 2021-22.
  - No position was delisted inside a hold.

## Gates (1x)
| Gate | Rule | Result |
|---|---|---|
| G1 | week-cluster t >= 2 | 3.19, pass (2x 2.99, 3x 2.79) |
| G2 | matched random-date null p < 0.05 | p 0.0005. Null mean -0.25%, null 95th pct +1.19% (2,000 reps, same perp on random days away from its unlocks). Pass |
| G3 | both halves positive | +2.10% to 2025-10-13, then +4.37%. Pass |
| G4 | positive without the top 3 perps (H, EIGEN, ZORA) | +2.38%. Pass |

## Logged variants (10 trials in all, with the primary)
| Variant | n | Mean | Week-cluster t |
|---|---|---|---|
| Net including funding (the short paid 0.43% per event on average) | 422 | +2.81% | 2.71 |
| Dose 1-2% of max supply | 246 | +1.47% | 1.21 |
| Dose 2-5% | 141 | +4.66% | 3.27 |
| Dose >= 5% | 35 | +9.94% | 4.03 |
| R181 split: unlock >= 0.82 days of ADV | 131 | +6.29% | 5.35 |
| R181 split: below 0.82 | 284 | +1.69% | 1.34 |
| Short alt, long BTC (gross) | 422 | +3.54% | 4.01 |
| Same, net of two legs at 1x | 422 | +3.14% | 3.56 |
| D-30 to D (net 1x) | 414 | +5.91% | 1.75 |
| D to D+7 (net 1x) | 415 | +0.24% | 0.25 |

- **Dose-response:** monotone in unlock size, both as a share of supply and relative to volume, as in the old session.
- **Market exposure:** the BTC-hedged version is stronger (t 4.0), so the effect is not short market beta.
- **After the unlock:** the drift ends on the unlock day. The week after is flat.

## Risk: the tail is large
- **Per-event spread:** sd 16.7%. 1st percentile -41.9%; 99th percentile +41.9%.
- **Six events lost more than 40% gross (short squeezes):**

  | Day | Perp | Gross loss | Funding |
  |---|---|---|---|
  | 2026-01-22 | RIVER | -132% | -45% |
  | 2026-09-27 | GRASS | -81% | |
  | 2025-05-12 | BB | -57% | |
  | 2025-08-14 | CYBER | -50% | |
  | 2025-11-13 | STRK | -42% | |
  | 2021-04-30 | ALPHA | -41% | |

  - The old go-real rule ("no event loses more than 40% unlevered") would already have failed six times in this
    archive.
  - **Seen after the run, not tested:** all six had unlock/ADV below 0.82.
- **Funding:** the short pays funding on average, -0.43% per event. On crowded events it is extreme (RIVER -45% in a
  week).
- **Sizing:** any forward or real version needs a per-event size cap and a written plan for squeezes. That is decided
  in the next PREREG, not here.

## Robustness (not counted)
- **Ticker check:** verified only, +3.22% (n 408, t 3.14); unverified, +3.80% (n 14).
- **Per year:**

  | Year | n | Mean | Note |
  |---|---|---|---|
  | 2021 | 11 | -4.33% | |
  | 2022 | 16 | +5.18% | |
  | 2023 | 41 | +2.56% | |
  | 2024 | 52 | +2.14% | |
  | 2025 | 134 | +3.86% | |
  | 2026 | 168 | +3.56% | t 2.46 |

  The 2021 sample is small and negative. Most of the evidence is 2025-26, when most unlocks had a perp.

## Reading
- **Against program trials (9,472,071):** a Bonferroni bar over the whole program would need t of about 5.7, and this
  t is 3.19.
  - The program count is mostly correlated atlas cells. This lane is a pre-specified replication of an independent
    old-session rule with fixed parameters.
  - Still, it is evidence to continue, not evidence to trade.
- **Agreement with the old session:**
  - This replication: +3.24%, t 3.19, null p 0.0005, on 422 events from a fresh calendar pull and a fresh symbol map.
  - Old session: +2.50%, t 2.43, null p 0.002, 414 events.
  - The two share years, so this is not independent of the old read.
- **Point-in-time risk:** the calendar can have been corrected after the fact. Old events that were rescheduled
  or added later would flatter this. The daily recorder (from 2026-10-20) removes that risk for forward events only.

## Next
1. **Forward MEXC paper lane** (new PREREG, new id):
   - events come from the daily recorder snapshots (point-in-time);
   - tickets are frozen at D-7;
   - a per-event size cap and a squeeze rule are fixed before the first ticket.
   - About 40 events are due before 2026-12-31.
2. **First reserved batch:** this frozen rule on reserved_2020 (30 events), reserved_mexc (41) and post_archive (15).
   Expect power of only about t 1.8 there at the archive's per-event signal-to-noise ratio.
3. **Not checked:**
   - MEXC spreads on thin unlock coins (R224's recorder covers only 32 contracts);
   - borrow and short restrictions around unlocks;
   - the actual timing of each unlock within day D (the exit is at the close of D, whatever the hour);
   - calendar revisions.
