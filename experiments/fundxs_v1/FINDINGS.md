# FINDINGS: fundxs_v1 (R302). Ranking perps by their funding paid in 2021 and stopped; since 2025 the price gives back the funding

**Verdict: NULL.** M263 is TESTED and closed in this form.
- **Trials:** 8, gate 0 on seen data.
- **Read:** frozen PREREG be5325e5, committed and pushed in 18618d4 before the run, and before R299's results were
  read. Run 2026-10-22 09:00 UTC with `scripts/run_fundxs.py`. All 8 inputs matched their frozen hashes.
- **The pick fails all three checks.** The best discovery book is fund3 h1 top150: each day, long the fifth of the top
  150 perps that paid the least funding over 3 days, and short the fifth that paid the most, for one day.
  - Discovery net 1x +25.3 bp/day, t +3.32.
  - Validation net 1x −7.2 bp/day, t −0.71. At 2x it is −14.3.
- **R276's number is reproduced, and it is 2021.** Over every period, at R276's 7 bp, this book nets +11.2 bp/day
  against R276's +10.43. At 1x it nets +68 bp/day in 2021, +3 to +8 in 2022-24 and −13 to −18 in 2025-26.

## What was tested
R276's reference factor `bn_fund_3d`, built as a book:
- **Universe:** the top 150 (or top 50) Binance perps by trailing 30-day quote volume.
- **Signal:** the funding each perp settled over the last 3 (or 30) days.
- **Book:** long the lowest fifth, short the highest fifth, in equal weights. Each leg's return includes the funding
  it pays or receives.
- **Holds:** 1 day (daily) or 7 days (weekly).
- **Costs:** API 8.5 bp per side at 1x, charged on each rebalance's turnover.
- **Windows:** discovery 2021-01..2023-12, validation 2024-01..2026-09.

## Result

**The pick: fund3 h1 top150 (bp/day; t is Newey-West, lag 5)**

| Window | Days | Gross (t) | Net 1x / 2x / 3x | t at 1x | Median day, 1x | Without best 10 days (1x) | Sharpe (1x) | Long leg | Short leg | Turnover a day |
|---|---|---|---|---|---|---|---|---|---|---|
| Discovery | 1,087 | +34.8 (+4.58) | +25.3 / +15.8 / +6.3 | +3.32 | +6.0 | +15.4 | 2.41 | +30.2 | +4.6 | 1.12 |
| Validation | 1,003 | −0.2 (−0.02) | −7.2 / −14.3 / −21.3 | **−0.71** | +7.1 | **−17.4** | −0.44 | −1.3 | +1.1 | 0.83 |

- **The checks:**
  - t ≥ 2.0 at 1x: **fails** (−0.71);
  - a positive 2x mean: **fails** (−14.3);
  - a positive mean without the 10 best days: **fails** (−17.4).
- **Break-even** is 31 bp per side in discovery. In validation the gross is about zero, so there is none.

**All 8 books (bp/day; t at net 1x)**

| Book | Gross disc / valid | Net 1x discovery (t) | Net 1x validation (t) | Validation 2x / 3x | Turnover a period |
|---|---|---|---|---|---|
| **fund3 h1 top150 (pick)** | +34.8 / −0.2 | +25.3 (+3.32) | −7.2 (−0.71) | −14.3 / −21.3 | 1.12 / 0.83 |
| fund3 h1 top50 | +40.7 / −8.5 | +31.9 (+2.94) | −16.0 (−0.85) | −23.6 / −31.1 | 1.03 / 0.89 |
| fund3 h7 top150 | +21.2 / −27.3 | +18.4 (+2.48) | −29.6 (−1.82) | −31.9 / −34.3 | 2.26 / 1.93 |
| fund3 h7 top50 | +27.3 / −55.4 | +24.5 (+2.42) | −58.0 (−1.74) | −60.6 / −63.1 | 2.26 / 2.14 |
| fund30 h1 top150 | +16.3 / +5.1 | +14.3 (+2.46) | +3.1 (+0.32) | +1.1 / −0.9 | 0.23 / 0.24 |
| fund30 h1 top50 | +21.8 / +21.2 | +19.4 (+2.10) | +18.4 (+0.96) | +15.5 / +12.7 | 0.28 / 0.33 |
| fund30 h7 top150 | +12.6 / +5.7 | +11.5 (+1.70) | +4.5 (+0.30) | +3.3 / +2.1 | 0.94 / 0.99 |
| fund30 h7 top50 | +20.9 / +13.2 | +19.5 (+2.03) | +11.7 (+0.43) | +10.2 / +8.7 | 1.13 / 1.23 |

- **Discovery is strong.** Seven of 8 books have a discovery t above 2. SPA over the 8 books rejects "no book beats
  cash" in discovery (p 0.046, best book fund30 h1 top150). In validation it does not (p 0.514).
- **Validation:** the fund3 books turn negative. The fund30 books stay positive at 1x but with t of 0.3-1.0, and their
  2024-26 years swing from +67 to −64 bp/day.

### The reconciliation with R190: price and funding parts
Each book's gross is split into its price part (the same legs with funding set to 0) and its funding part (what the
short leg receives minus what the long leg pays).

**The pick, by calendar year (bp/day)**

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 09) |
|---|---|---|---|---|---|---|
| Gross | +78.1 | +15.1 | +12.5 | +16.6 | −11.7 | −7.4 |
| Price part | +65.3 | +3.8 | +1.4 | +6.9 | −54.7 | −70.5 |
| Funding part | +12.8 | +11.3 | +11.0 | +9.7 | +43.0 | +63.2 |
| Net 1x | +68.3 | +6.1 | +2.8 | +7.8 | −18.0 | −13.0 |

- **The funding part is steady.** It is +10 to +13 bp/day in every year to 2024, about 40%/yr on one unit per leg. The
  short leg collects +6 to +7 bp/day in both windows; this is the carry R190 harvests.
- **The price part decided the book.**
  - In 2021, the perps paying the least funding outran the ones paying the most by +65 bp/day. That one year is R276's
    whole-period result.
  - In 2022-24 the price part was +1 to +7 bp/day. After costs, the book earned about the funding.
  - In 2025-26 the long leg collected +30 bp/day of funding in validation and lost about −31 bp/day in price.
- **Why 2025-26 differs:** extreme negative funding.
  - 2.0% (2025) and 3.2% (2026) of the top 150's perp-days had funding below −1% a day, against 0.1-0.4% in 2021-24.
  - The most extreme days were Binance squeezes with funding below −20% a day: MYX (2025-08), COAI (2025-10), HYPER
    (2025-07), ALPACA (2025-04) and LAB (2026-07).
  - Longs in those perps were paid to hold coins that then fell. The funding priced the drop.
- **So R276 and R190 do not conflict.**
  - R190 earns only funding, hedged with spot, when funding is high on liquid perps: about 1%/yr since 2025.
  - R276's cross-sectional book earned mostly a price effect in 2021, unhedged. That effect has not recurred.
- **The other books agree.** Every book's funding part is positive in both windows (+7.5 to +16.4 bp/day in
  discovery, +24 to +47 in validation). The price part is negative in validation for every book (−17 to −85).

### Ties, size and turnover
- **Ties at the base rate:** for fund3 in the top 150, the day's most common value held more than a fifth of the
  universe on 39% of discovery days and 18% of validation days. On those days a leg held tied perps picked at random
  (seeded). fund30 has almost no ties.
- **Size:** the short leg (the highest funding) is the smaller coins. In the top 150, its mean volume rank is 74-78
  in discovery and 81-83 in validation, against 57-60 and 74-78 for the long leg. In the top 50 the legs are matched
  (25-29).
- **Turnover:** the fund3 daily books turn over about 1 unit a day (of 2 held), the fund30 daily books 0.23-0.33.

## What this does and does not show
**It shows, for the top 150 and top 50 Binance perps in 2021-2026:**
- Long the lowest funding, short the highest, net of funding: strong in 2021-23 (t 2.0-3.3 on 7 of 8 books), driven
  by 2021. Not in 2024-26.
- The funding a book collects is steady. The price move against it is not, and in 2025-26 it cancelled the funding.
- R276's +10.43 bp/day reference reproduces here (+11.2 at 7 bp), and its source is 2021's price effect.

**It does not test:**
- **A hedged book.** Shorting the high-funding perps against their spot keeps the funding without the price part.
  That is R190 / R191 and the forward carry lanes.
- **MEXC prices and funding.**
- **Caps on extreme funding.** The 2025-26 long leg held squeezed perps paying their longs more than 1% a day.
  Excluding them would be a new lane, picked after seeing this.

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side on each rebalance's turnover.
- **The cost is not what failed.** The pick's validation gross is −0.2 bp/day.
- **At 2x and 3x:** the fund30 books stay positive in validation at 2x (+1.1 to +15.5), and three of them at 3x. Their
  t at 1x is 1.0 or less.

## Read against the program
- **Program trials:** 9,478,673 once R299 (12), R300 (24), R301 (16) and R302 (8) are appended to 9,478,613
  (`registry.program_trials()`).
- **8 trials, one pick, one validation read.** The pick's validation t of −0.71 is below zero, before any
  multiplicity.
- **Discovery's SPA p of 0.046 is not evidence of an edge now.** R276 had already shown the whole-period result, and
  validation is flat.
- **Power, written before the run:** a pick with a true annual Sharpe of 1.0 had 37% power. The pick's discovery
  Sharpe was 2.41; in validation it was −0.44. That is a change of sign, not low power.

## Next
- **M263 is TESTED and NULL.** R276's reference is explained: 2021's price effect plus a funding carry that the price
  gave back in 2025-26.
- **No new lane from this.**
  - The fund30 books' positive validation (t ≤ 0.96) is not a lead.
  - Funding carry stays with the hedged lanes (R191 forward, R278 / R294 cross-venue carry).
- **Data note for any funding lane:** 2025-26 has extreme negative funding on squeezed perps (below −20% a day). A
  mean across a leg is dominated by a few such days. Report trimmed means or caps, decided before the result.
