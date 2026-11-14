# PREREG: listings_v1 (R188), what new perpetual listings do next

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited.

- **Registry id:** R188
- **Code:** `lab/events.py`, `scripts/run_listings.py`
- **What the author had seen:** nothing about returns after listings in this data. The idea is structural: perps are
  listed when a coin is in demand (hype, airdrops, unlock schedules ahead), so the following weeks may drift as that
  demand fades or as supply unlocks; or momentum may carry on. Direction is not assumed.

## Question
After a new USDT perpetual is listed on Binance, does it beat or trail the market over the next one to four weeks, by
enough to pay one round trip, consistently across years? (Low turnover: one trade per listing.)

## Data
All 900 USDT perpetuals in the archive (delisted included), hourly klines, funding at its settlement hours. A listing is
the first hour with a close for a symbol, from 2021-01-15 on (earlier first hours are the panel start, not listings).
Benchmarks: the equal-weighted next-bar return of the 50 most liquid symbols at that hour (point in time), and BTCUSDT.
Costs: one-way 6/8/12/20 bp by the symbol's trailing liquidity rank at entry, paid in and out on both legs when hedged.

## Splits
Discovery: listings 2021-01-15 to 2023-12-31. Validation: listings 2024-01-01 to 2025-05-31 with windows ending before
2025-07-01. Holdout (listings from 2025-07-01): not read.

## Measures
For each listing: entry at the close of hour listing + delay (delay in 24 h, 72 h), hold H in 7, 14, 30 days; return
of the perp (funding included) minus the benchmark's over the same hours (excess vs the top-50 market, or vs BTC);
optional filter: trailing 24 h quote volume at entry >= 10 M USDT. The short side earns minus that, net of costs.
- Per configuration: number of events, mean and median excess, share negative, worst and best event, mean with t
  clustered by listing month, per-year means.
- Book: short every event with a fixed stake (1/max(open, 10) of capital), hedged long the benchmark; daily net PnL,
  annual return, Sharpe, Newey-West t (lag 10), max drawdown, per-year.
- Late baseline: the same symbols entered 180 days after listing, same delay/hold logic, to tell "new" from "this kind
  of coin".

## Primary and decision
Primary: delay 24 h, hold 14 days, excess vs the top-50 market, no volume filter.
- **SIGNAL (discovery)** if the primary mean excess has clustered |t| >= 3 and the same sign in >= 2 of the 3 discovery
  years (2021, 2022, 2023), net of costs on the side that its sign implies.
- **VALIDATED** if also on validation the same sign with clustered |t| >= 2 (net).
- A VALIDATED primary earns a one-shot holdout lane. Otherwise NULL, reported in full.

## Multiplicity
Trials = 2 delays x 3 holds x 2 benchmarks x 2 filters = 24 configurations (plus the late baseline as a control, not a
trial). Read against the program total.

## Expectations (written before running)
Probably negative excess on average (new listings fade), with a fat right tail (squeezes) that makes the short side
painful; possibly strong in 2021-2022 and weaker later as the pattern became known.
