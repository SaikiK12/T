# FINDINGS: vrpexec_v1 (R410). Cheaper hedging recovers the premium; a resting maker sale gives it back to adverse selection

**Verdict: NULL for BTC and for ETH by the frozen rule. 2 trials, gate 0, post-hoc after R409 (disclosed).**

The primary cell (maker sale, band 0.10, maker-first hedge) is negative at 1x on both coins.
- The run: `run.log`, 2026-11-05 21:03 UTC, PREREG `a0a5db97a03c`, 14 inputs matched. One run.
- Results: `results/summary.json` and `results/weeks.csv`.
- **Coverage:** 292 BTC weeks and 289 ETH weeks, the same as the plumbing counts.
  - BTC skips: 3 no reference, 4 no price path.
  - ETH skips: 7 no reference, 3 no price path.

## The primary cell: maker sale, band 0.10, maker-first hedge

| Check (PASS needs all six) | Bar | BTC | ETH |
|---|---|---|---|
| 1. Mean at 1x | > 0 | −4.2 bp/wk, no | −14.6 bp/wk, no |
| 2. NW t at 1x (lag 2) | ≥ 2.24 | −0.38, no | −1.07, no |
| 3. Mean at 2x | > 0 | −32.7, no | −45.3, no |
| 4. 1x in each half (2021-23 / 2024-26) | > 0 | −2.7 / −6.0, no | −14.9 / −14.2, no |
| 5. 5%-trimmed mean at 1x | > 0 | +5.3, yes | −7.6, no |
| 6. 1x without the 10 best weeks | > 0 | −17.7, no | −31.1, no |

- Primary at 3x: −61.3 (BTC) and −75.9 (ETH) bp/wk.
- Worst week: −985 and −1,021 bp. Maximum drawdown: 43% and 53% of one coin.

## All twelve cells (reported, none promoted)
Mean bp a week. Columns: m = 0 (mid, no fees) and 1x / 2x / 3x; the 1x t; the 1x halves; and the median hedge turnover
(coins a week).

| Cell | BTC 0x | BTC 1x (t) | BTC 2x / 3x | BTC halves | ETH 0x | ETH 1x (t) | ETH 2x / 3x | ETH halves | Turnover |
|---|---|---|---|---|---|---|---|---|---|
| taker / hourly | +42.5 | −13.7 (−1.45) | −69.9 / −126.1 | −1.9 / −26.5 | +45.9 | −13.3 (−1.11) | −72.4 / −131.6 | −6.8 / −20.4 | 7.7 |
| taker / band10 | +40.9 | +7.8 (0.75) | −25.3 / −58.4 | +16.7 / −1.8 | +37.8 | +2.2 (0.16) | −33.5 / −69.1 | +7.3 / −3.5 | 2.9 |
| taker / band20 | +41.4 | +13.0 (1.09) | −15.3 / −43.7 | +24.6 / +0.4 | +37.0 | +6.4 (0.40) | −24.2 / −54.8 | +10.3 / +1.9 | 2.0 |
| taker / hourly_mk | +36.4 | +0.4 (0.04) | −35.7 / −71.7 | +11.2 / −11.4 | +38.3 | −0.1 (−0.01) | −38.6 / −77.0 | +5.4 / −6.3 | 7.7 |
| taker / band10_mk | +38.2 | +11.9 (1.13) | −14.5 / −40.8 | +20.1 / +2.9 | +34.3 | +5.7 (0.43) | −22.8 / −51.4 | +10.5 / +0.4 | 2.9 |
| taker / band20_mk | +39.7 | **+15.6 (1.30)** | −8.5 / −32.6 | +26.9 / +3.3 | +34.8 | **+8.6 (0.54)** | −17.7 / −43.9 | +12.4 / +4.3 | 2.0 |
| maker / hourly | +13.8 | −30.9 (−3.05) | −89.0 / −147.1 | −26.8 / −35.3 | +12.2 | −33.8 (−2.69) | −94.7 / −155.6 | −33.4 / −34.2 | 7.7 |
| maker / band10 | +13.5 | −8.4 (−0.75) | −43.7 / −78.9 | −6.1 / −10.8 | +4.6 | −18.2 (−1.32) | −55.9 / −93.6 | −18.2 / −18.3 | 2.9 |
| maker / band20 | +14.6 | −2.6 (−0.21) | −33.2 / −63.7 | +2.3 / −7.9 | +4.4 | −13.3 (−0.83) | −46.0 / −78.7 | −13.6 / −13.1 | 2.1 |
| maker / hourly_mk | +7.9 | −16.8 (−1.65) | −54.9 / −93.0 | −13.7 / −20.3 | +4.6 | −20.8 (−1.68) | −61.2 / −101.6 | −21.4 / −20.2 | 7.6 |
| **maker / band10_mk** | +10.9 | **−4.2 (−0.38)** | −32.7 / −61.3 | −2.7 / −6.0 | +1.1 | **−14.6 (−1.07)** | −45.3 / −75.9 | −14.9 / −14.2 | 2.9 |
| maker / band20_mk | +13.0 | +0.1 (0.01) | −26.2 / −52.5 | +4.7 / −4.9 | +2.3 | −11.1 (−0.69) | −39.4 / −67.7 | −11.5 / −10.7 | 2.0 |

- **Cross-check against R409.** Taker / hourly (−13.7 / −13.3 at 1x) reproduces R409 (−12.2 / −18.0). It uses
  mark-based prices, a point-in-time strike and a few fewer weeks.
- **Maker-first hedge orders** filled on 99% of hours on both coins, on 1-minute trade-throughs.

## What each lever did (at 1x, from the table)
- **The hedge levers work.**
  - A 0.10 band cuts turnover from 7.7 to 2.9 coins a week, and a 0.20 band to 2.0.
  - Maker-first orders cut the fee per coin from 5 to about 2 bp.
  - Together they take BTC's hedge fee from 38.9 to 9.0 bp a week: taker / hourly against maker / band10_mk in
    `cost_split_1x_bp`.
  - With the taker sale, that turns −13.7 into +11.9 (band 0.10) and +15.6 (band 0.20) for BTC, and −13.3 into +5.7
    and +8.6 for ETH.
  - No hedge cell reaches t 1.5, every one is negative at 2x, and the 2024-26 half is +0.4 to +4.3 bp.
- **The maker sale does harm. It is adversely selected.** At m = 0, the maker sale earns 29 bp (BTC) and 34 bp
  (ETH) a week less than the taker sale. Split by how many legs filled (post-hoc, from `weeks.csv`):

  | Legs filled | BTC weeks | Maker − taker at 0x | at 1x | ETH weeks | at 0x | at 1x |
  |---|---|---|---|---|---|---|
  | none | 70 | −11.1 | −11.0 | 75 | −13.5 | −13.3 |
  | one | 181 | **−43.1** | **−30.3** | 173 | **−51.2** | **−36.3** |
  | both | 41 | +4.8 | +30.1 | 41 | +3.0 | +32.7 |

  - In most weeks only one leg fills: 45% of BTC legs, 44% of ETH legs, with a median of 45 minutes to fill.
  - It is the leg the market is moving toward: a call is lifted as the price rises. It is sold at a price set before
    the move and held unhedged until noon.
  - When both legs fill, the ask price pays as intended (+30 bp at 1x). That happens in only 14% of weeks.
  - Weeks with no fill lose 11-13 bp: the sale comes three hours later at the mark, and the hedge starts later.
  - The fill model is a trade-through proxy with no queue. A real resting order would fill less often and only on more
    aggressive buyers, so the true result is unlikely to be better.

## Reading
- **R409's cost problem was mostly the hedge, and the hedge can be fixed.** A band and maker-first orders cut the hedge
  bill by about 30 bp a week.
- **What remains is too small and is shrinking.**
  - The best cell (taker / band20_mk) is +15.6 bp/wk on BTC (t 1.30) and +8.6 on ETH (t 0.54). It is negative at 2x,
    and its 2024-26 half is +3.3 and +4.3.
  - R411 shows why: the 30-day premium fell from about +17 vol points (2021) to +1 (BTC, 2026).
- **A passive sale at the ask is not a free spread here.** A static resting offer in a moving market is picked off on
  the side that is about to cost. The maker lever, and therefore R412's planned fill calibration, is dropped.
- **The family's conclusion at our costs:**
  - The crypto variance premium exists gross (R409, R411).
  - Weekly ATM straddles do not carry it to a significant net result on 2021-26, even with cheap hedging.
  - Its recent size is a few bp a week.
- **Program context.** The read is against 9,784,334 program trials. None of the twelve cells would survive that even
  if it were the primary.

## Limits
These are as frozen in the PREREG:
- the trade-through fill model without queue;
- spreads from one snapshot;
- the reference IV from the last trade's mark;
- 1-minute hedge fills;
- settlement at the perp, with margin and tails not modeled.

The adverse-selection split above is post-hoc and descriptive.
