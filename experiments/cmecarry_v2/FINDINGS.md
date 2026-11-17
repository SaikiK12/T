# FINDINGS: cmecarry_v2 (R502). CME bitcoin future against the Binance perp, 2021-05..2026-09

**Verdict: CARRY_WEAK.**
- The primary book nets **+2.89%/yr** with a Newey-West t of 3.19. It is positive, but below R275's 4.13%/yr hurdle.
  - The book: BTC, MBT costs, 1x, 2021-05-03..2026-09-30.
- It turns negative at twice the costs (−1.19%/yr).
- No forward paper lane is earned. The PREREG reserves one for CARRY_PASS.

Run on 2026-11-17 by `scripts/run_cmecarry_v2.py run`. The PREREG and its eight input hashes verified first.
- Results: `results/report.json`, `results/btc_daily.csv` and `results/eth_daily.csv` (one row per CME settlement day).
- The Databento files are R501's 125 pulls, pinned by the manifest hash. Nothing new was bought for this run.

## Primary book (BTC at MBT costs)
| | Value |
|---|---|
| Settlement days | 1,362 over 5.41 years |
| Gross / net | **6.97 / 2.89 %/yr** (NW t 3.19) |
| Days in position | 25.4% (long future 16.0% of days; the rest short future, long perp) |
| Trades / rolls | 100 / 19 |
| Mean CME cost per side (fee + half-spread) | 10.9 bp |
| Months with a measured spread | 100% (130 contract-months) |
| Median half-spread, MBT | 1.7 bp front month, 6.5 bp second month |

**Where the cost goes.** This split is computed here from the daily file. It is not a pre-registered cell.
- The book's costs total about 4.1 points a year:
  - CME: about 3.1 points (fee plus half-spread);
  - Binance: about 1.0 point.
- On the same window at big-contract costs (5 BTC, $7 a side), CME's mean cost per side falls to 5.4 bp. The book then
  nets +4.51%/yr with t 4.75, above the hurdle.
- So the **micro contract's per-contract fee** is what keeps the book under the hurdle.
  - At $2.50 a side on 0.1 BTC, the fee is about 6 bp at $40k BTC.
  - The book clears 4.13%/yr only with an all-in MBT fee of roughly $0.65 a side or less. That is a linear estimate
    between the two cost cells.
  - Room 2's agents reported $1.6-2.5 a side all-in. Those figures are unverified, and none is near $0.65.
  - The big contract is $80k-600k of notional over the window, far outside a $10k book.

## Cost sensitivity (primary)
| Costs | Net %/yr | NW t |
|---|---|---|
| 1x | **2.89** | 3.19 |
| 2x | −1.19 | −1.21 |
| 3x | −5.28 | −4.11 |

## By year (primary, 1x)
| Year | Net %/yr | Gross %/yr | NW t | In position | Mean f7 | Mean b |
|---|---|---|---|---|---|---|
| 2021 (from 05-03) | 7.03 | 14.88 | 2.56 | 60% | 14.6 | 4.1 |
| 2022 | 2.51 | 10.79 | 0.73 | 31% | 4.2 | −2.1 |
| 2023 | 2.48 | 6.22 | 2.56 | 15% | 7.4 | 9.9 |
| 2024 | 5.16 | 8.45 | 2.06 | 27% | 12.2 | 11.3 |
| 2025 | 0.11 | 0.75 | 0.36 | 8% | 5.1 | 8.0 |
| 2026 (to 09-30) | 0.92 | 2.09 | 1.26 | 21% | 2.9 | 5.4 |
| 2024-01..2026-09 | 2.17 | 3.92 | 2.22 | 18% | | |

- **The spread has compressed.** Funding (f7) and basis (b) both fell after 2024, and they now sit close together. In
  2025 the book was in position on 8% of days and earned nothing.
- This matches the papers in room 2 (He, Manela, Ross and von Wachter; Borri, Liu, Tsyvinski and Wu): spot-perp and
  basis carry compressed sharply from 2024.

## Also reported, never chosen
| Cell | Net %/yr | NW t | Note |
|---|---|---|---|
| ETH at MET costs, 2021-12-06..2026-09-30 | **−2.70** | −2.42 | MET is 0.1 ETH ($100-480 over the window): $0.60 a side is 12-60 bp, and the mean CME cost is 35.9 bp a side |
| ETH at MET, 2x / 3x | −11.20 / −19.69 | | |
| BTC/ETH half and half, micros, 1x | −0.20 | | |
| BTC big contract, 2021-05..2026-09 | 4.51 | 4.75 | $80k-600k a contract over the window |
| ETH big contract, 2021-12..2026-09 | 3.14 | 3.27 | $50k-240k a contract over the window |
| BTC big contract, 2020-01-08..2021-04-30 (before MBT) | 15.60 | 2.68 | bull-market basis; spread unmeasured (one tick) |
| ETH big contract, 2021-02-16..2021-12-03 (before MET) | 16.76 | 2.76 | same |
| BTC thresholds 5 / 2.5 | 2.93 | 2.67 | 199 trades, 54% in position |
| BTC thresholds 20 / 10 | 1.28 | 2.24 | 18 trades |
| BTC thresholds 0 / 0 (always in) | −1.01 | −0.60 | gross 14.6, 236 trades, 81 rolls |
| ETH thresholds 5 / 2.5, 20 / 10, 0 / 0 | −11.04, −0.45, −26.42 | | |

**Expiry check.**
- The rule's expiry matched the data's roll in 6 of 81 BTC front-month changes. In the other 75, the data's front
  month changes on the expiry Friday itself.
  - On that day, the expiring contract has no 15:00 Chicago settlement: its final settlement is at 16:00 London,
    earlier.
  - The check's strict inequality flags that. The six that pass are 2021-12 and 2025-12..2026-04.
- The rule never holds a contract inside 14 days of its expiry. So none of these touch the returns.
- 2021-12-31 has c.0 equal to c.1 in the data. That is one day, and its held contract is the right one.

## What this says, and what it does not
- **A real but small edge.** The CME basis and Binance funding do drift apart, and a rule that bets on them coming back
  together earns about 7%/yr gross at BTC, with t above 3 net. So the spread is not noise.
  - At a $10k scale, the micro contract's fixed fee takes almost half of that gross.
  - What remains is below cash, and negative at 2x costs.
- **The edge is fading.** Since 2024 it nets 2.2%/yr. 2025 and 2026 are near zero.
- **ETH is worse.** The micro ether contract is too small for its fixed fee.
- **Not modeled** (as the PREREG says):
  - margin on two venues;
  - whether settlement prices are tradable (TAS on MBT is unverified);
  - weekend gaps before 2026-05-29;
  - the owner's actual broker fee from France.
  - The hurdle also treats the whole notional as capital. If idle collateral earned the T-bill rate (CME accepts
    T-bills as margin), the right bar for the overlay would be lower.
    - That is a framing question for every carry book in the lab, not a reading of this one.
    - It needs its own registered test before it changes any verdict.
- **Days, not months.** This answered from five years of CME settlements and recorded books, for $0.25 of data.
  Forward paper would have needed years.

## Lineage and process
- R501 ran the same frozen rule and crashed at its first summary, before any statistic (see
  `../cmecarry_v1/NOTES.md`).
- R502 is registered with 0 trials. R501 already counted this rule's single trial.
- Program trials at the freeze: 9,785,314.
- The registry row stays REGISTERED/PENDING: rewriting journal rows is not allowed. The verdict lives here and in
  `registry/methods.csv` (M548).
