# FINDINGS: dmake_v1 (R522). Quoting around the index on Deribit's thin new perps is picked off: −27 bp a fill

**Verdict: FAIL (gate 0).** All four checks fail at k = 15 bp:
- NW t of daily dollar PnL −6.59;
- 2x costs negative;
- negative without WLFI and CFX;
- both halves negative.

- **Registry:** R522, 5 trials. Program trials become 9,785,770.
- **Reproduce.** The PREREG (sha 95b88e37) was frozen in commit 7ccfe06c before any trade was fetched.
  - `fetch_deribit_trades.py --end 2026-11-20` wrote 67 coins (67 MB). Provenance: `docs/provenance/deribit_trades.json`.
  - `run_dmake.py run` ran once on 2026-11-21.

## Result: 67 coins, 91 days, $500 units
| k (from the index) | Fills | Mean edge, bp | Median, bp | Positive | $ per day | NW t |
|---|---|---|---|---|---|---|
| 5 | 333,060 | −25.3 | −15.7 | 4% | −4,632 | −6.14 |
| 10 | 261,997 | −25.8 | −15.5 | 8% | −3,710 | −6.35 |
| **15 (primary)** | 205,771 | **−26.7** | −15.6 | 11% | −3,018 | −6.59 |
| 25 | 130,688 | −29.1 | −16.7 | 14% | −2,095 | −7.07 |
| 40 | 72,651 | −33.3 | −18.5 | 17% | −1,331 | −7.52 |

- **Costs at k = 15 bp:** −26.7 / −34.7 / −42.7 bp a fill at 1x / 2x / 3x.
- **Fills:** 34 per coin per day.
- **Cash:** far below. This loses money at every cost and every k.

## Why (post-hoc, descriptive; candidate fills before the cooldown and cap)
| Age of the quote's index | Candidate fills | Edge, bp | Index move from quote to fill, bp |
|---|---|---|---|
| 2-5 s | 116,642 | −5.3 | −12.3 |
| 5-15 s | 105,179 | −7.4 | −14.4 |
| 15-60 s | 153,901 | −11.9 | −18.9 |
| 1-5 min | 179,383 | −19.8 | −26.8 |
| 5-60 min | 127,917 | −38.9 | −45.9 |
| over 1 h | 11,750 | −109.0 | −116.0 |

- **Adverse selection is the cost.** A trade that prints through a quote comes with the index moving against the
  quote. Even with a 2-5 second old index, the move is −12 bp, more than k − 8 bp of costs.
- **Wider quotes do not escape it.** The move grows with k.
- **The frozen rule adds a stale quote.** It knows the index only at trade times, so on thin coins the reference can
  be minutes old. That makes the average much worse than a live quoter's would be.

## What this does not show, and what is still open
- **This is a lower bound for market making, not a verdict on it.** The fill rule, a trade strictly through the
  quote, is the conservative choice for counting fills, but it keeps exactly the most toxic ones.
  - A resting order at the touch is also filled by takers who only hit the touch, and they are less informed.
  - Those fills cannot be seen in a trade tape. They need the book.
- **Missing pieces:** the hedge basis to Hyperliquid's price, funding on inventory, and points.
- **Next for Bet 2, if any:** touch-level fills need book data.
  - Kraken publishes order events with order ids, so its queue can be rebuilt.
  - Or a live recorder of Deribit's thin books.
  - Until then, make-and-hedge on thin books has no evidence for it, and this read is evidence against quoting
    around the index.
