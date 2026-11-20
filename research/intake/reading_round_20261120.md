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
- **What it earns.** The lab measures persistence itself, on data it holds: an AR(1) half-life of the Kraken-Hyperliquid
  and Kraken-Aster funding spreads per coin, and the decline against open interest. Not done yet.

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
