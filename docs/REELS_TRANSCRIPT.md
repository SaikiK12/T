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
