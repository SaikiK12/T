# FINDINGS: atlas_v1 (R185)

**Verdict: CONFIRMED in-sample, gross.** The atlas finds far more confident gross edges than its placebo, and about
half of them replicate on 2024-2025H1 against 9% (main+clock) and 0% (flow) for placebo picks. The edges are gross:
mostly directional short-horizon mean reversion, mostly below the round-trip cost per trade.

- **Registry row:** R185 (trials: 338,240 cells = 299,740 main+clock + 38,500 flow)
- **Reproduce:** prereg sha bd459f37; `python scripts/run_atlas.py discovery|validation --tensors main,clock` and
  `--tensors flow`; `python scripts/atlas_replication.py main+clock|flow`. Discovery lists frozen before validation
  (sha in results/validation_*_hashes.json).

## Numbers
Confident gross edges (CGE, "all" group) in discovery, real vs the two placebo passes:

| tensor | grouping pass | CGE real | CGE placebo | conditional cells |
|---|---|---|---|---|
| main+clock | session | 956 | 57, 53 | 3,947 |
| main+clock | tier | 896 | 86, 49 | 4,351 |
| main+clock | regime | 821 | 109, 53 | 1,606 |
| flow | session | 28 | 0, 1 | 165 |
| flow | tier | 43 | 1, 1 | 119 |
| flow | regime | 33 | 1, 0 | 7 |

Replication on validation (same sign and |t| >= 2):

| | main+clock | flow |
|---|---|---|
| CGE, real | 47.6% (2,673 list rows; 1,020 distinct cells: 45%) | 35.6% (104 rows; 44 cells) |
| CGE, placebo picks | 9.1% (407) | 0% (4) |
| conditional cells | 51.3% (9,904) | 33.7% (291) |
| same sign, CGE | | 91% |

**By kind.** Raw (directional) CGEs replicate 67%, 73%, 73%, 64%, 52% at h 1, 4, 12, 24, 72; excess (long the cell,
short the universe) 15%, 5%, 3%, 4%, 6%. By family (distinct cells): prevday 91%, prevday_raid 6/6, dayopen 79%, rsi 71%,
asia 71%, breadth 67%, ema_ratio 64%, bbz 59%, sweep 57%, ret 56%, donch 56%, clv 56%, atrp 55%, fvg 51%, struct 41%,
ema_cross 38%, btc_ret 26%, prem 23%, ribbon 18%, ob 9%, volz 3%, tbi 1%, fund 0%. Clock views pass nothing on their own.

**Where.** Conditional cells by group: liquidity tier top 10 84%, rank 11-25 72%, rank 26-50 75%; sessions Europe 60%,
US open 49%, Asia 38%, weekend 33%, US afternoon 24%, US evening 9%; BTC up and volatile 69%, up and calm 48%, down and
calm 15%.

**Size.** Replicated CGEs have a validation edge/cost (day-weighted) of median 3.25, 79% above 1. Per trade, counted
once per episode, the same cells earn a median 11 bp before costs in discovery and 5 bp in validation (maker_v1), under
the 12-16 bp round trip of the top 50: the day-weighted average overweights quiet days with few signals.

**Order flow (44 distinct CGEs).**
- Open interest vs price, raw: after a 24 h rise, with open interest falling (shorts covering) or rising (new longs),
  the next 12 h return is -61 / -56 bp in discovery and -63 / -55 bp in validation (t -5.4 / -4.8; edge/cost 3.8-4.4).
  Both quadrants agree, so the open-interest part adds little to the price reversal itself. 1 h and 4 h versions
  replicate too (-5 to -30 bp).
- Taker flow and positioning, excess at 72 h: the symbols with the most taker selling over 24 h trail the universe by
  -57 bp (discovery) and -37 bp (validation) over the next 72 h; those whose top traders are more short than the crowd
  by -54 / -40 bp (edge/cost 2.6-2.8 in validation). The other excess flow cells keep their sign (crowd and top-trader
  long/short extremes) but lose significance.
- Order-book depth (30 symbols from 2023) passes nothing in discovery (one year of data).

## Cost sensitivity
This lane is gross by design. Edge/cost at 1x: median 3.25 (day-weighted), so the median replicated cell would still
cover 2x and 3x costs on that measure; per trade it covers none (see maker_v1). The 72 h flow cells (edge/cost 2.6-2.8)
are the exception that keeps a margin at 2x per trade-day.

## What this does not show
- Gross, and day-weighted; overlapping hours of one episode count many times. Per-trade sizes are smaller.
- Raw cells include market timing: a long book of them is long beta (pack_v1).
- The three grouping passes repeat the "all" cells; list rows repeat across them, distinct-cell numbers are given.
- Flow metrics cover 84% of tradable hours; book depth 24% and only 2023 onward.

## Next
Context lifts (atlas_ctx R192, atlas_mtf R195); the 72 h flow excess cells as a neutral book.
