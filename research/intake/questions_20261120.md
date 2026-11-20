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
