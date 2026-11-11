# FINDINGS: asiaclose_v1 (R468)

**Verdict: PASS by the frozen rule (gate 0), recorded as PARTIAL. B carries no effect.** Fading the perp's move over
the home exchange's weekday-night closure paid +87.8 bp per event in A (April-August 2026, p 0.034). In B
(September-November) it paid +9.5 bp (p 0.71, median -0.1, hit 50%). B's mean clears the frozen bar (> 1 cost unit,
same sign), so the rule says PASS. The diagnostics below say the A effect did not carry into B.

Run: `python scripts/run_asiaclose.py`, 2026-11-11, after the freeze (PREREG sha256 `72983781`, commit `03ff9c62`).
- The PREREG verified and its 10 inputs matched.
- 36 bar and funding files matched `data/asiaclose/manifest.json`.
- The bars were fetched after the freeze by the frozen `scripts/fetch_asiaclose.py bars`. Provenance is in
  `docs/provenance/asiaclose.json` (combined sha256 `53181cef…`).
  - xyz's Korean markets have about 4,980 candles each, from 2026-04-18 (Hyperliquid's 5,000-candle limit).
  - Lighter's KIOXIA returned only 150 candles.
- **Events:** A night 586, A gap 180, B night 503, B gap 139.
- **Skipped:** 800 not yet listed, 2 at Kioxia's split, 191 unpriced.

## Decision cell: both venues, weekday nights, |W| ≥ 50 bp, exit X1 (an hour into D's session)
| sample | n | days | mean bp | sd | hit | p (day clusters) | MDE80 | unit |
|---|---|---|---|---|---|---|---|---|
| A (D 04-27..08-31) | 527 | 65 | +87.8 | 493 | 57% | 0.034 | 60 | 5.05 |
| B (D 09-01..11-10) | 413 | 41 | +9.5 | 304 | 50% | 0.71 | — | 5.13 |

- **A's side is fade.** B has the same sign and |mean| > 1 unit, so the frozen state is PASS.
- **Costs, A net of 1x / 2x / 3x units:** +82.7 / +77.7 / +72.7 bp. B's nets are +4.4 / -0.8 / -5.9 bp.
- The units are assumed: 4 bp slippage, plus xyz's growth-mode fees. These Asian books were never measured.

## The grid (52 cells)
- **A:** 51 of 52 cells have a positive mean; 28 have p ≤ 0.05.
- **B:** 39 of 52 cells are positive; 1 has p ≤ 0.05 (both/night/50/x1/SSE, 38 events).
- **Gap openings** (Mondays and after holidays, `both/gap/50/x1`): A +119 bp (p 0.004), B +58.5 bp (p 0.27).
- **By venue (decision configuration):**
  - xyz: A +75.0, B +16.5;
  - Lighter: A +105.6, B -2.4.
- **By exchange (diagnostic cells):**

  | exchange | A n | A mean | A p | B n | B mean | B p |
  |---|---|---|---|---|---|---|
  | KRX | 330 | +54.5 | 0.12 | 168 | -13.0 | 0.69 |
  | TSE | 49 | -76.5 | 0.27 | 58 | -20.1 | 0.62 |
  | HKEX | 130 | +232.4 | 0.037 | 149 | +25.3 | 0.57 |
  | SSE | 18 | +101.3 | 0.21 | 38 | +91.7 | 0.024 |

- **A leans on two Hong Kong AI listings:** ZHIPU +331 bp over 61 events, MINIMAX +112 over 53.

## Post hoc (not pre-registered; reported, not used for the verdict)
- **Robust centres of the decision cell:**
  - A: median +61.5, 5% trimmed mean +81.8;
  - B: median -0.1, trimmed mean +8.8.
- **Without ZHIPU and MINIMAX:** A +48.7 bp (p 0.12), B +6.6 (p 0.80).
- **Entry bounce ruled out in A.** With W taken an hour before E (entry still at E), A gives +94.8 bp (p 0.015) and
  B -1.3 bp (p 0.96). The A effect is therefore not a last-trade bounce at E.
- **Slope** of the E→X1 move on W: A -0.12 (correlation -0.10); B -0.04.
- **The two venues are one sample.**
  - The same stock on xyz and Lighter: W correlation 0.97 over 367 shared openings.
  - Fade-return correlation: 0.83.

## Reading
- **Read against 9,785,237 program trials,** a p of 0.034 on one cell is weak. The frozen bar for B (same sign,
  > 1 unit) was too loose to tell decay from persistence. B's median is zero.
- **The pattern matches M515 on Lighter.** R465's unseen months (C) also gave nothing at the decision exit.
  - A large effect in one stretch of 2026 has not held in the next.
  - The decay could be from listing-era volatility (the Hong Kong AI listings) or from changed oracle sessions.
  - Neither cause is tested here.
- **The two venues add no independent evidence** (W correlation 0.97).

## What this changes
- **M526** is TESTED: a gate-0 PASS by the frozen rule, with a confirmation sample that shows no effect.
- **The stop rule earns a forward paper lane** under a new id, with tickets at E and recorded book costs. Because B
  is flat, a forward lane would test persistence after decay, not a live edge. It needs a futility read early.
- M515 and its forward lanes (R463, R467) are unaffected.
- No orders, no money. Nothing here is a trade.
