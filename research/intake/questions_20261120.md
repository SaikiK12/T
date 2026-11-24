# Question bank, 2026-11-20: what the lab needs to know now

Each question serves a decision on the carry books (R509-R514) or the path to a first small stake. "Zones" are where
to scout. A reader follows `reading_protocol.md`.

## Q1. How likely is a resting order on a thin book to fill, and what does a fill cost in adverse selection?
- **Serves:** R513/R514 (passive entries), and the next carry lane's cost rule.
- **An answer looks like:**
  - a fill-probability model for a limit order at the touch, as a function of queue position, order flow and
    horizon;
  - a way to measure mark-out from public trades;
  - a rule for when to cross the spread instead of waiting.
- **Zones:**
  - Cont, Stoikov & Talreja (2010), a stochastic model for order-book dynamics;
  - Moallemi & Yuan, queue-position valuation;
  - Huang, Lehalle & Rosenbaum (2014), the queue-reactive model;
  - Lehalle & Mounjid (2016), imbalance and adverse selection;
  - Gould & Bonart (2015), queue imbalance.

## Q2. How persistent are funding spreads on thin perps, and what limits them?
- **Serves:** whether R508/R511's in-sample level should be expected forward; the 2025-26 decline; capacity.
- **An answer looks like:**
  - half-lives or decay of funding and basis deviations;
  - determinants: retail leverage, arbitrage capital, interest terms;
  - evidence on capacity and crash risk of crypto carry.
- **Zones:**
  - BIS WP 1087 "Crypto carry" (Schmeling, Schrimpf, Todorov);
  - He, Manela, Ross & von Wachter, fundamentals of perpetual futures;
  - Ackerer, Hugonnier & Jermann, perpetual futures pricing;
  - Christin et al., the crypto carry trade.

## Q3. How often do crypto venues fail or freeze, and what is lost when they do?
- **Serves:** sizing (`docs/reviews/sizing_20261120.md` leaves venue failure out), and how much capital to keep on
  each venue.
- **Now binding (2026-11-24).** It is the input that decides the stake's size in `scripts/stake_kelly.py`.
  - At leverage 2 with a halved edge, the stake beats cash only below about 2.5-5% venue failures a year.
  - A first search found only secondary, conflicting recovery figures: FTX at 9-142% depending on the valuation
    date; QuadrigaCX under 30%.
  - Read next: the hazard models of Moore & Christin (2013) and Moore, Christin & Szurdi (2018, "Revisiting the
    risks of Bitcoin currency exchange closure"). Then the court and administrator figures for each failure.
- **An answer looks like:**
  - base rates of exchange closure or loss, and loss given failure;
  - how insurance funds, auto-deleveraging and liquidation engines behave in stress;
  - mitigations for a small two-venue book.
- **Zones:**
  - Moore & Christin (2013), "Beware the middleman";
  - later exchange-risk studies;
  - BIS, IMF and ESMA reports on crypto-venue failures;
  - Hyperliquid's and Kraken's liquidation and auto-deleveraging docs.

## Q4. What do EU and French rules allow a retail client in crypto perpetuals?
- **Serves:** the first stake's leverage and venue choice; Kraken EEA.
- **An answer looks like:**
  - leverage caps;
  - margin close-out and negative-balance protection;
  - whether perpetuals are CFDs under ESMA's 2026 statement;
  - the AMF's national measure;
  - what Kraken EEA applies to retail.
- **Zones:**
  - ESMA statement ESMA35-243228190-8024 (24 February 2026);
  - ESMA's CFD product-intervention measures;
  - the AMF's CFD measure;
  - Kraken EEA derivatives documentation.

## Added later on 2026-11-20
### Q5. What creates the funding extremes on thin perps, and what makes them stop?
- **Serves:** forward expectations for R509-R515. The 2026-11-20 measurement found the edge is a stream of short-lived
  extremes (half-life of days), not a property of particular coins.
- **An answer looks like:**
  - drivers with evidence: new listings, open-interest build-ups, leverage-limit changes, squeezes, airdrops or
    unlocks, index-construction quirks on thin books;
  - which of them a public-data signal could see in advance.
- **Zones:**
  - papers on funding-rate determinants and on listing and unlock effects in crypto derivatives;
  - Kraken's and Hyperliquid's funding and index methodology pages;
  - exchange research notes (BitMEX, Kaiko and others, free).

### Q6. What exactly does Kraken EEA offer a French retail client in perpetuals?
- **Serves:** the first stake.
- **An answer looks like:**
  - leverage per contract, and whether the products are treated as CFDs;
  - margin and close-out rules, negative-balance protection;
  - insurance fund and auto-deleveraging rules;
  - fees for EEA futures;
  - the KID and the appropriateness test;
  - which contracts are offered to EEA clients.
- **Zones:** Kraken support and legal pages for Payward Europe Digital Solutions (CY) Ltd, Kraken futures
  documentation, CySEC's register entry.

### Q7. What did published studies of funding-rate arbitrage measure, and which risks do our books miss?
- **Serves:** external validity of R507-R515's PASSes, the stake's risk list, and sizing's stress case.
- **An answer looks like:**
  - measured returns, Sharpe, drawdowns and capacity of funding or cross-venue carry, with venues, period and costs;
  - failure modes the studies saw: liquidation of one leg, venue outages, depegs, auto-deleveraging, fee changes;
  - whether high carry predicts crashes, and how large the losses were;
  - anything that predicts funding extremes in advance (open interest, leverage, listings, unlocks).
- **Zones:**
  - arXiv and SSRN papers on funding-rate arbitrage across centralised and decentralised venues (2023-2026);
  - BIS WP 1087 "Crypto carry" (the full text; its PDF did not extract on 2026-11-20);
  - free exchange and data-vendor research on funding-arbitrage performance.
