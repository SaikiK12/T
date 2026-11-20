# FINDINGS: hip3gap_v1 (R518). The HIP-3 funding-design gap is real but costs take it all: about zero net

**Verdict: FAIL (R391's rule on book days, gate 0).** All four checks fail: t −0.03, and the 2x mean, the trimmed
mean and the mean without the two best coins are all below 0.

- **Registry:** R518, 1 trial. Program trials become 9,785,761.
- **Reproduce.** The PREREG (sha 066d2dbe) was frozen in commit deac57f, before R517 ran and before any cross-dex
  spread was computed. `run_hip3gap.py run` ran once on 2026-11-20, on R517's verified data (321 files).

## Result: R275's book (L14d th5% K20, `xfund_v2`), 2025-12-04..2026-11-20
| Cost | Book days (342), %/yr | Calendar %/yr |
|---|---|---|
| 1x (7 bp a leg) | −0.02 | −0.02 |
| 2x | −1.32 | −1.28 |
| 3x | −2.62 | −2.55 |

- **Shape.** NW t −0.03; max drawdown −0.61%; halves +0.03 and −0.04 bp/day; on average 8.4 of 20 slots held.
- **174 trades, mean hold 16 days.** Exits:
  - 142 by spread;
  - **20 because a leg was delisted**: deployers settled or delisted markets (Felix, Kinetiq, Dreamcash and mkts list
    many delisted markets);
  - 12 open.

## Where the money went (sum over trades, % of one leg's notional)
| Funding | Price | Cost (4 legs × 7 bp) | Net |
|---|---|---|---|
| **+54.9** | −6.8 | −48.7 | −0.7 |

- **The gap is there.**
  - Funding earned +0.32% a trade, about 7%/yr on one leg while held.
  - Pairs that went long the low-funding dex earned it: para>xyz +12.8, flx>xyz +11.1, km>xyz +8.0 (funding sums).
- **But R275's rule churns.** It exits at half the threshold and re-enters, so four legs of cost per 16-day trade
  equal the funding.
- **Price legs between two deployer oracles cost little on average,** with wide swings (flx>xyz −9.4, para>xyz +6.0).

## What it means
- **Plumbing, confirmed.** Each HIP-3 deployer's funding design differs (multiplier 0 to 1, interest about 5-11%/yr),
  and a long on the cheap dex against a short on the paying one collects the difference.
- **Economics, not enough.**
  - About 7%/yr on one leg is about 3.5%/yr on two-leg capital, unlevered, before any cost: below cash.
  - A hold-and-forget version with no churn would keep most of it. At 2-3x on portfolio margin that is perhaps
    7-10%/yr, with deployer halts and oracle gaps as the risk.
  - That would be a new lane, built post hoc from this reading. It is noted, not earned.
- **Risks seen, from the docs and in the data:**
  - deployers can halt a market and settle positions at the mark (20 dead-leg exits here; HyENA closed);
  - dexes margin in different stablecoins (USDC; tokens 360 and 268), so a pair can need two collateral assets;
  - each dex runs its own oracle.

## What this does not show
- **Today's designs only.** Deployers can change multipliers; the funding actually paid is what the book used.
- **Costs.** Growth-mode fees are below 7 bp a leg, but spreads on thin HIP-3 books are not measured.
