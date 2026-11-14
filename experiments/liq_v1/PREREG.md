# PREREG: liq_v1 (R206), do liquidation cascades overshoot?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R206
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/fetch_gate.py`, `scripts/run_gate_lanes.py liq`, `lab/slices.py`
- **Source claim:** `docs/CLAIMS.md` C07 (folklore, grade D).

## What the author had seen
No liquidation statistic of any kind. The atlas found OI-vs-price reversals after a 24 h rise (R185, a proxy). Gate's
fields were seen for one BTC row.

## Data and alignment
Gate `contract_stats` hourly for coins of the Binance research universe listed on Gate (about 2026-04-22 on); a Gate
row stamped X goes to Binance row X (known at that bar's close). Per coin-hour,
L = (long_liq_usd - short_liq_usd) / open_interest_usd (positive = longs were liquidated).

## Rule
- Thresholds per coin from its own trailing 720 Gate hours (min 360 hours with OI): q95 and q05 of L, from past hours
  only. L >= q95 and L > 0 (a long cascade): open a **long** slice (the reversal); L <= q05 and L < 0 (a short squeeze):
  open a **short** slice. Only tradable Binance coins (top 50).
- Slices held h hours, size 1 / (h x K_L), K_L = the mean number of coin-states per hour over the window (computed by
  the script), universe hedge, Binance returns with funding, tier costs.
- **Primary: h = 12.** Reported: h = 4, 24, 72; long-only and short-only legs.

## Window and decision
Binance rows from the first hour with thresholds to 2026-09-30 23:00 (about 4 months). **CONFIRMED (discovery
level)** if the primary's daily net at 1x has a positive mean with NW t (lag 5) >= 2; otherwise NULL. Short window:
any positive result is a lead for a forward test (Gate keeps 180 days, so October 2026 on can be scored later).

## Multiplicity
Trials = 4 (h = 4, 12, 24, 72). Program trials before: 9,471,645 (after R205's 3).

## Expectations
Liquidation spikes are rare per coin; the book is thin and lumpy; a 12 h bounce, if any, is likely smaller than the
round trip. NULL is the likely outcome.
