# FINDINGS: tlteom_v1 (R473). The end-of-month Treasury rally on TLT

**Verdict: PARTIAL** (frozen rule, one run on 2026-11-12 04:02 UTC, PREREG `ae000b89`).
- The effect replicates on TLT inside the paper's sample (R).
- It is still there after 2018 before costs (U).
- At trade.xyz's TLT perp cost it is too thin. U's 1x net is +13.0 bp a month at t 0.95, below the 1.0 bar, and 2026
  is negative.
- xyz:TLT's measured funding since listing (post hoc, below) is about four times the assumed 5.5%/yr. At that level
  the net edge is gone.
- No forward lane is earned.

## Main result (long TLT over the last 3 trading days of each month, close prices)
| Sample | Months | Gross bp | t | Net 1x | t | Net 2x | Net 3x | Sharpe 1x | Hit 1x |
|---|---|---|---|---|---|---|---|---|---|
| R 2002-08..2018-12 | 197 | +39.1 | 4.15 | +27.3 | 2.90 | +21.5 | +15.7 | 0.72 | 0.61 |
| U 2019-01..2026-10 | 94 | +24.7 | 1.79 | +13.0 | 0.95 | +7.2 | +1.4 | 0.34 | 0.55 |

- **Costs:** one unit is a 5.8 bp round trip (xyz growth-mode taker 0.9 bp plus 2 bp slippage, each leg), plus funding
  at 5.5%/yr over about 3.9 calendar days (about 5.9 bp).
- **Funding sensitivity in U (1x):** +18.9 bp (t 1.37) with no funding; +7.2 bp (t 0.52) at 11%/yr.
- **Monthly sd** is about 133 bp in both samples. The worst month in U is -288 bp; the best is +325 bp.
- **Dividend-adjusted gross** is +40.7 bp in R and +24.7 bp in U. No ex-dividend date fell inside a U window.

## Reported, not deciding
**Windows (gross, then net 1x):**
| Last t days | R gross | t | R net 1x | U gross | t | U net 1x | t |
|---|---|---|---|---|---|---|---|
| 1 | +22.9 | 3.99 | +15.0 | +5.1 | 0.54 | -2.7 | -0.28 |
| 2 | +35.6 | 4.48 | +25.8 | +17.4 | 1.48 | +7.6 | 0.65 |
| 3 (decides) | +39.1 | 4.15 | +27.3 | +24.7 | 1.79 | +13.0 | 0.95 |
| 5 | +41.0 | 3.75 | +24.1 | +37.9 | 2.14 | +21.1 | 1.19 |

- **The last day has faded.** In R it carried +22.9 bp of the +39.1; in U only +5.1. U's gain sits on days -5 to
  -2. This is post hoc; it fits the crowding concern in the PREREG's limits.
- **IEF (7-10 years, same window):** R +21.0 bp (t 4.41), U +22.2 bp (t 3.26, Sharpe 1.16), net 1x +10.6 (t 1.55).
  - IEF's effect per unit of risk is stronger than TLT's in U. xyz has no IEF perp.
- **The rest of the month** (dividend-adjusted, previous month-end close to entry close): R +16.4 bp (t 0.67), U
  -33.2 bp (t -0.79).
  - The window is what earns; bonds fell outside it in 2019-2026.
- **U's gross by year (bp, 12 months each unless noted):**
  - 2019: +65.5; 2020: +22.4; 2021: +31.9; 2022: +20.5;
  - 2023: +20.0; 2024: +42.0; 2025: +33.4;
  - 2026: -51.0 (10 months).
  - Every year to 2025 is positive. 2026 is the first negative year since 2004 in either sample.

## Post hoc: xyz:TLT funding since listing (decides nothing)
- **Data:** Hyperliquid's public `fundingHistory` for `xyz:TLT`, fetched on 2026-11-12 after the run:
  2026-09-17 20:00 .. 2026-11-12 04:00 UTC, 1,329 hours. Saved in `posthoc/xyz_tlt_funding.csv`.
- **Level:**
  - The median is 5.5%/yr (the base rate), but the mean is 20.1%/yr.
  - Longs paid in 80% of hours.
- **Month ends:**
  - The September 2026 window (09-25 close .. 09-30 close) would have paid 49 bp of funding, at a mean of
    36%/yr.
  - October's window (10-27 .. 10-30) would have paid 7 bp.
- **At the mean level**, a 3.9-day hold pays about 21 bp, nearly all of U's +24.7 bp gross.
- **Caveat:** eight weeks of a new market are a thin read of its long-run funding. The direction is clear, though:
  longs on xyz:TLT pay well above the 5.5% assumed in the PREREG.

## Reading
- **Program trials:** 9,785,249. R's t 4.15 is a published effect reproduced on another instrument. It checks the
  construction; it is not a discovery.
- **The economic question is U net of a reachable instrument's cost:**
  - On xyz:TLT, U's net is a t 0.95 edge at an assumed funding that the market has not offered since listing.
  - At 2x it is +7.2 bp (t 0.53); at 3x, +1.4 bp.
- **What survives:** the Treasury month-end rally is real and still positive before costs after the paper
  (TLT t 1.79, IEF t 3.26). It is a structural flow (index extension, insurers), not a price pattern.
- **What would reopen M528** (each a new lane id):
  - An instrument without perp funding, at a round trip of a few bp. For example, a UCITS long-Treasury ETF at an EU
    broker, which costs the bill rate on the capital for about four days.
  - Or xyz:TLT funding at month ends recorded near its base rate for several months.
  - Either would be decided forward. About 12 events a year is a slow forward test.
- **Next to R472 (M522):** R472's CalMod leg trades bonds against stocks in the same week. The two lanes should be
  read together; R472's result is still pending.

## Limits
- ETF closes, not perp fills. xyz:TLT has existed only since 2026-09-17.
- 2 bp slippage per leg is assumed, not measured. No xyz book cost was read here.
- The windows t = 1, 2 and 5 and IEF are reported only. Picking t = 5 after seeing them would be a new lane, not
  this one.
- The public notes read before the freeze had looked at TLT through 2025, so U is post-paper but not unseen.
- Yahoo's closes are its own. Raw responses and hashes are kept (`data/tlteom/manifest.json`,
  `docs/provenance/tlteom.json`).
