# FINDINGS: tapelag_lighter_v2 (R348), zero-fee scalps on Lighter traded toward Binance's quote

**Answer: NULL. Lighter's quote does not stay off Binance's long enough to pay.**
- Entering one full second after a dislocation, the trades earn about 0 before costs: −0.03 to +0.32 bp a trade
  across the six trials.
- So every trial loses its cost, about 0.7-1.0 bp a round trip.
- The primary (θ 1 bp, 5 s hold) loses 0.77 bp a trade. Its bucket t is −3.43, and its bootstrap p of a positive mean
  is 1.00.
- **Reading:** Lighter's makers close the gap with Binance within a second. The 300 ms taker delay on its zero-fee
  accounts protects them as designed.

| Trial | Trades | Gross bp | Cost bp | 1x bp | 2x bp | 3x bp | Bucket NW t (1x) | Bootstrap p | Family-wise p |
|---|---|---|---|---|---|---|---|---|---|
| θ 0.5, 5 s | 2,586 | −0.03 | 0.67 | −0.69 | −1.36 | −2.02 | −6.36 | 1.00 | 1.00 |
| θ 0.5, 30 s | 1,457 | −0.09 | 0.71 | −0.81 | −1.52 | −2.23 | −3.90 | 1.00 | 1.00 |
| **θ 1, 5 s (primary)** | **577** | **+0.01** | **0.78** | **−0.77** | **−1.55** | **−2.32** | **−3.43** | **1.00** | **1.00** |
| θ 1, 30 s | 407 | −0.34 | 0.82 | −1.16 | −1.99 | −2.81 | −2.42 | 1.00 | 1.00 |
| θ 2, 5 s | 122 | +0.19 | 1.04 | −0.85 | −1.88 | −2.92 | −2.00 | 0.99 | 1.00 |
| θ 2, 30 s | 103 | +0.32 | 1.06 | −0.75 | −1.81 | −2.87 | −0.95 | 0.81 | 0.97 |

- **Units:** bp per trade of the trade's notional. Cost is the round trip at 1x: the larger of Lighter's quoted
  half-spread and the coin's $1k book walk, on entry and on exit.
- **The primary's four conditions all fail:**
  1. The bootstrap p is 1.00.
  2. The 2x mean is −1.55 bp.
  3. The trimmed bucket mean is −1.89.
  4. None of its top 3 coins (ETH, BTC, SOL) is positive.
- **Sample:** 151 observable 5-minute buckets (12.6 hours) on 2026-10-21, 10-22 and 10-26.

## Where it fails
- **Every coin, day and side.**
  - Primary, by coin: BTC −0.66 (146 trades), ETH −0.46 (260), SOL −0.63 (135).
  - The alts that rarely trade lose more, because their book costs 0.8-4.1 bp a side.
  - By day: −0.95, −0.97 and −0.45. Longs −0.78 and shorts −0.76.
- **Thicker books do not help.** On trades with $1k at the touch at entry, the primary nets −0.75.
- **A later entry does not help.**

  | Primary, 1x | 1 s | 2 s | 3 s |
  |---|---|---|---|
  | bp a trade | −0.77 | −0.93 | −0.88 |

  After one second there is nothing left to catch.
- **The largest dislocations revert a little.** At θ 2, gross is +0.19 / +0.32 bp (5 s / 30 s) on about 110 trades
  each. That is a quarter to a third of the cost, and not significant.

## Lane details
- **Registry row:** R348, 6 trials.
  - PREREG sha256 `76a5fbbf…c4c9`, frozen and pushed in `61dc5b2` before the run, and claimed on #7 (comment
    6444294893).
  - All 35 inputs matched.
- **R347:** frozen in `baaec34`, then crashed in its summary before any statistic (pandas 3 typing).
  - It is recorded with 0 trials, and its files are unchanged.
  - R348 is R347's frozen rule and code, with one cast to numbers (`scripts/run_tapelag_lighter_v2.py`).
- **Reproduce:** `python scripts/run_tapelag_lighter_v2.py --run` writes `results/summary.json` and each trial's
  trades. The log is `run.log`.
- **Gate:** 1, research, on an unread sample. No one had read the tape against price changes. Only plumbing counts
  were read before the freeze (R347's PREREG).
- **Trials:** the program goes from 9,479,005 to 9,479,011 on this branch, or 9,479,028 counting Codex's R338-R346
  on PR #56.

## Costs (1x, 2x, 3x)
- **1x:** fee 0. Each side pays the larger of Lighter's quoted half-spread at that second and the coin's median $1k
  book walk over 20 snapshots, with a 0.1 bp floor. The walks: BTC 0.27, ETH 0.23 and SOL 0.30 bp a side, and the
  alts 0.77-4.10.
- **2x and 3x:** twice and three times that cost on each side.
- Every trial is negative at 1x, so the multiples only deepen the loss.

## What this closes, and what it does not
- **Closed:** taker scalps on Lighter's lag behind Binance, from this machine, on a Standard account, at 1-second
  resolution. M425's taker form is tested.
- **Not tested:**
  - **A faster account.** Premium's taker delay is 140 ms, but its taker fee is 2.8 bp a side, more than the
    dislocations.
  - **Making instead of taking.** A Standard account's cancels also wait 300 ms, so its quotes would be the stale
    ones.
  - **Signals other than the basis,** such as order-flow imbalance over 10-60 s (M264).
  - **What happens inside the first second.**
