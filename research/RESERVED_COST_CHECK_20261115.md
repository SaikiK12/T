# The reserved-sample PASSes, priced at measured cost (2026-11-15)

Reproduce: `python scripts/reserved_cost_check.py` → `research/reserved_cost_check_20261115.json`.
No download, no reserved read, no strategy test. This prices **already-published** nets against
**already-recorded** costs.

## Why this is the binding question

Three reserved-sample batches have run. Every PASS came with the same caveat, in its own FINDINGS:

> "Costs are not measured on these books. The coins are thin. ... The next step is to measure those
> book costs on KuCoin and MEXC for the 18 eligible contracts **before the lane is written**."
> — `experiments/reserved_batch2/FINDINGS.md`

`R404 book_costs_v1` is now recording exactly that (7 snapshots, 57 dYdX + 715 KuCoin + 577 MEXC
contracts, last 2026-11-15 00:20 UTC). So the blocker can be answered today, without spending a
fourth reserved read.

## The answer

| book | verdict | net 1x | bp/day on book capital | worst measured band |
|---|---|---|---|---|
| R286 C14 binance+gate | PASS | +2.86%/yr | 0.784 | **not recorded** (R404 covers dYdX/KuCoin/MEXC only) |
| R391 KuCoin+dYdX+Lighter+MEXC | PASS | +2.48%/yr | 0.679 | **KuCoin 337 bp/side = 48.2x** its assumed 1x |
| R392 GLT gate+mexc | PASS at 1x only | +0.73%/yr | 0.200 | MEXC 13.3 bp/side = 1.9x; Gate not recorded |

Measured median cost per side at $10k, against each book's frozen 7 bp/leg/side unit:

| venue | ADV band | n | bp/side | multiple of assumed 1x |
|---|---|---|---|---|
| kucoin | $0–50k | 179 | 337.2 | **48.2x** |
| kucoin | $50k–500k | 213 | 196.0 | **28.0x** |
| kucoin | $500k–5M | 243 | 276.1 | **39.4x** |
| kucoin | $5M+ | 80 | 14.9 | 2.1x |
| dydx | $0–50k | 52 | 165.3 | **23.6x** |
| dydx | $5M+ | 2 | 3.6 | 0.5x |
| mexc | $50k–500k | 439 | 13.3 | 1.9x |
| mexc | $5M+ | 44 | 2.2 | 0.3x |

**R391's PASS does not survive its own venue's measured cost.** It was decided at 7/14/21 bp per leg
per side and passed 3x (+1.38%/yr). Three of KuCoin's four ADV bands cost **28–48x** that unit, not
3x. Only the deepest band ($5M+, 80 of 715 contracts) is near the assumed range at 2.1x. The book's
edge is 0.679 bp/day on book capital; a 337 bp round-trip leg cannot be paid out of that.

**MEXC is the cheap leg** (0.3–1.9x), which is consistent with R224. The expensive leg is the
long-tail venue, and that is precisely where the "long tail adds capacity" claim lives.

## What this does and does not say

- It does **not** overturn R391's frozen verdict. That verdict was correct **at its frozen cost
  unit**. This says the unit is not achievable on most of the contracts the book trades.
- It is a **band median, not the book's own cost.** R404's per-symbol snapshots are in gitignored
  `data/`, so the exact per-contract join for R391's 28 contracts could not be done here. That join
  is the cost lane owner's next step and it is cheap — the data is already being recorded.
- **Binance and Gate are not recorded by R404**, so C14 (the strongest reserved PASS, +2.86%/yr,
  NW t 4.03) and GLT's Gate leg remain unpriced. R224 measured MEXC only. Extending the recorder to
  Binance and Gate is the highest-value *measurement* gap left, and it needs no reserved read.
- 7 snapshots over one day is a thin cost sample. R404 runs to 2026-11-18; the medians will move.

## Correction to my own earlier ranking

`research/VALUE_REVIEW_20261115.md` ranked the unlock short first on its gate-0 archive numbers.
**That was wrong.** `experiments/reserved_batch1/FINDINGS.md` shows R286 already read it on reserved
samples: **57 events, mean -3.45%, week-cluster t -0.87, leave-two-coins-out -4.59%, 2x -3.65%**, with
four 2020 events averaging **-55.7%**. It FAILED. I had read the scoreboard (as of R363) and the
lane's own FINDINGS but not R286's decision table. The correction is recorded at the top of that
file, with the original text left visible.

R494's sizing result stands as a risk description, but it sizes a book that has failed its one
out-of-sample test. The carry family — not the event family — is what reserved samples actually
confirmed.

## Also fixed: the reserved-read budget was understated

`docs/GATES.md` listed only batch 1. Batches 2 (R391) and 3 (R392) had also read. Reconciled from
each lane's PREREG and registry row:

| sample | reads used | left |
|---|---|---|
| 2020 crypto | 2 of 4 | 2 |
| Gate long tail | 2 of 4 | 2 |
| MEXC-only coins | 1 of 4 | 3 |
| KuCoin / dYdX / Lighter long tail | 1 of 4 | 3 |

A stale table here risks overspending a sample that cannot be un-read, so this was worth fixing
before proposing any batch 4.

## Recommended next work, in order

1. **Extend R404's recorder to Binance and Gate.** C14 is the best reserved PASS and its cost is
   unmeasured. No reserved read, no new signal, and it decides whether +2.86%/yr is real.
2. **Per-contract cost join for R391's 28 contracts** from the recorder's own files, then re-score
   its already-computed daily nets at measured cost. If it fails, say so; the long-tail capacity
   claim dies cheaply.
3. Only then consider a **batch 4** reserved read, with a candidate that is pre-committed and not a
   post-hoc seed. Spending a read to re-test a book whose cost is unknown is the wrong order.
