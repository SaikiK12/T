# Reflection, 2026-11-25 (cycle 7 of rule 11): why did the design gap's return fall through 2026?

## How I approached the last subjects, and what I would change
- **Cycles 4-6 went to the closed-market family,** and they ended in a frozen lane (R530) and a sizing correction:
  at the owner's scale, capital under the venue's margin rule binds before the market's depth (L042).
- **That correction points to the next question.** If capital is the scarce input, I need to know which family a
  euro should go to. The money case is still the design gap, so I need to know whether its edge is decaying for a
  structural reason or a passing one.
- **What I would change:** I quoted "the rent decays, as the paper measures" (cycle 2) and planned quarterly
  reassessments, without ever asking what is causing our own decay. A decay with a known cause can be forecast; a
  decay without one cannot.

## 0. What the lab already knows
- **R508** (Kraken + Hyperliquid, 111 coins, 2025-11-17 .. 2026-11-15, seen), % of book capital at 1x, from
  December 2025 to November 2026 (to the 15th): +1.93, +4.51, +2.80, +2.41, +1.75, +1.73, +2.60, +1.32, +1.56,
  +1.23, +0.86, +0.11.
  - Every month is positive, but the level falls from about 3%/month in winter to about 1% in autumn.
- **He et al.:** |ρ| falls about 22 points a year as arbitrage capital grows. Binance's portfolio margin (2022) cut it
  further by lowering m.
- **Hyperliquid's own margin regime changed during the window** (announcement channel, read 2026-11-25):
  - unified account live 2026-01-31;
  - portfolio margin pre-alpha from 2026-01-17, alpha from March, open to any account above $10k from about April,
    beta from 2026-06-25;
  - manual borrows from 2026-09-18 ($269M borrowed that day).
- **The lab's earlier rounds on the floor side:** R444 and R445 (Hyperliquid spot-against-perp carry under portfolio
  margin), R446 (vault deposits), and L008 (idle USDC earns about 2.65% under portfolio margin).

## 1. The economic question
Did the gap fall because arbitrage capital is closing it (structural, so it goes on falling), or because the market
moved through a phase in which it pays less (passing, so it comes back)?

## 2. The mechanism: which leg can move
- **The gap is Hyperliquid's funding minus Kraken's funding.**
  - Hyperliquid's funding is P + clamp(0.01% − P, ±0.05%) per 8 h, flat at the floor (about 10.95%/yr) while its
    premium sits in [−0.04%, +0.06%].
  - Kraken's funding is its premium alone.
- **Three ways the gap shrinks, and what each predicts:**
  1. **Arbitrage capital enters the floorless side** (long Kraken thin perps, short the floor venue). Kraken's funding
     on these coins rises toward Hyperliquid's floor, while Hyperliquid stays at the floor. This is structural (the
     barrier W/m on Kraken's side erodes).
  2. **Arbitrage capital enters the floor side through portfolio margin.** It lowers m for spot-against-perp trades
     on Hyperliquid, so Hyperliquid's above-floor premia shrink. That hits only the hours above the floor, and only
     coins with portfolio-margin collateral (BTC, HYPE). This is structural but narrow.
  3. **The market regime.** In flat or falling markets Kraken's premium-only funding is near zero or negative, while
     Hyperliquid stays at the floor, so the gap is wide. In strong rallies both premia rise and the gap can narrow. A
     move from winter's sell-off to autumn's rally would shrink the gap and later bring it back.
- **The gap's level is set by the floorless side,** because the clamp band shields the floor (cycle 1). So cause 1 is
  the one that matters for the money plan.

## 3. The cheapest decisive observation, with the prediction written first
- **Data:** R508's own pinned files (`data/kraken_hist/open/funding`, `data/hyperliquid/funding`), the 111 coins of
  `experiments/xfund_eea_v1/symbols.csv`, 2025-11-17 .. 2026-11-15. All of it was seen by R508. This is a
  decomposition, not a test.
- **By month, equal weight across coins, annualized:**
  - Hyperliquid's mean funding;
  - the share of Hyperliquid hours above the floor;
  - Kraken's mean funding;
  - the gap (Hyperliquid − Kraken);
  - Kraken's funding against the market's direction (BTC's monthly return).
- **Prediction (cause 1, from He et al.'s decay):** Kraken's mean funding on these coins rises through 2026 relative
  to Hyperliquid's floor, and Hyperliquid's funding stays near the floor. The gap narrows because of Kraken's leg.
- **What would refute it:**
  - **Cause 3:** Kraken's funding moves with the market and Hyperliquid's above-floor share falls with it.
  - **Cause 2:** the narrowing comes from Hyperliquid's above-floor hours on BTC and HYPE after April.

## 4. The observation (`scripts/check_gap_decay.py`; R508's seen window)
**By month, equal weight over 107-111 coins, %/yr:**

| Month | HL funding | HL hours above floor | Kraken funding | Kraken hours above HL's floor | Gap HL − Kraken | Top-20 \|gap\| | BTC % |
|---|---|---|---|---|---|---|---|
| 2025-11 | −15.0 | 1% | −11.3 | 20% | −3.8 | 103.6 | −17.6 |
| 2025-12 | −9.8 | 0% | −12.7 | 20% | +2.9 | 98.4 | −3.0 |
| 2026-01 | −9.2 | 2% | +12.9 | 27% | −22.1 | 208.0 | −10.2 |
| 2026-02 | −15.2 | 0% | −4.8 | 16% | −10.4 | 158.8 | −15.0 |
| 2026-03 | −7.0 | 0% | +4.1 | 20% | −11.1 | 173.0 | +2.0 |
| 2026-04 | −2.7 | 1% | −8.5 | 19% | +5.8 | 117.7 | +11.8 |
| 2026-05 | +4.4 | 2% | −10.8 | 20% | +15.2 | 117.1 | −3.5 |
| 2026-06 | +0.8 | 1% | −17.0 | 28% | +17.9 | 123.1 | −20.4 |
| 2026-07 | +4.3 | 2% | −5.1 | 32% | +9.4 | 96.4 | +7.3 |
| 2026-08 | +1.2 | 6% | +2.1 | 38% | −1.0 | 90.5 | +25.0 |
| 2026-09 | +9.5 | 11% | +10.7 | 44% | −1.2 | 62.5 | +6.4 |
| 2026-10 | +5.6 | 3% | −0.0 | 39% | +5.7 | 47.1 | −7.3 |
| 2026-11 (to 15th) | +5.2 | 2% | −5.5 | 35% | +10.7 | 59.1 | −17.1 |

**What it shows**
1. **The book harvests cross-venue dispersion in both directions, not the floor alone.**
   - From November to March, Hyperliquid's alt perps traded so far below spot that their funding sat under the
     floor (−7% to −15%/yr). The design-signed gap (long Kraken, short Hyperliquid) was negative on average in four
     of those five months.
   - R275's rule is sign-agnostic (it shorts whichever venue pays more), so it earned from the reverse side.
   - The "design gap" is the median coin's story (FINDINGS: median gap +5.3%/yr). The profit came from the tails of
     the dispersion.
2. **The book's return follows realized dispersion.**
   - Month by month, R508's return correlates with the top-20 |gap| at 0.91 in the same month, but only 0.27 with
     the previous month's.
   - Dispersion fell by about a factor of 3, from about 170%/yr in Q1 2026 to about 55% in Q4. That is the book's
     decline from about 3% a month to about 1%.
   - Last month's dispersion barely predicts this month's: spikes come with sell-offs, unannounced.
3. **There is a structural hint, from one matched pair.**
   - In two sell-off months a year apart (BTC −17.6% in November 2025, −17.1% in November 2026 to the 15th), the
     top-20 dispersion fell from 103.6 to 59.1.
   - Over the same year, Hyperliquid's alt funding no longer collapsed (−15.0 against +5.2), and the share of
     Kraken's hours above Hyperliquid's floor rose from 20% to 35%.
   - For the same market move, the dispersion roughly halved. That is He et al.'s capacity growth, seen at small
     scale.
   - It rests on one pair of months.
4. **Cause 2 (Hyperliquid's portfolio margin) is not supported.**
   - After 2026-04-15, Hyperliquid's funding on BTC and HYPE (the collateral-eligible coins) rose from 6.7% to
     8.5%/yr. On the other coins it rose from −9.3% to +3.9%.
   - There is no portfolio-margin-specific compression. The move is market-wide.
5. **My prediction (cause 1) was half right.**
   - Kraken's funding did rise relative to Hyperliquid's floor (hours above it went from about 20% to 35-44%).
   - But the main movement was the regime. The winter sell-off drove Hyperliquid's alt funding far below its floor,
     and the dispersion it created has been shrinking since.

## 5. What it changes
- **The forward base rate for the money plan is the autumn level, not the winter one.**
  - About 1% a month at 1x (top-20 dispersion about 50-60%/yr). Thorp's halving gives about 6%/yr; after the
    31.4% tax about 4%; against euro cash after tax (about 1.5%) about +2.5%/yr on capital at 1x.
  - That is thin against the stake note's bar ("forward edge of at least about 5%/yr").
  - Answer 4's figures (+11-15%/yr halved, €3-8k/yr) were built on the whole year, winter included. They overstate
    the current level by about two to three times.
- **The sleeve pays most in sell-offs.** Its best months came with falling markets, when Hyperliquid's alt perps
  sank below their floor. For an owner with long crypto exposure elsewhere, that is a useful shape. It also means
  the forward reads due in December, which cover November's sell-off, may look better than autumn did.
- **The quarterly reassessment gets a number:** the live top-20 |gap| across the book's pairs. It is observable
  every hour from the venues' own funding.
- **R509 and R510 are unchanged.** They are frozen, and their reads stay on their dates.

## 6. What could make this wrong
- **Equal weight over 107-111 coins is not the book.** The book picks the top-20 by trailing 14 days, and its
  return per unit of same-month dispersion varies from 1.4% to 2.2% a month per 100 points.
- **One matched pair of months** carries the structural hint.
- **R508's window is one year.** A longer pair history (R525 covers 2021-2026 for other pairs) could separate
  regime from trend. That is the next decomposition.
