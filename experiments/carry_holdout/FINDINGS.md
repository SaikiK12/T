# FINDINGS: carry_holdout (R191)

**Verdict: CONFIRMED by the frozen rule (net > 0, t 2.07), economically small.** The carry kept working but there was
little positive funding to collect in 2025-07..2026-09.

- **Registry row:** R191 (trials: 1)
- **Reproduce:** prereg sha 132c120c; `python scripts/run_carry_holdout.py` (run once, 2026-10-18).

## Numbers (457 days)
| variant | net total | net / yr | Sharpe | NW t | max DD | invested | avg open |
|---|---|---|---|---|---|---|---|
| primary (spot 10 bp, 1x) | +1.45% | +1.2% | 2.5 | 2.07 | 0.07% | 25% | 0.42 |
| 2x costs | +0.66% | +0.5% | 1.2 | 1.14 | 0.22% | 25% | 0.42 |
| spot 5 bp | +1.67% | +1.3% | 2.8 | 2.26 | 0.04% | 25% | 0.42 |

Funding +1.44%, basis +0.80%, costs -0.79% (primary). The mean trailing funding of top-50 perps in the window was
negative: longs were not paying, so positive carry was scarce.

## Reading
Carry is real and robust in sign, but it is a "works for a time" strategy: +35% in 2021, about 0 in 2022-2023, +8% in
2024, about 1%/yr since. Its size is set by the funding regime, which a forward monitor can read in real time.

## Next
Forward paper monitor of the frozen rule (no real money without `lab.gate.go_real`). A reverse-carry lane (long perp,
short borrowed spot when funding is negative) is a separate idea and needs its own registration and forward data.
