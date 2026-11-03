# FINDINGS: forcedswitch_v1 (R388). NULL

**Verdict: NULL** by the frozen rule (PREREG sha 4ed886f5…). Run once on 2026-11-03 with
`python -I scripts/run_forcedswitch.py`. Outputs are in `results/summary.json` and `results/events.csv.gz`.
1 of 387 primary events has a missing price.

## Primary (h = 8 h after entry at T + 1 h)

| Era | Events | Coins | Gross | Funding | Net 1x | Net 2x | Net 3x | Hit 1x |
|---|---|---|---|---|---|---|---|---|
| pre (no switch) | 175 | 100 | −224.4 | +195.6 | −68.7 | −108.7 | −148.7 | 40% |
| post_switched | 211 | 159 | −58.8 | +296.2 | +197.4 | +157.4 | +117.4 | 40% |
| post_not_switched (reported) | 8 | 8 | +202.6 | +210.9 | +373.5 | +333.5 | +293.5 | 60% |

All values are bp per event. The costs are 40 / 80 / 120 bp round trip, R273's.

**Checks (all needed):**
- **1 FAILS.** post − pre gross is +165.6 bp, but its t is only 0.72.
- **2 and 3 pass.** The post 2x net is +157.4 bp and the 3x net is +117.4 bp.
- **4 FAILS.** The halves are +405.6 bp and −8.9 bp.
- **5 FAILS.** The trimmed mean is −104.7 bp.
- **6 passes.** Leave-two-coins-out is +18.4 bp.

## Reading
- **The prediction did not hold.** After a switch print, price still falls on average (−59 bp over 8 h), less than
  after a pre-rule print (−224 bp). The difference is far from significant.
- **The long earns its money from funding.** It collects 3-4 hourly floor settlements, about +296 bp over 8 h.
- **The positive post-rule mean is a tail.**
  - The median 1x net is −174 bp, and the hit rate is 40%.
  - The five best events are 175% of the total. NFP, TRUST and SIREN alone sum to more than +49,000 bp.
  - The trimmed mean is −105 bp, and the later half is negative.
- **What it amounts to.** It is a lottery on short squeezes after hourly floor prints. It is not a reproducible edge
  at 40 bp a round trip.

## Other horizons (reported, not decided)

| h | Era | Gross | Funding | Net 1x | Net 2x | Net 3x |
|---|---|---|---|---|---|---|
| 4 | pre | −84.9 | +79.3 | −45.6 | −85.6 | −125.6 |
| 4 | post_switched | −86.4 | +177.2 | +50.8 | +10.8 | −29.2 |
| 24 | pre | −242.0 | +461.5 | +179.5 | +139.5 | +99.5 |
| 24 | post_switched | −109.2 | +601.0 | +451.8 | +411.8 | +371.8 |

- **The 24 h post_switched mean is large** but has the same tail shape (se of gross 274 bp). It was not decided on and
  is not evidence: a follow-up on it would be a new lane on seen data.

## Against the program
- The program had 9,784,326 trials before this lane (`registry.program_trials('registry/rounds.csv')`). This lane adds
  3.
- A t of 0.72 on the primary contrast is nowhere near any program-wide bar.

## Not checked
- Fills and slippage beyond R273's 40 bp at floor prints. These books are often thin and gappy at the floor.
- The cap state of each coin, which changed before the rule on some alts.
- Liquidation and margin paths of a long held across hourly floor prints.
- Gate 0 on seen data (R273, M261, M458, R387): even a PASS would not have been evidence.
