# FINDINGS: xvfund_v1 (R470), cross-venue funding carry on the same US stock perp, trade.xyz against Lighter

**Verdict: NULL.** Sample A (2025-12-03 .. 2026-08-31, 272 days) earns +1.36%/yr on capital at 1x, so its excess
over the 4%/yr hurdle is **-2.64 points** (Newey-West t -1.22). The bar was +3.0 points with t ≥ 2.0. B (71 days) is
+7.42 points (t 0.71), and almost all of it is price noise between the two venues, not carry.

**The carry is too thin, not just too costly.** Before any cost, A's excess is +0.28 points (+4.28%/yr gross).
From 2025-12-19 on, after xyz's funding change, it is +1.79 points. Both are below the +3 bar even at zero cost.

Run: `python scripts/run_xvfund.py`, 2026-11-11, after the freeze (PREREG sha256 `19eefce1`, commit `f7204243`).
- The PREREG verified and its 8 inputs matched; the 200 bar and funding files matched `data/xvfund/manifest.json`
  (`results/run.log`).
- The data were fetched after the freeze by the frozen `scripts/fetch_xvfund.py bars --start 2025-11-01T00:00:00Z
  --end 2026-11-11T00:00:00Z`. Provenance is in `docs/provenance/xvfund.json` (combined sha256 `7d2ec82d`).
- **Universe in practice:** 39 of the 50 pairs ever traded.
  - Six Lighter markets (AVGO, BE, GME, NOK, QCOM, WDC) have no candle in the window. Their funding is flat at
    Lighter's interest-only baseline (0.0004%/h). R465's fetch of the same markets was empty too.
  - Four more (AAOI, ARM, IREN, KORU) have 150 or fewer hourly candles.
- **Book:** 241 trades (233 closed, 8 open at the end); median hold 5 days, mean 7.0.
  - Entries: 130 shorted xyz and 111 shorted Lighter. The median |spread| at entry was 13.7%/yr.
  - The book held 5.0 of its 10 slots on average in A and 4.7 in B. A had 11 days with nothing held.

## Decision samples (on capital; excess = net minus the 4%/yr hurdle)

| sample | days | cost | net %/yr | excess pts | NW t (lag 10) | drawdown |
|---|---|---|---|---|---|---|
| A | 272 | 1x | +1.36 | **-2.64** | -1.22 | -1.65% |
| A | | 2x | -1.55 | -5.55 | -2.44 | -2.13% |
| A | | 3x | -4.46 | -8.46 | -3.51 | -3.38% |
| B | 71 | 1x | +11.42 | +7.42 | 0.71 | -2.30% |
| B | | 2x | +8.80 | +4.80 | 0.45 | -2.41% |
| B | | 3x | +6.19 | +2.19 | 0.20 | -2.51% |

- **Frozen rule:** A needs a 1x excess of at least +3.0 points, t ≥ 2.0, a 2x excess above 0 and a drawdown above -5%.
  A fails the first three, so the lane is NULL, whatever B shows.
- **Cost sensitivity:** each extra cost unit takes about 2.9 points a year in A. The 1x unit is 4.9 bp a side on
  growth-mode markets (xyz 0.9 bp + Lighter 0 + 2 × 2 bp slippage).
- **Read against the program's 9,785,245 trials:** a NULL needs no deflation. Nothing here would survive it anyway.

## Where the money went (1x, %/yr on capital)

| sample | funding | price | cost | net | daily sd | top-10-day share |
|---|---|---|---|---|---|---|
| A | +3.57 | +0.70 | -2.91 | +1.36 | 0.119% | 3.61 |
| B | +5.71 | +8.32 | -2.61 | +11.42 | 0.381% | 3.01 |

- **Funding.** The carry the rule harvests is about 7%/yr per deployed slot in A: 3.57%/yr on capital at half
  deployment. That is about half the median spread at entry (13.7%/yr): the trailing spread does not persist
  in full after entry.
  - A closed trade earned +14.9 bp of funding on its slot on average, against a 9.8 bp round trip.
  - That is not enough to beat a 4%/yr hurdle on the full capital.
- **December 2025 lost 1.23% of capital on funding.** Lighter's stock perps had just listed and their funding spiked.
  - On COIN, Lighter's longs paid 2.86% over 2-4 December, at up to 0.27% an hour.
  - The book had entered on the trailing 7-day spread and was then paid against.
  - This happened before xyz's 2025-12-19 funding change. Post hoc, 2025-12-03 .. 12-18 (16 days) nets -24.8%/yr.
    2025-12-19 .. 2026-08-31 (256 days) nets +3.0%/yr: funding +4.89, cost -2.79 and price about +0.9.
- **Price.** The two legs track each other: price adds +0.7%/yr in A.
  - B's +8.3%/yr is mostly three days in early November 2026 (+0.45 to +0.56% of capital each).
  - B's daily sd is 3.2 times A's. This is venue-gap noise, not something the rule controls.
- **Forced exits on Lighter's weekend gaps.**
  - 96 of 241 exits were forced because a close was missing, all on the Lighter leg. 56 of them fell on Sunday:
    the Sunday close needs a Lighter trade in the bars opened 21:00-23:00 UTC on Saturday, and often there is none.
  - Each forced exit and re-entry costs a round trip, which is part of the 2.9 points of cost.
  - A carry-forward price would avoid them, but that is a different rule, untested here. It would not lift A above
    the bar: A's excess at zero cost is +0.28 points.
- **Exit reasons:** spread 136, missing price 96, split guard 1, open at the end 8.

## What a forward lane would need (from A's sd)
- A's daily sd of 0.119% gives an annualized se of about 4.6 points at 90 days and 3.2 at 180 days.
- So the detectable excess (t 2.0, 80% power) would be about **13 points at 90 days and 9 at 180**.
- A's measured excess is -2.6 points (+0.3 before costs). No forward lane is earned, and none would be informative.

## What this closes, and what stays open
- **Closed (M527 on this pair):** trailing-funding carry between xyz and Lighter on the same US stock perp, at taker
  costs, with idle slots in cash. The baseline gap (xyz about 5.5%/yr, Lighter about 3.5%/yr) and its dispersion
  together do not clear a 4%/yr hurdle.
- **Not tested:**
  - maker entries;
  - a fully deployed book that scales the held slots up;
  - a carry-forward price over Lighter's weekend gaps;
  - pairs listed after 2026-11-10.
  Each would be a new lane. None of them changes the gross figure enough to matter: +0.28 points in A before costs.
- **Pattern with R462, R465 and R468:** effects on these new stock-perp venues were largest early (launch-period
  funding here) and flat afterwards.

## Limits
- Survivor universe (pairs listed on 2026-11-10); growth flags as of 2026-11-10; daily closes on last trades.
- Costs are assumed. The venues' books were recorded only from 2026-11-10.
- The margin and transfer risk of two separate venues is not modelled.
- A and B overlap the windows of R462, R465 and R466, whose funding entered weekend returns.

Files: `results/summary.json`, `results/daily.csv`, `results/trades.csv`, `results/run.log`.
