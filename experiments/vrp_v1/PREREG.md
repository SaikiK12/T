# PREREG: vrp_v1 (R209), does the volatility risk premium (implied minus realized) time BTC and ETH?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R209
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/fetch_extra.py` (Deribit DVOL), `scripts/run_vrp.py`
- **Source claim:** new, `docs/CLAIMS.md` C23: the variance risk premium predicts index returns (equities: Bollerslev,
  Tauchen, Zhou 2009, *Review of Financial Studies*; grade B for equities, untested here for crypto perps).

## What the author had seen
Deribit DVOL was fetched (hourly, BTC and ETH, 2021-03-24 on); the only values looked at are a few hours of
2021-04-01 (BTC about 86) while probing the endpoint. No DVOL statistic, no realized-volatility statistic, and no
relation to returns has been computed. The author knows BTC's broad price history.

## Signal (daily, at the 00:00 UTC row of day d)
- RV_d = 100 x sqrt(8760 x mean of squared hourly log returns of the coin's Binance perp close over rows d-720..d-1)
  (30-day realized volatility, annualized, in vol points).
- IV_d = DVOL close of the 23:00 hour of day d-1 (the hourly bar stamped 23:00 closes at 00:00), in vol points.
- VRP_d = IV_d - RV_d.
- Threshold: the median (and terciles) of VRP over days d-365..d-1, at least 180 days.

## Positions
- **Primary (BTC, median split, daily):** w_d = +1 (long BTCUSDT perp) if VRP_d > its trailing median, else -1,
  held from the 00:00 row of day d for 24 rows. Position at the close of row t earns ret[t] (funding included);
  BTC tier cost on each change of w.
- Variants: ETH (ETHUSDT with ETH DVOL); tercile extremes (+1 above the upper tercile, -1 below the lower, 0 between);
  weekly (w set on Mondays' 00:00 row and held 7 days).
- Trials: 2 coins x 2 splits x 2 rebalance = 8.

## Windows and decision
- In-sample: first day with a threshold .. 2025-06-30. Holdout (unspent for this lane): 2025-07-01..2026-09-30.
- **CONFIRMED** if the primary's in-sample daily net at 1x has a positive mean with NW t (lag 10) >= 2 **and** its
  holdout mean is positive. Otherwise NULL. Both windows are computed in the same run.

## Reported (not decided on)
2x and 3x costs; per year; the long and short halves separately (mean BTC return on high- vs low-VRP days); share of
days long; correlation of VRP with the trailing 30-day return (is it just momentum or reversal in disguise?).

## Multiplicity
Trials = 8. Program trials before: 9,471,683.

## Expectations
Crypto implied vol is usually above realized; a high premium follows calm periods and a low (negative) one follows
crashes. Equity evidence is at monthly-quarterly horizons; at daily and weekly ones the signal is noisy. Guess: NULL,
in-sample t between -1 and 1.5.
