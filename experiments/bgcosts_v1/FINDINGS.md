# FINDINGS: bgcosts_v1 (R495, M543). Binance and Gate cost, measured for the C14 carry universe

**Verdict: PRICEABLE.** 1,400 book rows over 860 contracts, 33 errors, one snapshot on 2026-11-15.
PREREG `4a7d68d667d5` verified before the read. **0 trials** — this measures cost, it tests no return.
No reserved sample read, no order placed, no key used.

Reproduce: `python scripts/record_bg_costs.py` (public endpoints; `www.binance.com` is `lab/live.py`'s
documented path because `fapi.binance.com` is 451 here).

## Measured cost per side, median over contracts

| venue | contracts | half-spread | $1k | $5k | $10k | unfilled at $10k |
|---|---|---|---|---|---|---|
| Binance | 701 | 2.37 bp | 7.17 bp | 13.43 bp | **18.27 bp** | 0.0% |
| Gate | 699 | 8.93 bp | 17.12 bp | 37.52 bp | **65.71 bp** | 4.7% |

Finite $10k side cost on 701 Binance and 666 Gate contracts, both above the frozen 60 minimum.

Against **C14's frozen 7 bp per leg per side** (`experiments/reserved_batch1/carry.toml`):
**Binance 2.61x, Gate 9.39x.**

## What that does to C14

C14's published nets are almost exactly linear in the cost multiple: 1x +2.86%/yr, 2x +1.86%, 3x +0.85%
(fitted slope -1.005%/yr per 1x, intercept 3.867). Extrapolating that line:

| legs priced at | multiple | implied net |
|---|---|---|
| Binance on both | 2.61x | **+1.24%/yr** |
| one Binance, one Gate (average) | 6.00x | **-2.16%/yr** |
| Gate on both | 9.39x | **-5.57%/yr** |

**Break-even is 3.85x the frozen unit = 26.9 bp per leg per side.** The book's actual pair averages
about 42 bp per side at $10k. On this snapshot, **C14 does not cover its measured cost.**

This is a *description at measured cost*, not a new verdict: C14's frozen PASS and R390's frozen
forward rule are unchanged. It says the cost unit the PASS was decided at is not what the venues
charge today at $10k.

## Why this is the useful result

Every reserved-sample PASS was blocked on the same sentence in its own FINDINGS — measure the book
costs before writing the lane. R404 measures dYdX, KuCoin and MEXC; **Binance and Gate were never
measured**, and C14 is the strongest reserved PASS in the lab (+2.86%/yr, NW t 4.03, p 2.8e-5).
Together with `research/RESERVED_COST_CHECK_20261115.md` (KuCoin 28-48x), **all three reserved PASSes
now have a measured cost, and none of them clears it at $10k.**

The pattern is consistent across the whole program: the gross edges are real and the cost is bigger.

## Size matters more than the signal

Cost falls steeply with smaller size, and that flips the answer:

| size per leg | Binance | Gate | pair average | multiple of 7 bp | vs break-even 3.85x |
|---|---|---|---|---|---|
| **$1k** | 7.17 bp | 17.12 bp | **12.14 bp** | **1.73x** | **inside** |
| **$5k** | 13.43 bp | 37.52 bp | **25.48 bp** | **3.64x** | **inside** |
| $10k | 18.27 bp | 65.71 bp | 41.99 bp | 6.00x | outside |

So the honest reading is not "carry is dead" but **"carry is a small-size book."** At $1k-$5k per leg
the measured pair cost is inside C14's break-even; at $10k it is not. The owner's capital is small, so
the $10k benchmark that R224 established may be the wrong yardstick for this book. Re-scoring R390's
daily nets at $1k and $5k measured cost is the obvious next step and needs no new reserved read.

## Limits

- **One snapshot.** R224 needed 102 snapshots over 37 coins to call a cost surface stable. These
  medians will move; this is a first measurement, not a cost model.
- **Current listings only.** Delisted contracts cannot be measured, so the 2020 sample's own costs
  are still unknown; today's cost is what a forward book would pay.
- **Shown book only:** no queue position, no latency, no impact beyond displayed levels, and the
  venue's fee is separate from the spread cost reported here.
- **The linear extrapolation** beyond 3x is an approximation from three published points, not a
  re-run of C14's engine. A proper re-score of R390's daily nets at measured per-contract cost is the
  next step and is cheap: `results/books.csv` has the per-contract numbers.
- Gate sizes are contracts and were scaled by each contract's `quanto_multiplier`; a contract without
  one was skipped, never priced as if `s` were coins.

## Files
- `results/books.csv` — per contract per venue: mid, half-spread, side cost at three sizes, USD within
  1% of mid, Gate multiplier and listed taker fee.
- `results/report.json` — venue medians, multiples, counts, errors and limits.
