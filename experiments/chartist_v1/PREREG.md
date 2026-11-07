# PREREG: chartist_v1 (R243). Seven classic chart rules on 4-hour and daily bars of the top-50 perps

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R243
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_chartist.py`, `lab/slices.run` (tier costs and funding, no hedge), `lab/screen.window_stats`,
  `lab/flowfeat.load` (kline open/high/low)
- **Queue:** M005 (Supertrend + RSI), M200 (oscillator grid: MACD, Stochastic, CCI, Bollinger), M202 (Ichimoku), M203
  (floor pivots). The owner asked for chartist methods tested even if they look bad.
- **Gate:** 0 (screen).

## What the author has seen
- The atlas (R185) measured hourly-bar views of RSI, Donchian position and returns at horizons up to 72 h, as gross
  conditional means, not as trading rules.
- The owner's old session (`docs/OLD_SESSION_EDGES.md`):
  - X25/R178, Supertrend(10, 3) plus RSI14 on 4 h: NULL, +238 bp in discovery and -5.5 bp in its holdout over 62,448
    trades, under its own rules and costs;
  - X32: candles, mtf_rsi, smc and fib families NULL, per summaries only.
- R185 rated the MACD line, as ema_cross(12, 26), CONFIRMED on gross conditional means only (queue M019), not as a
  costed rule.
- R242: vol-managed 30-day trend passed discovery and failed validation. R229/R230 (Codex): slow spot trend and
  rotation, NULL.
- No statistic of the rules below, as trading rules on 4 h or 1 d bars, has been computed.

## Bars
- Hourly klines of the top-50 eligible perps, resampled to UTC-aligned 4-hour bars (00, 04, ..., 20) and to daily bars
  (00:00 UTC).
- Open is the first hour's open, high the max, low the min, close the last hour's close.
- A bar with any missing hour is missing. Indicators need complete data over their lookback.

## Rules
Each rule gives, per coin and bar close, a state of +1 (long), -1 (short) or 0 (flat). Wilder smoothing (alpha 1/n)
for ATR and RSI; EMA with span n for MACD.

1. **SUPERTREND_RSI (M005):** Supertrend(10, 3) on ATR(10) with the standard final-band recursion.
   - +1 when Supertrend is up and RSI(14) > 50.
   - -1 when Supertrend is down and RSI(14) < 50.
   - Otherwise 0.
2. **MACD (M200):** the sign of MACD(12, 26) minus its 9-period signal line.
3. **STOCH (M200), a fade:** %D = 3-bar mean of %K(14).
   - +1 when %D < 20.
   - -1 when %D > 80.
   - Otherwise 0.
4. **CCI (M200), a fade:** CCI(20) on the typical price (H+L+C)/3, with the 0.015 mean-absolute-deviation constant.
   - +1 below -100.
   - -1 above +100.
   - Otherwise 0.
5. **BOLL (M200), a fade:** Bollinger(20, 2), population standard deviation.
   - +1 when the close is below the lower band.
   - -1 when it is above the upper band.
   - Otherwise 0.
6. **ICHIMOKU (M202):** Tenkan(9), Kijun(26), Senkou A = (Tenkan + Kijun)/2 and Senkou B(52), each plotted 26 bars
   ahead, so the cloud at a bar uses values from 26 bars earlier.
   - +1 when the close is above both cloud lines and Tenkan > Kijun.
   - -1 when it is below both and Tenkan < Kijun.
   - Otherwise 0.
7. **PIVOT_BREAK (M203):** floor pivots from the previous complete UTC day: P = (H+L+C)/3, R1 = 2P - L, S1 = 2P - H.
   - +1 when the bar's close is above R1.
   - -1 when it is below S1.
   - Otherwise 0.

Each rule runs on 4 h and on 1 d bars: **14 trials**.

## Book
- Each eligible coin holds its state at weight 1/N, where N is the number of eligible coins at the decision. The
  position is set at the bar's close (the close of its last hourly row) and held until the next bar's close.
- Directional (`hedge=False`). Tier costs on every change, funding included.

## Tests and stages (as R242)
Alpha and beta are measured against the equal-weight market's daily return.
1. **Discovery 2021-01-01..2023-12-31.** Pass if all hold:
   - 1x mean > 0 with NW t (lag 10) >= 2;
   - 2x mean > 0;
   - alpha > 0.
2. **Validation 2024-01-01..2025-06-30**, for discovery passers. Pass if the 1x mean > 0 with t >= 1.5 and alpha > 0.
3. **Holdout: not read.**

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean, NW t, Sharpe, max drawdown, gross and cost;
  - average gross and net exposure;
  - beta and alpha (t);
  - per year;
  - trimmed mean.
- Share of coin-bars long, short and flat per rule.

## Multiplicity
- Trials = 14.
- Program trials before: 9,471,937 (after R242).
- About 0.3 false discovery passes are expected under the null. The trend rules (1, 2, 6) are correlated with each
  other, and the fades (3, 4, 5) with each other.

## Expectations
- **Trend rules (Supertrend, MACD, Ichimoku):** R242's 30-day trend was positive in every year at a small size, and
  these are faster. Positive in 2022 (falling market) and costly on 4 h bars. Most likely below t 2 after costs.
- **Fades (Stochastic, CCI, Bollinger)** go against short-term moves. The atlas found weak hourly reversal at the
  coin level. Most likely NULL; on 4 h, the cost of frequent flips may make them negative.
- **PIVOT_BREAK** is a breakout rule. Most likely NULL.
- Overall: NULL is the most likely outcome. A null across 14 classic rules is itself the result the owner asked for.
