# Venue access from France, 2026-11-10

The owner asked (2026-11-10) that nothing be left for him to check. R439's and R440's FINDINGS said: "whether the
owner can hold positions on all five venues from France was not checked." This file checks it.

**How it was done.**
- One read-only Haiku agent searched the web.
- I then re-read the decisive pages myself: the venues' own terms, the AMF white list and the ESMA statement.
- Pages were read on 2026-11-10 through a fetch tool, which summarises. KuCoin's terms were also downloaded and
  matched word for word. Gate's and MEXC's pages refuse plain downloads (HTTP 403), so their wording comes from the
  fetch tool only.
- **This is not legal advice.** It records what each venue and regulator says about itself. Status: evidence, not a
  result. No frozen file was edited.

## Answer
**None of the four centralised venues in the carry books serves a French resident with perpetual futures.** Every
forward carry lane has at least one leg on one of them:

| Lane | Books' venues |
|---|---|
| R278 | gate+hyperliquid, binance+mexc, gate+mexc |
| R279 | KuCoin books |
| R294 | mexc+lighter |
| R390 | binance+gate |
| R440 | binance, gate, hyperliquid, mexc, kucoin |

The forward lanes still measure whether the edge exists. They do not measure a book the owner can hold from France.

## By venue
| Venue | France, by its own terms or notices | Regulator record | Read |
|---|---|---|---|
| **MEXC** | **Excluded.** Terms (last updated 13 Oct 2026), "Prohibited Jurisdiction" clause 1: no services and no registrations in France, its outermost regions included. | Not on the AMF white list. | Fetch tool, quoted |
| **KuCoin** | **Excluded.** Global terms (last updated 29 Oct 2026), Article 17(5): France is a "Restricted Location". | KuCoin EU Exchange GmbH holds a MiCA licence (Austrian FMA), passported to France from 27 Nov 2025 (AMF page dated 4 Dec 2025). It lists custody, exchange, placing and transfer, but no derivatives. | **Downloaded and matched** |
| **Gate** | **Excluded on the global platform.** User agreement, clause 2.5: France is a Restricted Location (also Germany, Spain, the Netherlands, Austria and Malta). | Gate Technology Limited holds a MiCA licence (Malta MFSA), passported to France from 30 Sep 2025 (AMF white list page dated 28 May 2026). It lists custody, trading platform, exchange, order execution and transfer, but no derivatives. | Fetch tool, paraphrased (no date found on the agreement) |
| **Binance** | **Stopped serving France on 1 Jul 2026.** Binance had no MiCA licence. Reports say French users lost spot, margin and futures and kept withdrawals only. | Not on the ESMA interim register as of an August 2026 report. A French application is reported; no decision found. | Secondary only (Cointelegraph, The Block, several others); Binance's own notice not read |
| **Hyperliquid** | **Not excluded, as reported.** Secondary sources say the terms restrict the US, Ontario and sanctioned regions. | No authorisation anywhere. | Primary terms **not read**: hyperliquid.xyz returns 403, and the docs URL tried returns 404 |
| **Lighter** | **Not excluded.** Terms (last updated 29 Dec 2025) restrict the US, Canada, the UK, China, North Korea, Russia, Ukraine, Cuba, Iran, Venezuela, Sudan, Belarus, Myanmar and Syria. France and the EU are not named. | No authorisation anywhere. | Fetch tool, quoted |

## EU rules that apply to all of them
- **France:** the MiCA transition ended on 1-2 July 2026 (AMF notices of 5 Feb and 6 Jul 2026). Unauthorised crypto
  providers must stop serving French clients. The AMF's crypto blacklist (latest 8 Oct 2026) names none of the six
  venues, but the list is not exhaustive.
- **ESMA, 24 Feb 2026 (ESMA35-243228190-8024):** derivatives sold as perpetual futures are likely CFDs when they meet
  the CFD definition. Retail CFD rules then apply: leverage caps, a risk warning, margin close-out and negative-balance
  protection. Trading on a venue or having a funding mechanism does not change that. The duty falls on the firm
  offering the product.
- **DEX use by a French resident:** a Paris law firm (Kohen Avocats, 7 Nov 2026) wrote that no text names Hyperliquid
  in France, but it is authorised nowhere. Using the interface does not make the user an offender. The user gets no
  investor compensation, no regulated leverage control and no custodian.
  - This is one firm's opinion, not a ruling.

## What it means for the program
1. **The confirmed carry edge sits on venues the owner cannot use from France.** R275, R437 and R439 earn +10 to
   +18%/yr on seen rows only because they include Binance, Gate, MEXC or KuCoin legs.
2. **The DEX-only book does not beat cash on seen rows.** These are the only venues found not to exclude France.
   - R288 hyperliquid+lighter: +3.53%/yr at 1x (NW t 7.34) against the 4.13% T-bill.
   - R288 dydx+lighter: +2.65%/yr, t 1.11.
   - dYdX's terms were not checked.
3. **The regulated EEA routes are already in the queue:**
   - M484/R430 OKX Europe X-Perps: NULL on BTC/ETH.
   - M487/R418 Kraken EEA: does not clear its frozen screen.
   - M488 Coinbase CDE against Kraken: execution capture only.
   - M490 cross-sectional alt X-Perp carry on OKX Europe: UNTESTED, the open lead.
   - OKX's own X-Perps guide says they are open to all 30 EEA countries, so France is included. Availability still
     "may vary" by residence and account, and the regulator records were not reached. See "OKX Europe X-Perps,
     checked later the same day" below.
4. **Paper lanes keep running.** They are the only way to learn whether the edge holds live. But a PASS on R278,
   R279, R294, R390 or R440 would not, by itself, give the owner a book he can hold from France. `lab.gate.go_real()`
   and the owner's own legal check decide any real use.

## OKX Europe X-Perps, checked later the same day
**How it was done.**
- One read-only Haiku agent searched the web.
- I re-read OKX's X-Perps guide myself through the fetch tool, which summarises:
  https://www.okx.com/en-eu/learn/what-are-x-perps-guide-for-european-traders (published 15 Apr 2026, modified
  29 Oct 2026, from the page's metadata).

**OKX's own guide says, quoted:**
- "X-Perps are available to eligible traders in the EEA, which includes all 30 European Economic Area countries."
  France is one of the 30. The page names no country, included or excluded.
- Requirements: "Be 18+ and reside in one of the supported EEA countries". The user also needs a verified account
  with KYC and must pass "a mandatory appropriateness test".
- "Both retail and professional clients can trade X-Perps."
- Caveats: "Availability may vary depending on your country of residence and account status." and "Certain services
  and features may not be available in your jurisdiction."
- "On X-Perps, you can trade with up to 10x leverage." "On X-Perps, the funding rate is settled every 8 hours."
- Seller: "OKX Europe Markets Ltd ("OEM"), which is authorised and regulated by the Malta Financial Services
  Authority", "Investment Services Licence Holder (Licence No. OEML-15905)."

**Not reached, so not verified:**
- OKX Europe's terms of service. The en-eu terms URL tried returns 404, so the restricted-country clause was not read.
- The MFSA register (HTTP 403).
- The ESMA MiFID register (captcha).
- REGAFI.
- So whether OEM's MiFID passport covers France is not confirmed from a register. It is only implied by the guide's
  "all 30" sentence.

**Read:** of every route checked, this is the only one where the seller's own page puts France in scope for perpetual
futures. R441 (crypto X-Perps hedged with OKX EEA spot) and R442 (stock X-Perps hedged with the stock at a broker)
test it on paper. Before any real use the owner still has to confirm in the app that his account can open X-Perps:
the appropriateness test and the account's country decide.

## What the France-reachable routes earned on paper (same day)
Each lane was frozen before its own statistic. Excess is over a 4% hurdle on the book's capital, at 1x costs.

| Lane | Book | Window | Excess, points | NW t | Verdict |
|---|---|---|---|---|---|
| R441 | OKX crypto X-Perp short, OKX EEA spot long | 83 days, seen | +1.37 | 0.62 | reported; forward to 2027 |
| R442 | OKX stock X-Perp short, stock long at a broker | 83 days | −4.50 | −4.65 | NULL (stop) |
| R443 | OKX X-Perps against Hyperliquid perps, by funding spread | 83 days, seen | −3.05 | −0.55 | reported; forward to 2027 |
| R444 | Hyperliquid spot long, Hyperliquid perp short | 679 days | −1.43 | −3.66 | NULL (stop) |
| R445 | R444 on HYPE and BTC only, fully deployed, spot backing the perp | 679 days, seen | +6.06 (2026: +0.15) | 3.67 | reported; forward to 2027 |

- **Read:** what is reachable from France earns about the T-bill, plus or minus a point or two.
  - The cross-venue spread (R443) is large before costs but flips within a week, so a two-venue round trip eats it.
  - The Hyperliquid-only carry (R444) is steady but leaves most of its slots in cash.
  - R445 removes the idle cash and assumes portfolio margin. Its +6 points come from 2025; in 2026 it earned about the
    hurdle. Its pairs were picked after R444, so only its forward read (2027-02-08, 2027-05-09) can decide.
  - R288's DEX-only cross-venue book (Hyperliquid against Lighter, both reachable) earned +3.53%/yr at 1x on seen
    rows, below the hurdle.
- The +10 to +18%/yr carry books stay on venues that exclude France (table above).

## Not checked
- Binance's own notice and restricted-country page.
- Hyperliquid's primary terms.
- ESMA's MiCA register CSVs.
- dYdX's terms.
- Whether any venue blocks French IP addresses in practice.
- Whether a non-French entity of the owner's could use these venues (a legal question for the owner's adviser).

## Sources (read 2026-11-10)
- MEXC terms: https://www.mexc.com/terms
- KuCoin terms of use: https://www.kucoin.com/legal/terms-of-use
- Gate user agreement: https://www.gate.com/user-agreement
- AMF white list, Gate Technology Limited: https://www.amf-france.org/en/warnings/white-lists/daspcasp/gate-technology-limited
- AMF white list, KuCoin EU Exchange GmbH: https://www.amf-france.org/en/warnings/white-lists/casp/kucoin-eu-exchange-gmbh
- Lighter terms: https://lighter.xyz/terms
- AMF, 5 Feb 2026: https://www.amf-france.org/en/news-publications/news/amf-reminds-digital-asset-service-providers-transitional-period-allowing-them-continue-providing
- AMF, 6 Jul 2026: https://www.amf-france.org/en/news-publications/news-releases/crypto-assets-end-pacte-law-and-european-mica-regulation-transitional-period-establishes-new-role
- ESMA statement, 24 Feb 2026: https://www.esma.europa.eu/sites/default/files/2026-02/ESMA35-243228190-8024_-_Public_statement_on_derivatives_in_scope_of_the_CFD_product_intervention_measures.pdf
- Binance and France (secondary): https://cointelegraph.com/news/binance-eu-service-limits-july-1-mica-effect and https://theblock.co/post/406766
- Kohen Avocats, 7 Nov 2026: https://kohenavocats.fr/?p=2163381
