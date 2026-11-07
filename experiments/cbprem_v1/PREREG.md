# PREREG: cbprem_v1 (R210), does the Coinbase premium lead BTC and ETH?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R210
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/fetch_extra.py` (Coinbase and Binance spot), `scripts/run_cbprem.py`, `lab/slices.positions`
- **Source claim:** `docs/CLAIMS.md` C18 (crypto social media; grade D).

## What the author had seen
Coinbase BTC-USD, ETH-USD, USDT-USD and Binance spot BTCUSDT, ETHUSDT hourly candles were fetched (2021-01 on). No
premium, no statistic, and no relation to returns has been computed. The author knows the claim is widely repeated
and that US-hours flow is often cited as the reason.

## Signal (hourly)
- prem_t = Coinbase X-USD close / (Binance spot XUSDT close x Coinbase USDT-USD close) - 1, all from the bar opening
  at t (closes at t + 1 h, the same instant as the research row t's close). Hours with any input missing: no signal.
- z_t = (prem_t - mean) / std over hours t-719..t (30 days, at least 600 finite hours).
- z_t > +2: open a long slice; z_t < -2: open a short slice, in the coin's Binance USDT perp. Each slice has size
  1 / h and closes h hours later, so the position is at most 1 in either direction (overlapping slices net).
- Position at the close of row t earns ret[t] (funding included); the coin's tier cost on every change.

## Variants and trials
BTC and ETH; h = 24 (primary for BTC) and h = 4. Trials = 4.

## Windows and decision
- In-sample: 2021-01-01..2025-06-30; holdout (this lane's own): 2025-07-01..2026-09-30.
- **CONFIRMED** if BTC h = 24 has a positive in-sample daily net mean at 1x with NW t (lag 10) >= 2 **and** a positive
  holdout mean. Otherwise NULL.

## Reported (not decided on)
2x and 3x costs; per year; signal hours per side; mean forward 1 h, 4 h and 24 h return after z > 2 and z < -2
(gross, before costs); the contemporaneous correlation of the hourly change in prem with the same hour's return (is the
premium a by-product of the move rather than ahead of it?).

## Multiplicity
Trials = 4. Program trials before: 9,471,691.

## Expectations
The premium is mostly contemporaneous with US-session flow and the USDT basis; whatever lead it had is public and
arbitraged. Guess: NULL; gross forward returns after extremes near zero or slightly reverting.
