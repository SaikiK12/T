# Sources: who makes money, where it shows, and what the research says

Research sweep, 2026-10-19. Every endpoint below was called with curl from this container on that day (about 09:30 UTC).
Web pages were read with a fetch tool. **No statistic about any edge was computed here.** The numbers quoted from
leaderboards are what the endpoints returned (data description, not tests). Testable claims are in `docs/CLAIMS.md`.

Evidence grades used here and in CLAIMS: **A** audited or verifiable by a third party (on-chain, regulator, broker
certified), **B** published study, **C** self-reported, **D** marketing.

## 1. Traders

### 1.1 Tarek El Marhri (Elmarhri), Instagram `tarek_elmarhri`

**Identity.** The Krechendo Trading site links to `instagram.com/tarek_elmarhri/` (seen in the HTML of
https://www.krechendo-trading.fr/). Instagram itself returned a login wall (HTTP 429, redirect to `/accounts/login`), so
**none of his Instagram posts were read.** YouTube channel: https://www.youtube.com/user/krechendotrading (RSS feed
read: conference talks, TV clips, a 2015 "live trading demonstration"; no crypto content found).

**Career (self-reported in press; not independently verified).**
- Started trading in 2000 with an ESSEC-student investment club that "made 101% in one year"; Refco (London) in 2003,
  then about 12 years on European futures: Marex Spectron and Kyte (London), Van der Moolen (Amsterdam, market maker),
  a Paris hedge-fund unit in 2010 (one bio says Millennium Management, another says "Icecap Paris").
  Sources: [FNH 2015](https://www.fnh.ma/articles/entretien-plongee-dans-le-monde-du-scalping),
  [Yabiladi 2019](https://en.yabiladi.com/articles/details/76202/diaspo-tarek-elmarhri-trader-hunt.html),
  [newtrading.fr review, 2026-09](https://newtrading.fr/?p=53595).
- Founded Krechendo Trading (Paris La Défense, 2013), a training school and desk-rental "trading arcade"; branches in
  Waterloo (Belgium, 2015), Agadir and Casablanca. Director of Darwinex France from 2017. Technical adviser to the film
  *L'Outsider* (2016). Regular TV commentator (BFM Business, LCI, M6, France 2, Canal+).

**What he trades and how.**
- Instruments: futures on Eurex and CME, mainly index and bond futures; in contests also turbos and forex
  ([Krechendo, WOT 2016](https://www.krechendo-trading.fr/2016/12/05/tarek-elmarhri-krechendo-trading-vainqueur-du-live-trading-event-du-wot-2016/)).
- Style: order-book trading ("trading au carnet d'ordres"), tape reading, scalping and day trading. In his words
  (FNH 2015, translated): "We don't try to anticipate the direction of the market", buy and sell zones come from "the
  order flow of large participants", and "our trades never last long, between 1 second and 5 minutes".
- Setup elements taught (course page
  [formation-trading-initiale](https://www.krechendo-trading.fr/formations-trading/formation-trading-initiale/)):
  order-book levels against chart levels, the day's key events (economic releases, bond auctions), a daily trading
  plan, a daily loss limit **and** a daily profit limit, position sizing when going live.
- Spot crypto, perpetuals or prop-firm crypto trading: **no evidence found** that he trades them.

**Track record.** None verifiable.
- Self-reported: the 101% club year (2000).
- Live-trading contest wins, all reported by Krechendo's own blog: World of Trading Frankfurt 2015 and 2016, Forex Day
  Madrid (9 June 2017, a 1.5-hour three-trader final), ITForum Rimini 2019 (a single CPI-release session, +EUR 1,311.50)
  ([Madrid](https://www.krechendo-trading.fr/2017/06/14/victoire-de-tarek-elmarhri-live-trading-a-madrid-lors-dune-finale-reunissant-3-traders-internationaux/),
  [Rimini](https://www.krechendo-trading.fr/2019/07/18/victoire-au-live-trading-itforum-a-rimini-2/)).
  These are short, selected sessions, not a record.
- No broker statement, audited return, Darwinex DARWIN or copy-trading profile under his name was found, despite his
  Darwinex role (a search for a DARWIN linked to him returned nothing).

**Business model.** Courses: initiation 1 day EUR 100 (newtrading), initial order-book course 2 weeks / 80 h
EUR 3,900, European diploma 5 weeks EUR 6,900 (newtrading), advanced "Vivre du trading" 7 weeks / 280 h EUR 9,900
([course page](https://www.krechendo-trading.fr/formations-trading/formation-vivre-du-trading/), updated 27/05/2025).
The published "quality indicators 2024" are certificate rates (83%, 90%), 0% drop-out and 100% satisfaction: they
measure course completion, **not trading profit**. Krechendo claims 3,000+ trained students and 4.9/5 on 250+ Google
reviews ([krechendo.com](https://www.krechendo.com/)).

**Red flags.**
1. Sells EUR 3,900-9,900 courses under "Trader et gagner de l'argent grâce au carnet d'ordres" but publishes no student
   P&L.
2. Promotes a prop firm, ZenitFunding, with a discount code (SAVE70) in two posts
   ([Jan 2025](https://www.krechendo-trading.fr/2025/01/24/la-propfirm-zenitfunding-debarque-en-france-et-en-europe/),
   [Mar 2025](https://www.krechendo-trading.fr/2025/03/06/interview-de-krechendo-trading-dans-forbes/)) without a
   stated relationship. ZenitFunding is a futures prop firm founded in 2024, CEO "unknown", operated from Belgium per
   [PropFirmMap](https://propfirmmap.com/trust-check/zenitfunding); a link to Krechendo's Belgian campus is
   **not verified**.
3. The "record" is contest sessions; years of experience differ between his pages (13, 20, 25).
4. 2018 Reuters story ([via Boursenews](https://boursenews.ma/article/actualite/le-pari-a-6-6-milliards-de-dollars-d-un-trader-francais-expose-les-defaillances-du-marche)):
   a trainee fresh from an 8-week Krechendo course traded about USD 6.6 bn notional of S&P 500 and EuroStoxx futures
   through Valbury from a EUR 20,000 account because the broker's limit was missing. Elmarhri blamed the account
   setup. It says nothing about his own skill, but shows trainees going live after short courses.
5. He cites Navinder Sarao and Paul Rotter as model order-book traders (FNH 2015); Sarao later pleaded guilty to
   spoofing.

**What transfers to us.** Sub-5-minute order-book scalping on deep CME/Eurex contracts does not translate to hourly
Binance data. Two testable pieces: a cost bound for sub-5-minute trading on perps (CLAIMS C01) and the daily
loss/profit limit overlay (C17).

### 1.2 Public traders and books with verifiable records

| Who | Venue | What is verifiable | Record (as returned 2026-10-19) | Grade and caveat |
|---|---|---|---|---|
| Hyperliquid leaderboard | on-chain perps | every fill and position is public | 47,468 accounts listed; 49% positive all-time, 22% positive over the last month; top named account "BobbyBigSize" +USD 141.4 M all-time | A for the numbers; names are self-chosen; the list is today's snapshot (selection on current PnL) |
| HLP vault `0xdfc2...f303` | Hyperliquid market-making and liquidation vault | on-chain | +USD 138.8 M PnL since May 2023, TVL USD 179 M, current APR 3.4% | A; the house side, with liquidation flow we cannot get. 6,395 of 9,478 user vaults are closed |
| James Wynn | Hyperliquid | on-chain, tracked by Arkham/Lookonchain | about USD 100 M lost in May 2025 on a 40x BTC long ([Cointelegraph](https://cointelegraph.com/news/hyperliquid-whale-loss-100-million-bitcoin-dips-below-105)) | A; a verifiable record can be a blow-up |
| Binance lead "A路飞" | Binance copy trading | platform-computed | #1 by 90-day ROI: ROI 9,572%, PnL USD 47,859 (so a base near USD 500), max DD 46.8%, win rate 71.8%, **copier PnL -USD 378,206** | B/C; platform numbers, not audited. 7 of the top 20 by 90-day ROI had negative copier PnL |
| OKX lead `1499200359BAE11A` | OKX copy trading | platform-computed | 472 lead days, PnL USD 1.92 M, 194 profit days vs 171 loss days, current copiers' PnL about -USD 10 | B/C |
| DARWIN SYO (@SERSANSISTEMAS) | Darwinex (FCA/CNMV broker) | broker-certified live record | since Jan 2018, FX/index/commodity CFDs, 15.0%/yr gross, AUM USD 13.9 M from 559 investors; fees 1.2% + 20% ([page](https://www.darwinex.com/darwin/SYO.4.12)) | A-/B; gross of fees; not crypto |
| Topstep (all traders) | CME futures prop | firm's legal disclosure | 2025: 16.8% of Combines passed; 51.8% of participants reached the funded level; 33.3% of funded participants got a payout; 0.71% of Express traders called up to Live ([topstep.com](https://www.topstep.com/)) | B; self-published but specific |

## 2. Copy-trading leaderboards and positioning endpoints (all tested)

No login, no keys. "200" means the call returned data on 2026-10-19. Rate limits were not measured except where a
header or exchangeInfo stated one; poll politely (about 1 request/s).

### 2.1 Binance (`https://www.binance.com`; headers `Content-Type: application/json`, `clienttype: web`)

| Call | Result | Fields and depth |
|---|---|---|
| `POST /bapi/futures/v1/friendly/future/copy-trade/home-page/query-list` body `{"pageNumber":1,"pageSize":20,"timeRange":"90D","dataType":"ROI","favoriteOnly":false,"hideFull":false,"nickname":"","order":"DESC","userAsset":0,"portfolioType":"PUBLIC"}` | 200, total 9,138 portfolios | leadPortfolioId, nickname, roi, pnl, aum, mdd, winRate, sharpRatio, copierPnl, currentCopyCount, maxCopyCount, startTime, chartItems (daily ROI). timeRange 7D/30D/90D/180D (360D and ALL rejected); dataType ROI, PNL, COPIER_PNL, SHARP_RATIO, AUM, MDD; page size capped at 30 |
| `GET /bapi/futures/v1/friendly/future/copy-trade/lead-portfolio/detail?portfolioId=` | 200 | 80 fields: profitSharingRate, marginBalance, aumAmount, totalCopyCount, closeLeadCount, lockPeriod, positionShow, startTime, description (often private-group invites) |
| `GET /bapi/futures/v1/public/future/copy-trade/lead-portfolio/performance?portfolioId=&timeRange=90D` | 200 | roi, pnl, mdd, copierPnl, winRate, winOrders, totalOrder, sharpRatio |
| `GET /bapi/futures/v1/public/future/copy-trade/lead-portfolio/chart-data?dataType=ROI&portfolioId=&timeRange=90D` | 200 | daily ROI series |
| `GET /bapi/futures/v1/friendly/future/copy-trade/lead-data/positions?portfolioId=` | 200 | open positions: symbol, positionSide, positionAmount, entryPrice, markPrice, unrealizedProfit, leverage, breakEvenPrice, notionalValue. Empty unless the lead shows positions (1 of the first 9 by AUM did) |
| `POST /bapi/futures/v1/friendly/future/copy-trade/lead-portfolio/position-history` body `{"pageNumber":1,"pageSize":30,"portfolioId":"...","sort":"OPENING"}` | 200 | closed positions: symbol, side, opened, closed, avgCost, avgClosePrice, closingPnl, maxOpenInterest, closedVolume, leverage, margin mode. **About 4.5 months kept**: the oldest row was 2026-05-27/06-02 even for leads started in 2024 |
| `GET /bapi/futures/v1/public/future/copy-trade/lead-portfolio/performance/coin?portfolioId=&timeRange=90D` | 200 | traded-volume share by asset |
| `.../lead-portfolio/trade-history` (POST) | 200 but empty | - |
| `.../lead-portfolio/copiers`; old futures leaderboard `getLeaderboardRank` (v1/v2/v3), `getOtherPosition` | 404 | the old leaderboard is retired |
| `GET /futures/data/{topLongShortPositionRatio, topLongShortAccountRatio, globalLongShortAccountRatio, takerlongshortRatio, openInterestHist}?symbol=&period=1h&limit=500`, `basis?pair=&contractType=PERPETUAL` | 200 | about 30 days only (older startTime gives error -1130). The archive `metrics` already holds the first five |
| `GET /fapi/v1/{premiumIndex, fundingInfo, fundingRate, depth, aggTrades, openInterest, ticker/24hr, ticker/bookTicker, exchangeInfo}` | 200 | exchangeInfo states 2,400 request weight per minute; depth(1000) used weight 20. fundingInfo lists 809 symbols with their funding interval (some 4 h) and caps |
| `GET /fapi/v1/allForceOrders` | 404 | liquidations only through the websocket stream |

### 2.2 OKX (`https://www.okx.com/api/v5`, GET)

| Call | Result | Fields and depth |
|---|---|---|
| `copytrading/public-lead-traders?instType=SWAP&sortType=overview\|pnl\|aum\|win_ratio\|pnl_ratio\|current_copy_trader_pnl&limit=20&page=` | 200 | about 260 traders (13 pages of 20; 4 pages for win_ratio, pnl_ratio). uniqueCode, nickName, pnl, pnlRatio, pnlRatios series, aum, winRatio, leadDays, copyTraderNum, accCopyTraderNum, traderInsts |
| `copytrading/public-weekly-pnl`, `public-pnl?lastDays=4` (daily, 366 days), `public-stats`, `public-preference-currency`, `public-copy-traders`, `public-config` (all `&uniqueCode=`) | 200 | stats: winRatio, profitDays, lossDays, avgSubPosNotional, investAmt, curCopyTraderPnl; copiers' own PnL |
| `copytrading/public-current-subpositions` | 200 | margin, lever, upl, posSide; **instId came back blank** |
| `copytrading/public-subpositions-history?limit=100` | 200 | instId, openTime/closeTime, open/close price, pnl, lever |
| `rubik/stat/contracts/long-short-position-ratio-contract-top-trader?instId=BTC-USDT-SWAP&period=1H&limit=100` (also `...account-ratio-contract-top-trader`, `...account-ratio-contract`, `contracts/open-interest-history`) | 200 | hourly, 100 rows per call, data back about 55-60 days (empty at 60) |
| `rubik/stat/taker-volume-contract?instId=&period=1H` | 200 | hourly back at least 365 days (zeros at 730) |
| `rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1H`, `margin/loan-ratio` | 200 | 720 rows (30 days) |
| `public/funding-rate-history?instId=&limit=400`; `market/history-candles?bar=1H` | 200 | funding about 3 months; candles back to 2020 |

### 2.3 Bitget

| Call | Result | Fields and depth |
|---|---|---|
| `GET https://api.bitget.com/api/v2/mix/market/{long-short, account-long-short, position-long-short, taker-buy-sell}?symbol=BTCUSDT&period=1h` | 200 | **only the last 30 rows (about 30 hours)**: live collection only. Header `x-mbx-used-remain-limit` present |
| `.../history-fund-rate`, `.../open-interest`, `.../history-candles` (1H back to 2023 tested) | 200 | - |
| `POST https://www.bitget.com/v1/trigger/public/uta/rankingList` body `{"pageNo":1,"pageSize":20,"dataCycle":30,"sortRule":2}` (2 ROI, 5 profit, 10 copiers' profit, 9 AUM; cycles 7/30/90/180) | 200 | 154 traders (UTA list): traderUid, displayName, followCount, total_income, profit_rate, total_follow_profit, AUM, max_retracement, totalEquity, topSymbols |
| `POST /v1/trigger/trace/public/traderDetailPageV2` `{"traderUid":"..."}` | 200 | aum, followProfits, totalReturnRate, last30DayBurst, tradeFrequency, settledInDays |
| `POST /v1/trigger/trace/order/historyList` `{"traderUid","pageNo","pageSize"}` | 200 | closed orders: open/close price and time, netProfit, fees, funding; only the first page served |
| `POST /v1/trigger/trace/public/currentPositionList` `{"traderId":"..."}` | 200 | empty for the trader tested |

Bitget web paths were found in the site's JavaScript; they are undocumented and need `Origin`/`Referer` headers.

### 2.4 Hyperliquid (on-chain, the only fully verifiable trader data found)

| Call | Result | Fields and depth |
|---|---|---|
| `GET https://stats-data.hyperliquid.xyz/Mainnet/leaderboard` | 200, 39 MB | 47,468 rows: ethAddress, accountValue, displayName, day/week/month/allTime {pnl, roi, vlm}; a current snapshot |
| `GET https://stats-data.hyperliquid.xyz/Mainnet/vaults` | 200 | 9,478 vaults: apr, pnl series, tvl, leader, isClosed |
| `POST https://api.hyperliquid.xyz/info` with `type`: `clearinghouseState`, `userFills` (2,000 latest), `userFillsByTime` (from startTime; capped), `portfolio`, `userFunding`, `vaultDetails`, `metaAndAssetCtxs`, `fundingHistory` (BTC from 2023-05), `candleSnapshot` (5,000 candles max) | 200 | positions, fills with closedPnl and fees, account-value history |

**Survivorship.** Every list is a current list. Binance shows active public portfolios (closed ones disappear); OKX shows
about 260 top traders; Bitget's UTA list 154; Hyperliquid's leaderboard ranks today's accounts. ROI on small capital
dominates ROI rankings (USD 47,859 of profit = 9,572%), and copiers can lose while the lead wins (USD -378,206). A fair
persistence test must snapshot forward from a fixed date; backfills from position histories cover survivors only.

## 3. Prop firms

Rules from each firm's own site where it loaded; **third-party** marks figures I could not confirm on the firm's site.

| Firm | Product | Fee | Target | Daily loss | Max drawdown | Other rules | Split, payout |
|---|---|---|---|---|---|---|---|
| [HyroTrader](https://www.hyrotrader.com/) (crypto, Bybit/BloFin demo, 700+ USDT perps, up to 150x on BTC/ETH) | Two-step | from USD 59, refundable deposit | 10% then 5% | 5% | 10% (static or trailing not stated) | min 5+5 days; no day > 40% of target; low caps (<USD 100 M) <= 5% of balance; martingale and cross-account hedging banned; manual reviews can remove profits; stop loss not mandatory | 80% to 90%; on demand above USD 100, within 24 h, USDT/USDC |
| HyroTrader | One-step | from USD 69, refundable | 10% | 4% | 6% | min 5 days; 40% day rule | 80% to 90% |
| HyroTrader | Zero-step | from USD 89, non-refundable | 10% | 3% | 5% | min 1 day; no single trade > 50% | 80% |
| (HyroTrader daily rule) | | | | floor = equity at 00:00 UTC - initial balance x daily %, equity includes open PnL and fees ([FAQ](https://www.hyrotrader.com/faq/rules/how-is-the-5-daily-drawdown-calculated/)) | | all accounts are demo; its FAQ says revenue comes from challenge fees | claims USD 8 M+ paid, 1.7k+ funded |
| [Crypto Fund Trader](https://cryptofundtrader.com/) (crypto + FX, 1:100, news allowed, no time limit, all demo) | 1 phase | not captured | 10% | 4% | 6% trailing | - | live 80% |
| CFT | 2 phases | not captured | 8% then 5% | 5% | 10% | - | live 80%; scaling plan to USD 1.28 M, split 50% to 90% by level |
| CFT | "Break" | not captured | USD 1,250 | - | USD 1,000 trailing | funded: 40% consistency | 80%; claims USD 21.8 M paid, USD 544k last month |
| Breakout (Kraken-owned since 2025-09; site 403 from here) | 1-step plans, **third-party** ([review](https://proptradingvibes.com/blog/breakout-max-drawdown)) | not captured | Pro 12%, Turbo 9% | 3% of equity | static: Classic 6%, Pro 5%, Turbo 3% | no consistency rule (third-party) | 80% to 90%, USDC on Ethereum |
| [FTMO](https://ftmo.com/en/trading-objectives/) (CFDs incl. a few crypto; crypto list not verified) | 2-Step | EUR 540 for 100k ([TradeInformer](https://www.tradeinformer.com/prop-weekly/what-ftmo-tells-us-about-prop-firm-finances)) | 10% then 5% | 5% of initial, from the 00:00 CE(S)T balance, equity-based | 10% static | min 4 trading days per phase | fee refunded with first reward |
| FTMO | 1-Step | not captured | 10% | 3% | 10% end-of-day trailing (follows highest 00:00 balance) | best day <= 50% of total profit (orders from 2026-10-12) | site claims USD 650 M+ paid |
| [Topstep](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit) (CME futures) | Combine 50K/100K/150K | USD 49/month for 50K plus USD 149 activation (**third-party**) | USD 3k/6k/9k (**third-party**) | platform-dependent | USD 2,000/3,000/4,500, end-of-day trailing, locks at the starting balance; breaches checked intraday | best day < 55% of target; max 5/10/15 contracts; flat by 3:10 pm CT in Express | 90%; payouts up to USD 12k; Live after 30 winning days of USD 150+ |
| Apex (site 403 from here) | EOD evaluation, **third-party** | - | 50K: USD 3,000 | USD 1,000 (one source) | USD 2,000 EOD trailing | 50% consistency at payout; PA activation USD 99 | USD 500 minimum payout, 5 qualifying days |
| ZenitFunding (Krechendo's posts) | futures (Eurex/CME), simulated | USD 165 list for 50K (PropFirmMap) | USD 3k / 9k / 20k on 50k/150k/300k | - | EUR 2,500 / 5,000 / 7,500 trailing | payouts on days 1-4 and 16-20 | 90% |

**Published pass and payout rates.**
- Topstep 2025 (firm disclosure, above): 16.8% pass per Combine, 33.3% of funded participants paid, 0.71% reach Live.
- FPFX Tech (prop-firm technology vendor, 300,000 accounts): 7% of accounts reached a payout; average payout about 4%
  of plan size; average pass rate 14%; average challenge about USD 100
  ([Finance Magnates, 2025-03-18](https://www.financemagnates.com/forex/only-1-in-20-traders-pass-prop-firm-challenges-reports-the-funded-trader/)).
- The Funded Trader CEO on Discord: 5-10% pass, about 20% of funded traders paid (self-reported). E8 Markets 17.7%
  pass (2023-01 to 2024-03), Fintokei 23% (2024), via TradeInformer. PipFarm: 41% reach the payout stage (survey).
- FTMO 2023 financial statements: revenue USD 203.9 M, operating costs 49% of revenue (TradeInformer). FTMO publishes no
  pass rate.
- Counterparty risk: The Funded Trader had 1,272 traders waiting for funds (Finance Magnates). My Forex Funds: the CFTC
  alleged at least USD 310 M in fees (2023); the case was dismissed with prejudice and the CFTC sanctioned in 2025
  ([Finance Magnates](https://www.financemagnates.com/forex/my-forex-funds-parent-defeats-cftc-in-court-as-judge-imposes-sanctions/)),
  after two years of frozen operations.

The lab's earlier lanes R143 (`funded`) and R144 (`challengeoption`) found a random start loses about USD 80 per
challenge; `docs/CONCEPTS.md` plans `lab/propfirm.py`. CLAIMS C15/C16 give exact rule sets for it.

## 4. Science

### 4.1 Order flow and taker imbalance
- **Silantyev, "Order flow analysis of cryptocurrency markets", *Digital Finance* 1 (2019)**,
  [doi:10.1007/s42521-019-00007-w](https://ideas.repec.org/a/spr/digfin/v1y2019i1d10.1007_s42521-019-00007-w.html).
  BitMEX XBTUSD trades and quotes: trade-flow imbalance explains contemporaneous price changes better than
  book order-flow imbalance; thin depth and slow book updates set crypto apart. Contemporaneous, not predictive.
- **Cont, Kukanov, Stoikov, "The price impact of order book events" (2014)**, [arXiv:1011.6402](https://arxiv.org/abs/1011.6402).
  Price changes are linear in order-flow imbalance at the best quotes, with slope inversely proportional to depth.
- **Donier and Bonart, "A million metaorder analysis of market impact on the Bitcoin" (2015)**,
  [arXiv:1412.4503](https://arxiv.org/abs/1412.4503). The square-root impact law holds over four decades of order size
  on Bitcoin; impact of uninformed flow decays almost fully. Our size will move hourly prices, and fading the flow
  harvests that decay.
- **Kim and Hansen, "The Quarter-Hour Effect" (2026)**, [arXiv:2607.09426](https://arxiv.org/abs/2607.09426). Six Binance
  perps: activity bursts at 1-, 5- and 15-minute marks; quarter-hour opening imbalance predicts 4-12 h returns; the
  short-horizon effect is about 0.5 bp (already in CONCEPTS).
- **Kitron and Wengrowicz, "Short-horizon mean reversion in cryptocurrency markets" (2026)**,
  [arXiv:2608.21888](https://arxiv.org/abs/2608.21888). 183 Binance pairs vs 187 US stocks, strictly out of sample with a
  frozen six-month holdout: 90% of pairs show significant 15-minute directional reversal (2.7% of stocks), strongest
  after taker-driven bars; gross edge peaks near 1.3 bp per trade against a 5 bp round trip: detectable, not tradable.
- **Garfinkel, Hsiao, Hu, "Disagreement and returns: the case of cryptocurrencies", *Financial Management* 54(3)
  (2025)**, [IDEAS](https://ideas.repec.org/a/bla/finmgt/v54y2025i3p633-672.html). Abnormal volume predicts lower daily
  returns where short-selling is constrained; those states coincide with higher order imbalance.

### 4.2 Top traders vs the crowd
- **No academic study of exchange top-trader long/short ratios was found** (two searches; results were vendor pages
  such as sharpe.ai with no method). The lab's own R198 (top vs crowd, holdout t 2.72) is the best evidence we have.
- **Kang, Rouwenhorst, Tang, "A Tale of Two Premiums", *Journal of Finance* (2020)**: in commodity futures, short-term
  speculator position changes act as liquidity provision and earn a premium; the closest academic analogue for
  "who is on the other side of the crowd". (From memory of the paper; not re-read today.)
- **Kakhbod, Kazempour, Livdan, Schürhoff, "Finfluencers" (SFI WP 23-30, 2023)**,
  [SFI](https://www.sfi.ch/en/publications/n-23-30-finfluencers). StockTwits: 28% skilled (+2.6%/month abnormal),
  56% "antiskilled" (-2.3%/month), and the antiskilled have more followers; a contrarian strategy against them earns
  about 1.2%/month out of sample.

### 4.3 Funding, carry and basis
- **Schmeling, Schrimpf, Todorov, "Crypto carry", BIS WP 1087 (2023)**, [BIS](https://www.bis.org/publ/work1087.htm).
  Futures-spot carry averages above 10%/yr and reaches 60%; driven by trend-chasing small investors seeking leverage and
  scarce arbitrage capital; **high carry predicts future crashes**.
- **Borri, Liu, Tsyvinski, Wu, "Cryptocurrency as an investable asset class: coming of age" (2025-26)**,
  [arXiv:2510.14435](https://arxiv.org/abs/2510.14435). Carry (short perp, long spot, Binance BTC 2020-08 to 2025-05):
  Sharpe 6.45 full sample, 4.06 from 2024, **negative in 2025**; funding mean about 8%/yr. Matches the lab's R190/R191.
- **He, Manela, Ross, von Wachter, "Fundamentals of Perpetual Futures" (2022-24)**,
  [arXiv:2212.06888](https://arxiv.org/abs/2212.06888). No-arbitrage bounds for perps; crypto deviations are larger than
  in FX, co-move across coins and shrink as markets mature; a simple arbitrage has high Sharpe.
- **Ackerer, Hugonnier, Jermann, "Perpetual Futures Pricing" (2023-24, *Mathematical Finance*)**,
  [arXiv:2310.11771](https://arxiv.org/abs/2310.11771). Perp price = expected spot at a random time set by the funding
  anchor. Note: `docs/CONCEPTS.md` cites "Ackerer et al." with the link 2212.06888, which is He et al.; not edited here.

### 4.4 Intraday and weekly seasonality
- **Baur, Cahill, Godfrey, Liu, "Bitcoin time-of-day, day-of-week and month-of-year effects" (FRL 2019)**,
  [UWA](https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/).
  15 M observations, seven exchanges: effects vary over time, no consistent pattern.
- **Shen, Urquhart, Wang, "Bitcoin intraday time-series momentum", *Financial Review* 57(2) (2022)**,
  [doi:10.1111/fire.12290](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/).
  With a volume-defined day, the first half-hour return predicts the last half-hour return, strongest in high-volume
  and high-volatility sessions; attributed to liquidity provision.
- Practitioner: [Quantpedia](https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/)
  (Gemini hourly 2015-2022): best 22-23 UTC, worst 03-04 UTC; no significance test or costs (grade C). The lab's atlas
  found market clocks alone predict nothing (R185).

### 4.5 Copy trading, leaderboards and trader skill
- **Apesteguia, Oechssler, Weidenholzer, "Copy Trading", *Management Science* 66(12) (2020)**,
  [BSE](https://bse.eu/research/publications/copy-trading). Experiment: seeing others' success raises risk-taking, more so
  when copying is possible; copy trading leads to excessive risk.
- **Barber, Lee, Liu, Odean, "The cross-section of speculator skill: evidence from day trading", *J. Financial Markets*
  18 (2014)**, [IDEAS](https://ideas.repec.org/a/eee/finmar/v18y2014icp1-24.html). Taiwan 1992-2006: under 1% of day
  traders earn reliably positive returns net of fees, but the top 500 by last year's return earn 37.9 bp/day after fees
  the next year. Persistence exists, in a tiny tail.
- **Chague, De-Losso, Giovannetti, "Day trading for a living?" (2019)**, [SSRN 3423101](https://papers.ssrn.com/abstract=3423101).
  All Brazilian equity-futures day traders starting 2013-2015: 97% of those who persisted 300+ days lost money; about 1%
  earned more than the minimum wage.
- Exchange-sponsored claims (grade D): Bitget H1 2023 "93% of futures copiers profitable"; KuCoin "48-50% of followers
  profitable". **No independent study of crypto lead-trader persistence was found.**

### 4.6 Cross-sectional momentum and reversal
- **Liu, Tsyvinski, Wu, "Common Risk Factors in Cryptocurrency", *Journal of Finance* (2022)**,
  [NBER w25882](https://www.nber.org/papers/w25882). Market, size and momentum span the cross-section of coin returns
  (coins above USD 1 M cap, 2014-2018).
- **Liu and Tsyvinski, "Risks and Returns of Cryptocurrency", *Review of Financial Studies* (2021)**,
  [NBER w24877](https://www.nber.org/papers/w24877). Strong time-series momentum and investor-attention effects in BTC.
- **Dobrynskaya, "Cryptocurrency momentum and reversal", *J. Alternative Investments* 26(1) (2023)**,
  [HSE](https://www.hse.ru/en/news/research/559533243.html). Momentum positive up to two weeks, flat at two to four,
  reversal from four weeks; weekly rebalancing costs are large.

### 4.7 Books (takeaways from the books as I know them; not re-read today)
- **Bouchaud, Bonart, Donier, Gould, *Trades, Quotes and Prices* (CUP 2018).** Order-flow sign has long memory because
  large orders are split; impact is concave (square root of size) and mostly transient; prices are "marginally
  efficient": predictable flow does not give predictable returns unless you capture the transient part. For us: the
  72 h flow fade is a bet on the transient part of the crowd's impact; size it by the square-root law.
- **Harris, *Trading and Exchanges* (OUP 2003).** Trading is zero-sum before costs; know who loses to you (utilitarian
  traders, hedgers, impatient retail). Informed traders, dealers and order anticipators each have a known edge and
  failure mode; the spread pays for adverse selection. For us: our counterparty in a crowd fade is the leveraged
  crowd paying funding.
- **López de Prado, *Advances in Financial Machine Learning* (Wiley 2018).** Backtest overfitting is the main failure;
  use purged and embargoed cross-validation, sample-uniqueness weights for overlapping labels (our 72 h slices overlap),
  triple-barrier and meta-labelling, the deflated Sharpe ratio and trial counts. The lab already uses DSR and CSCV.
- **Chan, *Algorithmic Trading* (Wiley 2013).** Test mean reversion with ADF, Hurst and half-life; futures momentum is
  largely roll yield (funding is crypto's roll yield); stop-losses suit momentum and hurt mean reversion; size with
  Kelly but expect regime breaks.
- **Narang, *Inside the Black Box* (Wiley, 2nd ed. 2013).** A system is alpha model + risk model + transaction-cost
  model + portfolio construction + execution; alpha types are trend, reversion, yield (carry), growth and quality.
  Much of the edge is implementation and costs; regime change and crowding (the 2007 quant crash) are the main risks.

### 4.8 Adaptation, drift and portfolio selection
- **Gama, Žliobaitė, Bifet, Pechenizkiy and Bouchachia, "A survey on concept drift adaptation" (2014)**,
  [*ACM Computing Surveys*](https://doi.org/10.1145/2523813). A taxonomy of abrupt, gradual, recurring and incremental
  drift, plus the distinction between detection and adaptation. It is a methods survey, not evidence that a crypto
  return process has a detectable drift regime.
- **Bifet and Gavaldà, "Learning from time-changing data with adaptive windowing" (2007)**,
  [*SDM*](https://doi.org/10.1137/1.9781611972771.42). ADWIN-style windows compare recent and older data while
  adapting the window length. Any use here would need a frozen threshold, an outcome-availability delay and a
  turnover/cost audit.
- **Tashman, "Out-of-sample tests of forecasting accuracy" (2000)**,
  [*International Journal of Forecasting*](https://doi.org/10.1016/S0169-2070(00)00065-0), and **Pesaran and
  Timmermann, "Selection of estimation window in forecasting" (2007)**,
  [*Journal of Econometrics*](https://doi.org/10.1016/j.jeconom.2006.03.010). Rolling-origin evaluation and
  past-only window selection are the relevant safeguards when relationships change.
- **Giacomini and White, "Tests of Conditional Predictive Ability" (2006)**,
  [*Econometrica*](https://doi.org/10.1111/j.1468-0262.2006.00718.x). A framework for evaluating forecasts selected
  from information available at the time; useful for a policy that switches among frozen candidate streams.
- **Koop and Korobilis, "Forecasting inflation using dynamic model averaging" (2012)**,
  [*International Economic Review*](https://doi.org/10.1111/j.1468-2354.2012.00704.x), and **Freund and Schapire,
  "A decision-theoretic generalization of on-line learning" (1997)**,
  [*Journal of Computer and System Sciences*](https://doi.org/10.1006/jcss.1997.1504). Dynamic weights and
  expert-regret methods are comparison families; their guarantees do not imply positive net crypto returns.
- **Li and Hoi, "Online portfolio selection: A survey" (2014)**,
  [*ACM Computing Surveys*](https://doi.org/10.1145/2512962). Online-selection families differ
  in memory, switching and transaction-cost treatment. The survey supplies comparison methods, not crypto-perpetual
  performance evidence.
- **Meta-labeling evidence:** a 2026 futures preprint reports near-chance AUC and no paired-bootstrap interval
  excluding zero across five contracts ([study](https://doi.org/10.2139/ssrn.7356724)); a 2025 BTC/ETH study using
  triple-barrier labels reports after-cost results on two liquid assets ([study](https://doi.org/10.1186/s40854-025-00866-w)).
  Neither validates an altcoin-perpetual filter here.
- **Wang and Pang, "Predictability on the Move: The Cryptocurrency Cross-Section" (October 2026 preprint)**,
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7556359). The abstract reports different selected
  signals in rolling windows and none selected by its full-sample StepM threshold. It is preliminary and does not
  settle persistence for this repository.

### 4.9 Venue/API operations
- **MEXC API FAQ and futures documentation:** the API connects directly to live trading and has no sandbox; order
  submission, external-ID reconciliation, open-position queries, cancel-all controls, depth versions and sequence-gap
  recovery are documented in the [API FAQ](https://www.mexc.co/mexc-api), [batch order endpoint](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/batch-place-order),
  [external-ID query](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-order-by-external-id),
  [open-position endpoint](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-open-positions),
  [cancel-all endpoint](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/cancel-all-orders-under-a-contract),
  [depth stream](https://www.mexc.co/api-docs/futures/websocket-api/order-book-depth) and [book-maintenance procedure](https://www.mexc.co/api-docs/futures/websocket-api/incremental-order-book-maintenance-mechanism).
  These are interface rules, not evidence of fill quality, uptime or private-account behavior.

## 5. Scrapeable data beyond the Binance archive

| Source | URL pattern (tested) | History | What it adds |
|---|---|---|---|
| Binance copy trading | `bapi/futures/v1/.../query-list`, `lead-data/positions`, `position-history` | live; closed positions about 4.5 months | trader-level positions (the archive has only aggregate top-trader ratios) |
| Binance futures/data, fapi | `/futures/data/*`, `/fapi/v1/*` on www.binance.com | 30 days; live | near-real-time copies of archive metrics (for forward tests); live funding interval changes |
| OKX Rubik | `/api/v5/rubik/stat/...` | top-trader ratios about 55-60 days hourly; taker volume at least 1 year | a second venue's top-trader and taker data, for replication |
| OKX copy trading | `/api/v5/copytrading/public-*` | daily PnL 1 year; positions history | about 260 lead traders with instruments |
| Gate | `https://api.gateio.ws/api/v4/futures/usdt/contract_stats?contract=BTC_USDT&interval=1h&from=` | **180 days hourly** (older: "from time exceeds 180-day limit") | **long/short liquidation size and USD**, top-trader account and size ratios, taker sizes, OI: the only liquidation history found |
| Bitget | `/api/v2/mix/market/*-long-short`, `taker-buy-sell` | last 30 hours | live-only third venue |
| Hyperliquid | leaderboard, vaults, `/info` | on-chain; funding from 2023-05 | verifiable trader-level PnL, positions and fills |
| Deribit | `https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=3600` | hourly DVOL from 2021 (1,000 rows per call, paginate) | implied-vol regime; options book summary |
| Coinbase | `https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600&start=&end=` | hourly back to 2015 (300 per call) | US spot premium |
| MEXC (owner's venue) | `https://contract.mexc.com/api/v1/contract/{kline/BTC_USDT?interval=Min60, funding_rate/history, detail, ticker}` | hourly klines back to 2022; funding about 540 days (BTC 1,620 rows) | the venue we would trade; a guessed copy-trading path returned 404 |
| dYdX v4, Kraken Futures | `indexer.dydx.trade/v4/...`, `futures.kraken.com/derivatives/api/v3/tickers` | not explored | 200 only |
| Binance archive, unused parts | `data/option/daily/{BVOLIndex, EOHSummary}`, `futures/um/{daily,monthly}/bookTicker` (BTC from 2023-05), `trades`, `aggTrades` | - | aggTrades/trades are large: owner's yes needed |

**Could not access or verify:** Instagram (login wall), Bybit (CloudFront geo-block 403), Breakout and Apex sites (403),
Topstep's pricing page and the Combine profit-target table (third-party figures used, marked), HyroTrader per-size
prices and max-drawdown type, Crypto Fund Trader prices (rendered by script), FTMO's crypto list and leverage,
any personal track record for Tarek El Marhri, Hyperliquid's historical S3 archive (not tested), and rate limits
other than Binance's stated 2,400 weight per minute.
