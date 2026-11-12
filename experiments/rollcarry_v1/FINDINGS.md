# FINDINGS: rollcarry_v1 (R478). Does funding on trade.xyz's futures-priced perps exceed the roll it pays for?

**Verdict: PARTIAL.**
- **The frozen read (NATGAS-UNG, A).** 25 weeks (2026-01-30 .. 07-17): **+10.52 points a year over the 13-week
  bill** (NW t 1.68), +10.16 at 2x cost and +9.80 at 3x.
- **The parts:** funding +26.64, perp price +29.38 (the short's gain), fund price −41.30, cost 0.36, bill 3.50.
  - The two price legs net to −11.9. That is mostly the roll-up the short pays in contango.
  - Funding exceeded it by about 15 points.
- No liquidation. The margin's low was 14% of notional, so the book re-split; maintenance is 5%.
- **B gave nothing on NATGAS:** −0.09 (t −0.05). Funding more than doubled (+68.7) and the roll-up rose with it
  (price legs −64.3).
- **What it earns** (PREREG): a PARTIAL with a positive 2x excess earns a forward paper lane under a new id. That lane
  must name a hedge a French account can hold. UNG, USO and BNO are US funds it cannot buy.

PREREG `b93bd2ea`, frozen and pushed before the fetch. One frozen run on 2026-11-12 at 08:32 UTC (`results/`).
- **Data** (`docs/provenance/rollcarry.json`):
  - xyz:NATGAS, CL and BRENTOIL: hourly funding, 4 h and 1 h candles.
  - UNG, USO, BNO and ^IRX: Yahoo daily. 17 files.
- **Listings:** NATGAS's first funding print was 2026-01-21, CL's 2026-01-06 and BRENTOIL's 2026-03-04.
- **Marks:** no fund close lacked a perp price. Marks from the 4 h fallback: NATGAS 56 of 200, CL 66 of 210,
  BRENTOIL 27 of 171.
- Trials 3; program trials 9,785,262.

## Results (annualized points of capital; notional is 3/4 of capital; costs at 1x unless stated)
| Pair | Sample | Weeks | Excess | NW t | 2x | 3x | Funding | Perp (short) | Fund | Cost | Bill | Weekly sd % | Funding rate %/yr | Hours shorts pay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **NATGAS-UNG** | **A** | 25 | **+10.52** | **1.68** | +10.16 | +9.80 | +26.64 | +29.38 | −41.30 | 0.36 | 3.50 | 0.70 | +34.5 | 23% |
| NATGAS-UNG | B | 17 | −0.09 | −0.05 | −0.56 | −1.03 | +68.72 | −62.45 | −1.82 | 0.47 | 3.81 | 0.28 | +84.7 | 9% |
| CL-USO | A | 27 | +17.50 | 3.21 | +16.99 | +16.48 | −12.42 | −58.58 | +93.47 | 0.51 | 3.52 | 0.88 | −15.9 | 36% |
| CL-USO | B | 17 | +1.10 | 0.49 | +0.32 | −0.46 | −18.63 | −29.75 | +54.66 | 0.78 | 3.81 | 0.16 | −22.6 | 50% |
| BRENTOIL-BNO | A | 19 | +16.69 | 2.24 | +16.10 | +15.52 | −10.82 | −2.54 | +34.71 | 0.59 | 3.48 | 0.70 | −16.0 | 34% |
| BRENTOIL-BNO | B | 17 | +1.52 | 0.56 | +1.11 | +0.71 | −28.67 | −17.59 | +52.42 | 0.41 | 3.81 | 0.29 | −36.9 | 50% |

- **Sign convention:** "Funding" is what the short received (negative when shorts paid). "Perp (short)" is the
  short's price PnL. "Fund" is the long fund's.
- **The bill sits inside the fund leg too.** Each fund holds T-bills as collateral, so the fund leg includes about
  0.75 × the bill, net of the fund's fee (UNG about 1%, USO 0.6%, BNO 1% a year).
- **Over the whole span:** NATGAS +6.23 (t 1.47), CL +11.17 (t 2.55), BRENTOIL +9.53 (t 2.01).

## Per roll cycle (business day 10 to business day 10; % of capital)
"Gap" is perp (short) + fund: the roll the short paid (negative) or collected (positive), plus mark noise. "Net" is
funding + gap − cost − bill.

| Cycle from | NATGAS fund / gap / net | CL fund / gap / net | BRENTOIL fund / gap / net |
|---|---|---|---|
| 01-15 | | +0.50 / +0.75 / +0.96 | |
| 02-13 | +2.90 / +0.16 / +2.78 | +1.55 / +1.63 / +2.85 | |
| 03-13 | +5.04 / −3.77 / +0.93 | −5.68 / +8.77 / +2.71 | −2.67 / +3.63 / +0.60 |
| 04-15 | +6.22 / −4.99 / +0.94 | −2.25 / +4.11 / +1.52 | −1.67 / +3.97 / +1.98 |
| 05-14 | +0.84 / −0.43 / +0.12 | −1.34 / +2.45 / +0.82 | −0.05 / +0.86 / +0.51 |
| 06-12 | −0.95 / +1.27 / −0.01 | +0.54 / +0.28 / +0.47 | +0.50 / +1.22 / +1.34 |
| 07-15 | +1.72 / −1.45 / −0.05 | −0.90 / +1.90 / +0.64 | −1.63 / +3.07 / +1.13 |
| 08-14 | +4.06 / −3.44 / +0.28 | −3.52 / +3.49 / −0.40 | −4.04 / +4.85 / +0.44 |
| 09-15 | +8.19 / −8.41 / −0.55 | −0.82 / +1.44 / +0.28 | −2.31 / +1.80 / −0.84 |
| 10-14 (to 11-11) | +8.52 / −7.73 / +0.36 | −0.79 / +1.31 / +0.07 | −1.32 / +1.89 / +0.16 |
| Net > 0 | 6 of 9 | 9 of 10 | 7 of 8 |

- **The roll shows up as theory says:**
  - NATGAS's gap was negative in 7 of 9 cycles: contango, so the oracle's roll lifts the perp against the short.
  - CL's and BRENTOIL's gaps were positive in every cycle: backwardation, so the roll lowers the perp.
  - Funding leaned against the roll in most cycles: longs paid in NATGAS and were paid in oil.
- **Funding did not fully offset the roll.**
  - In contango (NATGAS), longs paid more funding than the roll-up gave them.
  - In backwardation (oil), longs received less than the roll-down took.
  - Either way the hedged short kept the difference: 22 of 27 cycles net positive across the three pairs.
- **The margin shrank in the second half:**
  - NATGAS cycles 2-9 nets were within ±1% each, after +2.8 in the first.
  - The oil pairs' largest nets were in February-April 2026, the steep backwardation of the oil spike. From the
    July cycle on, their nets were −0.84 to +1.13 a cycle.
  - B's excess (+1.10 CL, +1.52 BRENTOIL, −0.09 NATGAS) is a fraction of A's. The edge is either shrinking as more
    capital arbitrages it, or it was a regime of the spring curve.

## Why funding might under-price the roll (mechanics, not tested here)
- Funding is half-scaled since 2025-12-19: `F = 0.5 [P + clamp(r − P, ±0.0005)]` per 8 h. Moving the full roll
  through funding needs twice the premium.
- The roll moves the oracle, not the mark's premium. Arbitrage then requires someone to hold the futures on xyz's
  exact roll days.
- Retail on xyz may lean long commodities (the same lean that makes stock-perp longs pay, R475-R477).
- None of these is measured here. The per-cycle table is consistent with them. It does not prove them.

## Risks and caveats (PREREG list)
- **Hedge timing:** the funds roll a few days after xyz. Within a cycle this is mark noise; the business-day-10
  cycles leave part of it in each cycle's gap. Across cycles it nets out.
- **CL and BRENTOIL A are reported, not decided**, though the author had not seen their A funding. Their t (3.21,
  2.24) stands next to 2 other pairs computed and the program's trial count. Both are oil, so they are not
  independent.
- **Costs are assumed:** 5 bp on the fund; 2.9 bp on the perp (growth mode); 10 bp a transfer. The 3x line still
  leaves +9.8 in A.
- **Margin:** CL's margin fell to 7.6% of notional (maintenance 2.5%) during the oil spike, without a liquidation.
  The 1 h and 4 h highs were checked.
- **Venue:** trade.xyz and Hyperliquid, USDC, the oracle relayer (17:00-18:00 ET gap), auto-deleveraging, halts.
- **No executable hedge was tested.** A French retail account cannot buy UNG, USO or BNO.
  - The executable routes are CME futures (micro WTI, Henry Hub) through a futures broker, rolled on xyz's days, or
    a UCITS ETC (e.g. WisdomTree's on LSE).
  - WisdomTree's ETCs follow Bloomberg sub-indices with their own roll months, so they add curve exposure.

## Reading against program trials (9,785,262)
- One pre-named decision (NATGAS) at t 1.68 is not significant on its own.
- What stands out is the sign pattern: the hedged short netted positive in 22 of 27 cycles on three perps whose
  funding and curve signs differ.
- B's decay is the main reason to stay cautious.

## Next
- **The earned forward lane (new id).** Short xyz:NATGAS, CL and BRENTOIL hedged with an executable instrument.
  - Hedge: CME front futures rolled on xyz's days (cleanest, needs a futures broker), or the WisdomTree ETCs on
    LSE (holdable, adds curve noise).
  - Decide on the three pairs together: their nets are mostly independent of the price legs and of each other's
    funding sign.
  - B's small nets imply low power over 26 weeks. The PREREG must state that power.
- **A post-hoc check, deciding nothing:** price the roll directly as the perp at business day 10 against the
  continuous front future (Yahoo CL=F, NG=F, BZ=F), which stays on the old contract until expiry. This tests
  whether the funds' roll timing created the gap.
- **M532:** PARTIAL. Funding exceeded the roll in A on NATGAS and fell short of it on oil, both in the short's
  favour; B is near zero.
