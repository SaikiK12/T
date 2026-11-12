# FINDINGS: ltroll_v1 (R481). Did Lighter's funding on its futures-priced commodity perps exceed the roll it paid for?

**Verdict: NULL.** On Lighter NATGAS, the funding longs paid matched the roll-up they received.
- **7 cycles** (2026-03-24 .. 10-14): **−0.41 points a year over the 13-week bill** (t −0.11), −1.59 at 2x and −2.77
  at 3x.
- **Funding vs roll:** funding +52.3% a year of notional against a roll-up of +50.0%. Funding − roll was +0.18% of
  notional a cycle (sd 1.01), positive in 2 of 7 after costs and the bill.
- **Lighter's documented months** (July-October) were all negative: −5.78 points a year (t −2.27).
- **Arbitrage held on Lighter**, where R478's post hoc found xyz longs paying about 1.3% of notional a cycle more than
  the roll.

PREREG `d6696eb3`, frozen and pushed (commit `c89fdc95`) before the fetch. One frozen run on 2026-11-12 at 14:12 UTC:
`results/cycles.csv` and `results/summary.json`.
- The PREREG and its 9 inputs verified; the 18 data files matched `data/ltroll/manifest.json`.
- Provenance: `docs/provenance/ltroll.json`.
- **Data:** Lighter 1-hour candles and hourly funding for NATGAS, WTI, BRENTOIL and XCU (2026-01-15 .. 10-16); Yahoo
  60-minute NG=F, CL=F, BZ=F and HG=F; daily ^IRX.
- **Marks:** no mark needed the 3-hour fallback. 7-8 funding prints were missing per market over the window.
- Trials 4; program trials 9,785,271.

## Results (points of capital a year; notional 3/4 of capital; costs at 1x unless stated)
| Market | Cycles | Excess | t | 2x | 3x | Funding %/yr notional | Roll %/yr notional | Net mean % / cycle (sd) | Positive | Documented Jul-Oct (t) | Wide bracket (t) | Max rise in a cycle |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **NATGAS** | **7** | **−0.41** | **−0.11** | −1.59 | −2.77 | +52.3 | +50.0 | +0.18 (1.01) | 2 | −5.78 (−2.27) | +5.50 (0.97), 6 cycles | 19.2% |
| WTI | 8 | +14.43 | 0.87 | +13.30 | +12.17 | −3.5 | −25.5 | +1.79 (5.10) | 6 | +9.56 (7.77) | invalid, see below | 73.6% |
| BRENTOIL | 7 | +1.34 | 0.27 | +0.16 | −1.02 | −31.8 | −36.4 | +0.37 (1.38) | 4 | +7.56 (1.38) | +0.27 (0.04), 6 | 26.5% |
| XCU | 8 | +1.79 | 0.31 | +1.13 | +0.48 | +7.2 | +2.7 | +0.37 (1.81) | 6 | +4.57 (0.99) | −0.67 (−0.11), 7 | 9.0% |

- **Sign convention:**
  - "Funding" is what the short received; on oil, shorts paid.
  - "Roll" is the roll-up passed to longs: positive in contango (NATGAS), negative in backwardation (oil).
- **NATGAS per cycle** (% of notional, funding / roll):
  - April (from listing): +7.05 / +5.56. May: +8.03 / +6.49. June: +1.10 / +1.16. July: −0.91 / −1.11.
  - August: +0.83 / +2.01. September: +3.67 / +4.24. October: +9.46 / +9.61.
  - Funding tracked the roll closely, cycle by cycle. In the last three it fell short.
- **WTI's +14.4 is one cycle.**
  - The first, partial cycle (2026-02-18 .. 03-13) paid shorts +13.2% of notional in funding, during a 74% rise of
    the perp.
  - A short at M = 1/3 would have been liquidated several times over in that cycle (re-splits are only charged as a
    2 bp allowance).
  - Without that cycle, WTI's cycles sit within ±3% each.
  - The four documented months were all positive (+0.53 to +0.99% of capital each): t 7.77 on 4 cycles, reported
    only.
- **BRENTOIL** (still on Lighter's own documented roll): +1.34 points (t 0.27), 2x +0.16, 3x −1.02. The PREREG's
  BRENTOIL forward-lane clause needed a NATGAS PASS, so it is not triggered.

## Checks on the measure
- **r on business day 4** (the premium before the roll) stayed within ±0.40% for NATGAS, ±0.30% for BRENTOIL and
  ±0.39% for XCU. WTI reached −1.06% in the March oil spike.
- **Lighter and xyz measured the same roll.**
  - Against the same Yahoo fronts at the same marks, Lighter's roll and xyz's (R478's post hoc) agree within 0.22% of
    notional in every full cycle. That includes April-June, before Lighter's published table starts.
  - So Lighter rolled on business days 5-9 before July too, and the PREREG's pre-July risk did not bite.
  - Details: `posthoc/xyz_vs_lighter.csv` and `.log`.
- **The wide bracket (business day 3 to 12) is invalid for WTI.**
  - Yahoo's CL=F switches to the next contract between business days 10 and 12. In April r(BD12) was back near 0,
    while CLK26 expired only on 04-21.
  - The PREREG's assumption (CL around the 20th) was wrong for Yahoo's continuous series. It does not touch the
    business-day-10 measure that decides.
  - For NATGAS the wide bracket differs from the narrow one by up to 1.1% a cycle. That is calendar-spread movement
    between business days 10 and 12, which neither bracket prices exactly. The narrow one is closer to the steps.
  - October has no business day 12 inside the data.

## Post hoc: xyz against Lighter on the same cycles (decides nothing)
`posthoc/xyz_vs_lighter.py` (run 2026-11-12 after the verdict) joins R478's post hoc xyz cycles with these.
- **The roll** was the same on both venues (above).
- **The funding was not.**
  - NATGAS: xyz longs paid **+0.77% of notional a cycle more** than Lighter longs (sd 0.89), more in 5 of 6 full cycles.
  - By cycle: May +0.27, June +0.02, July −0.35, August +1.46, September +1.74, October +1.46.
  - WTI: −0.45 (xyz shorts paid more than Lighter shorts), more on xyz in 2 of 7. BRENTOIL: −0.01, 3 of 6.
- **Reading:**
  - R478's NATGAS carry is a property of trade.xyz's funding, not of the futures roll. Lighter's longs paid the
    fair price for the roll; xyz's paid more, mostly since August.
  - A short xyz / long Lighter NATGAS pair would have kept that difference with the roll netting out, with no futures
    broker.
  - Six cycles, chosen after seeing three markets, are not evidence. They are a reason to test the pair forward.
  - Since 2026-10-22, Lighter's NATGAS is priced by RedStone with an undocumented roll. So a forward pair also
    carries roll-timing risk between the two oracles.

## Risks and caveats
- The identity measure prices the roll at business day 10, not at the five steps. Spread moves during the window add
  noise per cycle.
- Partial first cycles (NATGAS and BRENTOIL from 03-24, WTI from 02-18) include launch weeks.
- Funding is on a constant notional. Costs are assumed: 8 bp per hedge roll, 2 bp re-splits a cycle, 9 bp entry and
  9 bp exit.
- Liquidation is not modelled; see "Max rise in a cycle".
- No executable hedge was tested.

## What it earns
- **NULL by the frozen rule.** M532 did not replicate on Lighter: there, NATGAS funding paid for the roll and no more.
- R480 (xyz, forward) is untouched.
- The post hoc venue difference goes to the queue as a new method: a cross-venue pair on the same futures-priced
  commodity perp. It would need its own frozen forward lane.
