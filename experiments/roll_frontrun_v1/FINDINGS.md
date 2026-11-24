# FINDINGS: roll_frontrun_v1 (R529). Front-running the commodity index roll does not pay in CME calendar spreads, 2010-2026: NULL

**Verdict: FAIL** (NULL).
- The monthly mean is +0.97 bp at 2 bp of cost (NW t 0.24). It is −1.03 bp at 4 bp, and the halves are −0.9 / +2.8 bp.
- **Registry:** R529, 1 trial (method M562). Program trials become 9,785,791.
- **Reproduce.** The PREREG (sha 03a55377) was frozen in commit ae202dbc before any spread return was computed.
  `run_roll_frontrun.py run` ran once on 2026-11-24, on R505's held settlements (manifests pinned).
- **Forecast before the freeze:** P(PASS) ≈ 15% (prior 0.25, power about 0.6). It is the first forecast written
  under L031's rule.

## Results (long the next contract, short the one expiring in m+1, per unit of one leg's notional; monthly mean over roots)
| Window | 2 bp | 4 bp | 6 bp | NW t at 2 bp | Hit rate |
|---|---|---|---|---|---|
| **Full: last settlement before m → 9th settlement day (decided)** | **+0.97** | −1.03 | −3.03 | 0.24 | 48% |
| Pre-roll: → 4th settlement day | −1.74 | −3.74 | −5.74 | −0.66 | 48% |
| Roll: 4th → 9th settlement day | +0.32 | −1.68 | −3.68 | 0.10 | 49% |
| Energy only (CL, HO, RB, NG), full window | +1.25 | | | 0.24 | 51% |

- **Events:** 1,250 in 195 months (about 6.4 roots a month): CL 63, HO 141, RB 165, NG 99, GC 97, SI 80, HG 82, PL 66,
  ZC 81, ZS 95, ZW 81, LE 97, HE 103.
- **By root** (bp per event at 2 bp): CL −2.4, HO −7.6, RB +5.1, NG +1.5, GC −1.5, SI −0.4, HG +0.4, PL −1.0, ZC +10.4,
  ZS +11.8, ZW −15.3, LE +5.2, HE −0.3. No commodity group shows a consistent sign.
- **By year** (bp): swings from −28.7 (2018) to +36.9 (2021), with no trend and no early-years premium.
- **Annualized:** +0.12%/yr on one leg's notional at 2 bp, against cash at 4.1%/yr. Nothing to trade.

## What it means
- **The mandated, announced roll leaves no front-running premium at the settlement level after 2010.**
  - The spread does not widen ahead of the roll window, nor during it.
  - This fits arbitrage capital absorbing a fully public schedule, and the CFTC note that index money now rolls in
    more ways.
- **The payer exists, but someone is paid first.** A structural payer is necessary but not sufficient. A public
  calendar with deep markets gets competed away. The funding-design gap still pays because each leg needs its own
  margin on venues that institutions avoid. Here, both legs sit on one exchange with spread margining.

## What could invalidate this
- **Settlements only.** An intraday effect inside the 5-day window, or one before the last month-end, would not show.
  - The pre-roll window is negative, so an earlier start is unlikely to help.
- **The generic contract rule** may pick a non-index month for some roots. CL has thin coverage (63 events), because
  its m+2 contract is often outside the top three by open interest.
- **Seasonal noise** in grains and natural gas is large, and the per-root standard deviation is about 1.5% over 9
  days. A 5-10 bp effect would need more events to see.

## Pre-mortem against outcome
| Prediction before the freeze | What happened |
|---|---|
| 1. Arbitraged away after 2010 | Yes: no premium in either window |
| 2. Wrong B for some roots | Possible; no root shows a stable sign either way |
| 3. Seasonal noise | Yes: large by-root and by-year swings |
| 4. Thin CL coverage | Yes (63 events); energy-only also ≈ 0 |
| 5. Costs above a tick | Irrelevant: the gross is about 3 bp |
