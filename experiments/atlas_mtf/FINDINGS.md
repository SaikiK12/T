# FINDINGS: atlas_mtf (R195), fast signals under the coin's slower state

**Verdict: CONFIRMED (in-sample, gross).** The coin's own 4 h / 24 h state (trend, range, RSI, structure, volatility,
volume, funding, premium) changes how its 1 h signals pay, and those lifts replicate at 54% against a 6.7% placebo
baseline. Some 431 excess (market-neutral) conditional edges stay above 1x round-trip cost in validation.

- **Registry row:** R195 (trials: 643,736 real discovery lift cells passing the filters)
- **Reproduce:** prereg sha d701ea89; `python scripts/run_context_atlas.py discovery|flag|validation|report --lane
  atlas_mtf --families mtf --base 1h`. Discovery was interrupted at context 6/18 by a container restart and resumed per
  context (finished contexts are skipped; nothing was recomputed with other settings).

## Decision table (discovery 2021-2023 -> validation 2024-2025H1)
| family | CL | replicate | placebo CL | placebo replicate | SIGNAL |
|---|---|---|---|---|---|
| mtf | 55,592 | 54.3% | 4,515 | 6.7% | yes |
| of which raw | 49,449 | 57.2% | 3,993 | 7.1% | |
| of which excess | 6,143 | 31.6% | 522 | 4.2% | |

The contexts are the coin's own state, so there is no market-wide timing to subtract (the decomposition is not needed).

## Conditional edges above cost
| measure | CCE (disc.) | replicate 1x | 2x | 3x | placebo 1x |
|---|---|---|---|---|---|
| raw | 13,466 | 7,564 | 5,506 | 3,716 | 17 |
| excess | 1,511 | 431 | 232 | 131 | 2 |

Excess CCEs replicated at 1x by horizon: 120 at 1 h, 238 at 4 h, 39 at 12 h, 34 at 24 h; median validation edge 23, 35,
53 and 63 bp against a 14 bp round trip. The contexts that carry them: the daily and 4 h RSI (102 of 232 at 2x), the
4 h EMA cross (32), the 4 h Donchian position (31). Patterns, in validation:
- **Exhaustion**: a coin overextended on 1 h (ema_ratio[8] bin 6, Bollinger z bin 7) while its 4 h EMA cross is at its
  most stretched (z bin 6) trails the market by about 95-115 bp over 24 h.
- **Dip in a strong trend**: a coin oversold on 1 h (ema_ratio[21] bin 0) while its daily RSI is in the top bucket
  leads the market by about 117 bp over 4 h.

## Cost sensitivity
In the table (1x, 2x, 3x).

## What this does not show
As atlas_ctx: day-weighted means over the state's hours, rare states, a large trial count; per-entry and book-level
results are the next lane's job.

## Next
Joint slice-book lane with atlas_ctx's replicated excess CCEs (holdout unspent for these cells).
