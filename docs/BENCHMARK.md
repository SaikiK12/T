# Benchmark: the lab against the best open-source quant projects and free data (2026-10-20)

The owner asked for the best in each area, measured against what others build. Each row names the leader, what it does
better than the lab, and what the lab builds to pass it. Facts about other projects come from their READMEs and
docs, read on 2026-10-20 (sources at the end). Claims about the lab were checked in this repo the same day.

## Summary
- **Ahead of every open-source project read here: research honesty.**
  - Frozen pre-registration, a reality check per family, program-wide trial counting (9,477,741 trials) and reserved
    unread samples.
  - Freqtrade's hyperopt, vectorbt sweeps and RD-Agent's factor loop report the winner of a search without
    correcting for the search. RD-Agent's "about 2x higher annual return than factor libraries" is a claim of that
    kind.
- **Behind:**
  - **Performance views.** quantstats has 63 metrics, 17 plots and an HTML tear sheet; FreqUI shows profit charts. The
    control room has tables and two charts, but no equity curve, drawdown or monthly heatmap.
  - **Engine breadth.** NautilusTrader and hftbacktest simulate order books, queues and latency. `qx` prices
    hourly-close event legs only.
  - **Venue breadth.** NautilusTrader has 12 crypto adapters.
- **Data:** the lab already holds more derivative data types than any free tool read here. The gap is venues and the
  delisted long tail, which the Gate archive closes (below).

## Scorecard
| Area | Leader (what it has) | The lab now | Build (status) |
|---|---|---|---|
| Multiple-testing control | None of the frameworks read. Academic tools only: White's RC, Hansen's SPA, DSR / PBO (López de Prado). | Frozen PREREG, RC per family, matched nulls, program trial count, reserved 2020 and MEXC-only samples. | Keep. Show it: an honest leaderboard (each family's best t against its own null 95th percentile). **Built 2026-10-20.** |
| Performance tear sheet | quantstats: CAGR, Sharpe, Sortino, Calmar, drawdown details, VaR / CVaR, tail ratio, profit factor, Kelly, risk of ruin, Monte Carlo; plots of drawdown, monthly heatmap and rolling Sharpe / volatility. pyfolio: similar, plus turnover. | Per-strategy t, halves, 1x / 2x / 3x cost. No curves. | `lab/tearsheet.py`: quantstats' core metrics plus a deflated Sharpe at the program's trial count. Every forward lane and saved research stream on the control room. **Built.** |
| Live bot view | FreqUI: open and closed trades, profit per pair, daily and cumulative profit, backtest comparison, multi-bot. | Forward lanes, event tickets, on-time days. | Equity and drawdown per forward lane (with the tear sheet). |
| Automated research loop | RD-Agent(Q): an LLM proposes factors, codes them, runs them on Qlib and learns from the metrics. A trace UI shows each loop. | The hourly loop (Claude) plus the registry. There is no trace view. | Leaderboard plus the rounds table as the trace: hypothesis (method), family size, best t, null, verdict. A family is a `qx` spec, not new code. |
| Factor analytics | Qlib: Alpha158 / Alpha360 feature sets, IC and rank IC, group returns, model zoo. alphalens: IC decay, quantile spreads, turnover. | Atlas and screens; no reusable IC / quantile / turnover report. | Next: an alphalens-style factor report in `qx` cross-sections (the owner's "cross-sections in Rust"). |
| Backtest engine | NautilusTrader: Rust core, nanosecond events, L2 / L3 books, the same code in backtest and live. hftbacktest: queue position and latency models. vectorbt: vectorized sweeps. | `qx` (Rust): event families, hourly closes, funding, covers, cluster bootstrap RC. Python engine for daily books. | Next: cross-sectional books and intrabar (high / low) stops in `qx`. Later: a maker queue model for MEXC's 0-fee maker side (R193 showed adverse selection). |
| Venue adapters | NautilusTrader: Binance, Bybit, Coinbase, Deribit, Kraken, OKX, dYdX, Hyperliquid and others. ccxt: 100+ exchanges over REST. | Binance archive; MEXC, Gate, Hyperliquid, Deribit and Coinbase clients. Binance and Bybit live APIs are blocked from this container (HTTP 451 / 403). | A cross-venue funding recorder over the reachable venues (MEXC, Gate, Hyperliquid, OKX, Bitget, dYdX). **Built.** |
| Ops monitoring | Grafana-style job and data health; Hummingbot's dashboard was retired for Condor. | Jobs (structured plus running processes), data inventory, disk. | Data coverage timeline per source. **Built.** |

## Data: what the lab holds against free sources
**Held (2026-10-20):**
- **Binance archive, 2020-2026:** hourly klines with taker volume, metrics (open interest and top-trader ratios),
  premium index, funding and book depth.
- **Binance spot and COIN-M:** spot klines and COIN-M dated futures (basis).
- **Other venues:**
  - MEXC full history (607 contracts);
  - Hyperliquid funding and candles;
  - Gate 180-day contract stats;
  - Deribit;
  - Coinbase.
- **Events and recorders:** the DefiLlama unlock calendar, Binance notices, and the live recorders (MEXC funding and
  open interest, depth, notices, unlocks).

**Added on 2026-10-20: Gate's public bulk archive** (`scripts/fetch_gate_history.py`).
- **What:** hourly candles and every funding settlement for every Gate USDT perp from 2020, **delisted contracts
  included.** The S3 listing has 1,000+ contracts a month in 2026, against 81 in January 2021.
- **Why it matters:**
  - It is the widest and least survivorship-biased cross-section the lab has.
  - It is a second venue's funding for every Binance coin.
  - Coins Binance never listed form a fresh, unread sample.
- **Reserved routing:** 2020 rows and every coin with no Binance perp go to `data/gate_hist/reserved/`. GATES rules
  apply to that folder.

**Reachable and free, not yet fetched (probed 2026-10-20):**
| Source | What | Access | Value |
|---|---|---|---|
| Gate archive, other types | `funding_updates` (per-minute rate and premium), `mark_prices`, `orderbooks`, `trades`, 1m / 5m candles | S3, public | High for microstructure. Large: fetch per question. |
| Bybit public archive | Tick trades per perp per day since 2020; premium and spot index | public.bybit.com | Taker flow on a second venue. TB-scale in full: fetch per question. |
| OKX | Daily trades / aggTrades (static CDN); 1h candles, open interest history and 3 months of funding (API v5) | Public | A third major venue. Funding beyond 3 months only by recording forward, which the funding recorder now does. |
| Bitget, KuCoin, dYdX v4 | Funding history and candles | Public APIs | More venues for cross-venue funding. |
| DefiLlama | Stablecoin supply by chain, CEX reserves, protocol fees, DEX and perp-DEX volumes | Public API | Flow and macro features (daily). |
| Binance Vision | Options BVOL index and end-of-hour summary; COIN-M liquidation snapshots from 2023-06; mark and index klines | Public | Implied vol for BTC / ETH; liquidations for COIN-M only. |
| alternative.me, FRED, Polymarket | Fear & Greed since 2018, US rates / dollar / VIX, prediction-market odds | Public | Regime features. |
| CoinGecko / CoinPaprika | Market caps (365 days on the free tier) | Public | Size factor. Record forward for history. |

**Not free:**
- Aggregated cross-exchange liquidations and open interest history: CoinGlass and Coinalyze (Coinalyze needs a key,
  none in this container), Velo, Kaiko, Amberdata.
- Full tick data: Tardis gives the first day of each month free.
- The lab builds its own aggregates from the venues above instead.

## Build order (from this benchmark)
1. **Gate bulk archive.** Fetch, build, provenance. **Done 2026-10-20:** 861 open contracts, 758 reserved
   (`docs/provenance/gate_hist.json`).
2. **Control-room performance views:**
   - tear sheets per forward lane and research stream;
   - the honest leaderboard;
   - the data coverage timeline.

   **Done 2026-10-20**: the Performance, Leaderboard, Funding board and Coverage views of the control room.
3. **Cross-venue funding recorder:** an hourly snapshot of every venue's current and predicted funding, as a journal
   and a control-room board. It starts the point-in-time history that APIs do not keep. **Done 2026-10-20**
   (`scripts/record_funding_board.py`, hourly). Its first use is R275, a cross-venue funding carry family on
   `qx spread`.
4. **`qx` cross-sections:** a factor report in the alphalens / Qlib style (IC, rank IC by horizon, quantile spreads,
   turnover) and cross-sectional books, so a cross-sectional family is one spec.
5. **Free data, small first:** DefiLlama, alternative.me, FRED, Binance BVOL, then OKX / Bitget / KuCoin / dYdX
   history. **DefiLlama, alternative.me and FRED done 2026-10-20** (`scripts/fetch_macro.py`, 20 daily series).
   DefiLlama's derivatives and bridge charts are paid. Binance BVOL is next; Deribit DVOL is already held.

## Sources
- [microsoft/RD-Agent](https://github.com/microsoft/RD-Agent) and [R&D-Agent-Quant, arXiv 2505.15155](https://arxiv.org/html/2505.15155v2)
- [microsoft/qlib README](https://github.com/microsoft/qlib/blob/main/README.md)
- [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats)
- [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader)
- [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest)
- [freqtrade/frequi](https://github.com/freqtrade/frequi)
- [Hummingbot dashboard docs](https://hummingbot.org/dashboard/)
- [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant)
- [TradingAgents (TauricResearch) overview](https://dev.co/ai/frameworks/tradingagents)
- [Gate historical data announcement](https://www.gate.com/announcements/article/21688)
- [Tardis.dev OKX data docs](https://docs.tardis.dev/historical-data-details/okex-swap)
- [bybit-bulk-downloader](https://github.com/aoki-h-jp/bybit-bulk-downloader)
- Probed directly with HTTP on 2026-10-20: public.bybit.com, gateio-public-data (S3), static.okx.com, OKX API v5,
  api.bitget.com, indexer.dydx.trade, data.binance.vision, api.llama.fi, api.alternative.me, FRED,
  gamma-api.polymarket.com.
