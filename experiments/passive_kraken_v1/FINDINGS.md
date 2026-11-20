# FINDINGS: passive_kraken_v1 (R513). A resting order costs less than a taker order on Kraken's thin perps, most with a short wait

**Verdict: PASS (gate 0, cost measurement).**
- On Kraken's 68 thin coins, a resting order placed at the carry book's decision time, with a taker fallback at 6 h,
  saved **+4.91 bp per leg-side** on average against an immediate taker order.
- NW t (lag 5) 3.03 over 91 days; 74% of days were positive.

- **Registry:** R513, 1 trial. Program trials become 9,785,754.
- **Reproduce.**
  - The PREREG (sha 521b9904) was frozen in commit d371bc6 before any 5-minute candle in the window was fetched.
  - `run_passive_kraken.py fetch`: 132 symbols, each with 26,496 five-minute trade candles and 2,208 hourly marks,
    with receipts.
  - `run`, once, on 2026-11-20.
- **What the saving is.** Taker cost now, minus passive cost:
  - **Taker cost now:** the snapshot's $1,000 walk plus the 5 bp fee.
  - **Passive cost when filled:** −half-spread plus the 2 bp maker fee.
  - **Passive cost when unfilled:** the drift to the fallback time, plus the walk and fee.
- **Why it applies to a hedged pair.** Against an entry at the decision mid, a leg entered later at its limit L
  differs by (mid_t − L), whatever the price path in between. So the measure is the right one for a pair whose other
  leg is entered at once.

## Thin coins (under $100k a day on Kraken), by fallback horizon
| Fallback H | Mean saving, bp per leg-side | NW t | Days positive |
|---|---|---|---|
| 1 h | **+8.23** | 9.49 | 90% |
| 6 h (decided) | +4.91 | 3.03 | 74% |
| 24 h | +1.39 | 0.47 | 69% |

- **At H = 6 h.**
  - 85% of the orders filled conservatively (a print through the limit).
  - The mean passive cost was 15.1 bp against 20.0 bp for the taker order.
  - The 15% that did not fill cost on average 133 bp more than taking at once: the drift that kept them from filling.
- **Waiting longer is worse.** More orders fill, but the misses that remain carry larger drifts. A short wait with a
  quick fallback is the better rule.
- **Sides:** buys saved +8.05 bp, sells +1.77 bp at H = 6 h. Prices fell over most of the window.
- **Coins:** 51 of 68 thin coins had a positive mean saving.
- **The optimistic rule changes nothing at this resolution.** Touching the limit within a 5-minute candle almost
  always meant trading through it.

## By liquidity bucket (both sides, mean bp per leg-side)
| Kraken volume per day | Fallback H | Coin-days | Fill rate | Taker cost | Passive cost | Saving |
|---|---|---|---|---|---|---|
| under $10k | 1 h | 2,912 | 51% | 20.9 | 14.3 | **+6.6** |
| under $10k | 6 h | 2,912 | 80% | 20.9 | 19.0 | +1.9 |
| under $10k | 24 h | 2,912 | 92% | 20.9 | 25.1 | −4.2 |
| $10k-100k | 1 h | 3,276 | 75% | 19.2 | 9.5 | **+9.7** |
| $10k-100k | 6 h | 3,276 | 90% | 19.2 | 11.7 | +7.6 |
| $10k-100k | 24 h | 3,276 | 96% | 19.2 | 12.8 | +6.4 |
| $100k-1M | 6 h | 3,640 | 96% | 12.7 | 6.2 | +6.5 |
| over $1M | 6 h | 2,184 | 99% | 8.5 | 1.9 | +6.6 |

- **The thinnest coins gain only with a short wait.** Under $10k a day, the gain holds at 1 h and is gone by 24 h.
- **From $10k a day up,** a passive entry cuts the Kraken leg's cost by a third to two thirds at any horizon.

## What it means for the carry books (R508-R512)
- The Kraken leg is the costly one: 15-20 bp a side on thin coins, against 6-11 bp on Hyperliquid or Aster.
- At the 1 h fallback, passive entries bring the Kraken leg on thin coins from about 20 bp to about 12 bp a side.
- R508's book made +22.5%/yr at 2x and +20.7%/yr at 3x costs. Passive Kraken legs move the measured cost towards 2x
  of R508's 7 bp, so the book sits closer to its 2x line.
- This lane does not re-run any book. A forward lane would charge the Kraken legs the passive-then-taker cost from
  live books and trades.

## What this does not show
- **The spread is held constant** per coin, at the 2026-11-18/19 snapshot. Spreads widen in fast markets, which is
  also when orders fill.
- **The mark price stands for the mid.** On thin books they can differ by a few bp, which shifts the limit relative
  to the true quote.
- **Order size.** A $1,000 resting order can exceed the displayed size at the level on the thinnest coins. The
  conservative rule (a print through the level) guarantees the fill, but a larger order would rest longer.
- **Our own order is not in the market.** Resting it could change the book and the fills. That effect is small at
  $1,000 against these coins' flow, but unmeasured.
- **One window** (2026-08-17..11-15). The decided horizon (6 h) was fixed before the data; the better 1 h result is a
  reported horizon.
