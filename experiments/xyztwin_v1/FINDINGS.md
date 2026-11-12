# FINDINGS: xyztwin_v1 (R477). R475's funding carry on xyz index, ETF and metal perps hedged with London twins

**Verdict: PARTIAL.**
- **The frozen read.** A (2026-01-16 .. 07-17, 27 weeks, 26 with a slot held) earned **+1.62 points a year over the
  13-week bill** (NW t 0.50), +1.00 at 2x cost and +0.37 at 3x.
- **The parts:** funding +4.47, price −0.86, cost 0.62. Carry alone (funding − cost − bill) +2.48.
  - No liquidation. Maximum drawdown 1.53% of capital.
  - 6 trades in 5 names; 1.9 slots on average.
- **The noise is the hedge.** The price leg's weekly swings are larger than the carry, so t is 0.50.
- **What it earns** (PREREG): a PARTIAL with a positive 2x excess earns a forward paper lane under a new id, with
  measured costs. It is weak evidence: carry is positive, but A cannot tell it from zero once price noise is added.

PREREG `2ee0cbb4`, frozen and pushed before the fetch. One frozen run on 2026-11-12 at 08:29 UTC (`results/`).
- **Data** (`docs/provenance/xyztwin.json`): 13 xyz perps with their LSE twins and ^IRX, 53 files.
- 11 pairs kept. Two were dropped by the identity check:
  - NIFTY: 11 marks since its 2026-10-27 listing, under the 20 the scaling needs.
  - TLT: see "A flaw in the identity check" below. It affects B only.
- Trials 3; program trials 9,785,262.

## Results (annualized points of capital; costs at 1x unless stated)
| Variant | Sample | Weeks (active) | Excess | NW t | 2x | 3x | Funding | Price | Cost | Carry only | Slots | Trades | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **decide** | **A** | 27 (26) | **+1.62** | **0.50** | +1.00 | +0.37 | +4.47 | −0.86 | 0.62 | +2.48 | 1.9 | 6 | 1.53 |
| decide | B | 16 (16) | +12.92 | 1.80 | +12.07 | +11.22 | +7.62 | +9.05 | 0.85 | +3.88 | 3.7 | 8 | 0.58 |
| decide | all | 43 (42) | +5.83 | 1.44 | +5.12 | +4.41 | +5.64 | +2.83 | 0.71 | +3.00 | 2.6 | 14 | 1.53 |
| slots10 | A | 27 (26) | +0.81 | 0.50 | +0.50 | +0.19 | +2.23 | −0.43 | 0.31 | +1.24 | 1.9 | 6 | 0.76 |
| slots10 | B | 16 (16) | +6.46 | 1.80 | +6.04 | +5.61 | +3.81 | +4.52 | 0.42 | +1.94 | 3.7 | 8 | 0.29 |
| enter20 | A | 27 (21) | +3.49 | 1.39 | +3.09 | +2.69 | +3.19 | +1.53 | 0.40 | +1.96 | 1.2 | 5 | 1.11 |
| enter20 | B | 16 (16) | +7.71 | 1.63 | +7.12 | +6.53 | +5.00 | +4.56 | 0.59 | +3.15 | 1.6 | 5 | 0.68 |

- "Carry only" is funding − cost − bill on the capital in slots. Idle capital earns the bill (R475's rule), so a week
  without a slot adds 0.
- **slots10 is decide at half weight.** No more than five names ever qualified at once, so ten slots held the same
  names with half the capital each. Every line halves and t is unchanged.
- The twins accumulate their dividends; the perps pay none. The dividend column is therefore 0, and the dividend is
  in the price leg.
- B is reported only: its funding was scanned before the freeze (PREREG). B's +12.9 is mostly price (+9.05).

## Trades (decide)
| Name (twin) | Trades | Held | Sample |
|---|---|---|---|
| GOLD (IGLN.L) | 1 | 01-23 .. 03-13 | A |
| SILVER (PHAG.L) | 2 | 01-23 .. 04-10; 07-10 .. end | A, B |
| URNM (URNM.L) | 3 | 02-27 .. 03-27; 04-10 .. 07-10; 08-21 .. end | A, A, B |
| JP225 (IJPA.L) | 2 | 05-15 .. 07-03; 07-24 .. 08-21 | A, B |
| XLE (XLES.L) | 2 | 06-05 .. 07-03; 07-24 .. 10-16 | A, B |
| SMH (SMH.L) | 2 | 07-17 .. 07-24; 09-11 .. end | B |
| KR200 (CSKR.L) | 2 | 06-19 .. 09-04; 10-30 .. end | B |

- All exits were by rule (trailing funding under 6%/yr), or at the end. No deployer or market shut.
- EWY, EWJ, SP500 and XYZ100 never qualified: their trailing funding stayed under 12%/yr.
- Median daily traded notional of held names was about $0.9-1.0M, and much more on GOLD and SILVER. Capacity is
  not binding here at the owner's scale, unlike Paragon in R476.

## A flaw in the identity check (found after the run; changes nothing in A)
- The frozen check takes `tail(59)` of each pair's daily log returns and correlates them. A pair with fewer than 60
  marks keeps the first return, which is NaN. The correlation is then NaN and the pair fails.
- Post hoc (`summary.json` lists only the drop): TLT had 39 marks, and its correlation with DTLA over 38 returns is
  0.78, above the 0.5 bar. It was dropped by the NaN, not by its returns.
- TLT listed on 2026-09-17, so only B is affected. TLT's B funding (20%/yr) would probably have taken a slot.
- R474 trades the TLT pair forward on its own. A forward lane built on this rule must drop the NaN first.
- Correlations of the kept pairs (last 59 returns): 0.96-0.98, except JP225 against IJPA.L at 0.75 (Nikkei 225
  against MSCI Japan IMI, priced 30 minutes apart).

## Against R475 and R476
| Lane | Hedge | A excess (t) | A carry only | B carry only |
|---|---|---|---|---|
| R475 | US stock (xyz stock perps) | +11.18 (2.03) | +5.56 (price +5.62, one liquidation) | −0.84 |
| R476 | US stock (other deployers) | +3.12 (2.14) | +3.05 | +9.65 (Paragon) |
| R477 | London twin (xyz index, ETF, metal) | +1.62 (0.50) | +2.48 | +3.88 |

- **Carry was positive on all three in A**, and in B on two of three (xyz stocks fell to −0.84 as their funding
  halved). The totals differ by the price leg, which the hedge should cancel and only partly does.
- R477 has the noisiest hedge (different funds, FX on two pairs, a 30-minute timing gap). Its price leg swamps the
  carry, as the PREREG's power section expected (0.1-0.4 PASS probability).

## Costs and risks (PREREG list)
- **Costs are assumed:** 5 bp on the twin; 2.9 bp on the perp (all kept pairs but GOLD run in growth mode; GOLD 11
  bp); 10 bp a transfer. The 2x and 3x lines leave +1.00 and +0.37.
- **Basis between different funds:** KOSPI 200 against MSCI Korea, Nikkei against MSCI Japan IMI. These trades are
  hedged by a related fund, not the same index.
- **FX:** KR200 and JP225 carry KRW and JPY through the USD twin. An owner in euros also bears EUR/USD on the book.
- **Venue:** trade.xyz and Hyperliquid, USDC, oracles, auto-deleveraging, halts.
- **Taxes:** out of scope.

## Reading against program trials (9,785,262)
- One pre-named rule (R475's) on new markets: a replication of a rule, not a search.
- t 0.50 decides nothing on its own. What R477 adds: on a third set of markets, the funding carry was positive in A
  and in B.

## Next
- **Forward lane (earned).** Fold it into the R475/R476 forward lane under one new id, as a second book with its own
  decision or reported beside the stock book. Requirements:
  - correct the identity NaN;
  - measured xyz costs from the book recorder;
  - decide on carry, report the total.
- **M531:** PARTIAL. Carry +2.48 in A and +3.88 in B, but it cannot be told from zero once price noise is added.
