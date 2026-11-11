# FINDINGS: xvwknd_v1 (R466), the trade.xyz-versus-Lighter Sunday gap on the same stock

**Verdict: INCONCLUSIVE.** On Sunday evening the two venues' prices of the same stock sit close together, so the
decision cell (|G| ≥ 25 bp) has only 55 events in sample A, under its frozen floor of 100. M524 earns no forward lane.

- **The gap is small.** Over 487 market-weekends in A, the median |G| at 19:00 New York is 7.6 bp; 90% of gaps are
  under 30 bp.
  - The two venues' weekend moves correlate at 0.96 (R465's comparison).
  - The order books of the two venues are therefore close to arbitraged over the weekend.
- **The gaps that exist do close, but they look like last-trade noise.**
  - **Closure in A** (positive mean, hit rate 67-91% in every cell):
    - θ 10: +21.3 bp at X1 (p < 0.001);
    - θ 25: +47.4 bp at X1;
    - θ 25, the decision exit X2: +50.1 bp.
  - **The persistence diagnostic:**
    - only 33 decision-cell events had a fresh gap an hour earlier;
    - G(E - 1 h) and G(E) correlate at 0.25;
    - only 7 kept the same sign at |G| ≥ 25 bp.
  - **Reading:** a real gap between two books would persist from one hour to the next. A large closure with high hit
    rates and little persistence is the stated bounce bias: two last trades up to 59 minutes apart, each on one side
    of a weekend spread.
- **B does not hold the effect.**
  - θ 10: +10.4 bp at X1 (p 0.16) and +1.9 bp at X2 (p 0.97).
  - θ 25: X2 is -34.5 bp over 20 events.
- **The cheap end nets about zero.** Over all gaps (θ 0, X1), A's +11.1 bp barely covers the 10.7 bp unit.

Run: `python scripts/run_xvwknd.py`, 2026-11-11, after the freeze (PREREG sha256 `425dc594`, commit `43f43fbd`).
- The PREREG verified and its 13 inputs matched.
- 152 xyz files and 100 Lighter files matched their manifests (`results/run.log`).
- R465 ran just before, on the same Lighter data; this lane's code was frozen before either run.
- **Events:** A 487, B 212.
- **Skipped:**
  - 405 where one venue listed the market less than 7 days before Friday;
  - 96 without a fresh trade on both venues at E.

## Cells (bp per market-weekend, pair return before costs)
| θ | exit | n A | wk A | mean \|G\| | mean A | sd A | hit A | p A | unit | net 1x A | n B | mean B | p B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | X1 | 452 | 18 | 11.7 | +11.1 | 24 | 75% | <0.001 | 10.7 | +0.4 | 198 | +4.4 | 0.06 |
| 0 | X2 | 480 | 18 | 12.8 | +9.2 | 43 | 67% | 0.001 | 10.7 | -1.5 | 209 | +3.8 | 0.53 |
| 10 | X1 | 179 | 18 | 22.8 | +21.3 | 30 | 86% | <0.001 | 10.7 | +10.6 | 53 | +10.4 | 0.16 |
| 10 | X2 | 191 | 18 | 25.4 | +24.2 | 51 | 80% | <0.001 | 10.8 | +13.4 | 62 | +1.9 | 0.97 |
| 25 | X1 | 46 | 17 | 44.3 | +47.4 | 43 | 91% | <0.001 | 10.5 | +36.9 | 16 | +15.4 | 0.31 |
| 25 | X2 (D) | 55 | 17 | 50.1 | +50.1 | 75 | 84% | <0.001 | 11.3 | +38.9 | 20 | -34.5 | 0.63 |
| 50 | X2 | 18 | 11 | 78.3 | +95.0 | 76 | 94% | 0.001 | 12.5 | +82.5 | 9 | -120.7 | 0.44 |

- **The decision cell is marked (D).** It fails A's size floor (55 < 100), so the frozen verdict is INCONCLUSIVE,
  whatever its p.
- **Costs:** the unit is 9.8 bp in growth mode, 26 bp for MSTR, STRC and BMNR. 2x and 3x subtract two and three units
  (`results/cells.csv`).
- **Biggest gaps by market** (median |G| in A): ASML 93 bp, BMNR 53, RKLB 33. Most large-cap names sit under 10 bp.

## What this changes
- **M524 stays without a forward lane** (frozen rule: INCONCLUSIVE earns none). The last-trade evidence cannot tell a
  tradable gap from bounce.
  - Book walks on both venues at Sunday 19:00 would settle it.
  - If a Lighter forward lane for M515 records Lighter books at E, its records and R463's xyz book walks at the same
    instant would give that comparison at no extra cost.
- **R465's 0.96 correlation and this lane agree.** The weekend overshoot is common to both venues, so it is a
  property of how weekend stock-perp prices form, not of one venue's oracle.
- **Read against the program's 9,785,184 trials.**
