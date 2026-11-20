# FINDINGS: xfund_listing_v1 (R516). Listing-phase carry pays per trade, but its opportunities have dried up on Binance + Hyperliquid

**Verdict: PASS (R391's rule on book days, gate 0).**
- All four checks hold:
  - one-sided NW p 4e-9 (t 5.77);
  - the 2x mean is above 0;
  - the 10% trimmed mean is above 0;
  - so is the mean without TRB and AR.
- **Read with the by-year rows.** Most of the gain is from 2023, when Hyperliquid listed many coins Binance already had. The
  events fell to a few a year, and the six 2026 trades lost on net.

- **Registry:** R516, 3 trials (primary and two reported thresholds). Program trials become 9,785,759.
- **Reproduce.** The PREREG (sha 394ae5f8) was frozen in commit ebf02a1 before any listing-phase spread on this pair
  was computed. `run_xfund_listing.py run` ran once on 2026-11-20. All 10 inputs and 864 data files matched.

## Primary: Binance + Hyperliquid, threshold 20%/yr, K = 10, 2023-06-01..2026-09-30
| Cost | Book days, %/yr | Calendar days, %/yr of book capital |
|---|---|---|
| 1x (7 bp a leg) | **+3.89** | +1.92 |
| 2x | +3.27 | +1.62 |
| 3x | +2.65 | +1.31 |

- **The book's size.**
  - 601 book days of 1,218 calendar days (48%). On average 2.4 of 10 slots were held.
  - So the return per unit of capital in use was about **+15.9%/yr at 1x**, about the main carry book's level.
- **Risk.** Max drawdown -0.13% of book capital. The top 10 days hold 18% of the total. Funding share 0.97: the price
  legs were near flat.
- **Trades.**
  - 73 trades on 87 eligible listing events. Mean hold 20 days.
  - Exits: 38 by spread, 34 at the end of the phase, none by a price blowout.
  - Short Hyperliquid in 41 trades, short Binance in 32.
- **Per trade, on one leg's notional:**
  - mean net at 1x **+1.76%**, median +1.11%;
  - 74% positive;
  - worst -2.46% (BLZ, 2023: the spread flipped within 6 days), best +14.13%.

### By year
| Entry year | Trades | Mean hold, days | Median entry spread, %/yr | Net per trade, 1x | Net per trade, 3x | Positive | Calendar %/yr of the book, 1x |
|---|---|---|---|---|---|---|---|
| 2023 (from June) | 43 | 22 | 28 | +2.21% | +1.65% | 79% | +8.10 |
| 2024 | 15 | 20 | 36 | +1.45% | +0.89% | 87% | +1.09 |
| 2025 | 9 | 17 | 29 | +1.33% | +0.77% | 56% | +0.60 |
| 2026 (to Sep) | 6 | 12 | 35 | -0.12% | -0.68% | 33% | -0.05 |

- **Halves of book days:** +1.81 and +0.33 bp/day.

### Secondaries (reported, not decided)
- **Threshold 10%/yr:** 92 trades.
  - +3.44 / +2.80 / +2.15 %/yr on book days at 1x/2x/3x; NW t 5.67.
  - +13.3%/yr on capital in use.
- **Threshold 50%/yr:** 31 trades.
  - +3.69 / +3.25 / +2.81 %/yr on book days; NW t 4.75.
  - +22.1%/yr on capital in use.
- Both decline by year like the primary.

## What it means
- **The gap is real, and it was large.**
  - R275's engine cannot enter a pair before both venues have 14 days of funding and 20 days of returns.
  - In those weeks, a hedged pair earned about 1.5-2% net per trade in 2023-25 with flat price legs. That is the Q5
    mechanism (thin new books, large premia) in a tradable form.
- **The supply is the problem.**
  - Hyperliquid's catch-up listings of Binance coins were a 2023 event.
  - By 2025-26 most coins list on both venues within days, so few pairs have one venue 30 days ahead: 9 events in
    2025, 4 in 2026 to September.
  - The 2026 trades lost (6 trades, a small sample).
- **What is still open.** The one pair where listings still lag is a venue that lists late. Kraken lists after
  Hyperliquid and Aster, and its first 30 days had the widest spreads in R508's window. That is where a forward variant
  would look.
- **Its size.** At about +16%/yr on capital in use but only a few trades a year per venue pair, it is an overlay on
  the carry book: idle capital from the main book takes these trades. It is not a stand-alone source.

## What this does not show
- **Costs on new books.** 7-21 bp a leg is R275's charge. A coin's first days on a venue can be thinner, but at 3x the
  per-trade net stayed positive through 2025.
- **Execution timing.** Daily closes and settled funding. The first 3 days are spent measuring the spread, so the
  very first days of a listing are not traded.
- **Persistence.** The evidence is mostly 2023. 2026 is negative on 6 trades.
- **Access.** Binance USD-M to a French retail client was not checked. The venues the owner can use are Kraken (EEA),
  Hyperliquid and Aster.

## Next
- **Earned:** a forward variant (a new id) on Kraken + Hyperliquid + Aster listings, recording daily. It would count
  Kraken listing events from 2026 before registering it.
- **Not worth more history tests on this pair:** the supply of events is the binding fact, and it is already measured.
