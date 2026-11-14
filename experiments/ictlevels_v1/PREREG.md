# PREREG: ictlevels_v1 (R246). Round numbers, SMT divergence and the 8 AM New York range on hourly bars

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R246
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_ictlevels.py`. It reuses `lab/slices.run` (directional, `hedge=False`) and R243's window loop
  and pass rules.
- **Queue:** M011 (round-number levels), M012 (SMT divergence), M010 (8 AM ET one-hour range fade)
- **Gate:** 0 (screen).

## What the author has seen
- **The owner's old session:** R152 tested the 8 AM range fade on 1-minute data with R-multiple targets and was NULL
  (net -0.168 R, t -9.0). Its base rate: both sides of the range are hit on 58.9% of days.
- **R243 (chartist_v1):** the oscillator fades (Stochastic, CCI, Bollinger) and pivot breakouts lost. Daily
  Supertrend+RSI was the best at +11.3 bp/day, t 1.23.
- **R245:** liquid coins continue at 1 day. The atlas (R185) gives gross conditional means of 1-72 h returns by
  cross-sectional bin.
- **Not computed on this lab's data:** any statistic of round-number levels, SMT divergence or the 8 AM range on hourly
  bars.

## Universe and timing
- Top-50 eligible perps (`research.load_universe`), using hourly open/high/low (`data/klines_1h`) and close.
- Row t is the hourly bar opening at t. A trigger uses bar t's high, low and close and is acted on at its close.
  `slices.run` then earns ret[t], the next bar.
- **Sizing:** each book holds state s in {-1, 0, +1} per coin.
  - Position = s / (number of eligible coins that hour).
  - Directional, `hedge=False`, with tier costs and funding.
  - Alpha and beta are reported against the equal-weight market.

## Books (8 trials)

### Round numbers (M011): Osler (2003)
- **Grid.** The grid step for coin i at hour t is g = 10^(floor(log10 c_{t-1}) - 1), the levels with two significant
  figures. Spacing is 1-10% of price.
  - Levels are taken on the perp's own quoted price; 1000x contracts use their scaled price.
  - U = (floor(c_{t-1}/g) + 1) x g is the next level above the prior close.
  - Dn = floor(c_{t-1}/g) x g is the level at or below it.
- **RN_CROSS (follow; stops beyond round numbers accelerate the move).**
  - Cross up, floor(c_t/g) > floor(c_{t-1}/g): s = +1.
  - Cross down, floor(c_t/g) < floor(c_{t-1}/g): s = -1.
- **RN_REJECT (fade; take-profit orders at round numbers stop the move).**
  - High_t >= U while c_t < U: s = -1.
  - Low_t <= Dn while c_t > Dn and c_{t-1} > Dn: s = +1.
  - Both on the same bar: no trigger. A bar that crosses is not a rejection.
- **Hold:** a trigger sets s for 24 hours, and a newer trigger on the same coin replaces it.

### SMT divergence (M012): ICT
A coin makes a new N-hour extreme that BTC does not make in the same hour:
- **Bearish SMT:** high_t > max(high over t-N..t-1) while BTC's high_t <= BTC's max over t-N..t-1.
- **Bullish SMT:** the same with lows.
- Both on the same bar: no trigger. BTC itself is excluded. ETH is compared with BTC like the others.
- **SMT_FADE** (ICT's reading): bearish gives s = -1, bullish gives s = +1.
- **SMT_FOLLOW** (the mirror): the opposite sign. Registered as its own trial, because R245 found continuation among
  liquid coins at 1 day.
- N in {24, 168} hours. Hold 24 hours, and a newer trigger replaces the old one.
- Books: SMT_FADE/24, SMT_FOLLOW/24, SMT_FADE/168, SMT_FOLLOW/168.

### 8 AM New York range (M010)
- **Range:** the hourly bar opening at 08:00 America/New_York, Monday to Friday.
- **Trigger:** the first hourly close outside the range, among the bars opening 09:00-14:00 New York, on the same day.
- **Hold:** the position runs until the 16:00 New York close (the last bar earned is the one opening at 15:00). One
  trade per coin per day.
- **AM8_FADE:** a close above the range high gives s = -1; a close below the low gives s = +1.
- **AM8_FOLLOW:** the opposite sign.
- Unlike R152, there are no R-multiple targets or stops, and hourly bars are used instead of 1-minute bars.

## Stages (as R243)
1. **Discovery 2021-01-01..2023-12-31.** Pass if all hold:
   - 1x NW t (lag 10) >= 2;
   - 2x mean > 0;
   - alpha against the equal-weight market > 0.
2. **Validation 2024-01-01..2025-06-30**, for discovery passers only. Pass if the 1x mean > 0, t >= 1.5 and alpha > 0.
3. **Holdout: not read.**

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean, NW t, Sharpe, max drawdown;
  - gross and cost, gross and net exposure;
  - per year, trimmed mean;
  - beta and alpha against the equal-weight market.
- Trigger counts per book in discovery.

## Multiplicity
- Trials = 8.
- Program trials before: 9,471,957 (after R245).

## Expectations
- **Round numbers:** Osler's evidence is FX (one bank, 1999-2000). Crypto prices have no fixed tick culture across
  1000x contracts. Low prior; most likely NULL with RN_CROSS slightly positive gross.
- **SMT:** no independent study. FADE most likely loses (R243's fades lost), and FOLLOW is gross positive but eaten by
  the 24 h turnover.
- **AM8:** R152 was strongly negative on 1-minute data; expected NULL here.
- **Overall:** NULL.
