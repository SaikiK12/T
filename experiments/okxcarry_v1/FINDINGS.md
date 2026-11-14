# R430 okxcarry_v1: NULL. The OKX Europe X-Perp carry did not beat the T-bill on BTC or ETH

**Registry:** R430, 2 trials. The program total is now 9,784,363.
**Run:** once, 2026-11-09 17:46 UTC. PREREG `3df8f986…` was verified with its 9 frozen inputs, after the frozen
commit `07a2222` was pushed.
**Window:** 2026-08-06 16:00 to 2026-11-09 16:00 UTC. That is 95 days, 285 realized funding prints per coin, and no
missing value.

## Result
Static short X-Perp / long spot. The capital is the notional × 1.5 (L = 2). The T-bill hurdle is a mean of
**3.92%/yr**.

| | BTC | ETH |
|---|---|---|
| Realized funding, annualized on notional | **+1.51%/yr** | **+6.31%/yr** |
| Basis P&L over the window (index − mark legs) | −0.14% | −0.06% |
| Net on capital, 1x costs (0.30% round trip) | −0.13%/yr | +3.30%/yr |
| Net on capital, 2x / 3x | −0.90% / −1.66%/yr | +2.53% / +1.76%/yr |
| Excess over the T-bill, 1x (bar: ≥ +2.0 pts) | −4.04 pts | −0.62 pts |
| Mean rate by third of the window (per 8 h) | −0.0091%, +0.0006%, +0.0127% | +0.0012%, +0.0063%, +0.0098% |
| Negative prints (bar ≤ 20%) | 31% | 12% |
| Prints exactly at the 0.01% interest baseline | 42% | 53% |
| Largest daily mark high above entry (bar < 40%) | 35% | **47%** |
| NW t (lag 10) of daily funding sums | 0.44 | 4.86 |
| Worst drawdown of the carry account (L = 2, 1x) | −0.75% | −0.23% |

**Both coins fail:**
- BTC fails four of the five checks.
- ETH fails three:
  - the excess at 1x and at 2x;
  - the rally check: ETH's mark rose 47% above entry, so a short at L = 2 would have needed a margin top-up.
- **The lane verdict is NULL.** L = 1 and L = 3 do not change the verdict: the best case is ETH at 1x and L = 3,
  with +3.71%/yr, still 0.21 pts below the T-bill.
- **Holding a fixed coin quantity** instead of a fixed notional raises the funding sum (BTC 0.62% instead of 0.39%,
  ETH 2.14% instead of 1.64%) but not enough to change any check.

## Why: the X-Perp often trades below its index
- The X-Perp formula adds a 0.01%/8 h interest term, about 10.95%/yr. That was the back-of-envelope figure written
  to the owner on 2026-11-06, before this freeze.
- The realized prints are well below it. When the X-Perp trades at a discount to the index, the premium term is
  negative and cancels the interest.
- In BTC's first third, the mean print was negative: the short paid.
- Funding rose through the window: in the last third, BTC averaged +0.0127% per 8 h and ETH +0.0098%. That is an
  observation, not a result. Whether it persists is a question only forward data can answer, and the frozen rule
  does not reopen on it.

## Costs 1x, 2x, 3x
Shown in the table and in `results/coins.csv`. The verdict is NULL at every multiple and every leverage.

## Read against the program
- 9,784,363 program trials (`registry.program_trials`).
- A NULL at gate 0 on two pre-specified coins needs no further correction.

## Reported only: the cross-section of 167 crypto X-Perps
These are current listings, so delisted X-Perps are absent.
- **Post-run correction.** The frozen descriptive table (`results/xsection.csv`, `summary.json`) annualizes every
  instrument at 3 prints a day. In fact, 118 of the 167 X-Perps settle every **4 h**, so those rows are understated
  by half. Re-annualized with each instrument's own interval:
  - the median X-Perp paid **about 10.4%/yr** on notional;
  - the top decile paid more than 14%/yr;
  - 61% of instruments sat below 10.95%/yr.
  - The frozen numbers are kept as they are; this note is the correction.
- **Highest payers, on their own interval:** BEAT 30.8%, UP 24.9%, PONS 24.3%, VVV 23.6%, H 20.8%, TRIA 19.9%,
  APR 18.7% and FET 17.7%/yr on notional. These are small caps with unmeasured books and squeeze risk.
- **Not a result.** This list is chosen with hindsight and earns nothing by itself. A cross-sectional alt X-Perp carry
  is recorded as a new untested method (M490). It needs a point-in-time selection rule, measured books, and
  forward-captured prints before any decision.

## What this means for the owner
- **No France-eligible carry route found here.** On BTC and ETH over the last 3 months, the X-Perp route on OKX
  Europe earned less than T-bills after fees.
- **Not worth a forward lane in this form.**
- **Codex reached the same answer on other venues.** Its France-eligible carry screens on Kraken (R418) and on
  Coinbase CDE versus Kraken (R424) also failed.
- **The one thread left open is M490, the high-funding alt X-Perps.** It is untested and carries real tail risk.

## Limits
- **History:** one 95-day regime.
- **Prices:** mark and index closes stand in for fills; no book was recorded.
- **Spot:** assumed bought at the index price at an EU CASP, with no transfer or custody cost.
- **France access:** taken from the 2026-11-06 report and OKX's documents. It is not checked against the AMF/ESMA
  registers and is not legal advice.
- **Data host:** Codex's runtime host receives HTTP 403 from eea.okx.com; this container did not.
