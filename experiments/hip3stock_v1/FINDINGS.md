# FINDINGS: hip3stock_v1 (R475). Funding carry on trade.xyz US-stock perps, hedged with the stock

**Verdict: PASS by the frozen rule, recorded PARTIAL.**
- **The frozen read.** A (2026-01-16 .. 07-17, 27 weeks) earned **+11.18 points a year over the 13-week bill**
  (NW t 2.03), +9.79 at 2x cost and +8.40 at 3x.
- **Why it is recorded PARTIAL** (as R462 and R468 were): the PASS rests on one name and one kind of day.
  - Without BIRD the same book earns +5.80 (t 1.92), a PARTIAL.
  - Half of A's excess is the price leg, and most of that is one liquidation day.
  - Funding carry alone beat the bill in A (+5.56) but not in B (−0.84).
- **What it earns:** the PREREG gives a forward paper lane under a new id with measured costs to a PASS, or to a
  PARTIAL with a positive 2x excess. Both hold here. That lane is not registered yet (see "Next").

PREREG `14434bf9`, frozen and pushed (`ecec0c08`) before the fetch. One frozen run on 2026-11-12 at 07:58 UTC
(`results/`). Data `docs/provenance/hip3stock.json`: 144 xyz markets, 79 US equities, 62 kept (17 dropped: 10 on the
identity check, 7 with no funding or candles). Trials 3; program trials 9,785,259.

## Results (annualized points of capital; costs at 1x unless stated)
| Variant | Sample | Weeks | Excess | NW t | 2x | 3x | Funding | Price | Div | Cost | Carry only | Slots | Liq. | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **decide** | **A** | 27 | **+11.18** | **2.03** | +9.79 | +8.40 | +10.11 | +5.62 | +0.19 | 1.39 | +5.56 | 4.6 | 2 | 1.75 |
| decide | B | 16 | +8.86 | 1.12 | +6.98 | +5.10 | +4.88 | +9.71 | +0.34 | 1.88 | −0.84 | 4.9 | 2 | 0.72 |
| decide | all | 43 | +10.32 | 2.28 | +8.75 | +7.17 | +8.17 | +7.14 | +0.25 | 1.57 | +3.18 | 4.7 | 4 | 1.75 |
| slots10 | A | 27 | −0.64 | −0.15 | −1.83 | −3.03 | +7.97 | −4.76 | +0.16 | 1.19 | +4.12 | 7.7 | 4 | 3.02 |
| slots10 | B | 16 | +5.95 | 1.32 | +4.39 | +2.83 | +7.32 | +4.04 | +0.18 | 1.56 | +1.91 | 9.8 | 3 | 0.51 |
| enter20 | A | 27 | +6.08 | 2.03 | +4.86 | +3.65 | +9.11 | +0.48 | +0.05 | 1.21 | +5.60 | 3.3 | 2 | 1.61 |
| enter20 | B | 16 | +9.36 | 1.00 | +7.32 | +5.28 | +6.63 | +8.23 | +0.30 | 2.04 | +1.13 | 4.4 | 3 | 1.25 |

- "Carry only" is excess minus the price leg: funding − cost − bill. "Price" includes the dividends shown in "Div".
- After a 15% US withholding on dividends, A is +11.15 (decide).
- The bill (^IRX) took about 3.2 points of A's capital-weighted return.
- Trades (decide): 30 over the span, on 23 names. Exits: 21 by the rule, 4 liquidations, 5 open at the end.
  Mean hold 46 days. Split guard: 0 flags; 67 re-splits.

## Where A's result comes from
- **One liquidation day carries half of it.**
  - On 2026-06-17 the BIRD short perp breached maintenance on a 4-hour high. The paper book then lost the slot's
    whole USDC margin while the long stock kept its jump to the close.
  - That day added +2.59% of capital, about +5.0 annualized points in A.
  - The same thing happened to BIRD again on 2026-10-01, in B (+2.54%).
  - This is the isolated-margin payoff: the short's loss stops at its margin, so a spike in a held stock pays like
    a call option.
  - The PREREG expected liquidations to be "if anything, too harsh"; they helped instead. A trader who tops up
    margin to avoid liquidation would not collect these gains.
- **Post hoc, reported, decides nothing** (`posthoc/leave_one_name_out.py` and `.csv`):
  - Leaving out one traded name at a time, A stays positive in all 23 cases (+5.80 to +11.84). Only 15 stay a PASS;
    8 fall to PARTIAL with t 1.83-1.98.
  - Leaving out BIRD: A +5.80 (t 1.92), B −1.21. Leaving out MU: A +6.38 (t 2.19).
  - Dropping the four liquidation days altogether: A +6.52 (t 2.05; price +1.27, carry +5.25), B −0.85 (t −0.28).
- **The book is far noisier than assumed.**
  - The weekly sd of excess was 0.72% in A and 0.73% in B; the power section assumed 0.15-0.3%.
  - The extra noise is the price leg: mark mismatch (the perp sits an hour before the stock close in winter),
    swings in the perp's premium, and the liquidation days.
  - The two other variants show it too: slots10's price leg was −4.76 in A, enter20's +0.48.

## What changed between A and B
- Funding on the held names halved: +10.11 points of capital in A, +4.88 in B. Carry alone fell from +5.56 to
  −0.84.
- The names got thinner. The median daily notional of held names was $8.4M in A and $0.8M in B (SHAZ, BIRD, BOT,
  USAR, NET).
- This is the pattern of R462, R465, R468 and R470: large effects in the first months of the stock-perp venues,
  flat afterwards.

## A flaw in the identity check (post hoc, decides nothing)
- The frozen check (`Market.identity_ok`) correlates `diff().tail(59)` of daily log returns. With fewer than 60
  marks the first return is NaN, the correlation is NaN, and the market fails.
- Of the 10 identity drops, 6 were this flaw alone: BMNR, CVX, GLW, LRCX, TWST and UMC (27-48 marks, price ratio
  within 0.3% of 1, correlation 0.85-0.99). GOLD and CL are real collisions; TTWO and ICE had under 20 marks.
- Rerun with the NaN dropped (`posthoc/identity_nan.py`, `.csv`, `.log`):
  - A unchanged (+11.18, t 2.03): all six listed after it.
  - B +8.62 (t 1.09) instead of +8.86; BMNR and CVX were traded. Carry only −0.93.
- The same flaw sits in R476 (8 names) and R477 (TLT). Any forward lane must drop the NaN first.

## Reading against program trials (9,785,259)
One pre-named rule with three reported configurations. A t of 2.03 means little against the program's search. The
lab's precedent is to let forward evidence decide, never to treat a gate-0 PASS as an edge. A PASS that turns PARTIAL
when one name is removed is not evidence for real money.

## Capacity, costs and risks (PREREG list)
- **Capacity.** The median daily traded notional over each held stretch was $8.4M in A and $0.8M in B
  (`trades_decide.csv`). At 1% of daily notional, a $10k slot fits most A names but not the thinnest B names
  (BIRD $40k-$230k a day).
- **Costs are assumed, not measured:**
  - 5 bp on the stock; 2.9 bp on growth-mode perps, 11 bp otherwise; 10 bp a transfer.
  - The 2x and 3x lines show room to absorb costs (+9.8 and +8.4 in A).
  - Thin names' real spreads are not in the paper book.
- **Venue risk.**
  - The book depends on trade.xyz and Hyperliquid, USDC, the oracle, auto-deleveraging and halts.
  - Six of the other nine HIP-3 deployers have delisted every market (R474 FINDINGS).
  - R476 measures what a deployer exit costs this book.
- **Corporate actions.** A split settles the short. The book only rescales, and the split guard never fired here.
- **Margin path.** Liquidation is checked on 4-hour highs. Intraday spikes that recover inside 4 hours are missed,
  in both directions.
- **Transfers, EUR/USD and tax** are outside the paper book. US dividend withholding (15%) is shown above.
- **Fee flag.** Growth mode is read today and applied to all of history.

## Next
- **The forward lane this earns** is registered only after R476 (the other HIP-3 deployers) and R477 (London-twin
  hedges) have run. Its design should fix what this lane exposed:
  - mark both legs at the same instant, the 16:00 New York close, with the perp on hourly candles;
  - price xyz costs from the book recorder (claude/xyz-books-data);
  - pre-state how liquidations are handled (isolated margin left to liquidate, or topped up);
  - plan power for a weekly sd near 0.7%: about four years to see +5 points at t 2. That is too long for a single
    forward read, so the forward lane must decide on something faster or be honest that it is monitoring.
- **M530:** PARTIAL on xyz in A; B's carry alone was below the bill.
