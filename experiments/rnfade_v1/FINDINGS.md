# FINDINGS: rnfade_v1 (R249). Fade the first round-number cross of the day, with a shifted-grid control

**Verdict: NULL** as a book: none of the 4 books reached t 2 in validation (2024-01..2025-06).

**The mechanism replicated on unseen data, as a difference.**
- With a 4 h hold on the two-significant-figure grid, fading a close through a round level beat the same fade on a
  half-step-shifted grid by **+4.8 bp/day, NW t 2.53**.
- R246 found this post hoc in 2021-23 (-10.8 bp/day for following, t -3.30). Here it holds in 2024-25, a window
  nobody had read for this idea.
- **It is not tradeable at taker cost.** The same book grosses +13.7 bp/day and pays 13.5.

- **Registry row:** R249 (trials 4). Program trials after it: 9,471,987.
- **Gate:** 0.
- **Reproduce:** prereg sha 67ca0c97, frozen in commit f2b7968 before the run. Run `python scripts/run_rnfade.py`
  (about 1 minute).
- **Origin:** queue M230 (from R246's post-hoc check), M011.

## Numbers (validation 2024-01-01..2025-06-30; top-50 perps; directional; one trade per coin per UTC day)

| Book | Grid | Net bp/day 1x / 2x / 3x | NW t (1x) | Gross / cost (1x) | Gross exposure | Alpha (t) | Trimmed | Trades |
|---|---|---|---|---|---|---|---|---|
| RN2SF/4 | round | +0.2 / -13.3 / -26.8 | 0.03 | +13.7 / 13.5 | 0.16 | +0.2 (0.05) | +3.3 | 25,519 |
| RN2SF/4 | shifted | -4.7 / -18.1 / -31.6 | -1.03 | +8.8 / 13.5 | 0.16 | -4.6 (-1.02) | -0.7 | 25,507 |
| RN2SF/24 | round | **+8.8** / -1.2 / -11.1 | 0.88 | +18.7 / 9.9 | 0.86 | +9.4 (0.93) | +14.0 | 25,519 |
| RN2SF/24 | shifted | +4.6 / -5.4 / -15.3 | 0.46 | +14.5 / 9.9 | 0.86 | +5.1 (0.51) | +8.4 | 25,507 |
| RN1SF/4 | round | +0.2 / -4.2 / -8.6 | 0.07 | +4.5 / 4.4 | 0.05 | +0.2 (0.09) | +0.9 | 8,292 |
| RN1SF/4 | shifted | -1.6 / -6.0 / -10.5 | -0.85 | +2.9 / 4.5 | 0.05 | -1.5 (-0.83) | -1.2 | 8,385 |
| RN1SF/24 | round | +5.3 / +1.5 / -2.4 | 1.36 | +9.2 / 3.9 | 0.26 | +5.7 (1.44) | +4.8 | 8,292 |
| RN1SF/24 | shifted | +5.7 / +1.7 / -2.3 | 1.18 | +9.6 / 4.0 | 0.27 | +6.1 (1.22) | +5.6 | 8,385 |

**Round minus shifted grid** (1x daily net):

| Book | Difference bp/day | NW t |
|---|---|---|
| RN2SF/4 | **+4.8** | **2.53** |
| RN2SF/24 | +4.2 | 1.09 |
| RN1SF/4 | +1.7 | 0.85 |
| RN1SF/24 | -0.3 | -0.09 |

Per year at 1x (bp/day):

| Book | Grid | 2024 | 2025 H1 |
|---|---|---|---|
| RN2SF/4 | round | +3.7 | -7.0 |
| RN2SF/4 | shifted | -1.4 | -11.2 |
| RN2SF/24 | round | +8.4 | +9.5 |
| RN2SF/24 | shifted | +4.6 | +4.4 |
| RN1SF/24 | round | +6.0 | +4.0 |
| RN1SF/24 | shifted | +3.5 | +9.9 |

## Cost sensitivity
- One taker trade per coin-day on the 2SF grid costs 9.9 bp/day (24 h hold) to 13.5 (4 h hold) at 1x.
- **Only RN1SF/24 stays positive at 2x** (+1.5), and its own shifted-grid control does as well (+1.7). So the round
  level adds nothing there.
- Nothing is positive at 3x.

## Reading
- **The round-number reversal is real but small.**
  - On the two-significant-figure grid (levels 1-10% apart), the first close through a round level reverses more than
    the first close through a level halfway between. The extra is +4.8 bp/day of book (4 h hold) and +4.2 (24 h).
  - The direction is the same as R246's discovery, which makes this the lab's first unseen-window confirmation of a
    chart-level effect. It is still a gross effect, and the decision rule here was on the book, which failed.
- **On the one-significant-figure grid (BTC 60k/70k), there is no round-number effect.** Trades are few (8,292), and
  the 24 h book's +5.3 equals its control's +5.7.
- **The control is positive too at 24 h** (RN2SF +14.5 gross).
  - Fading the day's first move through any level, arbitrary or not, earned before costs in 2024-25.
  - That is plain one-day reversal of the day's first breakout. R248's REV1D/CRYPTO-1d (+6.4 gross) and R245's liquid
    tercile (continuation, -8.9 for reversal) disagree on it, so it is not a stable effect.
- **The way to keep a 5 bp/day gross effect is to stop paying taker cost on entry.** That means a resting limit order
  at the round level itself, filled only when price trades through it, with entry at the level rather than at the
  hourly close. It is queued as M232. R193 found simple maker fills adverse-selected, and R246's RN_REJECT (touch and
  close back) lost gross, so the prior is low.

## Queue
- **M230:** TESTED. The book is NULL; the mechanism replicated (difference t 2.53, RN2SF/4).
- **M232 (new):** a resting limit at the next two-significant-figure round level, fading the touch, from hourly highs
  and lows.
  - Entry at the level when the bar trades through it; exit after 4 h or 24 h.
  - Maker fee on entry, taker on exit. The shifted-grid control is pre-registered.
  - Only the 2025-07 holdout is left unread for crypto, and it is spent at program level. So the first fair read is
    forward paper, or a new venue's history (MEXC).

## Not checked
- Maker execution, and per-coin liquidity tiers (round numbers may matter more in the most-watched coins).
- Other holds (1 h, 8 h); a level-distance filter; half-steps (BTC 65k).
- The 2025-07 holdout (spent at program level).
