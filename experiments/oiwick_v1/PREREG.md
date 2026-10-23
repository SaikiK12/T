# PREREG: oiwick_v1 (R252). Fade liquidation cascades, proxied by an open-interest drop plus a long wick

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R252
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_oiwick.py`. It reuses `held()` from `scripts/run_ictlevels.py` and R246's book loop
  (`slices.run`, `hedge=False`, alpha against the equal-weight market).
- **Queue:** M176 (liquidation-cascade proxy)
- **Gate:** 0 (screen).

## What the author has seen
- **R206 (Gate liquidation data, 145 days in 2026):**
  - Fading liquidation spikes was NULL (h12 -36 bp/day, t -1.96).
  - Long cascades continued: the long-leg gross was -2 to -11 bp/day.
  - Short squeezes reverted, +10 to +26 bp/day gross at 4-24 h, but below cost.
- The old session's R158 (Coinalyze liquidations) was NULL.
- R246: one-hour reversal in crypto is real gross but costs more than it gives.
- No statistic of OI drops combined with wicks has been computed in this lab.

## Trigger (hourly, top-50 eligible perps)
- **OI drop:** log(oi_t / oi_{t-1}) <= log(0.97), i.e. open interest falls at least 3% in the hour (`metrics_1h`).
- **ATR:** Wilder ATR over 24 hourly bars, ending at t-1. The ATR excludes the trigger bar.
- **Long cascade:** lower wick (min(open, close) - low) >= 3 x ATR. Fade: s = +1 (buy).
- **Short squeeze:** upper wick (high - max(open, close)) >= 3 x ATR. Fade: s = -1 (sell).
- Both wicks on one bar, or any input missing: no trigger.
- **Hold:** H hours from the trigger close, and a newer trigger replaces the old one.
- **Sizing:** s / (number of eligible coins), directional, with tier costs and funding.

## Books (4 trials)
- **ALL/4** and **ALL/24:** both sides, held 4 h and 24 h.
- **SQZ/4** and **SQZ/24:** short-squeeze fades only, held 4 h and 24 h. These are a separate trial because R206's
  squeeze side reverted on a different venue and period.

## Stages (as R246)
1. **Discovery 2021-01-01..2023-12-31.** Pass if all hold:
   - 1x NW t >= 2;
   - 2x mean > 0;
   - alpha > 0.
2. **Validation 2024-01-01..2025-06-30**, for discovery passers. Pass if mean > 0, t >= 1.5 and alpha > 0.
3. **Holdout:** not read.

## Reported (not decided on)
- Triggers per side in discovery.
- **The mean raw forward return after each side** (1, 4, 24 h, close to close) in discovery, with counts, to show
  continuation or reversal before costs.
- Book statistics at 1x, 2x and 3x:
  - mean, t, gross and cost, exposure;
  - alpha, per year, trimmed mean.

## Multiplicity
- Trials = 4.
- Program trials before: 9,471,997 (after R251).

## Expectations
- R206's split predicts:
  - long-cascade fades lose (cascades continue);
  - squeeze fades gain gross but are rare enough that cost and noise dominate.
- **Most likely:** NULL. The one plausible discovery pass is SQZ/24.
