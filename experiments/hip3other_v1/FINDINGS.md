# FINDINGS: hip3other_v1 (R476). R475's stock-perp funding carry on the other HIP-3 deployers

**Verdict: PASS by the frozen rule, recorded PARTIAL.**
- **The frozen read.** A (2026-01-16 .. 07-17, 27 weeks, 21 with a slot held) earned **+3.12 points a year over the
  13-week bill** (NW t 2.14), +2.32 at 2x cost and +1.51 at 3x.
- **Unlike R475, this is carry, not price.**
  - Funding +5.12, price +0.07, cost 0.80; carry alone +3.05.
  - No liquidation; maximum drawdown 0.21% of capital.
  - Weekly sd of excess 0.09%, against xyz's 0.72%.
- **Why it is recorded PARTIAL** (as R462, R468 and R475 were):
  - The PASS rests on 9 trades in 9 names, 1.9 slots on average.
  - Six of the nine trades ended because their deployer shut down.
  - Leaving one name out drops it to PARTIAL or INCONCLUSIVE in 6 of 18 cases.
  - The A venues no longer exist.
- **What it earns** (PREREG): no lane on the A venues. It supports M530 across deployers. Paragon, which is live,
  carried the same rule in B; it can join the forward lane that R475 earns, under a new id.

PREREG `5893d9ec`, frozen and pushed before the fetch. One frozen run on 2026-11-12 at 08:23 UTC (`results/`).
- **Data** (`docs/provenance/hip3other.json`):
  - 183 markets on nine dexes, of which 75 listings are US equities by Yahoo's metadata.
  - 37 were kept. 23 were dropped by R475's return-correlation identity check: crypto, gold and WTI tickers that
    collide with US stocks, plus para_TTWO, para_MELI, para_SOFI, para_CIFR and six io names. 15 were dropped with
    no funding or candles (hyna_GOLD, all ten mkts listings and four io names).
- Trials 3; program trials 9,785,262.

## Results (annualized points of capital; costs at 1x unless stated)
| Variant | Sample | Weeks (active) | Excess | NW t | 2x | 3x | Funding | Price | Cost | Carry only | Slots | Trades | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **decide** | **A** | 27 (21) | **+3.12** | **2.14** | +2.32 | +1.51 | +5.12 | +0.07 | 0.80 | +3.05 | 1.9 | 9 | 0.21 |
| decide | B | 16 (16) | +10.63 | 3.53 | +9.21 | +7.79 | +14.14 | +0.98 | 1.42 | +9.65 | 3.9 | 9 | 0.37 |
| decide | all | 43 (37) | +5.91 | 3.05 | +4.88 | +3.85 | +8.48 | +0.41 | 1.03 | +5.50 | 2.6 | 18 | 0.37 |
| slots10 | A | 27 (21) | +1.37 | 1.68 | +0.82 | +0.27 | +3.09 | −0.28 | 0.55 | +1.65 | 2.7 | 13 | 0.42 |
| slots10 | B | 16 (16) | +7.94 | 3.81 | +6.68 | +5.41 | +10.74 | +1.14 | 1.26 | +6.80 | 6.8 | 17 | 0.16 |
| enter20 | A | 27 (15) | +3.25 | 1.88 | +2.78 | +2.30 | +4.20 | +0.35 | 0.48 | +2.91 | 1.2 | 5 | 0.02 |
| enter20 | B | 16 (16) | +10.01 | 3.16 | +8.40 | +6.79 | +13.35 | +1.23 | 1.61 | +8.78 | 3.8 | 11 | 0.32 |

- "Carry only" is funding − cost − bill on the capital in slots. Idle capital earns the bill (R475's rule), so a
  week without a slot adds 0.
- After a 15% US withholding on dividends, A is +3.11.
- B is reported only: Paragon's funding in B was scanned before the freeze (PREREG).

## Trades and deployer exits (decide)
| Deployer | Trades | Exits | Sample |
|---|---|---|---|
| Dreamcash (cash) | INTC, HOOD, META, AMZN, MSFT | 2 by rule, 3 at shutdown (META, AMZN, MSFT on 06-29/30) | A |
| Kinetiq (km) | BABA, BMNR, MU | 1 by rule, 2 at shutdown (06-10, 06-15) | A |
| Felix (flx) | NVDA | at shutdown (06-18) | A |
| Paragon (para) | COHR, IREN, CRDO, VST, AVGO, GLW, AAOI, NET, CIEN | 4 by rule, 5 open at the end | B (AVGO opened 06-18) |
| EntropyIO (io) | none | only io_SNDK passed the identity check | |

- **What the shutdowns did to the paper book:**
  - On the five exit days the price leg added +0.46% of capital; on every other day of A it added −0.54%.
    The exit days' price moves are thus about 0.46 of A's 1.6 percentage points of cumulative excess.
  - Funding up to the shutdowns was the larger part: +2.66% of capital over A, against 0.42% of costs.
  - The paper closes a name at its last 20:00 UTC mark. A real position is settled at the deployer's settlement
    price when it delists, which this book cannot price. So the exit days are the least reliable part of A.
- **Post hoc, reported, decides nothing** (`posthoc/leave_one_name_out.py`, `.csv` and `.log`):
  - Leaving one traded name out keeps A positive in all 18 cases (+2.65 to +4.25). 12 stay a PASS. 3 fall to
    PARTIAL (t 1.86-1.99) and 3 to INCONCLUSIVE (fewer than 20 active weeks).
  - Leaving out all six names that ended at a shutdown: A −0.90 (t −0.60), carry −0.27, 1.2 slots. The rest of A
    did not carry.

## A against B, and against xyz (R475)
- **xyz (R475):** A +11.18, half carry (+5.56) and half price (+5.62), with one liquidation. B's carry fell to −0.84 as funding halved.
- **Other deployers (here):** A +3.12, almost all carry. B (Paragon) +10.63, carry +9.65, price +0.98, no
  liquidation.
- Paragon's B carry is the strongest carry evidence in M530 so far, and Paragon is live. But:
  - its funding was scanned before the freeze, so B is not an unseen test;
  - its books are thin (next section).

## Capacity, costs and risks (PREREG list)
- **Capacity is the binding limit.** Median daily traded notional of held names over their holds: about $209k in A
  and $70k in B. The Paragon names ranged $45k-$400k a day.
  - At 1% of daily notional, a slot holds $500-$4,000.
  - A $10k book in 5 slots would be 1-4% of each name's daily volume.
  - The paper book has no size, so none of this shows in its returns.
- **Costs are assumed, not measured:** 5 bp on the stock; 2.9 bp (growth mode) or 11 bp on the perp; 10 bp a
  transfer. Thin Paragon books may cost more. The 2x and 3x lines leave +2.3 and +1.5 in A.
- **Venue risk is realized, not hypothetical.**
  - Felix, Kinetiq and Dreamcash all shut in June 2026, and six of nine trades in A ended that way.
  - A forward book on Paragon carries the same risk: the deployer can delist and settle at its own price.
- **Fee schedules:** each deployer sets its own share. The paper charges R475's flat rule.

## Reading against program trials (9,785,262)
- One pre-named rule (R475's, frozen before this fetch) on new venues: a genuine replication, not a new search.
- A t of 2.14 on 9 trades is weak against the program's trial count.
- What it adds is direction: on non-xyz deployers the funding carry did not depend on price luck.

## Next
- **The R475 forward lane:**
  - Universe: every live HIP-3 deployer's US-stock perps (xyz and Paragon today, io where a name passes the identity
    check).
  - Size each slot to the name's traded notional.
  - Plan for a deployer shutdown (exit rule and settlement price stated before it happens).
- **Decide on carry, report the total.** Carry is what transfers across venues, and its weekly sd here (0.09%) makes
  a 26-week forward read informative. The total excess still needs years at R475's noise.
- **M530:** PARTIAL across deployers. A small carry in A (venues gone) and a larger one in B (Paragon, seen).
