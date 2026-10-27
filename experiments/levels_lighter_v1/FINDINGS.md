# FINDINGS: levels_lighter_v1 (R337), R333's level trades on Lighter's own prices at its measured book cost

**Answer: NULL (gate 0). Four of the five frozen checks fail.** On Lighter, R333's break-or-rebound trades earn
+12.2 bp gross a trade over 2025-02..2026-09. Lighter's measured book cost takes half of that at 1x and all of it at
2x. The automated (API) route for M412 is closed at this scope.

| Check, primary book LZ_SUM | Result | Pass? |
|---|---|---|
| 1x t ≥ 2 | +171.6 bp/day, t 1.00 | no |
| 2x mean > 0 | −3.5 bp/day | no |
| 1x without the best 10 days > 0 | −102.8 bp/day | no |
| Both halves > 0 at 1x | Feb-Nov 2025 +541.1, Dec 2025-Sep 2026 −196.7 | no |
| 1x without the best coin (ZEC, 13.8% of the net) > 0 | +147.9 bp/day | yes |

- **Units:** bp per day is the constant-size book, each day's summed net in bp of one trade's notional.
- **Trades:** 17,322 on 92 coins, about 28.5 a day.
- **Per trade:** gross +12.2 bp; net +6.0 at 1x, −0.1 at 2x and −6.3 at 3x. The break-even is 6.1 bp a side.

**Lighter's prices are not the problem.**
- The same trades on Binance's prices earn +11.5 bp gross, against +12.2 on Lighter's.
- The two venues' trade returns correlate 0.9986. The median absolute gap is 5.5 bp a trade, and the mean gap favours
  Lighter by 0.6 bp.

**The model still has direction.** Random sides on the same trades lose −6.1 bp a trade; none of 1,000 draws reached
the model's +6.0. The model's edge over a coin flip is about 12 bp a trade, which is too small for this venue's cost.

## Lane details
- **Registry row:** R337, 6 trials. PREREG sha256 `ebbee742…bb37`, frozen and pushed in `68c8f0a` before the run,
  and claimed on #7 (comment 6428171638).
- **Run:** 2026-10-26 21:51 UTC. All 256 inputs matched their frozen hashes.
- **Reproduce:** `python scripts/run_levels_lighter.py --run` writes `results/summary.json`. The run log is
  `run.log`.
- **Gate 0:** R333 read these hours on Binance and fit this model.

## The books (bp per day of one trade's notional; t in brackets)
| Book | Trades | Gross | 1x | 2x | 3x | 1x per trade | Break-even, bp a side |
|---|---|---|---|---|---|---|---|
| **LZ_SUM** (primary) | 17,322 | +346.6 (2.01) | **+171.6 (1.00)** | −3.5 (−0.02) | −178.5 (−1.04) | +6.0 | 6.1 |
| LP1_TRADES (R333's stricter threshold) | 9,586 | +304.0 (1.99) | +103.6 (0.69) | −96.8 (−0.65) | −297.2 (−1.99) | +6.6 | 9.6 |
| LZ_BINANCE (same trades, Binance prices) | 17,322 | +328.4 (1.92) | +153.4 (0.90) | −21.7 (−0.13) | −196.7 (−1.15) | +5.4 | 5.8 |
| THROUGH (always the breakout) | 25,938 | +208.2 (0.76) | −262.2 (−0.97) | | | −6.1 | |
| AWAY (always the rebound) | 25,938 | −208.2 (−0.76) | −678.6 (−2.44) | | | −15.9 | |

- **R333's day-mean convention:** LZ is +2.6 bp/day at 1x (t 0.49), −3.4 at 2x and −9.4 at 3x.
- **By quarter, LZ per trade:**

  | | 2025Q1 | Q2 | Q3 | Q4 | 2026Q1 | Q2 | Q3 |
  |---|---|---|---|---|---|---|---|
  | Gross (bp) | +43.3 | +29.4 | +10.9 | +16.2 | −4.2 | +15.5 | −3.4 |
  | 1x (bp) | +37.2 | +22.9 | +4.3 | +9.3 | −10.7 | +10.1 | −8.0 |

  The edge has faded. Over the last ten months it is about zero before costs.
- **Coins:** 54 of the 92 traded coins are positive at 1x.
  - The largest shares of the net are ZEC (13.8%), WLD, UNI, SOL and ONDO.
  - The worst are ADA, LTC, AAVE, CRV and XPL.
  - Results do not sort by cost: coins at under 1.5 bp a side earn +8.1 bp a trade at 1x; coins at 3-6 bp earn +1.3.
- **Risk at 1x:**
  - one trade's 1% tail is −8.7% and its 99% tail is +9.0%;
  - the book's max drawdown is 12.2 trade notionals and its worst day −1.85;
  - up to 45 trades are open at once (p95 27).

## Reading
- **Trials:** the program goes from 9,478,999 to 9,479,005 trials with R337's 6.
- **Against R336.** R336 found +21.1 bp gross a trade on MEXC's 55 zero-fee coins over 2022-26. On Lighter's 97 coins
  over 2025-26, the same model earns +12.2.
  - R336's recent strength sat on coins chosen by October 2026's zero-fee list, many of them 2025 listings that
    trended. Its THROUGH control earned +21.5 and +40.7 bp a trade in 2025 and 2026.
  - On Lighter's broader set, THROUGH earns +4.9 gross, and the model's 2026 trades are about zero before costs.
  - That supports reading R336's recent result as coin selection more than the model.
- **The executable routes for the level model, all measured:**
  - MEXC API: 6/8 bp a side, about R336's 10.5 bp break-even. Closed.
  - Lighter API: closed by this lane.
  - MEXC web, manual (R336's PZ_CAP7, 7 a day): t 2.02 at 1x and not significant at 2x, with 2026 at −5.3 bp a trade.
  - What is left is not worth a forward lane on its own. **R336's forward lane (task 130) is dropped.**

## Costs (1x, 2x, 3x)
- **The cost:** each coin's median cost of a $1k market order walked through Lighter's shown book, over 20 recorder
  snapshots (October 2026), with a 1 bp floor and fee 0.
  - The median coin pays 5.4 bp a side, and the 90th percentile 36.6.
  - Shown above at 1x, 2x and 3x on entry and exit.
- **Excluded:** 777 events on 10 coins Lighter has since delisted. They have no book to measure, so this is a
  survivorship gap.

## Not tested here
- **Maker (limit) entries on Lighter.** They pay no spread and wait no 300 ms, but face adverse selection and missed
  fills. The lab's earlier maker lanes (R170, R193, R194) were NULL for that reason.
- **Exits read on Lighter's closes.**
- **Lighter's books before October 2026.**
