# PREREG: rnfade_v1 (R249). Fade the first round-number cross of the day, with a shifted-grid control

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R249
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_rnfade.py`. It reuses `held()` from `scripts/run_ictlevels.py` (R246), and R243's crypto
  window statistics.
- **Queue:** M230 (round-number sweep fade with low turnover), M011
- **Gate:** 0 (screen).

## Why this lane exists, and what the author has seen
- **R246 (2021-23):** RN_CROSS (follow every close through a two-significant-figure level, 24 h hold) grossed -17.7
  bp/day with 67 bp/day of cost.
- **A post-hoc check:** the same book on a grid shifted by half a step grossed -6.9. Round minus shifted was -10.8
  bp/day, NW t -3.30, negative every year.
- So closes through round numbers reverse more than closes through arbitrary levels. That was 2021-23, which is now
  spent for this idea.
- **Not computed for 2024-25 by anyone:** any round-number statistic, and any one-trade-per-day version.

## Rule
**Grids, on the prior hourly close c_{t-1}** (1000x contracts use their quoted price):
- **2SF:** step g = 10^(floor(log10 c_{t-1}) - 1), levels k x g (R246's grid).
- **1SF:** step g = 10^floor(log10 c_{t-1}), levels k x g (BTC 60,000 and 70,000; ETH 3,000 and 4,000).
- **Control, the shifted grid:** levels at (k + 0.5) x g, the same step.

**Trigger.** At an hourly close, the close crosses a level of the grid:
- floor(c_t/g - off) > floor(c_{t-1}/g - off): cross up, s = -1 (fade);
- the reverse: cross down, s = +1.
- off is 0 for the round grid and 0.5 for the control.

**Then:**
- **One trade per coin per UTC day:** only the day's first trigger on that coin counts.
- **Hold:** H hours from the trigger close (s is held for H rows, its own row included). A later trigger replaces it.
  - H in {4, 24}.
- **Sizing:** s / (number of eligible coins), directional (`slices.run`, `hedge=False`), with tier costs and funding.
  Alpha is taken against the equal-weight market.

## Books (4 trials; the 4 control books are not trials)
RN2SF/4, RN2SF/24, RN1SF/4, RN1SF/24, each with its control book on the shifted grid.

## Window and decision
- Top-50 perps (`research.load_universe`).
- **Validation 2024-01-01..2025-06-30** only. Discovery 2021-23 is spent for this idea, and the 2025-07 holdout is
  spent at program level.
- **Pass** if all hold:
  - 1x mean > 0 with NW t >= 2;
  - 2x mean > 0;
  - alpha > 0.

## Reported (not decided on)
- At 1x, 2x and 3x, for each book and its control:
  - mean, t, Sharpe, max drawdown;
  - gross and cost, exposure, per year;
  - alpha, trimmed mean, trades.
- **Round minus control:** the 1x daily net difference, with its NW t.

## Multiplicity
- Trials = 4.
- Program trials before: 9,471,983 (after R248).

## Expectations
- One trade per coin-day at most: about 1 entry per coin-day on 2SF, far fewer on 1SF. So cost per day falls about
  5-10x from R246.
- The R246 difference of -10.8 bp/day came from about 7 triggers per coin-day. A single fade per day keeps at best a
  small part of it.
- **Most likely:** round minus control is positive (the reversal survives), with a book that is still under t 2. 1SF
  has too few trades to tell. NULL.
