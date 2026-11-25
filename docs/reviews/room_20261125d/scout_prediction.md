# Scout: prediction markets (Polymarket, Kalshi), 2026-11-25

Scout: room_20261125d. Read-only. No orders, accounts or downloads. Experiments journals not opened.
One attempted recursive grep from the repo root covered experiments/; it was denied and did not run.

## 0. What the lab already holds (read first)

- M098 (registry/methods.csv:99): "Owner-approved acquisition needed"; "not legal for the owner"; "Read-only public prices only." Status BLOCKED.
- M291 (registry/methods.csv:263): the Polymarket No-bias and favourite-longshot rows. "Not MEXC: venue, region and wallet need the owner's yes." Status BLOCKED.
- M058 (registry/methods.csv:59): two-sided market making, including "Kalshi MM". "live L1 recorder (owner's yes)". Status BLOCKED.
- M164 and M165 (registry/methods.csv:165-166): marketing and tool rows, no testable rule.
- Cited rounds: R168, R193, R194 and R224 are not prediction-market tests (R193/R194 are MEXC maker books; R224 is MEXC costs). A grep of registry/rounds.csv for "prediction", "polymarket" and "kalshi" found no row.
- Legal card: research/intake/cards/SRC1103-028.md:37-40: "Mechanism: none for the owner; access is illegal." and line 32: "geo-blocks are never worked around."
- So no round has touched a prediction-market mechanism. The lab's only prediction-market rows are blocked at the access step.

## 1. Primary sources read (quotes come from WebFetch summaries; check the page before relying on wording)

- Polymarket liquidity rewards, https://docs.polymarket.com/market-makers/liquidity-rewards
  - "The pools below are configured reward caps."
  - "Rewards are distributed directly to maker addresses daily at midnight UTC."
  - "Quadratic scoring rule for an order based on position between the adjusted midpoint and the minimum qualifying spread"
  - "the order book is sampled once per minute at a random offset."
  - "The minimum reward payout is **$1**; amounts below this will not be paid."
- Polymarket fees, https://docs.polymarket.com/trading/fees
  - fee = C x feeRate x p x (1 - p), with rates 0.05, 0.01 and 0 by category; geopolitics is 0.
  - "Makers are never charged fees. Only takers pay fees."
  - No effective date on the page.
- Polymarket geoblock, https://docs.polymarket.com/developers/CLOB/geoblock
  - "Regulatory-Restricted Jurisdictions (Close-Only on Frontend and API)" includes FR.
  - "Users can close existing positions but cannot open new ones, on both the frontend and the API."
  - The page does not say whether reading public market data is restricted.
- Polymarket resolution, https://docs.polymarket.com/concepts/resolution
  - "Prediction markets use the UMA Optimistic Oracle for decentralized, permissionless resolution."
  - "After a proposal, there's a 2-hour challenge period where anyone can dispute the outcome."
  - Bond "typically $750 pUSD"; counter-bond "same amount as proposer".
- ANJ, France (primary, French): https://anj.fr/promotion-dune-offre-de-jeux-dargent-illegale-blocage-du-site-polymarket
  - "Le 16 juillet 2026, le président de l'Autorité nationale des jeux a ordonné"
  - "aux fournisseurs d'accès à Internet français de bloquer l'accès au site Polymarket"
  - "mais donnant en pratique lieu à des contournements" (the geoblock was circumvented in practice)
  - "au mois de juin dernier, 578 751 visites, et 205 057 visiteurs uniques"
  - "Quiconque fait la publicité d'une telle offre peut être puni d'une amende de 100 000 €."
- Kalshi fee rounding, https://docs.kalshi.com/getting_started/fee_rounding
  - "Net fee = trade fee + rounding fee - rebate"; "trade_fee = ceil_6dp(model_fee)"
  - The page does not state which markets pay fees.
- Kalshi fee schedule PDF (https://kalshi.com/docs/kalshi-fee-schedule.pdf) and fee-schedule page: HTTP 429, not read. The 0.07 coefficient in section 3 comes from secondary sites only.
- Kalshi member agreement PDF: the WebFetch result was binary; the "Restricted Jurisdiction" text was not read by me. The lab's card (research/intake/cards/SRC1103-028.md:21) quotes it as: "France is a \"Restricted Jurisdiction\"". Treat as lab-verified, not my check.
- Cardozo and Rivero-Wildemauwe, arXiv 2609.12878 (submitted 2026-09-11), https://arxiv.org/abs/2609.12878
  - "purchases below 10 cents lose 19.3 cents per dollar, while purchases at or above 90 cents earn 0.83 cents"
  - "surprisingly absent in Sports"; no fee treatment on the page.
- Gebele and Matthes, arXiv 2601.01706 (submitted 2026-01-05), https://arxiv.org/abs/2601.01706
  - "prices systematically violate the Law of One Price"
  - "arbitrage becomes capital-intensive or unenforceable"
  - "semantically equivalent markets exhibit persistent execution-aware price deviations of 2-4% on average"
- Young, OpenMarket, arXiv 2607.26245 (submitted 2026-07-28), https://arxiv.org/abs/2607.26245
  - "does not beat, and slightly underperforms, the probability already implied by Polymarket's own order book"

## 2. Public APIs tested once (run from this sandbox, not from France)

- Polymarket gamma: GET https://gamma-api.polymarket.com/markets?limit=100&offset=0&active=true&closed=false, HTTP 200, 552,324 bytes.
  - Fields seen: rewardsMinSize (200), rewardsMaxSpread (1.5), feesEnabled, takerBaseFee (1000), outcomePrices, liquidityNum, clobTokenIds.
  - Two pages (200 markets, ordering not known): 164 with reward fields, 196 with feesEnabled, median rewardsMaxSpread 4.5. 187 of 200 had Yes price below 0.10; 2 had Yes above 0.90. Not representative.
  - takerBaseFee = 1000 does not match the 0.05 or 0.01 rates on the fee page. Unreconciled.
- Kalshi: GET https://api.elections.kalshi.com/trade-api/v2/markets?limit=5&status=open. First call 429; second call (after 20 s) HTTP 200, 26,736 bytes. Fields seen: close_time (e.g. "2026-11-28T01:00:00Z"), can_close_early, custom_strike.
- Not tested: Polymarket CLOB book and prices-history endpoints. Not tested: any French-IP access. I did not try to get around any block.

## 3. Three candidate questions

### Q1. Polymarket maker rewards: is the subsidy larger than the adverse-selection cost?

- Hypothesis: a maker who quotes inside a market's max spread and above its min size earns reward share above its markout cost (the mid move after its fills).
- Opposite: rewards are split among many quoters and wiped out by markouts and inventory, so net is at or below zero.
- Payer and rule: the venue's reward pool. "The pools below are configured reward caps." Reward share uses a quadratic score, sampled once a minute, paid daily. The pool is fixed, so more quoters dilute it. The payer is the subsidy, not a trader.
- Why not known: M058 (registry/methods.csv:59) covers market making with no venue reward rule. No row names Polymarket rewards. M292 (line 264) covers fee tiers on MEXC, Binance and Hyperliquid, not prediction markets.
- Data: reward parameters held via the gamma endpoint (tested). Book and fill data: CLOB public endpoints (not tested).
- Cheapest decisive observation: 7 days of per-minute book snapshots on 20 reward markets, with mid moves after each simulated fill. Hours of code, about 0 EUR. The docs' per-minute sampling makes this a direct replay.
- Kill result: average reward per share minus average 60-second markout is at or below zero across the 20 markets.
- Value if true for a French owner with about 10k EUR: about zero. The FR geoblock is close-only, and quoting opens positions. Only a legal jurisdiction would make this usable.
- Probability it is true: 25%. A fixed pool with a quadratic score is crowded by fast quoters, and the markout is unmeasured.

### Q2. Same event, two venues: does a persistent cross-venue gap survive matched resolution wording and fees?

- Hypothesis: after matching resolution wording, the cross-venue gap for the same question stays above fees and capital cost by at least 1 point for a meaningful share of matched pairs.
- Opposite: the 2-4% gap in the paper comes from different resolution wording. With wording matched, it falls to fee size.
- Payer and rule: capital (each venue needs its own collateral) and resolution semantics. "arbitrage becomes capital-intensive or unenforceable" (arXiv 2601.01706). Kalshi's CPI contracts settle on the BLS first value, per a secondary summary; I did not read the contract PDF.
- Why not known: M098 (registry/methods.csv:99) is about prices as signals, not same-event spreads. R275 (registry/rounds.csv:94) is cross-venue funding on perps, a different payer.
- Data: Kalshi market list (tested, close_time) and Polymarket gamma (tested, outcomePrices, clobTokenIds). Pair matching needs titles and rules text, both available from the same APIs.
- Cheapest decisive observation: hand-match about 30 events where both venues list the same question; log both quotes hourly for 7 days. About one day of work, about 0 EUR.
- Kill result: after matching rules and charging both fee schedules, the net edge is at or below zero for at least 90% of matched pairs.
- Value if true for a French owner with about 10k EUR: zero in practice. Polymarket is close-only for FR. The lab card reports Kalshi as a restricted jurisdiction for France; I did not verify that from the PDF. Read-only research on public data is allowed, but the ANJ block means access from France may be blocked, and I did not test that.
- Probability it is true: 35%. One paper reports 2-4%. Practitioner pages say gaps shrink to near zero after fees; the MarketMaster figure (+1.6% raw, -0.06% after fees) is a vendor page, low quality.

### Q3. Per-order rounding and the longshot tail: does fee drag erase the 19.3 cent bias for small tickets?

- Hypothesis: small tickets pay a fee that is large relative to their price, so buying a longshot in one or two contracts is worse than the average bias, and buying No on a 90c+ favourite in small size is where a fee-aware edge could sit.
- Opposite: fees are small at the tails, so the bias survives fees at any ticket size.
- Payer and rule: small-ticket takers. Kalshi: "trade_fee = ceil_6dp(model_fee)" and "Net fee = trade fee + rounding fee - rebate" (docs.kalshi.com fee rounding). Polymarket: "fee = C x feeRate x p x (1 - p)", "Only takers pay fees." The p(1-p) shape makes fees small at the tails and large near 50c.
- Computed here (code run, Polymarket formula, 5 dp; Kalshi at 0.07 coefficient, ceiling to the cent, secondary-source coefficient):
  - Polymarket rate 0.05: per 100 shares, 0.2375 USD at p 0.05; 1.25 USD at p 0.50. Per share at p 0.05: 0.24 c, which is 4.75% of price.
  - Kalshi, 1 contract at p 0.05: 1 c, which is 20% of price. 10 contracts: 4 c. 100 contracts: 34 c.
  - The arXiv bias is 19.3 cents lost per dollar below 10c, so single-contract tail buys sit near the same size as the bias. This is arithmetic, not a test.
- Why not known: M291 (registry/methods.csv:263) names the longshot and No bias and says fees matter, but no row computes the rounding effect at ticket size. M292 covers fee tiers on other venues only.
- Data: fee formulas (docs, tested by reading). Price histories: the arXiv dataset is not in the repo; Polymarket prices-history endpoint not tested.
- Cheapest decisive observation: the table above, done. Then the net bias by ticket size (1, 10, 100 contracts) from the arXiv data if its authors release it, or from public price histories if the endpoint works.
- Kill result: for 10-contract tickets and up, the net bias after fees and rounding is at or below zero on the sell side (No at 90c and above).
- Value if true for a French owner with about 10k EUR: a cost lesson only. Avoid one-contract tail buys. Trading is not open to the owner from France (close-only on Polymarket).
- Probability it is true: 30% for a net sign change, high (about 90%) that the rounding arithmetic is right as stated. M291 overlaps this; the new piece is the ticket-size effect.

## 4. Access for a French resident (honest answer)

- Polymarket: the ANJ ordered French ISPs to block access on 2026-07-16 (primary, section 1). The geoblock page lists FR as close-only (primary). Opening new positions from France is not available. Closing is.
- Kalshi: the lab's card reports France as a restricted jurisdiction (SRC1103-028, line 21). I could not read the PDF, so this is unverified by me.
- Conclusion: no candidate can be traded by the owner from France. Read-only research on public data is allowed, but I did not test French access, and I have not tried to get around any block.

## 5. Caveats

- Quotes from WebFetch summaries. I did not check them byte-for-byte; the URLs are the places to check.
- Kalshi fee coefficient 0.07 is from secondary sites. The Kalshi fee PDF returned 429.
- Polymarket takerBaseFee = 1000 is unexplained.
- The gamma sample is 200 markets with unknown ordering; the 187-of-200 low-price share does not describe the market.
- Nothing was traded, and no account or credential was used.
