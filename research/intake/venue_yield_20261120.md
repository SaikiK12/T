# Collateral yield and venue incentives on the owner's venues: read and measured by Claude, 2026-11-20 (M475, family V1)

- **Why.** `CLAUDE.md` step 2. The binding constraint: the carry books earn about the cash rate (R515, Q7), so whatever
  the posted margin earns is a P&L term of the same size class. V1 was the only edge family never measured
  (`docs/EDGE_MAP.md`).
- **How.** Read by me from the venues' own docs (Markdown copies), with no subagent. The Hyperliquid rate was measured
  from its public info API the same day.

## Hyperliquid: portfolio margin pays interest on idle USDC
- **Sources.** Read in full:
  - "Portfolio margin" (`hyperliquid.gitbook.io/hyperliquid-docs/trading/portfolio-margin.md`);
  - its FAQ (`…/support/faq/portfolio-margin.md`).
- **Rule.** Under portfolio margin (PM), "any idle USDC balance is automatically supplied to earn yield". Suppliers
  earn what borrowers pay, pro rata.
- **Rate formula (docs):**
  - borrow APY = 0.05 + 4.75 × max(0, utilization − 0.8), compounded continuously;
  - the protocol keeps 10% of borrow interest as a liquidation buffer;
  - so supply APY = borrow APY × utilization × 0.9.
- **Measured, 2026-11-20 about 14:00 UTC** (`POST api.hyperliquid.xyz/info {"type":"allBorrowLendReserveStates"}`):

  | Token | Utilization | Supply APY | Note |
  |---|---|---|---|
  | USDC (0) | 0.589 | **2.65%** | $643M supplied, $379M borrowed |
  | 268 | 0.323 | 1.45% | $3.6M supplied |
  | 360 | 0.126 | 0.57% | $0.15M supplied |
  | HYPE (150), BTC (197) | 0 | 0% | collateral, LTV 0.65 / 0.5 |

  - Check: 0.05 × 0.589 × 0.9 = 2.65%, so the formula matches the live state.
- **Who pays:** PM users who borrow USDC against HYPE or BTC (LTV 0.65 and 0.5), mainly for spot-perp carry.
- **Eligibility, the binding fact.**
  - Account value above **$10,000**, or above $5M of weighted volume.
  - The account must hold no open position when PM is switched on.
  - Upper bound: the FAQ says below $5M, the docs say $25M.
- **What it adds to a carry book.** It applies only to the Hyperliquid leg's idle part.
  - Unlevered, with Hyperliquid half of the book and about 80% of that leg idle: about +1%/yr on book capital at
    today's rate. That is about a tenth of R508's +10%/yr.
- **Risks:**
  - withdrawals of supplied USDC wait when utilization reaches 100%;
  - borrowers are liquidated by a backstop liquidator with no market phase;
  - the rate moves with HYPE/BTC borrowing demand and is not served as history.

## Aster: USDF as margin
- **Sources.** Read in full:
  - "Single-Asset Mode & Multi-Asset Mode" (`docs.asterdex.com/trading/perpetuals/…md`);
  - "Trade & Earn" (`docs.asterdex.com/program-and-rewards/trade-and-earn.md`).
- **Rule.** Multi-Asset Mode (cross margin only) accepts USDF at a 99.99% collateral value ratio and asBNB at 95%.
- **Two USDF reward streams:**
  - **deposit rewards**: hold more than 1 USDF; hourly snapshots; distributed weekly;
  - **trading rewards**: trade at least 2 days a week with at least $50,000 of weekly volume (since 2025-11-20);
    capped at 100,000 USDF per account.
- **Rates:** neither page states one.
  - Third-party pages quote 0.8% for deposits and up to 14.5% for trading rewards. Not verified; campaign rates.
  - USDF's yield comes from delta-neutral funding positions (Aster's custody page, seen as a search snippet), so it
    moves with funding, like our books.
- **Other terms:**
  - since 2026-04-09, interest is charged on negative USDT/USD1 balances beyond −$1,000;
  - "all program rules may be amended or cancelled at Aster's discretion";
  - wash trading disqualifies.
- **What it adds.** For a small hedged carry book, about nothing:
  - the trading-reward volume is about 20-100 times the turnover of a $2-10k book;
  - buying volume would cost more than it earns, and it borders on the farming the terms disqualify.
- **Not read:** Aster's restricted-jurisdiction terms for USDF. sUSDe, its closest analogue, is not offered to EU/EEA
  residents (`research/intake/README.md`).

## Lighter: zero fees, not yield
- **Sources:** search results quoting `docs.lighter.xyz/trading/trading-fees`. I did not read that page itself.
- **Standard accounts:** zero maker and taker fees, with 200-300 ms latency.
- **Premium accounts:** pay fees, which LIT staking discounts.
- **Points:** third-party pages describe weekly pools (200-250k points), with conflicting numbers.
- **What it adds.** No collateral yield was found. Zero fees cut the cost of a Lighter leg by 4-5 bp a side against
  Hyperliquid. Points are not counted, because their value is a hope until a token exists.

## For the stake plan
- **Size.** The planned first stake (`docs/reviews/sizing_20261120.md`: $2,000 at most) is below Hyperliquid's $10k
  threshold, so that yield is not available to it.
- **When it applies.** If a later stake passes $10k on Hyperliquid, switching on PM before opening positions adds about
  +1%/yr at today's rate. The cost is that collateral and perps share one liquidation account.
- **Not a reason to size up.** The carry evidence decides the size.

## Next
- **A cheap forward record** of `allBorrowLendReserveStates`, once a day, so that the term has a history. Its own file
  and its own workflow step; no change to the shared cache keys (lesson L002).
- **Before any use of USDF,** read Aster's terms for EEA residents.
