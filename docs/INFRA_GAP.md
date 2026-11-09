# Why fast firms win, why we do not, and what their infrastructure would change

Written by Claude on 2026-11-09 for the edge loop (`docs/loop/PROMPT.md`). It rests on R431's measurements and on
public figures. Facts marked **secondary** come from press or vendor pages and were not checked against filings. Facts
marked **verified** were read on the official page on the date given. The ledger at the bottom grows each tick.

## 1. How big they are (secondary)
- **Jane Street:** about $20.5bn of net trading revenue in 2024, about double 2023
  ([The Star, citing Bloomberg](https://www.thestar.com.my/business/business-news/2025/04/25/jane-streets-us21bil-trading-haul-tops-citigroup)).
- **Citadel Securities:** about $9.7bn of revenue in 2024 ([Global Trading](https://www.globaltrading.net/?p=38181)).
- **XTX Markets:** about £3.93bn of revenue in 2025
  ([Finance Magnates](https://www.financemagnates.com/forex/brokers/xtx-markets-revenue-rises-43-to-393-billion-in-2025/)).
- **Flow Traders:** €485.8m of net trading income in FY2025 on €1.94tn of ETP value traded, with €1.04bn of trading
  capital (annual-report excerpts; the PDF was not opened).

These firms earn a fraction of a basis point per unit traded, many millions of times a day, on flow and fee terms
that a small account cannot get.

## 2. Where the money comes from, and what a small public-data player has of each
| Source of edge | What it is | Do we have it? |
|---|---|---|
| **Flow** | Retail orders bought or internalised. Citadel Securities paid $2.6bn for order flow in 2020-21, per Rule 606 data cited in [CRS IF12594](https://www.everycrsreport.com/reports/IF12594.html). Also RFQ/OTC requests and ETF creation and redemption as an authorised participant | No |
| **Fee terms priced by scale** | Rebates and tiers that only large makers reach (details below) | No |
| **Speed** | Microseconds to a few ms from event to order; it pays only when the payer is slower | No. We are ~250 ms behind (R431) |
| **Breadth** | IR ≈ IC × √(independent bets). A tiny edge on thousands of instruments, many times a day | Partial. About 100 coins, daily decisions |
| **Balance sheet** | Carrying inventory, liquidation backstops (Hyperliquid's HLP takes backstop liquidations), cheap funding | $10k |
| **Models and people** | Fair value across related books, toxicity and inventory control | Public methods only |

**Fee terms, verified on 2026-11-09:**
- **Binance's USDⓈ-M liquidity-provider program**
  ([announcement, effective 2024-01-03](https://www.binance.com/en/support/announcement/detail/f5d3200b65104308b8349cee59a2296e)):
  - USDC-M maker rebates are −0.006%, −0.007% and −0.008%: −0.6, −0.7 and −0.8 bp a fill.
  - A tier needs at least 0.20%, 0.60% or 1.50% of the venue's weekly maker volume, or a top-40% quoting rank.
  - Applying needs $100M of futures volume in 30 days. At $10k of capital, that is a turnover of about 330 times
    capital every day.
  - The current terms were not checked against later updates.
- **Binance USDC-M perpetuals** ([announcement, 2025-12-09](https://www.binance.com/en/support/announcement/03180947641b414ebcb9a6c407fe80e2)):
  - Maker 0.0000% at every tier.
  - Taker 0.0400% for regular users, falling to 0.0094% at VIP 9.
  - "Until further notice", extended on 2026-03-30.

## 3. If we had their infrastructure (but not their flow, capital or fee tier)
| Edge | Our result | With colocation alone | What would flip it |
|---|---|---|---|
| Binance USDT→USDC taker lead | R431 NULL: +0.08 bp gross vs 8 bp a round trip | **No.** One ms after publication the gross is already −0.06 bp. Even the VIP 9 taker fee (0.94 bp a fill) is far above it | Nothing a taker can buy. Binance's own arbitrage settles in a median 7 ms, and many moves are stamped on both books in the same ms: the edge goes to whoever quotes both books |
| Binance USDC maker | R431 Part C: takers' markout +0.55 bp at 1 s against a 0.01-0.04 bp touch, 0% maker fee, so about −0.5 bp a fill | **No.** Speed keeps queue position but does not remove the toxicity | **Scale:** with the −0.8 bp tier, about +0.27 bp a fill before inventory, cancel races and queue loss. That needs ≥ 1.5% of maker volume |
| Lighter as a slow maker | R426 negative on a 225 s fragment; R428's stream blocked by jurisdiction | Standard: a maker's cancels wait 300 ms, and a Premium taker hits after 140 ms. **The speed bump protects Premium makers from Standard takers, not us** | A Premium maker (0 ms cancel, 0.4 bp fee) whose cancel lands before 140 ms. From here the one-way delay alone is ~125 ms, so it is unmeasured and marginal |
| Funding carry | R391 +2.48%/yr (gate 1), below a T-bill | **No change:** funding settles hourly or every 8 h | Capital and fee tier scale it; speed does not |
| Forced flow (liquidations) | R206 and R252 NULL | **No.** The backstop goes to the venue's vault (HLP) or the firm holding the flow | Being the backstop |

**The conclusion:** speed is not what we lack most. Where we are slow, the fast firms' edge rests on flow, fee tiers
and balance sheet, and infrastructure alone would not flip any of the five rows. Two rows flip only with scale (the
rebate tier) or a venue's account tier (Lighter Premium).

## 4. What a slow, small, public-data player can still reach
An edge we can take needs a payer who is not racing, and a reason the fast firms leave it:
1. **Capacity too small for them.** Long-tail carry (R391) and unlock shorts on small caps (R265, +3.24% an event at
   gate 0; R266 forward). The money does not scale to their size.
2. **The hold is too long for their mandate.** Multi-day scheduled flows: unlocks, index and listing events, carry.
3. **A rule makes speed worthless.** Clocks such as funding settlement or a daily mark, as long as the payoff comes
   after the rule's window and not inside it. The settlement hops inside the window failed at per-coin cost (R354,
   R363).
4. **A venue where our account tier is not the slowest.** This is untested. On Lighter we are the slowest on both
   sides (row 3 above).
5. **Barriers.** These cut both ways for us. Lighter refuses our native runner's jurisdiction (R428), and prediction
   markets are not legal for the owner (M291).

**How the loop uses this:** before any test, write who pays and which of points 1-5 explains why the fast firms left
it. If none fits, the expected gross is zero and the test needs a stronger reason.

## 5. Ledger: edges only infrastructure or scale would flip
Append one row per tick when a candidate dies on infrastructure or scale. Never delete rows.

| Date | Edge | Evidence | What flips it | Why not us |
|---|---|---|---|---|
| 2026-11-09 | Binance USDT→USDC taker lead | R431 frontier flat at 0 from 1 ms | Nothing for a taker; quoting both books | We cannot quote at ms speed |
| 2026-11-09 | Binance USDC passive making | R431 Part C, +0.55 bp toxicity | −0.6 to −0.8 bp LP rebate | Needs ≥ 0.2-1.5% of maker volume and $100M in 30 days to apply |
| 2026-11-09 | Lighter Standard maker behind the speed bump | Doc arithmetic: 300 ms cancel delay vs 140 ms Premium taker | Premium account and a cancel path under ~140 ms | ~125 ms one-way from here; native stream blocked (R428) |
