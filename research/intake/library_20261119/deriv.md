# Notes: derivatives / funding / carry digest

Started 2026-11-19.

## Read (scope actually read)
1. He, Manela, Ross, von Wachter. Fundamentals of Perpetual Futures. arXiv:2212.06888v5 (Jun 2024). Read: abstract, Sec 1 intro, Sec 2 funding definition, Sec 3 Props 1-2 statements (proofs NOT read). Binance clamp discussion (fn 3) not read.
   - Funding payment kappa*(F_s - S_s) ds; kappa=1095 maps an 8h rate to annual units.
   - Prop 1: F_t = kappa/(kappa-(r-r')) * S_t (no random-maturity arb), needs kappa > r (Assumption 3).
   - Prop 2: |F_t - kappa/(kappa-(r-r')) S_t| <= C (round-trip cost C).
2. Ackerer, Hugonnier, Jermann. Perpetual Futures Pricing. arXiv:2310.11771v2 (Sep 2024). Read: abstract, intro, Sec 2 model, Prop 1 and Prop 3 statements (proofs NOT read).
   - Linear perp, constant rates: f_t = (kappa - iota)/(kappa + r_b - r_a) * x_t (Prop 3). iota = interest term of funding.
3. Christin, Routledge, Soska, Zetlin-Jones. The Crypto Carry Trade. CMU v1.0 (Aug 2022). Read: abstract, Sec 1, Sec 2 (return definition), Sec 4.1-4.2 partially (leverage/margin/liquidation).
   - Binance funding = 0.01%/8h + basis adjustment (fn 3). Long-spot/short-perp Sharpe 7-10 in sample (BTC 12.8 and 7.0 as stated in intro).
   - July 2021 Binance cut max leverage 125x -> 50x; carry returns fell.
4. Koijen, Moskowitz, Pedersen, Vrugt. Carry. JFE 2018, accepted manuscript (CBS repo, CC BY-NC-ND). Read: Sec 1, Sec 2 (eqs 2-4).
   - C_t = (S_t - F_t)/X_t for a futures; commodity carry ~ basis/convenience yield.
5. Kim & Park. Designing funding rates for perpetual futures in cryptocurrency markets. arXiv:2506.08573 (Jun 2025). Read: abstract, Sec 1.1-1.2, literature review, Sec 4.1 assumption text. Proofs and BSDE theory NOT read or verified.
   - Literature leads: Dai et al. (2025) on clamp-based no-arb bounds (not retrievable); Angeris et al.; Alexander et al. (2020); Christin et al. (2022); Wang & Zhang (2025).
6. Angeris, Chitra, Evans, Lorig. A primer on perpetuals. arXiv:2209.03307 (Sep 2022). Read: abstract, intro, Thm 2 (funding formula, text extraction garbled, reconstructed approx), Sec 3-4 intro. Thm 7 (discount-rate perp) NOT read.
7. ESMA. Public statement ESMA35-243228190-8024 (24 Feb 2026). https://www.esma.europa.eu/node/228326 ; PDF /sites/default/files/2026-02/ESMA35-243228190-8024_-_Public_statement_on_derivatives_in_scope_of_the_CFD_product_intervention_measures.pdf. Read: background, scope, investor-protection parts (about 75 of 126 extracted lines).
   - Funding-rate mechanism and insurance funds are explicitly irrelevant to the CFD-scope assessment.
8. BIS WP 1087 "Crypto carry", Schmeling, Schrimpf, Todorov. https://www.bis.org/publ/work1087.htm. Read: abstract page only. PDF blocked (JS challenge to curl).
9. BIS WP 1164 "Public information and stablecoin runs", Ahmed, Aldasoro, Duley. https://www.bis.org/publ/work1164.htm. Read: abstract summary via WebFetch only. PDF blocked.
10. Ritchken, "Pricing Futures and Forwards" slides (Case Western). Notes2.PDF, 45 pages; read assumption and property slides only (~pp 11-16). Explicit cost-of-carry formula not seen in extracted text (inferred F = S e^{rT} under constant rates).
11. Hyperliquid funding docs. https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding . Read via WebFetch summary, not verbatim-checked by me.
   - F = P + clamp(r_int - P, -0.0005, +0.0005); r_int = 0.01%/8h; premium sampled every 5 s, averaged hourly; cap reported 0.5%/h (conflicts with a community doc quoting 4%/h).
12. Binance USDS-M funding FAQ. https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031 . Read via WebFetch summary.
   - Premium index every 5 s; clamp +/-0.05% around 0.01%/8h; flat 0.01% if P in [-0.04%, +0.06%].
   - Settlement 8h default; 1h at cap/floor from 2025-05-02; back to 4h after 16 cycles from 2026-01-02 (per summary).
13. Lighter docs, https://docs.lighter.xyz/trading/funding.md . Read via WebFetch summary.
   - premium_t sampled each minute; hourly average; InterestRate 0.01%; SmallClamp 0.05%; BigClamp 4%/8h; fundingRate = clamp(...)/8 per hour.
14. Kraken linear multi-collateral perp spec, support article 4844359082772. Read via WebFetch summary.
   - No interest/base-rate term stated; premium from 60 minutely impact-mid observations, average of middle 30; hourly funding clamp +/-0.5%; settlement hourly. Doc-level support for lab premise; not checked against the API docs.
15. Nimmagadda and Ammanamanchi. BitMEX funding correlation with Bitcoin exchange rate. arXiv:1912.03270 (Nov 2019). Read: abstract via WebFetch summary. Funding heteroskedastic; GARCH forecast; Granger claim.

## Found, not read
- Schar, Decentralized Finance (St. Louis Fed Review 2021): Basel/Fed PDFs not retrieved (landing page only).
- Dai, Li, Yang, "Arbitrage in Perpetual Contracts" (SSRN 5262988): no arXiv version; not fetched.
- BitMEX Q3 2025 "The Anchor and the Ceiling" (blog.bitmex.com/2025q3-derivatives-report): redirected to blog index; not read.
- MiCA Reg (EU) 2023/1114: EUR-Lex returned empty; not read.
- Mastering Bitcoin / Mastering Ethereum (GitHub mirrors): licence status unverified; not read; out of derivatives scope.
- Alexander et al. (2020), Wang & Zhang (2025): named in Kim & Park only.
- Kraken inverse perp docs: fetched page had no funding text.
- Hull (paid), Kraken and Aster/Paradex funding pages: not read.
