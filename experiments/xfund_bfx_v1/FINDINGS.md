# FINDINGS: xfund_bfx_v1 (R507). R275's carry book passes on Binance + Bitfinex, a venue never read for carry

**Verdict: PASS (R391's rule, gate 1 "another venue").** All four checks hold: the one-sided NW p is 3.6e-33, the 2x
mean is above 0, the 10% trimmed mean is above 0, and so is the mean without the two best coins.

- **Registry:** R507, 1 trial. Program trials become 9,785,748.
- **Reproduce.**
  - The PREREG (sha e775b1a3) was frozen in commit a8c229c before any in-window Bitfinex data was fetched, except the
    one probe slip it discloses.
  - Fetch: `python scripts/run_xfund_bfx.py fetch`, run as three workers (`DEVIATIONS.md`).
  - Read: `python scripts/run_xfund_bfx.py run`, once, on 2026-11-18 09:00 UTC. All five inputs matched their pins.
- **The book:** R275's L14d th5% K20, unchanged (`lab.xfund`), at 7 / 14 / 21 bp per leg.
- **What PASS means here.** The cross-venue funding premium generalises to a venue whose funding design differs: it
  has a dead zone. PASS earns no money and no forward lane by itself (see "What this does not show").

## Primary book: binance+bitfinex L14d th5% K20, 2021-01-22..2026-09-30
| Cost | %/yr on book capital | bp/day |
|---|---|---|
| 1x (7 bp a leg) | **+5.21** | +1.43 |
| 2x | +4.17 | +1.14 |
| 3x | +3.13 | +0.86 |

- **Book days and t.** 2,078 book days. NW t (lag 10) 11.94. The iid t is 8.76, so daily nets are negatively
  autocorrelated.
- **Robustness.** Trimmed mean +1.39 bp/day. Without AXS and ZEC, the two best coins: +1.23 bp/day (+4.48%/yr).
- **Halves:** +1.64 and +1.22 bp/day. Since 2025: +0.87 bp/day.
- **Risk.** Max drawdown (running sum) -0.94%. 3 of 69 months were negative; the worst was -0.16%. The top 10 days hold
  16% of the total.
- **Where the return comes from.** Funding share 1.00: price legs added nothing on average. Gross is about
  +6.2%/yr. Costs take about 1.04%/yr per 1x, so the book breaks even near 6x costs (about 42 bp a leg).
- **The book.**
  - On average 17.2 of 20 slots were held (18.2 before 2025, 14.9 since).
  - 845 trades on 54 coins; 11 were forced exits.
  - 79% of trade-days were long Bitfinex / short Binance: 522 trades, +176 bp net each on average, 63% winners.
  - 21% were the reverse: 323 trades, +82 bp net, 47% winners.
- **Read against the program.** The one-sided Bonferroni threshold over 9,785,748 trials is z 5.73. The NW t of 11.94
  clears it.

### By year (%/yr on book capital, 1x / 2x / 3x)
| 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to Sep) |
|---|---|---|---|---|---|
| +7.76 / +6.97 / +6.17 | +5.48 / +4.20 / +2.92 | +5.52 / +4.55 / +3.57 | +5.77 / +4.80 / +3.82 | +3.24 / +1.99 / +0.74 | +3.06 / +2.15 / +1.24 |

Every year is positive at all three cost levels. The last two years are about half the earlier ones.

### Per coin
- 50 of 54 traded coins were net positive.
- **Best** (bp/day of book): AXS +0.104, ZEC +0.095, STG +0.083, IOT (IOTA) +0.073, ETH +0.064.
- **Worst:** ANC -0.044 (the Terra collapse), then APE, SUI and HYPE, each above -0.003.

### Funding profile (descriptive; 68 coins with Bitfinex periods in the window)
- **Bitfinex funding is mostly zero.** The share of zero-rate 8 h periods per coin has median 59% (range 13%-84%).
- **Median annualised funding per coin:** Bitfinex +0.96%, Binance +4.89%.
- **Mechanism.** When premiums are small, Binance's rule pays its +0.01% per 8 h interest floor. Bitfinex's dead zone
  pays nothing. The book mostly collects that difference, at about half of it on two-leg capital, as the PREREG
  stated before the fetch.

### Secondary book (reported, not decided): L14d th10% K20
- +5.00 / +4.03 / +3.07 %/yr at 1x / 2x / 3x; NW t 11.47; 785 trades; max drawdown -1.02%.
- By year at 1x: 2021 +7.7, 2022 +5.7, 2023 +5.4, 2024 +5.5, 2025 +2.7, 2026 +2.6.

## Universe and data
- **Discovery.**
  - 879 Binance coin codes were probed. `DEVIATIONS.md` says 880: that count included the CSV header.
  - 17 were found: 12 delisted crypto pairs and the 5 non-crypto pairs that `DEVIATIONS.md` moves aside.
  - With 59 listed pairs, 76 were fetched.
- **The run read 71 receipts and mapped 69 coins.**
  - `ATO` did not map. It is Bitfinex's code for ATOM, and today's currency map lacks it, so ATOM is missing from this
    universe.
  - `XDC` did not map: there is no Binance perp.
  - LIT has no data in the window.
- **Data checks before the run** (no returns read):
  - every progress line is complete;
  - no status page is missing;
  - every funding series runs in 8 h steps with no gap;
  - each receipt's two sha256 values match its files.

## With the five non-crypto pairs (reported, never decided on)
- Run from a scratch copy of the receipts after the frozen read, as `DEVIATIONS.md` set out: 74 coins.
- Result: +5.69 / +4.65 / +3.62 %/yr at 1x / 2x / 3x; NW t 12.13; 841 trades.
- Only two of the five traded:
  - BTCDOM added +0.134 bp/day, the most of any coin, and becomes the first coin dropped by the best-two check;
  - XAUT added +0.001.
- XAG, XPD and XPT never entered the book.

## What this does not show
- **Access from France.** Bitfinex's own list of eligible jurisdictions was not found.
  - Third-party reviews say Bitfinex holds no MiCA authorisation and that the EU transition ended on 2026-07-01. The
    ESMA register was not checked directly.
  - In the EU, perpetual futures fall under MiFID.
  - Until the owner or a primary source settles this, the book has no venue the owner can trade. **No forward lane is
    proposed.**
- **Capital.** The return is on two-leg book capital at 1x.
  - At 1x, +5.2%/yr (+3.1%/yr in 2025-26) is about the dollar cash rate of 2023-25 (4-5%), so there is little
    excess over cash.
  - Leverage would scale it, but cross-venue margin is a known failure mode (R280: isolated legs liquidated at 1x). It
    is not measured here.
  - Other C13 books are larger: binance+kucoin made +10.80%/yr over the same window (R277).
- **Costs.**
  - Bitfinex's fees before its current zero-fee schedule, and its spreads and depth over 2021-2026, were not checked.
  - The 3x line covers 21 bp a leg; the book breaks even near 42 bp.
- **Funding timing.** Bitfinex settles at 00:00, 08:00 and 16:00 UTC on the period's final average spread beyond
  ±0.05%. Longs pay when it is positive
  ([Bitfinex derivatives interface](https://support.bitfinex.com/hc/en-us/articles/360035973913-The-Bitfinex-Derivatives-trading-interface);
  [Bitfinex blog](https://blog.bitfinex.com/education/why-choose-bitfinex-to-trade-crypto-derivatives-futures/)).
  This matches the sign used here. Booking at the period's end is the conservative choice in the PREREG.
- **The Binance rebuild.** Its funding rows were not compared one by one with the original files
  (`docs/reviews/data_rebuild_20261117.md`).

## Next
- C13 gains a venue whose funding has a dead zone, and the premium still carries (`registry/candidates.csv`).
- Before any Bitfinex lane, check access from France against a primary source. Any such lane would be new and frozen.
