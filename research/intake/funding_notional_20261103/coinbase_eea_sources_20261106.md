# Coinbase Europe: public inputs for the next carry question

Codex, source qualification **2026-11-06..07 UTC**. Primary sources and actual unauthenticated probes;
**no economic statistic** calculated from these new Coinbase observations.
Canonical M488; proposed raw collection R419. This extends the reachable EEA
universe after [R418](../../../experiments/kraken_carry_v1/FINDINGS.md) failed
its capital hurdle. It does not substitute Coinbase International for Europe.

## The European intermediary and exchange are now linked by primary documents

Coinbase, [European launch](https://www.coinbase.com/en-sg/blog/futures-contracts-europe),
Daniel Seifert and Vinayak Doraiswamy, **2026-03-09**, explicitly lists France.
That is a service announcement, not the owner's account/appropriateness result.
The launch's five-year wording must also be read against newer product documents.

Coinbase Financial Services Europe Ltd (CBFSE),
[Trade and Order Execution Policy](https://www.coinbase.com/legal/cbfse_tradeandexecutionorder),
updated **2026-09-11**, states agency execution rather than a principal position
against clients; licence **CySEC 374/19**, MiFID II. The
[Execution Venue Disclosure](https://assets.ctfassets.net/o10es7wu5gm1/4XySMfsAChUWmbqSvMjym6/9b08b70f8f5722ddafa689051cd432b5/Execution_Venue_Disclosure_-_Coinbase_Financial_Services_Europe_Ltd.pdf),
updated **2026-06-17**, identifies the exchange/broker for futures exactly:

The named exchange is Coinbase Derivatives, LLC (CDE), a CFTC-regulated
Designated Contract Market; the executing intermediary is Coinbase Financial
Markets, Inc. (CFM), a CFTC-regulated Futures Commission Merchant.

This is the reason CDE market data is relevant to this EEA research route.
It does not establish that every listed CDE product is enabled for a particular
French client. No account, KYC, credentials or personalized legal determination.

## The published European fee schedule was found in the public page accordion

CBFSE's [landing page](https://www.coinbase.com/cbfse) links the primary
[Fees and Charges v1.4](https://assets.ctfassets.net/o10es7wu5gm1/3fVuEIOKaXOxfN2P31zfwM/349ad352b7f35706bdd25d07b9f0cb1d/Coinbase_Financial_Services_Europe_Ltd_Fees_and_Charges_v1.4-1__1_.pdf),
updated **2026-09-30**. Exact relevant statements:

Fees apply to each contract on each entry/exit side. Relevant tariff extracts:

> Regular: “(0.02%) of Notional Value + $0.12 per contract”
>
> Liquidation: “(0.10%) of Notional Value + $0.12 per contract”

The fixed component is **$0.10 exchange + $0.02 clearing per contract** in this
schedule. Do not omit it, treat a base unit as one contract, use a claimed free
maker fill, or silently add the regular charge on top of the published total
liquidation tariff. The owner-specific preview/any future changes remain to be
verified before execution. The document calls these regular trades, not a
separate advertised maker/taker ladder.

The similarly named [Coinbase app derivatives fees](https://help.coinbase.com/en/coinbase/derivatives/derivatives-fees)
is explicitly **Bermuda**, excludes Advanced, and is **not** this fee source.
U.S. fee/assessment assumptions are not silently substituted either.

## Current contracts: names are not reliable expiry fields

The [EU KID directory](https://www.coinbase.com/cbfse/kids) separates fixed
maturity, perpetual-style and perpetual products. Its English
[Cryptoasset Futures — Perpetual KID](https://assets.ctfassets.net/o10es7wu5gm1/BZARqSOZbawtsh26Vd3Xw/2c697d5de66911be22c29bd7d73a6e62/en-crypto-futures-perpetual_.pdf),
revised **2026-08-24**, says:

> “The Product is a perpetual future, which means it has no expiration date except as may be set out in the SID”

It identifies CDE, CBFSE, USD pricing/settlement and a Friday **17:00–18:00 ET**
maintenance window. Its embedded link was followed to the public
[Specific Information Documents](https://www.coinbase.com/cbfse/sids/en-crypto-futures-perpetual),
dated **2026-08-24**: BTC on page **2**, ETH on page **20** explicitly identify
exchange codes **BIP / ETP**, sizes **0.01 BTC / 0.1 ETH**, and a **30 December
2089 reference maturity**, with cash settlement under exchange rules if held
until that date. These source details are now qualified; the owner's account
entitlement remains unverified. The generic KID's no-expiry description must
be read with this specific long reference maturity, rather than treated as an
unconditional infinite-term contract.

The successful public responses identify:

| Public Advanced id | Venue | Native contract size | Raw expiry field | Raw class / funding interval |
|---|---|---:|---|---|
| BIP-20DEC30-CDE | cde / FCM | 0.01 BTC | 2089-12-30T16:00:00Z | EXPIRING / 3600s |
| ETP-20DEC30-CDE | cde / FCM | 0.1 ETH | 2089-12-30T16:00:00Z | EXPIRING / 3600s |

Both public `base_increment` values are **1**. These are captured identity/rule
facts, not a claim about actual fills. **Do not parse 2030 out of the id or
infer absence of funding from EXPIRING.** The current raw 2089 field agrees
with the dated SID's reference maturity. Preserve both fields and their source
dates and require product-specific interpretation in
any subsequent score. Empty `region_enabled` is not permission to trade.

## What really responds, and what does not

API probes below accessed **2026-11-06** with ordinary urllib, no custom User-Agent,
authentication, redirects on APIs, account or order. Raw successful bodies and
per-request UTC/hash receipts are in
[`coinbase_eea_20261106/`](coinbase_eea_20261106/).

- [List Public Products documentation](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/public/list-public-products), undated: actual `GET /api/v3/brokerage/market/products?product_type=FUTURE&limit=50` returned **200**, **50** product objects. This is one current, volume-ordered page, not a point-in-time or exhaustive universe.
- [Get Public Product](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/public/get-public-product), undated: ordinary individual BIP/ETP metadata GETs each returned **200**. Raw current `funding_rate`/`funding_time`, margin and session fields are present; rate values/distributions were not inspected or annualized.
- [Get Public Product Book](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/public/get-public-product-book), undated: BIP/ETP GETs each returned **200**, **100 bid + 100 ask rows**. Full response captured; no depth sweep/PnL. Native quantity units remain raw in the collector.
- [Kraken Get ticker by symbol](https://docs.kraken.com/api-reference/market-data/get-ticker-by-symbol), undated: named PF_XBTUSD/PF_ETHUSD GETs each returned **200** and echo their symbol. Absolute/relative current/predicted rate fields remain distinct. Kraken's public books and EEA margin metadata were independently captured in R418.
- Coinbase's [primary CDE OpenAPI](https://docs.cdp.coinbase.com/api-reference/derivatives-api/rest-api/cde-spec.json), undated, declares server `https://api.exchange.fairx.net` and `security: []` on **POST /rest/instruments** (read-only metadata) and **GET /rest/funding-rate**. The latter accepts `symbol` and `trading_session_date` and includes rate, future/spot/fair-value price and event-time fields in its documented response. See the saved functional schema extract and full-document hash.
- **Observed contradiction:** one ordinary filtered metadata POST returned **401**. After checking the distinct history resource's explicit public declaration, one unauthenticated GET for documented example `BIPZ30`, session **2026-11-05**, also returned **401**. Neither denied resource was retried or authenticated; no alternate host. History is documented but unavailable unauthenticated here, not proved absent globally. The future collector excludes this host completely.

The [NautilusTrader adapter documentation](https://nautilustrader.io/docs/latest/integrations/coinbase/)
(secondary, undated, partial read) says historical funding requests are not
implemented. That is an adapter limitation, not evidence the exchange has no
history; the primary OpenAPI above is more precise. Its live REST polling
description is also not a settlement/units certificate.

## CDE funding arithmetic needs verification even against official examples

Coinbase Help's [funding mechanism](https://help.coinbase.com/en/derivatives/perpetual-style-futures/funding-rate)
(undated, accessed **2026-11-07**, full relevant mechanics) describes hourly
rates, a 20-point three-minute premium average divided by 24, and 75% current /
25% previous-rate smoothing. No rate is published for an entirely closed hour.
Clearing aggregates hourly funding at midday/end-day; FCM posting can be once
or twice daily. Its example uses one 0.01-BTC contract at $100,000 and **0.1%**,
producing **$1**, consistent arithmetic.

The separate official [examples](https://help.coinbase.com/en/derivatives/perpetual-style-futures/examples)
page (undated, accessed **2026-11-07**, full relevant examples) instead says
“A funding debit of $1.00” for the same contract/mark and **0.010%**. Direct
arithmetic gives `1 * 0.01 * 100000 * (0.010 / 100) = $0.10`, a **10x**
inconsistency. Its quoted **$100** trading gain also conflicts with the stated
`($101000-$100000)*0.01 = $10`. These are documentation contradictions, not
observed trading losses or gains. Do not calibrate public REST units from them.

Coinbase [Prime posting](https://help.coinbase.com/en/prime/derivatives/funding-payments-for-us-perpetual-style-futures)
(undated, accessed **2026-11-07**, partial relevant clauses) posts net cash at
**17:00 ET**; [clearing guidance](https://help.coinbase.com/en/derivatives/perpetual-style-futures/margin-and-clearing)
(undated, same access, partial) describes two clearing cycles. Different
client posting need not contradict clearing. Neither establishes CFSE's exact
client ledger timing or the scale/fixing of Advanced REST `funding_rate`.
The source-reader receipt records the read scope; a separate ordinary urllib
request for the funding page returned403 and was not retried or bypassed.
Keep accrual and spendable cash separate; future models must reconcile units
with authoritative exchange rules and independent settled data, without an
account or credentials in this work.

## Why the next implementation is raw collection, not a backtest

The new [R419 protocol](../../../experiments/eea_pair_capture_v1/PREREG.md)
and inactive `scripts/record_eea_pair.py` preserve Coinbase and Kraken BTC/ETH
books, public rate/mark metadata and daily EEA risk metadata in the same
timestamped packet. This supports a later **two-perp** carry question without
R418's expensive spot purchase. It does not establish that the spread is large
enough, persistent or executable.

The collector never computes a funding APR, settlement payment, fee/PnL or
signal. The documentation arithmetic contradictions above remain unresolved. Raw
Coinbase rate scale/fixing identity, actual cash-credit timing,
effective maintenance rules and product-specific account access still require
qualification before a new economic protocol. Current/public is not settled;
an hourly observation is not proof of the whole hour's cashflow. Unknowns stay
unknown. Collection is inactive here and is not wired into Claude's loop. Four delayed
book reobservations after a fixed three-second wait preserve the possibility
of disappearing depth; receipt clocks give actual per-book delays. No intent,
order-uid persistence, fill or alpha is inferred from L2 differences.

Read status: fees PDF **full (2 pages)**; venue disclosure **full (1 page)**;
KID, policy, launch and developer pages **partial (relevant clauses/schema)**;
SID **partial (index, BTC page 2 and ETH page 20; other products not extracted)**;
CDE spec **partial (two public operations and response/request schemas)**;
raw successful responses **full capture, schema/count/identity inspection only**.
The landing page was read for links; its full HTML remains a local diagnostic
copy, with a committed receipt/hash rather than a duplicated website.

The original historical budget is not reset: older reported use **7,757 calls /
229.85 MiB**, exact older bytes unavailable. Qualification receipts are incremental;
the prospective collector has separate small hard stops and cannot fetch history.
No forward data or fresh alpha evidence exists merely because its code is ready.
