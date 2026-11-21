# FINDINGS: deribitgap_v1 (R519). The decided static book FAILS: it locked the wrong sign at entry. R275's book on the same pair earns +4.5%/yr, t 7.0 (reported)

**Verdict: FAIL (R391's rule on book days, gate 0).** All four checks fail for the primary `StaticBook`:
−2.39 / −2.43 / −2.48 %/yr at 1x/2x/3x, NW t −1.81.

- **Registry:** R519, 2 trials. Program trials become 9,785,763.
- **Reproduce.**
  - The PREREG (sha c3dc0d2a) was frozen in commit 21a46384 before any Deribit funding or price was read.
  - Two plumbing deviations were fixed before any result, in `DEVIATIONS.md`:
    - a listed perp that is "not open" stopped the frozen fetch;
    - Deribit's 1D bars close at 08:00 UTC, so the frozen loader put them 16 hours off Hyperliquid's.
  - `run_deribit_gap_h1.py run` ran once on 2026-11-21: 89 coins; 304 Deribit files, 151 hourly files and 470
    Hyperliquid files verified.

## Primary: `StaticBook` (L30, entry at a spread >= 0, held), 2023-06-10..2026-11-17
| Cost | %/yr | NW t |
|---|---|---|
| 1x (7 bp a leg) | −2.39 | −1.81 |
| 2x | −2.43 | |
| 3x | −2.48 | |

- **By year at 1x:** 2023 −0.5; 2024 −6.3; 2025 −2.3; 2026 +0.8. Max drawdown −13.3%.
- **Why it lost.** In June 2023 Deribit's premia were high, so the 30-day window shorted Deribit on most coins (BTC,
  ETH, SOL, DOGE, LTC, XRP and others). The book then held that sign for 3.4 years.
  - Funding went against it: BTC −71.8% of notional over 1,256 days, so Hyperliquid paid about 21%/yr more than
    Deribit on BTC.
  - Funding summed to −48.8% over all trades.
  - Price summed to −273%, most of it one UNI trade (−254%, a blowout exit on a probable bad print).
- **The rule's fault, not the gap's.** The PREREG let the entry window choose the sign. The design asymmetry fixes
  it: long the floorless venue.

## Secondary (reported, not decided): R275's book (L14d th5% K20) on Deribit + Hyperliquid
| Cost | %/yr on book capital |
|---|---|
| 1x | **+4.52** |
| 2x | +3.43 |
| 3x | +2.35 |

- **NW t 7.02.** Trimmed mean +1.12 bp/day. Without NEAR and UNI: +0.88 bp/day. Max drawdown −0.85%.
- **Concentration.** The top 10 days hold 25% of the total.
- **By year at 1x:** 2023 +6.8; 2024 +5.2; 2025 +2.5; 2026 +4.5. Halves +1.57 and +0.91 bp/day.
- **Trades.** 541 trades, mean hold 29 days, 12.5 of 20 slots held. Short Hyperliquid 306 times, Deribit 235.
- **Coins.** 49 coins traded; the top 5 hold half the net. Broad on the old liquid perps: NEAR, UNI, DOGE, TRX, LTC,
  AVAX, BCH, LINK, ADA, ALGO, BTC and DOT are all positive. Funding share 1.08.
- **Status.** It passes R391's four checks, but it was a reported secondary, so it earns a forward lane, not a
  verdict.

## What it means
- **The gap is real and large on liquid coins.** Hyperliquid's floor against Deribit's dead zone was worth about
  21%/yr on BTC over 2023-26. Most of the time the short sits on Hyperliquid.
- **A book that follows the sign earns it:** +4.5%/yr unlevered on two-leg capital, about cash. It is liquid (BTC, ETH,
  DOGE, LTC, AVAX, LINK…), so leverage on cross margin is plausible. That makes it the high-capacity version of R508's
  faille, which R508 never had.
- **Lesson.** When an edge comes from a design asymmetry, fix the sign by the design. Do not let a short window pick
  it.

## What this does not show
- **Deribit access for French residents:** third-party lists only.
- **The UNI print:** not inspected bar by bar.
- **Survivorship:** live Deribit listings only, since the API listed no expired perps.
- **Costs:** Deribit's taker fee is 3.5 bp and Hyperliquid's 4.5 bp, so 1x (7 bp a leg) is about right for liquid
  coins. Thin new Deribit perps were not measured.
- **Funding rule:** the dead-zone rule was read through search summaries only. The data agree with it: Hyperliquid
  paid more most of the time.

## Next
- **Earned:** a forward paper lane (a new id) of R275's book on Deribit + Hyperliquid, recording live books.
- **Also:** a static book with the sign fixed by design (long Deribit). It is post hoc from this read, so it can only
  be tested forward.
