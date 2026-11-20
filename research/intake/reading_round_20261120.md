# Reading round 2026-11-20: four questions, by the new protocol

- **Method.** `reading_protocol.md`: four Haiku readers, one per question in `questions_20261120.md`. Each used
  `scripts/read_source.py` to locate pages, read only those pages, and wrote mini-cards.
- **Cost.** 85-89k tokens per reader (Q1 88.8k, Q2 87.2k, Q3 88.2k, Q4 85.1k). The 2026-11-19 library readers used
  167-251k each, so this is about 55% less. Each reader read 14-20 pages from 4-6 sources and gave an answer.
- **Checked by the session** (rule 5), because these claims set the first stake:
  - ESMA's 2026 statement: pp. 1-2 re-read through the locator;
  - ESMA's 2018 CFD measures: ESMA's own press release and FAQ, through search.

## Q1. Fills on thin books (serves R513/R514)
- **Answer.**
  - No paper gives fill odds at 1 h or 6 h for crypto perps.
  - The decomposition that applies (Moallemi & Yuan, pp. 9, 20): a resting order's value = P(fill) × (half-spread
    − adverse-selection cost), and P(fill) falls with the queue ahead.
  - Lehalle & Mounjid (pp. 12, 17): cancel when the imbalance turns against the order; cross at the deadline.
  - Huang, Lehalle & Rosenbaum (pp. 3, 16): with uniform cancellation and a trader who never cancels, the
    queue-reactive model may overstate fill probability.
- **What it earns.**
  - Kraken's public order-event history carries an order `uid` on every event (checked by the session on
    2026-11-20). So the queue ahead of a resting order is observable, and the decomposition can be estimated on Kraken
    without assumptions.
  - **Hypothesis to test:** R513's saving shrinks when the imbalance at placement runs against the order.
- **Not read:** Cont, Stoikov & Talreja (2010), and Gareche et al. (2013).

## Q2. Funding persistence and limits (serves R509-R512's expectations)
- **Answer.** No free source read measures a half-life of funding or of cross-venue funding spreads, or the capacity
  of crypto carry. The gap stays open.
- **What the evidence read says.**
  - Long-side leverage demand sets funding. Funding and carry fell when Binance cut its maximum leverage from 125x to
    50x in July 2021 (Christin et al., pp. 5, 15, 20; working paper).
  - Crypto carry is driven by retail leverage demand and scarce arbitrage capital, and high carry predicts crashes
    (BIS WP 1087, abstract page only; the PDF did not extract).
  - With no interest term, the perpetual's deviation grows with the interest spread and shrinks with the premium's
    anchoring strength (Ackerer, Hugonnier & Jermann, p. 12).
- **What it earns:** the lab measures persistence itself, on data it holds.
- **Measured by the session, 2026-11-20** (descriptive, no decision). Kraken-Hyperliquid daily funding spread
  (Hyperliquid minus Kraken), 111 coins of R508's table, 2025-11-17..2026-11-15:
  - **Around each coin's own mean, the spread reverts fast.**
    - Daily AR(1) median 0.38-0.42: a half-life under 1 day.
    - Weekly means: AR(1) about 0.3, a half-life of about 4 days.
  - **A coin's mean level is only weakly persistent.**
    - Half 1 against half 2 (split at 2026-05-17): rank correlation 0.47 (thin coins 0.34). The slope of the second
      half's mean on the first's is 0.10.
    - Coins with |spread| above 20%/yr in half 1 kept the sign in 57% of cases.
    - 76% of all coins kept the sign, mostly through the structural floor (Hyperliquid above Kraken).
  - **What it means.**
    - The carry book's edge is a persistent structural baseline (the floor gap) plus a stream of short-lived extremes
      that the 14-day signal catches and rotates out of. It is not a stable property of particular coins.
    - Its forward return depends on extremes continuing to arrive, which the literature read ties to retail leverage
      demand.
    - A coin's past extreme is no reason to hold it.

## Q3. Venue failure (serves sizing)
- **Answer.**
  - The only published base rate is old and small-sample. Moore & Christin (2013): 18 of 40 Bitcoin-fiat exchanges
    closed in 2011-13; one-year closure probability 29.9% (95% CI 12-42%); median life 381 days.
  - Reimbursement was known for 11 closures: 5 paid nothing, 6 said they paid (pp. 3-5).
  - Higher volume lowered the closure hazard (doubling volume: ×0.84).
  - Loss given failure is not measured anywhere read.
- **Hyperliquid's rules** (docs, read through summaries):
  - liquidation on the book, then the liquidator vault below 2/3 of maintenance margin, then auto-deleveraging;
  - auto-deleveraging ranks by (mark/entry) × (notional/account value), so low notional per unit of equity lowers a
    leg's priority.
- **Kraken Futures' insurance fund and auto-deleveraging rules:** not reached (403).
- **What it earns.** For sizing, treat the collateral on each venue as lost in the stress case. Keep legs unlevered
  where possible, withdraw surplus collateral, and alert well above the liquidation line.

## Q4. EU and French rules for a retail client (serves the first stake)
- **Answer, checked.**
  - **ESMA's statement of 24 February 2026** (ESMA35-243228190-8024, pp. 1-3, read in full by the reader; pp. 1-2
    re-read by the session):
    - derivatives marketed as perpetual futures that give leveraged exposure to crypto "are likely to fall within the
      scope" of the national CFD measures;
    - the commercial name, the funding mechanism and voluntary safeguards do not change that.
  - **ESMA's 2018 CFD measures** (its press release and FAQ):
    - leverage on opening a position from 30:1 down to **2:1 for cryptocurrencies**;
    - margin close-out at 50% of the minimum required margin, per account;
    - negative-balance protection per account.
  - The AMF's national measure carries these rules in France (secondary; its text was not read).
- **Kraken's EEA page** advertises "up to 10x" for EU clients. Its EEA contract specifications, and whether it treats
  its perps as CFDs, were not reached.
- **What it earns.**
  - Plan the first stake at no more than 2:1 on the Kraken leg, as `docs/reviews/sizing_20261120.md` proposes.
  - Ask Kraken EEA in writing which cap and protections apply.
  - Expect a key information document (KID) and an appropriateness test at account opening.

## Second wave, the same day (Q5, Q6)
- **Cost:** about 87k tokens for Q5; Q6 was a similar size (6 pages of Kraken docs, read through web-fetch summaries).

### Q5. What creates the funding extremes
- **Mechanism, published.** He, Manela, Ross & von Wachter, pp. 12, 14, 64-65:
  - Funding is the averaged impact-price premium passed through a clamp around the interest term. Beyond the clamp,
    funding moves one-for-one with the premium, so thin books make the premium large and jumpy.
  - Cross-venue arbitrage is capital-limited, because each leg needs its own margin. So a thin venue can stay
    mispriced, and divergence peaks in liquidity stress.
- **Predictors.** No source read tests listings, unlocks, open-interest build-ups or squeezes as predictors.
  - A BitMEX Q1 2025 report, seen only as a snippet, puts the median post-listing funding peak at about 6 days.
- **Measured by the session** (descriptive, R508's coins and window). The absolute Kraken-Hyperliquid daily funding
  spread, by days since the Kraken contract's listing:

  | Days since listing | Coin-days | Median, %/yr | Share above 100%/yr |
  |---|---|---|---|
  | under 30 | 31 | 128 | 84% |
  | 30-90 | 151 | 41 | 24% |
  | 90-180 | 415 | 18 | 13% |
  | 180-365 | 1,816 | 27 | 19% |
  | over a year | 37,773 | 18 | 11% |

  - New listings give the largest spreads. Means stay high later (54-99%/yr) from occasional spikes.
  - The first-month sample is small. A listing-age signal could be tested as a new, registered variant (not done).

### Q6. What Kraken EEA offers a French retail client
Read through web-fetch summaries of Kraken's own support pages:
- "Perpetual contract specifications for clients in the EEA", updated 13 November 2026;
- the Liquidation FAQ;
- the Equity Protection Process page;
- "What are derivatives (EEA)";
- the EEA questionnaire page;
- "Unlock derivatives (EEA)".

What those pages say:
- **Leverage:** up to 10x on most perps (two at 20x). Initial margin as low as 10%; maintenance at half the initial.
- **Liquidation:** partial in 10% steps, then full. "No margin calls or any warnings."
- **Negative balances:** the account "can never go below zero"; the equity-protection page names no region beyond
  "outside of the U.S.".
- **Shortfalls:** no insurance fund. A derivatives liquidity pool covers them; auto-deleveraging is not mentioned.
- **Funding:** capped at ±0.5% an hour.
- **Onboarding:** an appropriateness questionnaire and a tax number are required.
- **Not found:**
  - no KID;
  - nothing on CFD classification or on ESMA's 2026 statement.
- **Contract count:** about 327 perps listed for the EEA.

What it means for the stake:
- Kraken publishes 10x, while ESMA's 2026 statement makes retail perps likely CFDs (2:1). The conflict is unresolved
  on Kraken's pages. The owner's written question to Kraken EEA settles it.
- Either way, the stake plan stays at 2x or less.
- **Liquidation comes without a warning,** so the book needs its own margin buffer and alerts.
