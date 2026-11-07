# R325 root Market/Enum extraction

Six static GETs total184953response-body bytes: root4pages116426bytes plus
independent reader2pages68527bytes. All200, no redirect/retry/login or market API
call. Root exact received links came from prior WS navigation and new Market
index. Read all four main article contents: Market index, Enum Values, Exchange
Information and Order Book. Navigation/scripts/style/linked pages remain unread.
URLs, Last-Modified2026-10-09, response hashes and actual UTC/bytes are retained;
this is not a whole API corpus or deployment version. No source GET remains in
this finite intake. Small full HTML bodies stay in ignored source cache only.

Market index explicitly says these endpoints require no authentication. That
supports public exchangeInfo/depth access, not signed owner/account/order calls.
ExchangeInfo supports symbol or comma-separated symbols,weightIP25. Status is
String1online/2pause/3offline; isSpotTradingAllowed is an API flag, tradeSideType
1all/2buy/3sell/4close. Quote/base asset identity is supplied separately. These
advertised fields do not certify the owner's permission or future session.

baseSizePrecision is documented MIN order quantity; quoteAmountPrecisionMarket
MIN MARKET order amount; maxQuoteAmountMarket MAX MARKET amount. Their names do
not establish an increment. baseAssetPrecision is precision, not evidence that
all decimal-grid quantities/ticks are executable. R325 uses that grid only as a
named conditional sizing convention alongside the established perpetual grid.
Actual spot increment/rounding and quantity asset remain unverified. Unknown
metadata/online/API/direction/market-order fields block numeric cost cells.

Public makerCommission/takerCommission fields are scenario inputs. They prove
neither owner's tier, fee asset, promotion quota nor actual fill commission. A
zero-charge control must not turn into an actual-zero-fee assertion. All MARKET
and other enum entries were read; deposit/withdrawal statuses are contextual,
not trading methods or authorization to inspect any account.

The price-band prose uses buy<=lastPrice*(1+bidMultiplierUp) for named LIMIT/IOC/
FOK orders and sell>=lastPrice*(1-askMultiplierDown). It differs from common
Binance multiplier semantics; R325 does not transplant that formula into MARKET
orders or declare a source trade strategy.

REST depth has symbol/limit, default100/max5000,weightIP3, lastUpdateId and
[Price,Quantity] bids/asks. It defines NO source quote timestamp or quantity
asset. The sample's bid15 exceeds ask14; the parser rejects it rather than
copying the example as a valid executable book. New records retain separate
request/completed-body first-seen UTC+monotonic clocks. Local co-receipt does not
prove matching-engine age, fills or availability at report time.

The independent ws_source_review separately records shared-wrapper sendTime's
Java epoch-ms example, official protobuf repository link and aggregate bootstrap
scope/ambiguities. They do not certify303 partial snapshots or deployed clocks.
No old R324 fact/file/result is rewritten. Current source knowledge narrows some
earlier unread scope; it does not retroactively certify R324 execution.

Perpetual REST/metadata units reuse frozen R312 sources and lab/mexc_depth.py:
[price,contract_quantity,order_count], qty*contractSize converts base. The source
prose's order/count contradiction stays documented in experiments/mexc_costs/
REVIEW.md. No same-name spot field inherits perpetual contracts or Lighter units.

Eleven distinct input/access/model mechanics are enumerated in sources.json,
with six existing M047/M134 aliases. No new M-id/alias/strategy was created.
M047 premium trigger/72h exit and M134 trailing72h20%APR rule are not backtested
here. Dated-futures M244 and M170/R301 remain distinct. Actual fee/session/funding
cash, source clock/lot proof and a new prospective protocol remain necessary.
