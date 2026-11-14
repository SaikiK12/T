# PREREG: tsbattery_v1 (R242). Four crypto time-series rules: week-open bias, pre-FOMC drift, ETH/BTC regime, vol-managed trend

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R242
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_tsbattery.py`, `lab/slices.run` (tier costs and funding, no hedge), `lab/screen.window_stats`,
  FOMC dates from `lab/sessions.FOMC`
- **Queue:** M013 (week-open bias), M191 (pre-FOMC drift), M009 (ETH/BTC alt-season regime), M184 (vol-managed trend
  on the full perp universe)
- **Gate:** 0 (screen).

## What the author has seen
- The context atlas (R192) measured lifts of known signals by a macro clock that has FOMC statement days as one class,
  and by weekday. It did not test a pre-FOMC long book or the week-open rule.
- R229 (Codex): slow spot trend on six major coins, NULL against risk-matched passive. R222: 150-day cross-sectional
  momentum, NULL. R237: cross-asset trend outside crypto, NULL.
- R238: the 28-day cross-sectional winners earned only in 2021.
- No statistic of the four rules below has been computed.

## Universe and accounting
- The top-50 eligible perps (`u.elig`), hourly returns with funding (`u.ret`).
- `lab/slices.run` with `hedge=False`. These are directional rules, so the market is part of the bet.
- Position P[t] is set at the close of row t and earns row t+1. Tier costs are charged on every change of position.
- Daily decisions are taken at the close of the bar that ends at 00:00 UTC. Positions are held for 24 hours, on coins
  eligible at the decision.

## Rules (four trials)
1. **WEEKOPEN (M013).** On each day from Tuesday to Sunday, each eligible coin takes `sign(close_now / close at Monday
   00:00 UTC - 1)` at weight 1/N, so gross is 1. Flat on Mondays, when the week opens.
2. **FOMC (M191).** Long all eligible coins at 1/N each, from 14:00 New York time on the day before each scheduled
   FOMC statement day to 14:00 on the statement day (24 hours, before the statement). Flat otherwise. Dates come from
   `lab/sessions.FOMC`; the schedule is published a year ahead.
3. **ETHBTC (M009).** Daily: `x = 60-day log change of ETH/BTC` (1,440 hours).
   - If x > 0: long eligible coins other than BTC at 0.5/N_alt each, and short BTC at 0.5.
   - Otherwise the reverse.
   - Gross 1.
4. **VOLTREND (M184).** Daily, for each eligible coin with complete data:
   - weight `sign(30-day return) x min(0.40 / vol30, 2) / N`, where vol30 is the annualised standard deviation of the
     last 720 hourly returns, and N is the number of such coins;
   - long or short, directional.

## Tests and stages (crypto windows)
Each rule's daily net is compared with the equal-weight market: the mean of eligible coins' hourly returns summed per
day, without costs. Regressing on it gives a beta and an alpha (the residual mean).
1. **Discovery 2021-01-01..2023-12-31.** Pass if all hold:
   - 1x mean > 0 with NW t (lag 10) >= 2;
   - 2x mean > 0;
   - alpha against the market > 0. This keeps out a rule that is only long a rising market.
2. **Validation 2024-01-01..2025-06-30**, for discovery passers. Pass if the 1x mean > 0 with t >= 1.5 and alpha > 0.
3. **Holdout: not read** (spent at program level).

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean, NW t, Sharpe, max drawdown;
  - gross, cost, average gross and net exposure;
  - beta and alpha (with t) against the market;
  - per year;
  - trimmed mean.
- FOMC: the number of events in each window.
- The equal-weight market itself (mean, t, max drawdown) for comparison.

## Multiplicity
- Trials = 4.
- Program trials before: 9,471,933 (after R241).

## Expectations
- **WEEKOPEN** is a short-horizon trend rule that trades daily at a cost of about 1/N per coin flip. Most likely
  NULL.
- **FOMC:** about 24 events in discovery, so power is very low. The equity pre-FOMC drift (Lucca-Moench) has faded
  since 2015. Most likely NULL.
- **ETHBTC** is a slow regime. 2021 had an alt season and 2022-23 did not. Possible either way, most likely NULL.
- **VOLTREND** is trend on a falling market (2022), so it is likely positive in 2022 and negative in 2021's chop.
  Most likely NULL against alpha.
