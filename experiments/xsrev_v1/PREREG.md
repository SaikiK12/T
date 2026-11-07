# PREREG: xsrev_v1 (R245). Short-term reversal inside liquidity terciles

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R245
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_xsrev.py`, `lab/screen.py` on a sub-universe (eligibility restricted to one liquidity tercile)
- **Queue:** M008 (daily reversal in illiquid coins), M181 (liquidity-conditioned 1-7 d reversal)
- **Gate:** 0 (screen).

## What the author has seen
- The owner's old session: R169 xsrev and R170 xsrevmaker, both NULL. No numbers survive.
- The atlas (R185): gross conditional means of 1-72 h returns by xs bin over the whole top-50, not by liquidity
  tercile.
- R236: illiquid coins earned in 2021-23 and lost in 2024-25. R238: the 7-day and 28-day winners earned in 2021, so
  over the whole top-50 there was momentum, not reversal, at a one-week hold.
- No statistic of reversal within a liquidity tercile has been computed.

## Universe
- Top-50 eligible perps. Liquidity terciles come from `u.rank`, the point-in-time trailing liquidity rank among the 50
  (1 = most liquid):
  - **LIQ:** rank 1-17;
  - **ILLIQ:** rank 34-50.
- Each book runs on a sub-universe whose eligibility is restricted to its tercile at each hour. Bins, K, the hedge
  basket and costs all use that sub-universe.

## Features and books (lab/screen.py, xs4 bins, since a tercile has about 17 coins)
- **r1d** = log(c_t / c_{t-24}), hold 24 h.
- **r7d** = log(c_t / c_{t-168}), hold 168 h.
- Reversal side only: **L** longs the bottom bin (losers) and shorts the top bin (winners). Size 1 / (hold x K), with
  K fixed on discovery. Hedged with the tercile's equal-weight basket. Tier costs, funding.
- Trials: {r1d/24 h, r7d/168 h} x {LIQ, ILLIQ} = **4 books**.

## Stages (as R238)
1. **Discovery 2021-01-01..2023-12-31.** Pass if both hold:
   - 1x NW t (lag 10) >= 2;
   - 2x mean > 0.
2. **Validation 2024-01-01..2025-06-30**, for discovery passers. Pass if the 1x mean > 0 with t >= 1.5.
3. **Holdout: not read.**

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x: mean, NW t, Sharpe, max drawdown, gross and cost, per year, trimmed mean, K.
- The ILLIQ minus LIQ difference in mean for each feature (descriptive).

## Multiplicity
- Trials = 4.
- Program trials before: 9,471,953 (after R244).

## Expectations
- **Literature:** reversal in small or illiquid coins, momentum in large ones (Ficura 2023; Zaremba 2021).
- **Lab priors:** R238 found momentum at one week over the whole top-50, and R169 was null.
- **Most likely:**
  - r1d/ILLIQ is positive gross but eaten by the cost of a 24 h hold on illiquid tiers;
  - r7d/LIQ is negative (momentum among large coins);
  - NULL overall.
