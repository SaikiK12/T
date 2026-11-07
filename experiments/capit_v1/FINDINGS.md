# FINDINGS: capit_v1 (R303). Buying capitulation: deep dips kept falling in 2024-26, and the panic-day basket is positive but too rare to prove

**Verdict: NULL** (10 trials, gate 0 on seen data). The pick fails all three validation checks.
- **Read:** frozen PREREG 59653223, committed in 811283d before the run. Run 2026-10-22 12:00 UTC with
  `scripts/run_capit.py`; all 8 inputs matched their frozen hashes.
- **The pick** was dip40 h5: each day, buy the top-150 perps whose close is at least 40% below their 25-day average,
  short the top-50 basket against them, and hold 5 days.
  - Discovery 2021-23: +670 bp per event net at 1x, t +2.08 (120 event days).
  - Validation 2024-26/09: **−450 bp per event**, t −4.58 (627 event days).
- **Every dip book lost in validation** (t −3.8 to −5.5), and the long leg alone lost too (t −2.6 to −4.0). It is not
  the hedge. In 2024-26, coins far below their average kept falling.
- **The panic-day basket** (buy the top 50 after a breadth or cascade day) beat holding the basket in both windows in
  3 of 4 books. Its best validation t is 1.55, on 59 events. That is short of the bar, as the PREREG's power section
  expected.

## Result

**All 10 books (bp per event; dip books are hedged, net of 4 sides; trigger books are net of 2 sides and of the
window's drift; t is Newey-West)**

| Book | Disc events | Disc net 1x (t) | Valid events | Valid net 1x / 2x / 3x | Valid t | Valid without 10 best | Long leg alone, valid (t) |
|---|---|---|---|---|---|---|---|
| dip20 h1 | 570 | −43 (−2.85) | 888 | −60 / −94 / −128 | −5.51 | −78 | −46 (−2.6) |
| dip20 h5 | 570 | +10 (+0.17) | 884 | −189 / −223 / −257 | −3.77 | −234 | −200 (−2.8) |
| dip30 h1 | 262 | +22 (+0.54) | 758 | −80 / −114 / −148 | −4.03 | −114 | −67 (−2.7) |
| dip30 h5 | 262 | +234 (+2.02) | 754 | −328 / −362 / −396 | −4.82 | −376 | −326 (−3.8) |
| dip40 h1 | 120 | +74 (+0.88) | 631 | −106 / −140 / −174 | −4.18 | −153 | −86 (−2.7) |
| **dip40 h5 (pick)** | 120 | **+670 (+2.08)** | 627 | **−450 / −484 / −518** | **−4.58** | −541 | −460 (−4.0) |
| breadth h2 | 24 | +14 (+0.07) | 59 | +130 / +113 / +96 | +1.28 | −59 | +123 (+1.2) |
| breadth h5 | 24 | +132 (+1.18) | 59 | +254 / +237 / +220 | +1.55 | +23 | +236 (+1.4) |
| cascade h2 | 31 | +67 (+0.54) | 22 | +171 / +154 / +137 | +1.40 | −255 | +164 (+1.4) |
| cascade h5 | 31 | −3 (−0.02) | 22 | +100 / +83 / +66 | +0.47 | −674 | +82 (+0.4) |

- **The checks on the pick:** validation t ≥ 2.0 at 1x fails (−4.58); a positive 2x mean fails (−484); a positive
  mean without the 10 best events fails (−541).
- **The pick's discovery mean was thin:** its 10 best events made 74% of the sum, and 2023 had only 4 events.
- **The exit check (pre-registered):** 8 of the pick's 2,752 validation perp-events had no close in the hold. Booking
  them at −50% instead of 0 moves the mean from −450 to −463 bp. It changes nothing.
- **SPA (consistent p, 10 books, 7-day grid):** 0.134 in discovery (best dip30 h5) and 0.074 in validation (best
  breadth h5).
- **Drift:** the top-50 basket's mean 5-day return, net of funding, was +62.6 bp in 2021-23 and −18.0 bp in 2024-26.
  The trigger books are read over it.

**Net 1x per event, by calendar year (bp)**

| Book | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| dip20 h1 | −23 | −50 | −53 | −48 | −72 | −55 |
| dip40 h5 (pick) | +212 (40) | +948 (76) | −29 (4) | −134 (74) | −495 (285) | −489 (268) |
| breadth h5 | +72 (2) | +152 (16) | +258 (6) | +213 (34) | +319 (14) | +77 (11) |
| cascade h2 | +240 (2) | +63 (19) | +87 (10) | +252 (12) | −16 (8) | +253 (2) |

Event days in brackets. The trigger books use the all-period drift in this table.

## What this shows and does not show
- **Deep-dip rebounds were a 2021-22 effect.**
  - dip20 h1 lost in every year, before costs too: it grossed −9 bp per event in discovery and −26 in validation.
    The deeper 1-day books earned in 2021-22 and lost from 2024.
  - The 5-day books paid in 2021-22 and turned negative from 2023 (dip20) or 2024 (dip30, dip40).
  - A 40% dip was a near-daily state in 2025-26 (285 days in 2025, 268 of 2026's 273), not a rare panic.
  - This matches R245: reversal books lost, and liquid names continued.
- **Not shown:** that shorting deep dips works. The sign flipped between the windows, and its validation read is now
  seen.
- **The panic-day basket is the one lead.**
  - breadth h5 was positive over the drift in all six years.
  - With 24 and 59 event days it cannot reach t 2.0 on this panel. The pre-registered power section said a
    NULL there is weak evidence.
  - It goes to unseen data only, under a new id:
    - the 2020 reserved sample (March 2020 is the archetypal breadth day, but only about 80 perps traded);
    - or forward days.
  - It is not a candidate from this lane.
- **Survivorship:** the lane uses Binance columns only, which include delisted perps (`lab/coverage.py`). No-exit
  events are rare (5-14 per dip book and window).

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side.
- **Dip books:** they lose at every level. The 1-day dip books lose before costs.
- **Trigger books:** they keep most of their mean at 3x, because they trade 2 sides once per event. Cost is not what
  holds them back; the event count is.

## Read against the program
- **Program trials:** 9,478,673 in `registry.program_trials()` before this lane; 9,478,683 with R303's 10.
- **The best validation book is not a pass:** breadth h5's t is 1.55, and its SPA p is 0.074 over these 10 books
  alone. Against nine million program trials it is not evidence. Only an unseen read can make it one.

## Next
- **M302 and M286** are TESTED, NULL on this panel.
- **New lead:** a panic-day basket (the breadth trigger, 5-day hold, read over the drift), registered for unseen data.
  It is listed in DIRECTION for reserved batch 2 and as a forward paper candidate.
