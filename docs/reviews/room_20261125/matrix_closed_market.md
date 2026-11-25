# Rules matrix, column: closed-market pricing of stock / ETF / index / commodity perps

- Question: how does each venue mark, index, fund and bound a stock (or other closed-market) perp while the cash market is closed (nights, weekends, holidays)?
- Reader: room 2026-11-25. Reader's own work, from local copies first, then primary web pages.
- Date read: 2026-11-25 (all rows unless a row says otherwise).
- Conventions: `[local]` = file:line in the scratchpad copy named; `[web]` = URL fetched with curl on 2026-11-25; `[search]` = search-engine summary only, not confirmed on the primary page; `Inference:` marks my reading. "unknown" = not found in the sources I could reach.
- Snapshot dates of local copies: trade.xyz llms-full 2026-11-24 22:33; Lighter 2026-11-25 00:29; Hyperliquid 2026-11-25 04:25; venue docs 2026-11-25 08:25; `perpdexs.json` (HIP-3 config dump) 2026-11-20.

Local path shorthand: `S` = `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad`.

---

## Matrix

### 1. trade.xyz (`xyz`, HIP-3 dex on Hyperliquid), US stock perps (NVDA, AAPL, TSLA, MSFT, AMZN, META, GOOGL, indices SP500/XYZ100, commodities GOLD/SILVER/WTIOIL)

- **Venue / product:** trade[XYZ] HIP-3 deployment on HyperCore. US stocks, US-equity and commodity indices, commodities.
- **External source when open:** Relayer, "a robust set of venues, markets, and institutional data providers" [local: `S/xyzdocs/llms-full.txt:205-215`, Oracle Price > External Pricing]. US stock external session per spec table: `ext = 24/5, from Sunday 8:05 PM ET to Friday 8:00 PM ET` for NVDA, AAPL, TSLA, etc. (`S/xyzdocs/llms-full.txt`, Specification Index rows; parsed with `S/room_parse/xyz_spec.py`). Some names (URNM, DKNG, BIRD, BX, ZM, EBAY, BB, ICE, NCLD, SHAZ, BOT) are Mon 9:30 AM–Fri 4:00 PM ET only.
- **Closed-window oracle/mark rule (quoted):**
  - Oracle: "When external inputs are unavailable, the oracle advances via a continuous-time exponentially weighted moving average that incrementally adjusts the previous oracle price by a fraction of the impact price difference." [local: `xyzdocs/llms-full.txt:220-240`]. Time constant: "It uses a time constant `\tau = 30` minutes" [line 232]. The constant was cut from 8 h to 1 h on 2025-11-21 and to 30 min on 2026-04-30 [local: `xyzdocs/llms-full.txt` "Oracle Time Constant Updates", lines ~4629-4640].
  - Impact price: "the impact bid price ... and impact ask price ... average execution prices to trade a configured impact notional amount". Oracle step cap: "The oracle price may move at most ±50 bps from its current value" [line 260].
  - External price during closure: "When external markets are closed, the external price remains fixed at the external close price while the oracle advances via its internal pricing mechanism" [line 266].
  - Mark: median of three: (1) oracle; (2) oracle + 150-second EMA of (mid − oracle); (3) median of best bid, best ask, last trade (protocol). "The mark price component published by the Relayer may differ from the current mark price by at most the market's Mark Clamp" [lines 252-260].
  - Discovery bounds: "Discovery bounds restrict the mark price within ±(1/max leverage) of a reference price during both external and internal pricing sessions" [line 282]. During internal sessions "the reference price ... is initially based on the last externally derived oracle price (e.g., the Friday close...)" [discovery-bounds page, `xyzdocs` ~lines 290-300].
  - Re-anchoring ratchet: "When the oracle price approaches the edge of the current bound and reaches a configured trigger threshold ..., the reference price for the discovery bounds re-anchors to that bound" [discovery-bounds page]. Number of re-anchors per direction = "Discovery Bound Resets" column, NVDA 1, AAPL 1, TSLA 2, MSFT 2, AMZN 2, META 2, GOOGL 2, GOLD 2, SP500 1.
  - **Conflict inside the same docs:** the v2 changelog (2026-03-13) says the 1/max-leverage band is "enforced 24/7" around "the last externally derived oracle price" and that the ratchet text is "an archive of the v1 discovery bounds design" [`xyzdocs` "Discovery Bounds v2", ~line 4605-4625]. The mechanics page still presents the ratchet as current. Which applies today is unclear. Inference: for equities the band is fixed around the last external close, and resets may be inactive.
- **Specific parameters (spec index, parsed):** NVDA max lev 10x, bound ±10%, resets 1, mark clamp 1%; AAPL 20x, ±5%, resets 1, clamp 1%; TSLA 20x, ±5%, resets 2, clamp 1%; MSFT 20x, ±5%, resets 2, clamp 1%; SP500 50x, ±2%, resets 1, clamp 0.5%; GOLD 25x, ±4%, resets 2, clamp 0.5%; WTIOIL 20x, ±5%, resets 2, clamp 1%.
- **Funding and interest during closure:** funding multiplier 0.5 on every listed asset [spec index; `xyzdocs` ~line 370-385]. Interest input "HyperCore's standard `0.0001`, or 0.01% per eight hours, except `EUR`, `GBP`, `JPY`, and `KRW`, which use `0`" [line 373]. Premium: "P = (0.5 × (impact_bid_px + impact_ask_px) / oracle_px) − 1" [line ~362]. Hourly payment uses the oracle, not the mark: "The oracle price, not the mark price, converts position size to notional" [line ~390]. Funding cap: "Funding is capped by HyperCore at an absolute value of 4% per hour" [line 387].
  - **Conflict:** the Hyperliquid funding doc says "Funding on Hyperliquid is capped at 0.5%/hour" [`S/hldocs/llms-full.txt:1746`]. Clamp: trade.xyz gives the default as "0.0003" [line ~375], the Hyperliquid doc and xyz changelog give "clamp ... −0.0005, 0.0005" [`hldocs:1730`; `xyzdocs` changelog ~4659].
- **Price bounds during closure:** discovery bounds above; mark within the bound and within the Mark Clamp (1% stocks, 0.5% SP500/GOLD) per Relayer update; oracle ±50 bp per update. Liquidation "cannot be liquidated while those bounds are in effect" if the liquidation price lies outside the bound [discovery-bounds page / v2 changelog].
- **Reopen:** "When external pricing resumes, the reference price reverts to the live externally derived price and all reset counters return to zero" [discovery-bounds page]. "When external inputs resume, the oracle reverts to the externally derived price on the next tick" [line ~245]. Risk note: "A gap, reopening auction, corrected value, or material difference ... can produce rapid or sequential price movements" [local `xyzdocs` Liquidity/market-hours risk ~5175-5185].
- **Reachable from France/EEA:** unknown. No restriction list for trade[XYZ] found in the local copy. Not checked on the Hyperliquid terms page.
- **Date read:** 2026-11-25 (local copy 2026-11-24).

**Holiday rule (trade.xyz):** "Internal Pricing continues to follow applicable equity market holidays and trading hours" [`xyzdocs` "Equities - Internal Session Hours", changelog, 2026-08-13]. Internal session changed from "Friday 8:00 PM – Sunday 8:00 PM ET" to "Friday 8:00 PM – Sunday 8:05 PM ET". The futures holiday table [`xyzdocs` Holiday Closures, ~4260-4290] has partial opens (e.g. 2026-11-27 "Open 00:00–13:15") that I did not map onto the equity-session rule.

---

### 2. Hyperliquid core (HIP-3 host; not a stock market itself)

- **Product:** HyperCore perps. Stocks only through HIP-3 dexes (xyz, flx, vntl, km, cash, para, io).
- **Oracle (core):** "The spot oracle prices are computed by each validator as the weighted median of Binance, OKX, Bybit, Kraken, Kucoin, Gate IO, MEXC, and Hyperliquid spot mid prices ... weights 3, 2, 2, 1, 1, 1, 1, 1" [`hldocs/llms-full.txt:330`]. HIP-3 deployers supply their own oracle: "the deployer generally takes on the oracle" [search summary, Ventuals row].
- **Core mark:** "Mark price is the median of ... 2. The median of best bid, best ask, last trade on Hyperliquid 3. Median of Binance, OKX, Bybit, Gate IO, MEXC perp mid prices with weights 3, 2, 2, 1, 1" [`hldocs:1619-1627`]. This is for crypto; for HIP-3 the deployer's mark (above) applies.
- **Funding (core, for reference):** "Funding on Hyperliquid is capped at 0.5%/hour" [`hldocs:1746`]. Interest "predetermined at 0.01% every 8 hours" [`hldocs:~1712`].
- **Closed-window / reachable / date read:** not applicable at core level. Reachable unknown. Read 2026-11-25.

---

### 3. Lighter (RWA perps: equities, indices, commodities, FX)

- **Product:** RWA markets; 100+ equity and ETF markets (NVDA, TSLA, AAPL, GOOGL, MSFT, AMZN, META, SNDK, MU, EWY, INTC, IBM, AMD, MSTR, ORCL, PLTR, ...) [`lighterdocs/llms-full.txt` "Market Specifications" table, parsed].
- **External source when open:** Pyth Pro for most equities (the table's Oracle column), Chainlink/RedStone/Stork for others [same table]. "Oracle sources can change with market hours; use `priceOracleInfo` for the currently selected source and underlying" [line ~463].
- **Closed-window rule (quoted):**
  - "Outside the underlying's trading hours, external prices can become stale and pricing switches to the price derived from the order book" [`lighterdocs:415`]. Stale threshold: "The current mainnet stale threshold is typically 1 minute; it can vary by market" [internal pricing page, ~1338].
  - Internal index: "the internal EMA (τ = 30 minutes) is used directly, with no price cap" [Prelaunch/Pre-IPO section, `lighterdocs:1389`]. Index EMA is over impact prices: "The internal price is derived from order book impact prices, smoothed using a time-weighted Exponential Moving Average" [~1336-1350]. Spread filter: "Updates whose impact bid/ask spread exceeds the spread threshold ... are ignored ... 2% on Lighter" [~1340].
  - Internal mark component: τ = 2 min; for RWA markets with an oracle-relative cap: "Mark_internal ∈ [P_oracle · (1 − 1/L), P_oracle · (1 + 1/L)]" [`lighterdocs:1375-1377`].
  - Mark (fair-price): mark = median(Impact Price, price1, price2) for crypto; `price1 = index + EMA_8min(clamp(Impact − index, ±index/200))` [`lighterdocs` ~1280-1300]. For RWA, "the only change is that the `cexPrices` component is replaced with the pricing methodology defined below" [~1348].
  - **Cap removal (2026-07-10):** "Since July 10, 2026, the following RWA markets have no price caps based on the last oracle price: SPY, US500, QQQ, US100, XAU, XAG, NVDA, TSLA, AAPL, AMZN, MSFT, GOOGL, META, XCU, SNDK, WTI, XPD, XPT, BRENTOIL, MU, EWY, SPCX, DRAM, SOXL, SKHYNIXUSD, SAMSUNGUSD, INTC, NATGAS, IBM, AMD, MSTR" [`lighterdocs:1400-1406`]. Names not on this list (ORCL, PLTR, COIN, HOOD, CRCL, ASML, CRWV, ...) keep the oracle-relative cap ±1/L. "To prevent manipulation attacks, internal prices will continue to be validated against prices from other trading venues" [same].
  - Risk checks: "Other platforms: the price is compared against prices for the same asset on other trading platforms" [`lighterdocs` Risk Checks ~1310]. "These checks are discretionary" [same].
- **Funding during closure:** "Funding works as in standard perp markets, except that the FundingPremiumMultiplier is set to 1/100" applies to Pre-IPO/prelaunch [`lighterdocs:482`]. For RWA: "It is set to 1 for crypto markets, 1/2 for RWA markets, and 1/100 for Pre-IPO and Prelaunch markets" [`lighterdocs:1193`]. Interest is per market: "Per-market values are returned by `orderBookDetails` in `base_interest_rate`, `funding_clamp_small`, and `funding_clamp_big`" [`lighterdocs:1195`]. Big clamp: "limits funding payments to 4% per 8 hours, or 0.5% per hour" [`lighterdocs:1192`]. Interest rate value for equities: not read (live API field).
- **Price bounds during closure:** cap ±1/L around oracle for listed-cap names not in the 2026-07-10 removal list; no cap for names on that list (only the risk checks vs other venues). Premium cap ±0.5% of index in `price1` [`lighterdocs:~1300`].
- **Reopen:** "Leverage does not change outside trading hours ... However, price volatility may increase at market open" [`lighterdocs:411`]. "As soon as a fresh external price is available, pricing switches back to it" [~1338].
- **Reachable from France/EEA:** unknown. No restriction list in the local copy.
- **Date read:** 2026-11-25 (local copy 2026-11-25 00:29).

---

### 4. Paradex (TradFi perps: single-name equities, equity indices US500/US100, commodities)

- **Product:** TradFi perps. Single equities, indices, industrial metals and energy [web: `https://docs.paradex.trade/trading/tradfi-markets.md`, fetched 2026-11-25].
- **External source when open:** "Pyth (stocks and FX) score 3, Open hours; Stork score 2, Open hours; Binance 1; Bybit 1, 24/7; Hyperliquid 1, 24/7; OKX 1, 24/7; Lighter 0.7, 24/7" [web, Source scores table].
- **Closed-window rule (quoted):**
  - Market hours: "Equities (single stocks): Open 24/5, from Sunday 8:00 PM ET to Friday 8:00 PM ET" [web].
  - "Closing Price is equal to the oracle price at the market closing time." "Internal Price is the EMA of the Mark Price with a 1-hour half-life. At the start of the closing period, the Internal Price is initialized to the Closing Price." [web].
  - Closing-hours weights: "Hyperliquid 21.28%, OKX 21.28%, Bybit 21.28%, Lighter 14.89%, Closing Price 10.64%, Internal Price 10.64%" [web, Source weights, Closing hours].
  - "The price consumed from external exchanges (Binance, Bybit, Hyperliquid, OKX, Lighter) is the index price of the TradFi perpetual." [web].
  - Mark: no separate closed-window mark formula found on the TradFi page; I did not find the mark definition in the fetched text. Inference: the mark follows the standard Paradex mark, which is not in the local copy.
- **Funding and interest during closure:** Raw funding: "pull the Premium Rate toward the Baseline Interest Rate (0.01%) ... Scale by the Funding Multiplier (0.5x for TradFi, 1x for all other markets) and clamp by ±the Maximum Funding Rate" [`S/venuedocs/paradex_funding.md:13`, `:84`]. Max funding "0.5% (TradFi)" per 8h [`paradex_funding.md:99`]. Interest 0.01% (not zero).
- **Price bounds during closure:** not stated on the TradFi page. The index is a weighted median; no band quoted.
- **Reopen:** at open the weights switch back to "Pyth 31.9%, Stork 21.3%, Binance 10.6%, Bybit 10.6%, Hyperliquid 10.6%, OKX 10.6%, Lighter 7.4%" [web].
- **Reachable from France/EEA:** unknown.
- **Date read:** 2026-11-25 (web). Local `docs.paradex.trade.txt` is an index only.

---

### 5. Variational (Omni: TradFi perps, equities, ETFs, commodities, indices)

- **Product:** TradFi perps, 550+ markets across crypto and TradFi [`S/venuedocs/docs.variational.io.txt` ~line 387].
- **External source when open:** "The index price represents the real-time price of the underlying market, and is sourced from the Variational Oracle" [`docs.variational.io.txt:1027`]. Oracle: "a weighted combination of prices on different exchanges" [~line 281].
- **Closed-window rule (quoted):**
  - "The underlying market may have non 24/7 trading hours. During the off hours, the index is smoothed as follows:" [`docs.variational.io.txt:1089`].
  - "**Fixed Mode (Daily Maintenance, Holidays and Weekends)**: Fixed Mode is applied on Equity-based RWA Perps. No recalculation occurs, the Price Index remains fixed at the last available value." [lines 1094-1096].
  - "**Orderbook EWMA Mode** (Daily Maintenance, Holidays and Weekends): Orderbook EWMA Mode is active on Commodity-based RWA perps. Instead of using prices from vendors, index price uses Impact Mid Price derived from the orderbook" [lines 1097-1101]. The index is also smoothed by EWMA and "the movement of index price is limited within the orderbook EWMA mode" [line ~1102].
  - Mark: "derived from a combination of the underlying asset's spot price (Index Price) and additional data (e.g. funding rates, OLP's current risk profile)" [line 631]. No closed-window clamp on the mark quoted.
- **Funding during closure:** "the interest rate is set to 0%" and "clamp (interest rate − Average Premium Index (P), −0.0005, 0.0005)" [`docs.variational.io.txt:1105-1107`]. Dividend funding: a special payment on ex_date−1 with reduce_only from 18:00 ET [~1130-1150].
- **Price bounds during closure:** the index is frozen (equities). No band on the mark quoted.
- **Reopen:** not described on the page. Inference: a frozen equity index jumps to the vendor price on reopen in one step (no smoothing stated).
- **Reachable from France/EEA:** unknown.
- **Date read:** 2026-11-25 (local copy 2026-11-25 08:25).

---

### 6. edgeX (stock perps; V2 Starknet)

- **Product:** stock perpetuals, "linked to underlying equity assets" [`S/venuedocs/edgex-1.gitbook.io.txt:798-800`].
- **External source when open:** "Market Status: The system determines the current status as 'Market Open' or 'Market Closed' in real-time, based on the official trading schedule" [line ~805]. Oracle provider: "edgeX employs independent oracle providers" [line 69].
- **Closed-window rule (quoted):**
  - "Market Orders Rejected: The system will reject all Market Orders." [line 813]. "Limit Orders Only: ... the limit price must fall within the designated price range" [~814].
  - "Price range Calculation: Formula: Long price upper limit is Last Closing Index Price × (1 + 1 / Max Leverage of the pair); Short price lower limit is Last Closing Index Price × (1 − 1 / Max Leverage of the pair)." [line 821].
  - "Mark Price Adjustment: During market closure, the Mark Price is also restricted within the price range. Clamping Mechanism: The price change is limited to 0.5% every 3 seconds." [lines 824-827].
  - Conditional orders triggered while closed "must follow the same rules" (rejected if market, rejected if out of range) [line ~815].
  - "Price Deviation Risk: ... the contract price may temporarily deviate from the external spot price" [~830].
- **Funding during closure:** not read in the stock section. Unknown.
- **Price bounds:** ±1/L around last closing index (mark and limit orders); mark change ≤0.5% per 3 s.
- **Reopen:** not described beyond "status transitions" [~830].
- **Reachable from France/EEA:** unknown.
- **Date read:** 2026-11-25 (local copy 2026-11-25 08:25).

---

### 7. Extended (RWA perps: order-book RWA markets; RFQ RWA markets are a separate model)

- **Product:** order-book RWA perps (equities, ETFs, indices, commodities, FX) and RFQ RWA markets [`S/venuedocs/docs.extended.exchange.txt` "RWA Markets", ~673-680, ~1594-1632].
- **External source when open:** "For RWA perpetual markets, index and mark prices rely on: external oracle data during trading hours; off-hours pricing during non-trading hours" [`docs.extended.exchange.txt:676-681`]. Equities & ETFs: "Stork", regular/pre/post-market "NYSE/Nasdaq midpoint prices via licensed data providers; Overnight: Blue Ocean ATS" [oracle table, ~711].
- **Closed-window rule (quoted):**
  - "Off-hours Pricing: During off-trading hours, if the oracle has not been updated for more than 5 minutes, both the Index Price and Mark Price for RWA markets are derived from order book liquidity." [`docs.extended.exchange.txt:785-787`].
  - "Index_t = Index_{t-1} + (1 − β) · Adj_t", with Adj_t = max(Impact_Bid − Index, 0) − max(Index − Impact_Ask, 0), "β = exp(−Δt*/τ)", "Δt* = min(Δt, c·τ)", "τ = 30 min", "c = 0.1" [lines ~789-815]. "caps each step at ≤ 9.5% of Adj_t" [~815].
  - "**Maximum Deviation**: To limit off-hours price drift, the maximum deviation of the Index Price and Mark Price from the last known oracle price is capped at |Index_t − last_oracle_price| ≤ 1 / max_leverage." [line 831-833].
  - Trading hours: "order book RWA markets are available for trading 24/7, including weekends and public holidays, though spreads may be significantly wider" [~1600-1610]. "While a market is halted, order placement and execution are unavailable" applies to the Prime RFQ markets only.
- **Funding during closure (RWA):** "Funding Rate = (Average Premium + clamp(Interest Rate − Average Premium, 0.05%, −0.05%)) / 8" [`docs.extended.exchange.txt:568`]. "The Interest Rate component is set at 0.0035% per 8 hours (~3.83% annualised)" [line 572]. Premium index as impact-minus-index over index, computed every 5 s [~560].
- **Price bounds:** |Index − last oracle| ≤ 1/max leverage (index and mark) during off-hours.
- **Reopen:** oracle returns to Stork midpoint feeds. Not described beyond the availability table.
- **Reachable from France/EEA:** unknown for order-book RWA perps. The Extended spot terms list EEA countries, including France, as Restricted Persons [`docs.extended.exchange.txt:4111`]. That schedule is headed "RESTRICTED REGIONS (SPOT)", so it may not cover perps. Not confirmed.
- **Date read:** 2026-11-25 (local copy 2026-11-25 08:25).

---

### 8. Aster (stock perps: US, HK, KRX stocks; 24/7)

- **Product:** stock perps, USDT-settled, up to 50x [`S/venuedocs/docs.asterdex.com.txt:5927-5931`].
- **External source when open:** "Index prices are sourced from multiple providers including the Pyth Oracle" [`docs.asterdex.com.txt:5937-5940`].
- **Closed-window rule (quoted):**
  - Standard mark: median of Price 1 = index × (1 + funding × (time to next funding / interval)), Price 2 = index + 5-min MA of (mid − index), and the contract price [`docs.asterdex.com.txt:5943-5955`].
  - "**EWMA-Smoothed Mode.** During low-liquidity periods (overnight, weekends, and public holidays), Aster applies an Exponentially Weighted Moving Average (EWMA) to the last traded price, replacing the raw Contract Price with a smoothed version" [5957-5963]. "EWMA Price: (1 − β) · LastTrade(t) + β · EWMA price(t − 1), where β = exp(−1/1600)" [line 5965]. "If no trade is filled ... the previous contract filled price EWMA(t−1) is carried forward" [~5967]. Mark = median of the three, EWMA in place of contract price.
  - EWMA active: "Overnight 8:00 PM → 4:00 AM EST; Weekend 8:00 PM Fri → 4:00 AM Mon; Public holiday 00:00 → 23:59 EST; Half-day 13:00 EST after close" [`docs.asterdex.com.txt:5987-6035`].
  - Order caps (US stocks table, line ~5976-5985): limit orders "> 5% more aggressive than MarkPrice will be rejected" in pre-market, post-market and overnight; market orders "can fill up to 5% more aggressive than MarkPrice, the rest will be canceled".
  - Mark clamp: none quoted for stocks. Pre-market (Pre-launch) ±1% clamp is a different product [~5791].
- **Funding during closure:** not read. Unknown.
- **Price bounds:** order caps only (±5% vs mark on off-hours order types). No mark band quoted.
- **Reopen:** EWMA returns to standard mode in the market-open window (Inference from the table; the table lists EWMA only for off-hours).
- **Reachable from France/EEA:** France (FR) appears in the "Restricted Countries" table [`docs.asterdex.com.txt:7460-7475`]. The page's intro refers to "prediction market trading" and says some countries are blocked "only on the Aster frontend". Scope for perps unclear. Read as: restricted per the table, not confirmed for perps.
- **Date read:** 2026-11-25 (local copy 2026-11-25 08:25).

---

### 9. OKX (Stock Perpetuals and TradFi X-Perps)

- **Product:** Stock perpetuals (USDT-margined) and TradFi X-Perps (expiry-dated, EEA page) [web: `https://www.okx.com/help/stock-perpetuals`; `https://www.okx.com/help/tradfi-x-perps-eea`; fetched 2026-11-25].
- **External source when open:** "Index Price from other exchanges (Hyperliquid, Binance)" plus stock feeds; "During regular market hours, the index draws from all sources, with stock price feeds carrying significant weight" [stock-perpetuals page].
- **Closed-window rule (quoted):**
  - "During off-hours, weekends, and holidays, the index relies more on OKX's own contract price and stock perps index price on other exchanges" [stock-perpetuals].
  - Index bands: "The index price is limited within a 10% range of the stock price, where the stock price is provided by data vendors such as Pyth. During off-hours, weekends and market holidays, stock prices stop updating, but the last available stock price is still used for index bands calculation" [stock-perpetuals]. "The 10% index bands may be adjusted in real time according to market conditions" [same].
  - X-Perps: "OKX retains the last available TradFi price and constrains the live Index Price to within ±10% of that reference price" [X-Perps page, web].
  - Mark: "Mark Price = Index Price + Basis Moving Average; Basis Moving Average = Moving Average of (Mid Price − Index Price)" [stock-perpetuals].
- **Funding during closure:** "The Interest Rate (I) used in the funding rate calculation is set to 0%. You are only charged funding if you hold a position at settlement time." [stock-perpetuals]. Settlement intervals per contract.
- **Price bounds:** index ±10% of last stock price; mark = index + basis MA (no separate clamp quoted).
- **Reopen:** not described beyond "gap risk can occur when the underlying market reopens" [X-Perps page].
- **Reachable from France/EEA:** probably yes, not confirmed country by country. The EEA page is for OKX Europe Markets Ltd (Malta, MFSA), and its disclaimer says "Access to TradFi X-Perps may be restricted or prohibited in certain jurisdictions, including (but not limited to) the United States" [web, `tradfi-x-perps-eea`]. No French exclusion found.
- **Date read:** 2026-11-25 (web). Note: the search summary said some OKX pages state margin in USD/USDC/USDG and others USDT; the fetched pages say USDT-margined for stock perps and USD-margined for TradFi X-Perps. Not a closed-window issue.

---

### 10. Bybit (TradFi perpetual contracts, USDT perps; stocks and commodities)

- **Product:** TradFi perps (stock perps and commodities) [web: V5 docs].
- **External source when open:** "components can include price feeds, exchange indices, and futures prices" [web: `https://bybit-exchange.github.io/docs/v5/tradfi-integration`, fetched 2026-11-25].
- **Closed-window rule (quoted):**
  - "Market closed: components that stop updating, such as certain equity or commodity feeds from Pyth, may be temporarily excluded to reduce the effect of stale prices." [V5 docs, line ~215].
  - "Session transitions: a smoothing mechanism helps maintain index price continuity." [V5 docs].
  - "Bybit reserves the right, at its sole discretion, to determine what constitutes the 'opening period' and the 'market closed period'" [search summary of the Bybit help center; help center returned 403 to curl, so not read on the primary page: **blocked**].
  - Anchor cap "±3% or ±5%, depending upon the product" [search summary; not verified].
  - **Unverified:** the search summary said that on weekends "Friday's closing price is used as the index price component" and that the remaining weights are rescaled. I did not find this on the fetched V5 page; the V5 page only says "may be temporarily excluded". Treat as unverified.
- **Funding during closure:** unknown.
- **Price bounds:** anchor cap ±3% or ±5% (search summary; unverified).
- **Reopen:** smoothing mechanism on session transition [V5 docs].
- **Reachable from France/EEA:** unknown (help center blocked).
- **Date read:** 2026-11-25 (V5 page read; help center blocked).

---

### 11. Bitget (TradFi perpetual futures: stock and commodity indices)

- **Product:** traditional-asset perps, USDT-settled [web: `https://www.bitget.com/support/articles/12560603898830`, fetched 2026-11-25].
- **External source when open:** "Bitget connects to third-party data providers ... The index price is calculated as the weighted average of prices from external data sources, updated every 200ms" [web].
- **Closed-window rule (quoted):**
  - "During traditional market closures, including daily maintenance halts, weekends, and public holidays, external data sources stop producing new prices. The index price switches to the internal mode and is continuously advanced using an Exponential Moving Average (EMA) based on the futures' order book." [web].
  - Internal EMA: "S_new = S_old + (1 − β) × IPD", "IPD = max(P_impactBid − S, 0) − max(S − P_impactAsk, 0)", "β = exp(−Δt* ÷ τ)", "Δt* = min(Δt, c × τ)"; "Time constant τ: default 1200s", "Single-step cap coefficient c: default 0.1" [web].
  - Band: "the system uses the last available closing price in the external mode as its reference, and the index price under internal mode may not deviate from that closing price by more than 10%" [web].
  - Mark: standard "Mark Price = median(Price 1, Price 2, Price 3)" [web]. Deviation clamp: "Actual mark price = clamp(calculated mark price, index price × (1 − deviation constraint), index price × (1 + deviation constraint))"; "typically set at 3%" [web].
- **Funding during closure:** not read. Unknown.
- **Price bounds:** index ±10% of last external close; mark ±~3% of index (configurable).
- **Reopen:** "external mode" resumes when more than half of external sources update normally [web, line ~65 "switch back to external mode"].
- **Reachable from France/EEA:** unknown.
- **Date read:** 2026-11-25 (web).

---

### 12. Binance (TradFi perps: stocks, indices, commodities, FX)

- **Product:** TradFi perps; 24/7 [search summaries; Binance Square and third-party posts; **not official docs**].
- **External source when open:** "the price index aggregates data from multiple vendors, updating every second during market hours" [search summary of a Binance announcement].
- **Closed-window rule:**
  - Conflicting summaries: one says "Outside these hours, it remains fixed at the last value to maintain stability"; another says "uses a moving average in low-liquidity hours and stays fixed on weekends and holidays" [search]. Mark: "applying a smoothed futures price calculated with an Exponentially Weighted Moving Average (EWMA) during off-hours" [search].
  - Deviation limit: "±3% for commodity contracts like XAUUSDT" [search].
  - Funding: "settled every eight hours ... capped at ±2.00% per interval" [search; 17-3 check].
- **Funding during closure:** ±2% per interval (secondary).
- **Price bounds:** mark-to-index ±3% for commodities (secondary).
- **Reopen:** not found.
- **Reachable from France/EEA:** unknown.
- **Date read:** 2026-11-25 (search only; primary Binance Academy/contract spec page not reached). **Not primary-confirmed.**

---

### 13. Kraken (xStocks perps, tokenized equity perps; non-US clients)

- **Product:** "tokenized equity perpetual futures" on NVDA, AAPL, TSLA, GOOGL, HOOD, S&P 500, Nasdaq 100, gold [web: `https://blog.kraken.com/product/xstocks/tokenized-equity-perpetual-futures`, fetched 2026-11-25].
- **External source when open:** "xStocks are fully collateralized, 1:1 asset-backed tokenized equities that trade on-chain 24/7, including weekends and public holidays" [web]. The reference price is onchain xStocks trading: "a continuous, real-time reference price even when legacy markets are offline" [web].
- **Closed-window mark / oracle rule:** not found on the blog page. Marketing says "continuous price discovery" but gives no formula.
- **Hours conflict:** the search summary cites a Kraken support article ("Market hours explained", updated 2025-12-23) saying trading runs Sunday 8:00 PM ET to Friday 8:00 PM ET, and that off-hours pricing comes from underlying extended sessions [search, not fetched].
- **Funding / interest / bounds:** unknown.
- **Reopen:** unknown.
- **Reachable from France/EEA:** unknown. The blog says "eligible non-U.S. clients in 110+ countries" without naming France.
- **Date read:** 2026-11-25 (blog fetched; support page not fetched). **Mark rule unknown.**

---

### 14. Ostium (RWA perps, Arbitrum; stocks, indices, FX, commodities)

- **Product:** RWA perps; stocks and indices [search; DeFiLlama listing].
- **External source when open:** "In-house built Real World Asset feeds, with node and aggregator infrastructure operated by Stork Network" [search summary of Ostium docs; the gitbook pages are marked deprecated].
- **Closed-window rule (quoted):** "Although orders cannot be executed during market closures, you may still place Limit and Stop orders when markets are closed. These orders will automatically execute when markets reopen and the specified price conditions are met. Note that Market orders cannot be placed during non-trading hours." [web: `https://docs.ostium.com/supporting-infrastructure/price-oracle`, fetched 2026-11-25]. "Supplementing the standard weekly schedule, feeds include holiday session data that specifies dates when markets are closed for trading." [same].
- **Closed-window mark / oracle price:** not described on the page I fetched. Third-party write-ups describe a "halt-and-freeze" model; not confirmed on the docs.
- **Funding / interest:** RWAs use rollover fees, not funding (third-party: DeFiLlama/BeInCrypto). Unknown on docs.
- **Price bounds / reopen:** unknown beyond the limit/stop queue above.
- **Reachable from France/EEA:** unknown.
- **Date read:** 2026-11-25 (docs fetched; mark rule not on that page).

---

### 15. Felix (HIP-3 `flx` on Hyperliquid; single-ticker equities, commodities, indices)

- **Product:** single-ticker equities (NVDA, TSLA, COIN, CRCL, ...), indices (USA100), commodities (GOLD, SILVER, OIL, COPPER, PLATINUM, PALLADIUM, GAS) [`perpdexs.json` `flx` `assetToStreamingOiCap`; web docs]. Oak Research (third-party) lists some Felix markets (flx:CRCL, flx:NVDA, flx:TSLA) as "Delisted" [search]. Current status not verified.
- **External source when open:** "During on-hours (weekdays 9:30 AM ET – 4:00 PM ET to start), we aggregate prices from NYSE/NASDAQ (multiple data providers for redundancy) and take the median across feeds" [web: `https://usefelix.gitbook.io/perps/getting-started/perp-specifications/single-ticker-equities`, fetched 2026-11-25]. Pricing infrastructure: RedStone.
- **Closed-window rule (quoted):**
  - "For the 24/7 markets we divide the oracle price into three segments (weekday on-hours, weekday off-hours, weekend off-hours)" [web].
  - Weekday off-hours: "Oracle = EMA_1h(median(impact_bid_price, impact_ask_price))" [web]. Weekend off-hours: "Oracle = EMA_8h(median(impact_bid_price, impact_ask_price))" [web]. "Holidays are treated as weekends." [web].
  - "Each oracle update (every 2.5s) can change oraclePx by at most 1%." [web].
  - Mark: "median of the following 3 values: MarkPx0: Oracle Price; MarkPx1: Oracle Price + 150s EMA of difference between oracle price and midPx; MarkPx2: The median of best bid, best ask, last trade on Hyperliquid" [web]. "Each oracle update (every 2.5s) can change markPx by at most 1%." [web].
  - Band: "externalPerpPx limits a perp market's price movement to the given band of +/- min(1/max_leverage, 20%)." [web].
  - Admission: "Felix says its off-hours protections are experimental. Felix-deployed perps have dampened funding rates during off-hours" [web search summary; primary sentence is on the Felix FAQ, not fetched].
- **Funding during closure (on-chain config snapshot 2026-11-20):** `assetToFundingMultiplier`: `flx:NVDA` 0.0, `flx:TSLA` 0.0, `flx:USA100` 0.0 [`S/perpdexs.json`]. Interest: none listed for these assets. Inference: funding is switched off on these markets as of the snapshot.
- **Price bounds during closure:** oracle ≤1% per 2.5 s update; mark ≤1% per update; external band ±min(1/L, 20%).
- **Reopen:** unknown. Sunset guide says equities "lock at the Thursday 4 PM ET close" for settlement [search summary of Felix sunset guide].
- **Reachable from France/EEA:** unknown.
- **Date read:** 2026-11-25 (web); config 2026-11-20.

---

### 16. Kinetiq Markets (`km`, HIP-3) and other HIP-3 dexes (Ventuals `vntl`, Dreamcash `cash`, Paragon `para`, EntropyIO `io`)

- **Product:** equity perps in each. Kinetiq: AAPL, BABA, BMNR, GOOGL, MU, NVDA, PLTR, RTX, US500, USBOND, USTECH, SMALL2000 (`perpdexs.json`). Ventuals: ANTHROPIC, OPENAI, MAG7, SEMIS, ... (pre-IPO/themes). Dreamcash: AMZN, GOOGL, HOOD, INTC, META, MSFT, NVDA, GOLD, SILVER. Paragon: AAOI, AVGO, CRDO, ... Entropy: AAPL, NVDA, ANTH, OAI.
- **Oracle / closed-window rule:** docs not retrieved (search could not reach docs.ventuals.com or Kinetiq's markets page). Secondary: Kaiko is Kinetiq's oracle and "supports pricing outside traditional market hours" [search, Kaiko page]. Ventuals: "By weighting 50% of the oracle price to an 8h EMA" [search, unverified third-party]. Entropy: "RedStone Live Powers Entropy Pre-IPO and RWA markets on Hyperliquid" [search title only].
- **Funding parameters (on-chain config snapshot 2026-11-20, `S/perpdexs.json`):**
  - `km:NVDA` interest rate 0.0000456621 (per hour?; units not checked).
  - `vntl:ANTHROPIC` multiplier 0.0.
  - `cash:NVDA` multiplier 0.000001.
  - `io:NVDA` multiplier 0.5.
  - `para:AAOI` multiplier 0.6.
  - `flx:NVDA` / `flx:TSLA` / `flx:USA100` multiplier 0.0.
  - `xyz`: multiplier 0.5 on NVDA, AAPL, SP500, EUR.
- **Oracle updater (config):** Felix (`flx`), Ventuals (`vntl`), EntropyIO (`io`) set `oracleUpdater`, sometimes to the same address `0x94757f8d...`. Paragon's `oracleUpdater` equals its own deployer address. Kinetiq, dreamcash and xyz have `oracleUpdater` null.
- **Reachable from France/EEA:** unknown for all.
- **Date read:** 2026-11-25 (search; config 2026-11-20). **Closed-window rule unverified for Kinetiq, Ventuals, Dreamcash, Paragon, EntropyIO.**

---

### 17. Venues with no equity perps in the local copies

- dYdX (`docs.dydx.xyz.txt`), Drift (`docs.drift.trade.txt`), Backpack (`docs.backpack.exchange.txt`): zero hits on TSLA/NVDA/AAPL/SPY/NASDAQ/S&P in the local copies [local grep, 2026-11-25]. dYdX premise note on cross markets: `docs/reviews/dydx_premise_20261124.md` (funding only; no equity list).

---

## Disagreements

Pairs and groups whose closed-window rules differ in a way that could force a predictable price gap or transfer around the reopen. Each entry: the difference, the transfer I expect (Inference), and the cheapest observation to test it.

**D1. Fixed index vs book-driven index over the weekend (Variational vs xyz / Lighter / Extended / Bitget / Felix / Aster / Paradex).**
- Variational equity index: "Fixed Mode ... the Price Index remains fixed at the last available value" [`docs.variational.io.txt:1094-1096`]. Variational's equity mark moves only with funding and OLP risk [line 631].
- xyz: the oracle follows its own impact EMA (τ 30 min) and the external price is "fixed at the external close price" [`xyzdocs:232`, `:266`].
- Lighter: index = internal EMA τ 30 min, uncapped for the names on the 2026-07-10 list [`lighterdocs:1389`, `:1400-1406`].
- Extended: index moves toward book impact prices with Δt cap 3 min, bounded ±1/L from last oracle [`docs.extended.exchange.txt:789-833`].
- Bitget: internal EMA τ 1200 s, band ±10% [web].
- Felix: EMA_8h over median impact on weekends [web].
- Aster: EWMA of last trade, β = exp(−1/1600) [`docs.asterdex.com.txt:5965`].
- Expected transfer (Inference): on Variational the weekend mark stays near the last external close and the whole gap is taken at reopen in one step. On the book-EMA venues the mark drifts with the book and reverts over hours after the open. A position opened on a drifting venue and closed on a frozen one earns the reopen gap on the frozen venue only if the drift and the external move have the same sign. The fixed-index venue is therefore the one that carries the reopen risk, and the book-driven venues carry the weekend fade (R462/R463 family).
- Cheapest observation: for each venue, take the Friday-close external price and the Sunday-open mark or index; log the weekend move per venue; compare the sign with the Monday open (the 156/192 same-sign test in `reflection_20261125`).

**D2. Peer-import vs own-book index (Paradex, OKX vs xyz, Lighter, Bitget, Extended).**
- Paradex closing-hours index: Hyperliquid 21.28%, OKX 21.28%, Bybit 21.28%, Lighter 14.89%, own Closing Price 10.64%, own Internal Price (EMA of Paradex mark, 1 h half-life) 10.64% [web]. Total peer weight 78.7%, of which the own-mark EMA and closing price together are 21.3%.
- OKX stock perp index: "relies more on OKX's own contract price and stock perps index price on other exchanges" (Hyperliquid, Binance) during closures [web].
- xyz: no peer import in its oracle (own book EMA only) [`xyzdocs:220-240`].
- Expected transfer (Inference): a weekend overshoot on Hyperliquid's xyz book propagates into Paradex's index with weight about 0.21 and into OKX's index (weight unquoted), and then into their marks. Paradex's own mark feeds back into its index (internal price 10.64%). The loop is endogenous (Seo, Cha, Son, Lee, Lee & Sung 2026 Lemma 1; `research/intake/oracle_frontiers_20261125.md`). Expected transfer: a Paradex weekend mark tracks xyz's, not the external close, and reverts at reopen when the external sources return.
- Cheapest observation: regress Paradex's closing-hours index changes on Hyperliquid's xyz mark changes and Lighter's index changes at 1-minute frequency; the predicted slope is about 0.21 on HL with no lag.

**D3. Band width and clamp: capped vs uncapped names on the same underlying (xyz vs Lighter vs edgeX vs Extended vs Felix vs OKX vs Bitget vs Aster).**
- NVDA: xyz ±10% discovery band (10x), mark clamp 1% [`xyz` spec]; Lighter NVDA no cap since 2026-07-10 [`lighterdocs:1400-1406`]; Extended ±1/L (= ±1/max_leverage, the NVDA max lev is not read); edgeX ±1/L [`edgex:821`]; Felix ±min(1/L, 20%) [web]; OKX ±10% [web]; Bitget ±10% and mark ±3% [web]; Aster order caps ±5% and no mark clamp [`docs.asterdex.com.txt` table].
- Expected transfer (Inference): when the closed-window price moves beyond xyz's band, the mark on xyz stops and the bound holds liquidation (xyz: "cannot be liquidated while those bounds are in effect"). On Lighter the same move is uncapped. At reopen, a long on the capped venue is at the band edge and cannot be liquidated; the uncapped venue's mark has already moved. The transfer runs from the capped venue's short side to its long side, at the reopen gap size. Sign: the venue with the wider band carries the excess.
- Cheapest observation: pick a weekend where xyz NVDA mark hits its band (log discovery_bounds_upper/lower and mark); compare with Lighter NVDA mark and with the Sunday-open external price; record the reopen gap per venue.

**D4. Funding during closure: zero, dampened, or 0.5x with interest 0.01% (Variational / OKX / Felix / Lighter RWA / Paradex / Extended / xyz / Binance).**
- Variational: interest 0%, clamp ±0.0005 [`docs.variational.io.txt:1105-1107`].
- OKX stock perps: interest 0%; charged only at settlement [web].
- Felix: on-chain multiplier 0.0 for NVDA, TSLA, USA100 (2026-11-20) [`S/perpdexs.json`]; docs say "dampened" [search].
- Lighter RWA: multiplier 1/2; interest per market (value not read) [`lighterdocs:1193`].
- Paradex TradFi: multiplier 0.5; baseline interest 0.01%; cap 0.5%/8h [`paradex_funding.md:13,84,99`].
- Extended RWA: interest 0.0035%/8h; clamp ±0.05% [`docs.extended.exchange.txt:568-572`].
- xyz: multiplier 0.5; interest 0.01%/8h (EUR/GBP/JPY/KRW 0); cap 4%/h (xyz) vs 0.5%/h (Hyperliquid doc) [`xyzdocs:373-387`; `hldocs:1746`].
- Expected transfer (Inference): a position held through the closure pays nothing on Variational, OKX and Felix (zero funding), and pays a positive carry on xyz/Paradex/Extended. A weekend overshoot that is not funded is a free option to hold the drift to the reopen. The transfer is from the side that holds the drift to the side that holds the reopen reversion.
- Cheapest observation: the hourly funding ledger on each venue over one weekend; the difference between the funding charged on xyz NVDA and on Variational NVDA for the same notional is the carry; check it against the mark drift.

**D5. Holiday treatment: full-day closure vs partial sessions (Aster vs xyz vs Felix vs Variational vs Paradex).**
- Aster: "Public holiday 00:00 → 23:59 EST" EWMA mode, so a holiday is a full closed day [`docs.asterdex.com.txt:5987-6035`].
- Felix: "Holidays are treated as weekends. Shorter regular sessions due to holidays will transition to weekend status afterwards." [web].
- xyz: holidays follow "applicable equity market holidays and trading hours" [`xyzdocs` changelog 2026-08-13]; futures holiday table has partial opens (e.g. 2026-11-27 Open 00:00–13:15).
- Variational: "Fixed Mode (Daily Maintenance, Holidays and Weekends)" [`docs.variational.io.txt:1094`].
- Paradex indices: "Follows CME equity index futures holiday closures" [web].
- Expected transfer (Inference): on a holiday with a short session (Thanksgiving Friday, Christmas Eve), Felix and Aster treat the day as a weekend and freeze or smooth from the last trade, while xyz follows the partial equity session. The mark on the two venues can diverge by the full session move that xyz prices and the others do not.
- Cheapest observation: on 2026-11-27 (Thanksgiving Friday, early close in the xyz futures table), record xyz NVDA mark vs Felix/Aster mark over 13:00–20:00 ET.

**D6. Oracle-source hierarchy at reopen (Paradex and Lighter RWA revert to vendor feed; xyz reverts on the next tick; Variational resumes on the vendor index; Bybit smooths).**
- xyz: "When external inputs resume, the oracle reverts to the externally derived price on the next tick" [`xyzdocs:245`]. Discovery reset counters reset [discovery-bounds page].
- Lighter: "As soon as a fresh external price is available, pricing switches back to it" [`lighterdocs:1338`].
- Bybit: "a smoothing mechanism helps maintain index price continuity" [V5 docs].
- Bitget: back to external "once it is detected that more than half of the external data source data is being updated normally" [web].
- Paradex: at open the weights jump (Pyth 31.9%) [web].
- Expected transfer (Inference): xyz and Lighter reopen with a one-tick jump to the vendor price (no smoothing), while Bybit and Bitget smooth the transition. A reopen gap then lands on xyz/Lighter in one step, and on Bybit/Bitget over several updates. Long/short holders on the smoothed venues can exit inside the smoothing window at a better price than on xyz/Lighter.
- Cheapest observation: the first 60 seconds after the Monday open, one-second marks per venue, against the Monday open external print.

**D7. Kraken's two hour rules and no mark rule (Kraken vs the rest).**
- Kraken blog: 24/7 pricing from onchain xStocks [web]. Kraken support (search summary only): 8:00 PM ET Sun–Fri, off-hours from extended sessions [search].
- Expected transfer (Inference): Kraken's mark has no published closure rule; its weekend price follows onchain xStocks, which is a peer-import of a tokenized asset rather than a book. Unknown until the spec is read.
- Cheapest observation: Kraken's own contract specification page (not reached).

**D8. Stock perps with no closed-window rule published (Binance, Ostium, Kinetiq, Ventuals, Dreamcash, Paragon, EntropyIO, Bybit funding).**
- These rows are not primary-confirmed. Expected transfer: unknown. Do not size anything on these venues' closed-window behaviour until the primary spec is read.

---

## Blocked / not reached

- Bybit help center `https://www.bybit.com/en/help-center/article/Introduction-to-TradFi-Perpetual-Contracts`: HTTP 403 (blocked; not bypassed).
- Kraken support "Market hours explained" and xStocks perp spec: not fetched (search summary only).
- Ostium docs.ostium.com other pages (mark, funding): not fetched beyond price-oracle page.
- Ventuals, Kinetiq, Dreamcash, Paragon, EntropyIO docs: not retrieved.
- Binance official TradFi specs: not retrieved (search summaries only).

## Limits

- Several rows rest on search summaries that I did not confirm on a primary page: Bybit anchor/Friday close, Binance, Kraken hours, Ostium holiday treatment, Felix delisting status.
- trade.xyz discovery-bound resets: the docs disagree on whether the ratchet is live (see row 1).
- Funding clamp and cap values: xyz and Hyperliquid disagree (see row 1 and row 2).
- Reachability was not checked against any terms page for xyz, Lighter, Paradex, Variational, edgeX, Bybit, Bitget, Binance, Kraken, Ostium, Felix, Kinetiq. The reachable column is "unknown" for those.
- The HIP-3 config snapshot (`perpdexs.json`) is dated 2026-11-20 and may be stale.
