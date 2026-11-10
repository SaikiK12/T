# FINDINGS: carry5_v1 (R439)

**Verdict: the five-venue book SURVIVES the frozen rule (registry: DONE, CONFIRMED).**
- `binance+gate+hyperliquid+mexc+kucoin L14d th10% K20` on the M468 engine (`lab/xfund_v2.py`) makes +18.46%/yr at 1x,
  NW t 8.71. The 2x mean and both halves are positive.
- **Adding KuCoin makes the book steadier but not measurably richer.** Against the same rule on R275's four venues (paired,
  reported, not gating), the gain is +1.48%/yr, NW t 0.54. On constant entry notional the two books earn the same, about
  +14.7%/yr.
- What it does improve: t rises from 4.77 to 8.71, the top-10-day share falls from 33% to 18%, and max drawdown from -5.9%
  to -4.4%. KuCoin gives the same rule a second deep venue next to Gate, so it depends less on a few days.
- This is gate 0 on seen rows and inherits R275's best-of-560 pick. It admits nothing to real money.

## Read
- **Run once** on 2026-11-10 with `scripts/run_carry5.py --run` (exit 0, load 89 s). The PREREG (8a16c979) and its 18
  inputs matched.
- **Order:** PREREG frozen and registry row R439 appended in c481b68, pushed, then the run.
- **Data identity:** at plumbing the v1 four-venue book equalled R275's daily net to 5e-11 on 2,078 days. The run repeats
  that check and stops on a mismatch.
- **Outputs:** `results/report.json`, `results/daily.csv` (both books, 1x/2x/3x), `results/trades_v2.csv`, `run.log`.

## Results (%/yr on book capital; costs 7, 14 and 21 bp per leg)
| Book | v2 1x | v2 2x | v2 3x | NW t | halves bp/day | 2025+ bp/day | max DD | top-10-day share | Decision |
|---|---|---|---|---|---|---|---|---|---|
| five venues (this lane) | +18.46 | +17.02 | +15.57 | 8.71 | +3.61 / +6.51 | +6.90 | -4.4% | 18% | SURVIVES |
| four venues (R437 all four, reference) | +16.99 | +15.41 | +13.83 | 4.77 | +2.89 / +6.42 | +6.76 | -5.9% | 33% | (reference) |

- **Paired (five minus four), daily net at 1x:** +0.40 bp/day, +1.48%/yr, NW t 0.54 over 2,078 days. Not significant.
- **Above cash:** +18.46, +17.02 and +15.57%/yr all beat the 4.13% T-bill hurdle.
- The four-venue row reproduces R437's all-four v2 figures (+16.99%/yr, t 4.77).

## Where the return comes from (reported)
| Book | Funding | Funding on constant entry notional | Drift | Price | Costs | Net on constant notional |
|---|---|---|---|---|---|---|
| five venues | 22.05 | 18.24 | +3.81 | -2.14 | 1.45 | about +14.65 |
| four venues | 17.28 | 15.00 | +2.28 | +1.29 | 1.58 | about +14.71 |

- "Net on constant notional" is v2 net minus drift. It is the conservative figure, as in R438.
- **KuCoin raises funding but gives it back in price.** Constant-notional funding is +3.2 points higher. The price leg
  goes from +1.29 to -2.14. KuCoin legs are valued on daily closes, so their price P&L is noisier. On constant notional the
  two books are level.
- Drift is larger with KuCoin (+3.81 against +2.28). R438 measured the same covariance on the KuCoin pair books: funding
  spreads widen on the leg whose price rose.

## Book mechanics
- **Trades:** 1,177 (four venues: 1,285). Average pairs held 19.8 of 20.
- **Exits:** spread 1,117, dead 25, blowout 15, open at the end 20. The four-venue book has 40 dead and 22 blowouts.
  Which legs the fewer exotic exits came from was not broken down.
- **KuCoin legs:** 48.8% of trades have a KuCoin leg.
- **Pairs by venue (long/short listing as `pairs_by_venues`):** binance/gate 293, kucoin/gate 189, gate/binance 152,
  gate/kucoin 121, binance/kucoin 119, gate/hyperliquid 49, kucoin/binance 47, kucoin/mexc 37, others 170. The Gate and
  Binance pairs are about halved compared with the four-venue book (560 and 331).

## Read against the program
- **Program trials:** 9,784,982, including this lane's 1.
- **Inherited selection:** the rule is R275's all-four pick, best of 560 by t. KuCoin itself was replicated by R277 (2 of 4
  sets), and R438 confirmed those books on M468. This lane adds no new choice, but it is not independent evidence for the
  rule either.
- **What follows (frozen):** the book SURVIVES and the paired difference is positive, so the PREREG names a forward paper
  lane of the five-venue book as the next id. The paired gain is not significant and is level on constant notional. A
  forward lane would therefore be for the steadier daily path, not for a higher return. The forward KuCoin lanes R279 A and
  B already watch KuCoin's live funding.

## Limits
- **Seen data, current-survivor universe** (R275's manifest plus R277's KuCoin column). Gate 0 only.
- **Fills** at daily last-trade closes; KuCoin prices are daily bars, the other venues hourly. No mark prices. Moving
  collateral across five venues is not priced, and it is harder with more venues.
- **Costs** are the flat 7/14/21 bp per leg of R275 and R277, not measured KuCoin book costs.
- **Venue access:** whether the owner can hold positions on all five venues from France was not checked. It is the
  owner's call before any real use.
- **Capital:** returns on entry notional; peak margin is above average (see R438's limits).
