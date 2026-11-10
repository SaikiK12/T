# FINDINGS: carry_v2_audit_kc_v1 (R438)

**Verdict: both books SURVIVE the frozen rule (registry: DONE, CONFIRMED).**
- R279's two forward KuCoin carry books keep their edge on R277's archive under the corrected M468 engine
  (`lab/xfund_v2.py`): A gate+kucoin and B binance+kucoin.
- With R437, every forward cross-venue carry book except R294 (mexc+lighter, left to M469 with measured costs) has now
  passed the accounting audit.
- **Measured, post hoc:** v2's higher funding comes from notional drift: +3.28 points a year on gate+kucoin, +1.49 on
  binance+kucoin. Most of that drift is not leverage. It is a covariance: funding spreads widen on legs whose price
  rose since entry. This also corrects R437's reading (addendum there).
- This is gate 0 on seen rows. It can only lower confidence, and it did not. The forward lanes remain the decider.

## Read
- **Run once** on 2026-11-10 with `scripts/run_carry_v2_audit_kc.py --run` (exit 0, about 75 s). The PREREG
  (c256d996) and its 14 inputs matched.
- **Order:**
  - CLAIM posted on #7.
  - PREREG frozen and registry row R438 appended in 2063911, then pushed, then the run.
- **Data identity:** in the run and at plumbing, v1 reproduced R277's frozen 1x daily net to 5e-11 on both books.
- **Outputs:**
  - `results/books.csv` and `report.json`.
  - `results/daily.csv`: v1 and v2 daily nets at 1x, 2x and 3x.
  - `results/trades_v2.csv` and `run.log`.
- **Post-hoc diagnostics, descriptive, no decision:**
  - `diagnostics/decomp.py` / `decomp.out`: R437's funding, price and cost split, and the sensitivity without blowout
    and dead-leg trades.
  - `diagnostics/drift.py` / `drift.out`: the funding drift on this lane's two books and on R437's seven.

## Results (%/yr on book capital; costs 7, 14 and 21 bp per leg)
| Book | Forward | v1 1x | v1 NW t | v2 1x | v2 2x | v2 3x | v2 NW t | v2 halves bp/day | v2 2025+ bp/day | v2 max DD (v1) | v2 top-10-day share | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gate+kucoin L14d th5% K20 | R279 A | +11.76 | 11.41 | +14.98 | +13.57 | +12.17 | 9.63 | +1.88 / +6.32 | +7.57 | -1.6% (-0.7%) | 17% | SURVIVES |
| binance+kucoin L14d th5% K20 | R279 B | +10.80 | 11.17 | +11.28 | +9.84 | +8.40 | 8.50 | +1.39 / +4.79 | +5.79 | -4.8% (-2.3%) | 14% | SURVIVES |

- **Above cash:** both books beat the 4.13% T-bill hurdle at 1x, 2x and 3x.
- **Exits under v2:**
  - Almost all exits are spread exits (1115 and 1150), with 20 still open at the end.
  - Blowouts: 4 and 2. Dead legs: 1 and 1. Unlike R437's Binance-and-Gate books, exotic exits carry nothing here.
  - Their share of gross is 0.2-0.5%. Unobserved pair-days: 43 and 45. Average pairs held: 19.6.
- **Drawdown:** v2's max drawdown is about twice v1's on both books. binance+kucoin goes from -2.3% to -4.8%.

## Why v2 differs from v1 (post hoc, `diagnostics/decomp.out`, `diagnostics/drift.out`)
Annual P&L on book capital, v1 → v2:

| Book | Funding | Price | Costs | v2 funding on constant entry notional | Drift | Mean notional / entry |
|---|---|---|---|---|---|---|
| gate+kucoin | 13.39 → 17.00 | −0.22 → −0.62 | 1.42 → 1.40 | 13.72 | +3.28 | 1.054 |
| binance+kucoin | 12.72 → 13.95 | −0.49 → −1.22 | 1.44 → 1.44 | 12.46 | +1.49 | 1.040 |

- **The drift is measured, not assumed.**
  - The diagnostic replays the same v2 books.
  - Each held pair-day's funding is paid twice: on the leg's current notional, as v2 does, and on constant entry
    notional.
  - The first sum equals v2's funding exactly (check column in `drift.out`).
- **Most of the drift is not leverage.**
  - Average notional is only 4-5% above entry. Leverage alone would add about 13.7 × 0.054 ≈ 0.7 points on
    gate+kucoin and 0.5 on binance+kucoin.
  - The rest (about 2.5 and 1.0 points) is a covariance: funding spreads are wider on legs whose price has risen since
    entry. Rallies crowd longs onto one venue.
  - A real position holds a fixed quantity, so it would collect this covariance with only slightly more average
    margin.
  - Peak margin is higher than average. The drawdown doubling is the visible cost.
- **On constant notional** (v2 net minus drift): gate+kucoin is about +11.7%/yr and binance+kucoin about +9.8%/yr. These
  are near v1's levels. They are the conservative figures.
- **Sensitivity without blowout and dead-leg trades** (5 and 3 trades removed): +14.93%/yr (t 9.91) and +11.19%/yr
  (t 10.07). Essentially unchanged.

### The same measurement on R437's books (correcting R437's point 1)
| Book (R437) | v1 funding | v2 funding | Constant-notional | Drift | Mean notional / entry | Leverage share of drift |
|---|---|---|---|---|---|---|
| gate+hyperliquid (R278 A) | 11.47 | 14.11 | 11.45 | +2.65 | 1.117 | ~1.3 |
| binance+hyperliquid | 9.81 | 12.04 | 9.83 | +2.21 | 1.117 | ~1.2 |
| binance+mexc (R278 B) | 7.58 | 7.60 | 7.59 | +0.01 | 0.910 | n/a |
| all four | 14.06 | 17.28 | 15.00 | +2.28 | 1.093 | ~1.4 |
| gate+mexc (R278 C) | 22.34 | 24.34 | 21.93 | +2.40 | 1.067 | ~1.5 |
| binance+gate (R390 A) | 11.51 | 13.73 | 12.58 | +1.15 | 1.014 | ~0.2 |
| hyperliquid+mexc | 12.25 | 12.70 | 12.25 | +0.45 | 0.988 | n/a |

- "Leverage share" is (mean notional / entry − 1) × constant-notional funding. It is an approximation: the notional is
  averaged over both legs and over pair-days.
- **Drift is the whole funding gain** on the Hyperliquid books and gate+mexc: constant-notional funding equals v1's.
  - **Leverage is about half of it** on those books.
  - **On binance+gate (R390 A) leverage is almost none:** its +1.15 is mostly covariance.
  - **R390 A and all four keep about +1 point from the other v2 changes:** constant-notional funding is 12.58 against
    v1's 11.51 for R390 A, and 15.00 against 14.06 for all four. The likely source is Gate's freshness rule, which
    admits more coin-days.
- **R437's statement** "it is leverage drift, not new edge, and the v1 figure is the fairer capital-neutral number" is
  therefore only partly right.
  - v1 is the conservative number.
  - A fixed-quantity book would earn part of the gain on near-unchanged average capital.
  - Neither reading changes any decision.

## Read against the program
- **Program trials:** 9,784,981, including this lane's 2.
- **Inherited selection:** the two books were the 2 of 4 sets that passed R277's replication rule, and R277 ran R275's
  best rule (best of 560). This audit inherits both selections and adds no evidence beyond R277's.
- **What it changes:**
  - The accounting doubt now covers every forward carry book but R294.
  - That doubt is cleared on held data for gate+kucoin, binance+kucoin, and R437's four forward books.
  - The constant-notional figures are the ones to compare with the forward lanes' frozen accounting.

## Limits
- **Seen data, current-survivor universe** (R277's): gate 0 only.
- **Fills** at daily last-trade closes on both venues; KuCoin prices are daily bars. No mark prices. Moving collateral
  between venues is not priced.
- **Fixed-quantity capital:**
  - v2 reports returns on entry notional. A margin-aware base (R280) was not combined with v2.
  - The drift diagnostic gives average notional, not peak margin.
- **The covariance reading is post hoc** and was not registered. It does not support a new rule without its own
  PREREG.
- **The 20% blowout threshold** and the flat 7/14/21 bp costs are R437's and R277's, not measured KuCoin book costs.
