# Public trading-video intake (2026-10-20)

This is a compact source digest, not a transcript archive or evidence of profitability. The detailed source-by-source
methods and tested/open scopes are in [`source_methods_20261020.json`](../research/intake/source_methods_20261020.json)
and map to the single live queue, [`registry/methods.csv`](../registry/methods.csv). The previous two Instagram reels
remain represented below; their source version is preserved in Git history (SHA-256 before this digest:
`24cf420675d3c1aadc112c65222f1ecd23434729d9d95146281b650268749859`).

No raw video, audio, market data or model weights were committed or downloaded. Speech is paraphrased, never presented
as a verbatim transcript. Captions, summaries and descriptions are identified separately because several pages did
not expose a transcript.

## Owner-provided clips

| Source | What was accessible | Distinct leads retained | Main gaps |
|---|---|---|---|
| [Git Radar Instagram reel](https://www.instagram.com/reel/DcOhWbqm3vK/) | Speech and caption summary from the prior intake | Deterministic backtest/paper/live engine parity; NautilusTrader as an execution tool | No edge rule; M029/M088 are related engineering checks |
| [Filip Gajko Instagram reel](https://www.instagram.com/reel/DcgZhLyiZ3o/) | Music and title card only; repository names were inferred, not spoken | Six-role tool-stack claim only | No named tools in the media and no trading rule; inference is not source fact |
| [TikTok: “08/06 — Trade Recap 100 points from GEX 715 QQQ”](https://www.tiktok.com/@aleks_rosme/video/7670945661621128470) | Public caption/title; no public speech-caption track found | One title-only GEX-level claim | No level construction, entry/exit, contract, costs or verified P&L |
| [TikTok: 3D volatility surface](https://www.tiktok.com/@aleks_rosme/video/7698695375250623766) | Creator-provided English caption track | Sell relatively rich IV and buy relatively cheap IV; use strike/expiry surface and Greeks for pricing/hedging | Pairing, delta/tenor, richness threshold, vol model, hedge, timing and costs absent |
| [TikTok: QQQ 713 GEX reclaim](https://www.tiktok.com/@aleks_rosme/video/7698764847109999894) | Creator-provided English caption track | QQQ GEX reclaim/retest with call-heavy premium, bullish order-flow, daily value-area-low context; SPX gamma/put-spread context | GEX source/sign, premium/flow definitions, contract, trigger, risk and execution absent |

The two TikTok caption tracks are summarized in new words; the first clip's “100 points” and the third clip's “6R” are
creator claims, not independently checked outcomes. Components of the QQQ setup are kept as separate intake records but
mapped to one composite queue row; the value-area-low component is related to M207, not the same standalone VWAP rule.

## Additional public video leads

### Follow-up: Aleks Rosme account request

The owner later supplied the [whole TikTok profile](https://www.tiktok.com/@aleks_rosme). The profile was inaccessible;
a bounded YouTube channel-metadata request also failed with proxy 403. No new speech transcript or exhaustive list of
posts was obtained. The three clips above remain the directly received TikTok scope. Third-party repost captions and
video-title listings are discovery leads only; viewer comments are not creator rules or performance evidence.

His [official site](https://www.aleksrosme.com/) links a [Net Drift guide](https://www.youtube.com/watch?v=xzoQc4lWAkA)
and affiliate tools Quant Data and Deepcharts. Eight follow-up records `AR26-*` retain these distinctions:

| Received material | Retained scope / existing queue |
|---|---|
| [Quant Data Net Drift documentation](https://help.quantdata.us/en/articles/9900974-mastering-the-net-drift-tool-leveraging-order-flow-sentiment-for-smarter-options-trading) | Crossover, convergence/divergence and volume-confirmation components relate to M235; these are vendor applications, not newly verified Aleks rules. Filters, midpoint uncertainty and multi-leg treatment matter. |
| [Quant Data GEX guide](https://help.quantdata.us/en/articles/15807345-gamma-exposure-gex-api-python-quickstart-dealer-positioning-guide) | Model signing and snapshot/intraday distinction: context for M235/M175. GEX is estimated positioning, not observed dealer inventory. No authenticated feed accessed. |
| [Deep Print settings](https://www.deepcharts.com/helpcenter/article/deep-print-%28footprint%C2%AE%29) | Tick grouping, bid/ask volume and profile settings: context for M238/M207. These capabilities supply neither his thresholds nor an automatic absorption strategy. |
| [2024 Starter Strategy](https://aleksrosme.gumroad.com/l/strategy) | Indexed brochure specifies M15 entry, H1 area and 2R. Actual rule file unavailable; no definition of area, entry or stop. CONTEXT, related timeframe idea M022 only. |
| [Trades Journal](https://aleksrosme.gumroad.com/l/journal) and official tool directory | Workflow/tool context. Journal features, dark-pool labels, replay and copier listings do not establish additional executable rules or a track record. |

Assessment: retain the options/flow composite as an unresolved lead. MEXC hourly candles cannot reproduce US-options
premium or price-level footprint data. A crypto adaptation would be a separate rule, with its own data and frozen
test; weak or incomplete source ideas remain retained. No strategy outcomes, costs or profits were computed here.

| Source | Transcript basis | Extracted methods / queue mapping |
|---|---|---|
| [SPX 0DTE: Gamma Zero, order flow and key levels](https://www.youtube.com/watch?v=E_PSlPIq0R4) | Public description/chapter summary; no full transcript verified | Prior-session/Asia/London levels with Gamma Zero/Call/Put walls; order-flow confirmation; SPX 0DTE spread scalping. New M235/M237; flow component M238. |
| [Cboe: volatility, dispersion and 0DTE pricing](https://www.cboe.com/video/ldjz4jorjd/) | Official editorial summary, not a transcript | Option dispersion / correlation-risk lead. The separate Cboe paper specifies short SPX ATM straddles and long component ATM straddles; preserve legs rather than relying on the “long dispersion” label. M236. |
| [SPX/SPY GEX and options-flow video](https://www.youtube.com/watch?v=SkvitOO2Zog) | Description only; promotional, no verified transcript | GEX walls/flip plus options-flow direction; related component of M235, with no independent outcome evidence. |
| [Hummingbot Botcamp Cohort 7 demo](https://hummingbot.org/blog/hummingbot-botcamp-cohort-7-demo-day-recap/) | Official written recap of nine student demos | Spot/perp carry; cross-sectional momentum; liquidation rebound; multi-horizon trend/reversion; Uniswap V3 range LP; Avellaneda–Stoikov market making; VWAP-band reversion; CEX/DEX market making; Bollinger perp reversion. Existing matches include M034/M058/M134/M140/M176/M207; open variants are M242/M243/M245/M246. No strategy P&L is reported. |
| [Hummingbot Bot Pod Ep. 8](https://hummingbot.substack.com/p/the-bot-pod-episode-8-demo-day-highlights) | Official transcript/highlights, 2026-05-22 | Cross-venue perp price/funding spread with progressive entry (M241); stochastic market making at touch (M058); portfolio TP/SL and inventory hold (context); passive limits to catch thin-market price errors (M240). The MM demo's roughly flat P&L is a speaker anecdote, not an audited track record. |
| [Hummingbot Bot Pod Ep. 7](https://hummingbot.substack.com/p/the-bot-pod-episode-7-deep-dive-into) | Official transcript/highlights, 2026-05-16 | Executable depth/fee arbitrage vs passive maker-plus-hedge (M239/M240); Solana concentrated-liquidity selection by fee/TVL (M242). The examples are not independently verified. |
| [Hummingbot funding-rate arbitrage video](https://www.youtube.com/watch?v=Ly8R5g3juxw) | Public listing, no transcript verified | Short higher-funding venue and long lower-funding venue; maps to existing M059. Hummingbot's official implementation is a useful mechanics reference, not performance evidence. |
| [Deribit dated-futures cash-and-carry](https://www.youtube.com/watch?v=rp4dOTW2TNU) and [official written walkthrough](https://insights.deribit.com/education/cash-carry-live-trade-example/) | Official written walkthrough | Long spot/short dated future, close near convergence or roll; M244, related to M047/M134/M170. |
| [Deribit variable-rate cash-and-carry](https://www.youtube.com/watch?v=BSWVZJ703Mg) and [official written walkthrough](https://insights.deribit.com/education/variable-rate-cash-carry-live-trade-example/) | Official written walkthrough | Long spot/short perp; funding varies, exit after adverse funding persists, maintain the hedge as size changes; related to M134. |
| [TradingLab: order-flow reversal](https://www.youtube.com/watch?v=ljk9BovCSqI) | Secondary transcript summary only; Tesla example | Zone retest plus footprint imbalance, absorption, initiation and CVD divergence; portability and precise execution unverified. M238. |
| [Krypto Káy: liquidation heatmap tutorial](https://www.youtube.com/watch?v=F8YFm-xg5bs) | Description only | Use estimated liquidation zones for entries/exits; related to tested/blocked M069/M070/M140/M176, not evidence of a new edge. |
| [Prop-firm pass-probability video](https://www.youtube.com/watch?v=R0tNSiUQ-Q8) | Video plus creator transcript page | Score path-dependent pass probability under the actual firm's target, drawdown and consistency rules; maps to M028/M199/M211. Rule claims need dated official firm terms. |

The method IDs, source versions, exact scope, existing tested scope, aliases and missing mechanics for these leads are
preserved in the intake JSON and alias CSV. The queue additions are all unresolved; no backtest or result is claimed.

## Second discovery batch (2026-10-20)

Three read-only agents and a targeted web pass added 39 public sources. They are catalogued in the intake JSON with
source version/date, accessible basis, exact lead, queue alias and missing mechanics; no media was saved. This batch
contains leads, not a new search universe or performance evidence.

| Lane | Sources and extracted rule families | Queue treatment and gaps |
|---|---|---|
| Options / 0DTE | [Saint Trader 0DTE flow](https://www.youtube.com/watch?v=ez7KBOsEpaQ), [Geeks of Finance GEX](https://www.youtube.com/watch?v=_0jd6CMyk9s), [Option Alpha's four GEX profiles](https://optionalpha.com/videos/gamma-exposure-strategy-4-gex-profiles-for-spx-0dte-day-trading), and OIC/CME videos on [skew](https://www.optionseducation.org/videolibrary/volatility-ii-understanding-options-skew), [parity](https://www.optionseducation.org/videolibrary/theoretical-option-pricing), [volatility](https://www.optionseducation.org/videolibrary/volatility-strategies), [gamma by DTE](https://www.optionseducation.org/videolibrary/gamma-as-a-function-of-time), and [post-earnings IV](https://www.optionseducation.org/videolibrary/implied-volatility-and-post-earning-volatility-risk). | GEX profiles remain aliases of M235/M237; skew and IV-surface value map to M234; parity/reverse conversion is new M248; IV-percentile/event-vol structures are new M249. All still lack finite strikes, thresholds, timing, hedge, fills and costs. |
| Crypto / execution | [Binance arbitrage transcript](https://www.dailymotion.com/video/x9r8n9k) and [second triangular-arb transcript](https://www.dailymotion.com/video/x9r8q52), [liquidation heatmap video](https://www.youtube.com/watch?v=qFwvTRATC-c), [Bybit funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate), [Bybit order book](https://bybit-exchange.github.io/docs/v5/market/orderbook), and Hyperliquid's [funding](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding) and [perpetual API](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals). | Same-venue triangular arbitrage is new M247. Cross-venue gaps, liquidation levels, funding clocks, oracle accounting, book-depth controls and market-making simulator ideas map to M239/M240/M059/M134/M241/M058/M227. No source supplies synchronized fills, queue, latency or costed P&L. |
| Systematic / prop | QuantConnect examples for [trend/carry regimes](https://www.quantconnect.com/research/15989/futures-trend-following-and-carry-in-different-risk-regimes/), [adaptive allocation](https://www.quantconnect.com/research/16041/trend-and-carry-allocation/), [synthetic-spot trend](https://www.quantconnect.com/research/16014/futures-spot-trend/), [joint roll/momentum](https://www.quantconnect.com/research/15359/momentum-effect-combined-with-term-structure-in-commodities/), and [Dual Thrust](https://www.quantconnect.com/research/15258/dual-thrust-trading-algorithm/); [CME spread mechanics](https://www.cmegroup.com/education/courses/understanding-futures-spreads/futures-spread-overview); and Pura Vida's [eight-portfolio video](https://puravidaedge.com/videos/systematic-prop-firm-trading-8-portfolios/) and [post-payout buffer transcript](https://puravidaedge.com/videos/drawdown-buffer-after-first-payout/). | Explicit volatility multiplier and adaptive weights are aliases of M035/M184; synthetic-spot trend is new M250 and joint roll/momentum is new M251. Dual Thrust, spread execution and prop state machines map to existing M205/M170/M211. Reported returns are creator/backtest claims, not project results. |

The batch also records the official Bybit/Hyperliquid/Binance funding mechanics, an [Avellaneda–Stoikov order-book
simulator](https://github.com/harshitgrover/Order_Book_Simulator), [funding-rate paper-trading code](https://github.com/TiwariSudhanshu/Funding-Rate-Arbitrage),
and primary funding/risk explanations from [Kraken](https://www.kraken.com/in/learn/futures-trading-funding-rate-arbitrage)
and [VoiceOfChain](https://voiceofchain.com/academy/funding-rate-chart-binance). These are implementation or accounting
leads; they do not establish a MEXC edge. The full 34-record extraction and 39-source list, including weak generic arbitrage videos and
their limitations, remains in the JSON so they are not silently discarded.

## Primary-source checks

- [Cboe volatility surfaces](https://datashop.cboe.com/volatility-surfaces) index IV by expiry and strike/delta; the
  surface product is not among the project's held inputs. A surface is calculated from option prices, so it does not
  replace the underlying option quotes.
- [OIC/OCC options FAQ](https://www.optionseducation.org/referencelibrary/faq/general-information): open interest
  pairs long and short contracts and does not, by itself, reveal which side opened or dealer direction. Treat GEX
  positioning as a vendor/model estimate, not observed intent.
- [Cboe's SPX 0DTE analysis](https://www.cboe.com/insights/posts/volatility-insights-evaluating-the-market-impact-of-spx-0dte-options/)
  reports no discernible market impact in its studied sample; this cautions against treating GEX levels as forced price
  magnets, but does not test the videos' exact rules.
- [MEXC contract API docs](https://mexcdevelop.github.io/apidocs/contract_v1_en/) document public funding-history and
  current contract data endpoints. Documentation does not establish usable historical coverage or order-book fills;
  no data was downloaded in this intake.
- Hummingbot's [funding-arbitrage reference script](https://github.com/hummingbot/hummingbot/blob/master/scripts/v2_funding_rate_arb.py)
  and [release note](https://hummingbot.org/release-notes/1.27.0/) demonstrate an implementable cross-venue signal
  pattern, not a profitable result.

All media-derived ideas remain leads. Historical examples, demo rankings, captioned R-multiples, and promotional
statements are not validated returns. Any study still needs a finite frozen rule, appropriate controls, executable
prices, and 1x/2x/3x costs before outcomes are read.

## MEXC mechanics follow-up: finite proposals, not results

Seven official pages support six `XM26-*` records in the existing bundle. These rules are **our unregistered
proposals**, not exchange recommendations. No outcome, market download or synthetic implementation is claimed. Three distinct scopes have canonical BLOCKED
rows M280–M282; other controls retain existing parents/context. Related does not mean exactly tested.

| Source mechanics | Proposed bounded work / relationship |
|---|---|
| [MMR adjustment](https://www.mexc.com/announcements/article/mexc-will-adjust-maintenance-margin-rate-for-mu-sndk-and-19-usdt-m-futures-jul-3-17827791536452) and [leverage-only cut](https://www.mexc.com/en-GB/announcements/article/maximum-leverage-adjusted-for-cvcusdt-futures-sep-13-2026-14-17827791538535) | Separate the events: the former can change existing-position liquidation exposure; the latter does not prove forced selling. Proposed first-seen-notice short, 24-hour exit, opposite-sign and unaffected-coin controls; new M280, related M079/M209. |
| [Tick-size change](https://www.mexc.com/announcements/article/tick-size-adjustment-for-gold-xaut-usdt-ctusdt-and-ckbusdt-futures-pairs-17827791539119) | Hold an existing reversal signal fixed and compare executable net around the change. Old orders retain their original grid. Related M058/M232/M240; books and fill modeling required. |
| [Trigger-order FAQ](https://www.mexc.com/support/article/mexc-futures-trigger-order-faqs-318924677761021952) | Compare the same 15% cover under last/fair/index triggers, executing on the book. Relevant to Claude's remote M261; no dangling M261 alias is added to this branch. |
| Trigger FAQ, leverage notice, [price-protection definition](https://www.mexc.com/en-GB/learn/article/quick-guide-to-futures-information-terminology-and-trade-futures-with-confidence/2) | Build synthetic triggered/submitted/partial/filled/rejected states; retain exposure until a fill. Cover gaps, margin, disabled trading and changed-leverage rejection. Protective-order activation does not ensure execution. |
| [Index/fair/last FAQ](https://www.mexc.com/support/article/faq-on-index-price-fair-price-and-last-price-7950960183961) | Related M173 variant: gate dislocation entries on recorded constituent/source health, versus identical ungated rules. Unknown source state stays unknown; current weights cannot reconstruct history. |
| [IN funding-frequency notice](https://www.mexc.com/announcements/article/adjustment-to-inusdt-funding-rate-settlement-frequency-jul-1-2026-18-17827791536624) | Transport the already chosen Binance candidate to prospective MEXC notices, without a new horizon search; normalize actual intervals/caps. This is not another generic funding study. |

The IN page displays **July 2 publication but July 1 effectiveness**. An entry at effective time would precede its
displayed publication date; prospective local first-seen time must govern availability. The general trigger FAQ also
describes fair price loosely; the dedicated price FAQ supplies the formula. Neither marketing language nor a
displayed last price proves an executable fill. Mutable page versions and actual excerpt scope are identified in
the supplement; original HTML was not archived. Full rules, eligibility, controls and 1x/2x/3x costs must be frozen
before any new strategy outcome.

These three distinct scopes are retained as BLOCKED canonical rows M280 (margin notices), M281 (tick-size execution) and M282 (funding-notice venue transport). Trigger/rejection controls and index-state variants retain existing parent relationships; no study was run.

## Strategy-library and data-source follow-up

The existing provider catalog now includes ten additional entrypoints: QuantConnect's strategy library, Research
and Tutorials repositories; QuantInsti Blueshift demos; Financial Hacker; QuantStart; Robot Wealth; Open Source
Asset Pricing; Kenneth French's factor library; and QuantPad. Catalog access is not full strategy extraction.
Public examples, subscription workspaces and derived factor data have different reuse/data-access boundaries.
QuantStart's direct pages returned 502; its scope remains indexed metadata. QuantPad's official site establishes
platform capabilities and a subscription library, not possession of that library or verified MEXC coverage.

One [pinned official Dynamic Breakout II Method](https://github.com/QuantConnect/Tutorials/blob/4a341890296f7e79e095508f06170c72ccaa629c/04%20Strategy%20Library/04%20The%20Dynamic%20Breakout%20II%20Strategy/02%20Method.html)
was read separately: adaptive 20–60-day lookback, channel plus Bollinger confirmation, moving-average exit. It is
retained as M283 with source commit/blob/hash. Prose says 30-day volatility while the snippet uses the adaptive
window from 31 requested observations; full indicator updates, sizing and execution were not received. This is
a BLOCKED composite lead, not a tested rule or a replication of an existing fixed-window indicator result.


A pinned third-party [Backtrader reproduction](https://github.com/letianzj/QuantResearch/blob/79bbf6a8b5ad74ac2c165663b5e12eb70d76a54e/backtest/bt/dynamic_breakout_ii.py) was then read in full (commit `79bbf6a8`, blob `c581f127`, SHA-256 `04c09f26…7d2a`), strictly as a code-fidelity check. It is not official QuantConnect code. Its volatility update `(today_std / yesterday_std) / today_std` simplifies to `1 / yesterday_std`, so it is not a relative volatility change; the Donchian comparisons are commented out, leaving close-versus-Bollinger entries. The driver names a Yahoo SPX CSV for 2010–2019 and 0.1% commission, but no run output or data was received. M283 remains BLOCKED: this derivative does not resolve the official Method's 30-day versus adaptive-N/history-window conflict. No outcomes or tests were run.
