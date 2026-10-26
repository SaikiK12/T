# Scripts

<!-- written by scripts/catalog.py; edit the sources (registry, docstrings), not this file -->

Everything here is run from the repository root, e.g. `python scripts/<name>.py --help`. Each
line is the first line of the script's own docstring.

## Fetch: download archives and public history (21)

- [`fetch_binance_options.py`](fetch_binance_options.py): Binance European options history from data.binance.vision (docs/AUCTION_AND_FLOW.md): the only free archive of option positioning the lab has found, for gamma, delta, vanna and charm exposure ...
- [`fetch_binance_recent.py`](fetch_binance_recent.py): Binance USD-M hourly klines past the archive's end (lab.data.END, 2026-09-30) for named perps.
- [`fetch_cboe.py`](fetch_cboe.py): Cboe volatility index history (free daily CSVs, no key): the term structure (VIX1D, VIX9D, VIX, VIX3M, VIX6M, VIX1Y), vol of vol (VVIX), tail pricing (SKEW) and the other asset classes' vol ...
- [`fetch_coinm.py`](fetch_coinm.py): Binance COIN-M hourly klines from data.binance.vision for every contract in the archive (272: perpetuals and dated quarterlies of about 10 coins, 2020 onward): the dated-futures basis term ...
- [`fetch_coinmetrics.py`](fetch_coinmetrics.py): Coin Metrics community API (free, no key): daily market caps and on-chain metrics for every asset it serves free.
- [`fetch_deribit_trades.py`](fetch_deribit_trades.py): Every Deribit BTC and ETH option trade, from Deribit's public history server, reduced to signed hourly flow per option plus every block trade kept whole (docs/AUCTION_AND_FLOW.md).
- [`fetch_equation_history.py`](fetch_equation_history.py): Bounded public input restoration for equations_v1.
- [`fetch_extra.py`](fetch_extra.py): Small public histories for lanes outside the Binance archive: Deribit's hourly implied-volatility index (DVOL, BTC and ETH, from 2021-03), Coinbase hourly spot candles (BTC-USD, ETH-USD, USDT-USD) ...
- [`fetch_fundamentals.py`](fetch_fundamentals.py): Protocol fundamentals from DefiLlama's free API for every token that has a Binance perp: daily TVL, fees and revenue.
- [`fetch_gate.py`](fetch_gate.py): Gate.io USDT-perp hourly contract stats (top-trader and all-account long/short ratios, taker sizes, liquidations, open interest) for the coins of the Binance research universe.
- [`fetch_gate_history.py`](fetch_gate_history.py): Gate.io's public bulk archive (gateio-public-data on S3, no keys): hourly candles and settled funding for every USDT perp, delisted ones included, from 2020-01 to the last complete month.
- [`fetch_hlp.py`](fetch_hlp.py): Hyperliquid's HLP vault (the exchange's community liquidity vault: market making, liquidations, a share of fees), measured from its public history (POST api.hyperliquid.xyz/info, vaultDetails, no ...
- [`fetch_hyperliquid_history.py`](fetch_hyperliquid_history.py): Hyperliquid public history for every listed perp (POST api.hyperliquid.xyz/info, no keys): hourly funding with premium since 2023-05 (500 rows per call, paged), daily candles over the full ...
- [`fetch_macro.py`](fetch_macro.py): Small free daily series for regime and context work: crypto sentiment, US rates and liquidity, stablecoin supply and DeFi activity.
- [`fetch_mexc_history.py`](fetch_mexc_history.py): Download MEXC public history for every crypto USDT perpetual listed today: hourly contract klines, hourly index klines and settled funding, from 2025-04-01 (funding history starts 2025-04-27 on ...
- [`fetch_mexc_tradfi.py`](fetch_mexc_tradfi.py): Download MEXC public history for its TradFi USDT perpetuals (contract type 2: stocks, indices, commodities, ETFs).
- [`fetch_notice_bodies.py`](fetch_notice_bodies.py): Plain text of each Binance delisting article in the notice journal (data/recorders/notices/binance_delisting.csv), from the public CMS detail endpoint.
- [`fetch_spot.py`](fetch_spot.py): Binance spot hourly klines from data.binance.vision for every perp with a USDT spot pair (data/spot_pairs.json, 481 pairs): the spot leg for carry and basis lanes (M047, C09).
- [`fetch_trend_daily.py`](fetch_trend_daily.py): Fetch the frozen slow_trend_v1 spot sample; never calculate market outcomes.
- [`fetch_unlocks.py`](fetch_unlocks.py): DefiLlama token-unlock schedules (the old session's E01 source), from the free dataset mirror: the protocol list, the emissions index, and one schedule file per protocol (documented unlock events ...
- [`fetch_venue_history.py`](fetch_venue_history.py): Funding and candle history from two more perp venues, public APIs, no keys.

## Record: point-in-time collectors (cannot be backfilled) (14)

- [`record_deribit_chain.py`](record_deribit_chain.py): Hourly snapshot of the Deribit option chains (BTC, ETH, and the USDC-settled ones such as SOL and XRP): open interest, mark implied volatility, prices and the underlying of every listed option, ...
- [`record_dex_prices.py`](record_dex_prices.py): Hourly on-chain pool prices next to the MEXC perp price of the same coin, for M288 (DEX-CEX gap; the prop trader's "on-chain AMMs against exchange futures", docs/VENUE_STRUCTURE.md).
- [`record_digest.py`](record_digest.py): Append a SHA-256 digest of every recorder file under data/recorders/ to experiments/recorders/journal/digests.csv (committed).
- [`record_funding_board.py`](record_funding_board.py): Hourly snapshot of the live funding rate of every USDT perp on six more venues: Gate, Hyperliquid, OKX, Bitget, KuCoin and dYdX (MEXC is recorded by record_mexc_ticker.py; Binance and Bybit refuse ...
- [`record_lighter_book.py`](record_lighter_book.py): Hourly snapshot of what a taker order costs on Lighter, the zero-fee perp DEX (docs/VENUE_STRUCTURE.md): for every active perp, the best bid and ask, the cost per side of a market order of USD 1k ...
- [`record_mexc_depth.py`](record_mexc_depth.py): mexc_costs (R224): what a taker order costs on MEXC for the coins the forward books trade, measured from the public order book, as set out in experiments/mexc_costs/PREREG.md.
- [`record_mexc_ticker.py`](record_mexc_ticker.py): Hourly snapshot of every MEXC perpetual: the displayed funding rate with its next settlement time, cycle and caps (funding_rate), and the ticker (last, bid/ask, index and fair price, 24 h volume, ...
- [`record_news.py`](record_news.py): Point-in-time headline recorder: every FEEDS source polled every POLL_S seconds, each new item kept once with the time we first saw it.
- [`record_notices.py`](record_notices.py): Binance announcement catalogs (Delisting, New Cryptocurrency Listing, Latest Binance News) as an append-only journal: one row per article with its id, title, release time (ms, as published) and ...
- [`record_tape.py`](record_tape.py): Order-flow tape recorder (M264): Binance USD-M, MEXC and Lighter perps' best bid/ask and trades for `COINS`, bucketed to the second by lab/tape.py, into data/tape/. Paper only: it reads public ...
- [`record_unlocks.py`](record_unlocks.py): Daily point-in-time snapshot of the DefiLlama unlock calendar: the emissions index (every token's documented past and upcoming unlock events, circulating and max supply, price, market cap) as ...
- [`record_wallets.py`](record_wallets.py): Hourly record of which coins can be deposited and withdrawn on Bithumb, Gate, KuCoin, HTX and Bitget (M294).
- [`scrape_hyperliquid.py`](scrape_hyperliquid.py): Forward collector of on-chain trader data from Hyperliquid, for docs/CLAIMS.md C04 (do top on-chain traders keep winning; does mirroring their positions pay).
- [`scrape_leaderboards.py`](scrape_leaderboards.py): Daily snapshots of public copy-trading leaderboards (Binance, OKX) for a forward persistence test (docs/CLAIMS.md C02, C21, C22).

## Forward: paper lanes and the loops that run them (20)

- [`forward_all.sh`](forward_all.sh): Compatibility entry point: task graph/locks/timeouts live in lab/operations.py.
- [`forward_announce.py`](forward_announce.py): R272 announce_fwd: R271's two candidates forward on MEXC paper (experiments/announce_fwd/PREREG.md).
- [`forward_carry.py`](forward_carry.py): carry_fwd (R220): the R191 funding carry rule forward on paper, entered one bar late, on Binance and on MEXC, as set out in experiments/carry_fwd/PREREG.md.
- [`forward_delayed.py`](forward_delayed.py): flow72_fwd3 (R214): R200's forward books with each slice entered one bar after its signal bar, as set out in experiments/flow72_fwd3/PREREG.md.
- [`forward_delist.py`](forward_delist.py): R268 delist_fwd: the spot delisting-notice short, forward on MEXC paper (experiments/delist_fwd/PREREG.md).
- [`forward_lag.py`](forward_lag.py): Processing lag of the forward lanes: how long after each hour's bar closed R200 computed its signal, and which on-time days were scored from hours computed late (a backfill after the container or ...
- [`forward_loop.sh`](forward_loop.sh): Optional hourly scheduler at minute 6.
- [`forward_mexc.py`](forward_mexc.py): mexc_fwd (R215): R200's forward signals traded one bar late on MEXC hourly closes and MEXC funding, as set out in experiments/mexc_fwd/PREREG.md.
- [`forward_mexc_sq.py`](forward_mexc_sq.py): mexc_fwd_sq (R218): the agreement-squared flow book on MEXC prices and funding, one bar late, as set out in experiments/mexc_fwd_sq/PREREG.md.
- [`forward_montag.py`](forward_montag.py): R270 montag_fwd: the Monitoring Tag short at +24 h, forward on MEXC paper (experiments/montag_fwd/PREREG.md).
- [`forward_seq.py`](forward_seq.py): mexc_seq (R221): the sequential decision for the MEXC flow books A, X2 and B, as set out in experiments/mexc_seq/PREREG.md.
- [`forward_tick.py`](forward_tick.py): flow72_fwd2 (R200): one forward tick, as set out in experiments/flow72_fwd2/PREREG.md.
- [`forward_unlocks.py`](forward_unlocks.py): unlocks_fwd (R266): the unlock short forward on MEXC paper, as set out in experiments/unlocks_fwd/PREREG.md.
- [`forward_vt.py`](forward_vt.py): vt_fwd (R225): R217's volatility target (rule R1) applied forward to the MEXC flow books A and B (R215) and X2 (R218), warmed up on R217's archived daily nets, as set out in ...
- [`forward_xbook.py`](forward_xbook.py): xbook_fwd (R285): the cross-family forward book (M281), as set out in experiments/xbook_fwd/PREREG.md.
- [`forward_xfund.py`](forward_xfund.py): xfund_fwd (R278): R275's cross-venue funding carry books forward on paper, as set out in experiments/xfund_fwd/PREREG.md.
- [`forward_xfund_kc.py`](forward_xfund_kc.py): xfund_kc_fwd (R279): R277's two replicating KuCoin carry books forward on paper, as set out in experiments/xfund_kc_fwd/PREREG.md.
- [`forward_xfund_lt.py`](forward_xfund_lt.py): xfund_lt_fwd (R294): R288's mexc+lighter carry book forward on paper, as set out in experiments/xfund_lt_fwd/PREREG.md.
- [`live_parity.py`](live_parity.py): Live vs archive parity: are the live public endpoints the same data as the archive the lanes were built on?.
- [`notice_loop.sh`](notice_loop.sh): Every 5 minutes: record Binance's notice catalogs, then ticket R272 announce_fwd, so an event ticket is written minutes after a notice and enters at the next full hour.

## Run: one lane's frozen measurement (102)

- [`qx_run.py`](qx_run.py): Run a family lane on the qx engine, end to end: verify, check inputs, run, summarise, register.
- [`qx_run_verified.py`](qx_run_verified.py): Run a qx lane only with a source-matched build, then retain an immutable run receipt.
- [`run_accounting.py`](run_accounting.py): accounting_v1 (R264): how much the legacy zero-fill of missing next returns moves flow books A, B and X2, as set out in experiments/accounting_v1/PREREG.md.
- [`run_allocation.py`](run_allocation.py): R228: a frozen, descriptive allocation diagnostic on previously seen books.
- [`run_amihud.py`](run_amihud.py): amihud_v1 (R236): 30-day Amihud illiquidity as one-week spread books, as set out in experiments/amihud_v1/PREREG.md.
- [`run_atlas.py`](run_atlas.py): atlas_v1 (R185): the gross-edge atlas, as set out in experiments/atlas_v1/PREREG.md.
- [`run_auction.py`](run_auction.py): auction_v1 (R290): auction-market levels on 1-minute bars of the BTC, ETH and SOL perps, from real session anchors and from placebo clocks, as set out in experiments/auction_v1/PREREG.md (M305, ...
- [`run_battery.py`](run_battery.py): Run the battery_v1 lane for one walk-forward fold, as set out in experiments/battery_v1/PREREG.md.
- [`run_brute5k.py`](run_brute5k.py): brute5k_v1 (R263): 5,472 chart strategies (76 base rules x 4 timeframes x 3 directions x 3 filters x 2 stops) on the top-20 perps, a monthly walk-forward selection of what worked over the last L ...
- [`run_capit.py`](run_capit.py): capit_v1 (R303): buying capitulation on Binance perps.
- [`run_capital_mix.py`](run_capital_mix.py): R309: fixed initial-capital carry/spot comparison; archived inputs only, no trading.
- [`run_carry.py`](run_carry.py): carry_v1 (R190): hedged funding carry, as set out in experiments/carry_v1/PREREG.md.
- [`run_carry_holdout.py`](run_carry_holdout.py): carry_holdout (R191): one-shot holdout of the R190 primary, as set out in experiments/carry_holdout/PREREG.md.
- [`run_carrycrash.py`](run_carrycrash.py): carrycrash_v1 (R207): high market-wide carry as a BTC crash signal, as set out in experiments/carrycrash_v1/PREREG.md.
- [`run_cascmkt.py`](run_cascmkt.py): cascmkt_v1 (R253): buy the equal-weight market for 24 h after an hour in which at least 3 top-50 perps show R252's long-cascade trigger, as set out in experiments/cascmkt_v1/PREREG.md.
- [`run_cbprem.py`](run_cbprem.py): cbprem_v1 (R210): the Coinbase premium as a BTC/ETH signal, as set out in experiments/cbprem_v1/PREREG.md.
- [`run_charmexpiry.py`](run_charmexpiry.py): charm_expiry_v1 (R296): does Deribit's Friday 08:00 UTC expiry move the BTC and ETH perps? As set out in experiments/charm_expiry_v1/PREREG.md.
- [`run_chartist.py`](run_chartist.py): chartist_v1 (R243): seven classic chart rules on 4 h and 1 d bars of the top-50 perps, directional books, as set out in experiments/chartist_v1/PREREG.md.
- [`run_chartxm.py`](run_chartxm.py): chartxm_v1 (R247): R243's seven chart rules (run_chartist.states, unchanged) on daily bars of 11 forex pairs and 10 world equity indices, equal-weight books per group, as set out in ...
- [`run_clockflow.py`](run_clockflow.py): clockflow_v1 (R289): fixed-clock flows on 1-minute bars of the BTC, ETH and SOL perps, as set out in experiments/clockflow_v1/PREREG.md.
- [`run_context_atlas.py`](run_context_atlas.py): atlas_ctx (R192): context lifts of the atlas signals, as set out in experiments/atlas_ctx/PREREG.md.
- [`run_continuation_control.py`](run_continuation_control.py): R323 fixed conditional continuation policies and common-account replay.
- [`run_ctxslice.py`](run_ctxslice.py): ctxslice_v1 (R201): the replicated excess context edges of atlas_ctx (R192) and atlas_mtf (R195) as one slice book, as set out in experiments/ctxslice_v1/PREREG.md; ctxslice_v2 (R204): its 12-24 h ...
- [`run_daylimit.py`](run_daylimit.py): daylimit_v1 (R208): daily loss and profit limits on the flow slice books, as set out in experiments/daylimit_v1/PREREG.md.
- [`run_dealerflow.py`](run_dealerflow.py): dealerflow_v1 (R292): does dealer gamma estimated from Deribit taker flow (M308) explain the next UTC day's realized volatility beyond a HAR base, and the sign of the next day's hourly return ...
- [`run_delay.py`](run_delay.py): delay_v1 (R213): the flow books with entry delayed d hours after the signal bar, as set out in experiments/delay_v1/PREREG.md.
- [`run_delist.py`](run_delist.py): R267 delist_v1: the Binance delisting-notice short on the hourly archive (experiments/delist_v1/PREREG.md).
- [`run_dependent_null.py`](run_dependent_null.py): R321 registered null-only size/power study; no market outcome is read.
- [`run_dispgate.py`](run_dispgate.py): dispgate_v1 (R260): flow books A, B and X2 at half size on days when 30-day cross-sectional dispersion is in its top tercile and the alt index's 90-day return is negative (docs/SIZING_EVIDENCE.md ...
- [`run_dow.py`](run_dow.py): dow_v1 (R254): day-of-week books on SPY, world indices, the US dollar, BTC and crypto.
- [`run_effratio.py`](run_effratio.py): er_v1 (R293): can tomorrow's efficiency ratio be forecast, and does skipping predicted chop days improve a trend rule? As set out in experiments/er_v1/PREREG.md (M314, from the owner's reel ...
- [`run_equations.py`](run_equations.py): R310: one frozen 12-policy funding/basis family, offline only.
- [`run_equations_v2.py`](run_equations_v2.py): R311: exact R310 policy repeat after source-only Lighter page-seam recovery.
- [`run_flow72.py`](run_flow72.py): flow72_v1 (R196): short the coins with heavy taker selling / top traders short vs the crowd, 72 h, universe-hedged, as set out in experiments/flow72_v1/PREREG.md.
- [`run_flow72_holdout.py`](run_flow72_holdout.py): flow72_holdout (R198): one shot of the frozen 72 h flow slice book on 2025-07-01..2026-09-30, as set out in experiments/flow72_holdout/PREREG.md.
- [`run_flow72_slices.py`](run_flow72_slices.py): flow72_v2 (R197): the three 72 h flow cells as overlapping slices, as set out in experiments/flow72_v2/PREREG.md.
- [`run_fundgate.py`](run_fundgate.py): fundgate_v1 (R297): does the market's funding response to up days time the crypto market? As set out in experiments/fundgate_v1/PREREG.md (M295, from a Bankless guest's remark, docs/COMMENT_DIG.md).
- [`run_funding_prefix.py`](run_funding_prefix.py): R322 finite source-arithmetic/account fixtures; no market collection or policy.
- [`run_fundxs.py`](run_fundxs.py): fundxs_v1 (R302): the Binance funding level as a cross-sectional signal, net of the funding each leg pays (M263).
- [`run_fxindex.py`](run_fxindex.py): fxindex_v1 (R239): G10 forex momentum, dollar trend, VIX reversal, Halloween, pre-holiday and the variance risk premium, as set out in experiments/fxindex_v1/PREREG.md.
- [`run_gate_lanes.py`](run_gate_lanes.py): Lanes on Gate.io contract stats, traded on Binance returns: xvenue_v1 (R205, top traders vs the crowd measured on Gate) and liq_v1 (R206, liquidation cascades), as set out in their PREREGs.
- [`run_ictlevels.py`](run_ictlevels.py): ictlevels_v1 (R246): round-number levels, SMT divergence against BTC and the 8 AM New York range on hourly bars of the top-50 perps, directional books, as set out in ...
- [`run_impact.py`](run_impact.py): impact_v1 (R262): square-root market impact on flow books A, B and X2 at capital $1k-$10M, on top of the tier costs, as set out in experiments/impact_v1/PREREG.md.
- [`run_intrars.py`](run_intrars.py): intrars_v1 (R300): intraday cross-sectional relative strength among the top 50 perps (M318, from Linda Raschke on Better System Trader 124).
- [`run_itsm.py`](run_itsm.py): itsm_v1 (R203): intraday time-series momentum, as set out in experiments/itsm_v1/PREREG.md.
- [`run_levcarry.py`](run_levcarry.py): levcarry_v1 (R280): leverage and liquidation on the forward carry books, as set out in experiments/levcarry_v1/PREREG.md.
- [`run_listings.py`](run_listings.py): listings_v1 (R188): returns after new perpetual listings, as set out in experiments/listings_v1/PREREG.md.
- [`run_listings_holdout.py`](run_listings_holdout.py): listings_holdout (R189): one-shot holdout test, as set out in experiments/listings_holdout/PREREG.md.
- [`run_lmw.py`](run_lmw.py): lmw_v1 (R251): Lo-Mamaysky-Wang kernel chart patterns (head-and-shoulders, broadening, triangle and rectangle tops and bottoms) on daily bars of the top-50 perps, 11 forex pairs and 10 world ...
- [`run_lotcap.py`](run_lotcap.py): lotcap_v1 (R298): harvest R282's lottery-cluster median while capping the squeezes.
- [`run_maker.py`](run_maker.py): maker_v1 (R193): limit-order entries on the replicated gross edges, as set out in experiments/maker_v1/PREREG.md.
- [`run_merge.py`](run_merge.py): merge_v1 (R186): walk-forward merge of many signals into one forecast, traded only where it clears costs, as set out in experiments/merge_v1/PREREG.md.
- [`run_merge_v2.py`](run_merge_v2.py): merge_v2 (R187): trade-consistent, faster, session-aware merge, as set out in experiments/merge_v2/PREREG.md.
- [`run_mlaudit.py`](run_mlaudit.py): R305 mlaudit_v1: what carries R304's pick (GBM h7 on the 24 clean features)?.
- [`run_mlrank.py`](run_mlrank.py): mlrank_v1 (R299): machine-learned cross-sectional rankers on the daily point-in-time panel.
- [`run_mlrank2.py`](run_mlrank2.py): R304 mlrank_v2: R299's rankers again, without the three features whose coverage leaks survival.
- [`run_montag.py`](run_montag.py): R269 montag_v1: short the perps of coins Binance adds to its Monitoring Tag (experiments/montag_v1/PREREG.md).
- [`run_msnr.py`](run_msnr.py): R306 msnr_v1: Malaysian support and resistance (M323) on 4-hour candles, as set out in experiments/msnr_v1/PREREG.md.
- [`run_nagel.py`](run_nagel.py): nagel_v1 (R308): the 1-day cross-sectional reversal only after market stress (M325), as set out in experiments/nagel_v1/PREREG.md.
- [`run_oiwick.py`](run_oiwick.py): oiwick_v1 (R252): fade liquidation cascades proxied by a >= 3% hourly open-interest drop plus a >= 3 ATR wick, on the top-50 perps, as set out in experiments/oiwick_v1/PREREG.md.
- [`run_optflow.py`](run_optflow.py): optflow_v1 (R295): does signed Deribit option flow lead BTC and ETH perp returns over the next 1, 4 or 24 hours? As set out in experiments/optflow_v1/PREREG.md.
- [`run_optimizer.py`](run_optimizer.py): Finite static M027 allocation screen; imports never read project outcomes.
- [`run_owner_acceptance.py`](run_owner_acceptance.py): R320 finite risk/component validation and integrated owner acceptance evidence.
- [`run_pack.py`](run_pack.py): pack_v1 (R194): many maker cells in one hedged book, as set out in experiments/pack_v1/PREREG.md.
- [`run_paired_account.py`](run_paired_account.py): R319 registered paper lifecycle and held-book economic accounting, offline only.
- [`run_pairs.py`](run_pairs.py): pairs_v1 (R250): weekly-formed pairs on the top-50 perps, distance (Gatev) and Engle-Granger selection, z-score entry 2 and exit 0, as set out in experiments/pairs_v1/PREREG.md.
- [`run_paper_account.py`](run_paper_account.py): R318 offline account integration, on invented fixtures and sealed seen books.
- [`run_partial_execution.py`](run_partial_execution.py): R231: pre-registered partial adjustment of the unchanged R229 spot target.
- [`run_pcares.py`](run_pcares.py): pcares_v1 (R287): Avellaneda-Lee PCA residual reversion on the top-50 Binance perps at hourly scale, as set out in experiments/pcares_v1/PREREG.md (M298).
- [`run_pivotfade.py`](run_pivotfade.py): pivotfade_v1 (R248): fade a close beyond the prior day's floor pivot R1/S1 (the mirror of R243/R247's PIVOT_BREAK) on daily world indices and forex (validation 2013-19, then the 2020-26 holdout ...
- [`run_posfam.py`](run_posfam.py): posfam_v1 (R211): the two halves of top_vs_crowd and the top-account ratio as 72 h slice books; posfam_v2 (R212): the top-account ratio as a contrarian book.
- [`run_posimpulse.py`](run_posimpulse.py): posimpulse_v1 (R234): the 24 h and 72 h change in top-vs-crowd positioning as 72 h spread books, tested for information beyond the level book, as set out in experiments/posimpulse_v1/PREREG.md.
- [`run_posimpulse_v2.py`](run_posimpulse_v2.py): posimpulse_v2 (R240): imp24/H and imp72/H from R234 tested on validation only, with K fixed on 2023, as set out in experiments/posimpulse_v2/PREREG.md.
- [`run_propfirm.py`](run_propfirm.py): propfirm_v1 (R202): the lab's return streams under prop-firm rule sets, as set out in experiments/propfirm_v1/PREREG.md.
- [`run_qbasis.py`](run_qbasis.py): qbasis_v1 (R301): the dated-futures basis as a cross-sectional signal on Binance perps (M170, from Chi, Hao, Hu and Ran, J. Futures Markets 2023).
- [`run_rebalancing.py`](run_rebalancing.py): R232: fixed equal-weight rebalance cadences versus unchanged buy-and-hold units.
- [`run_regime.py`](run_regime.py): regime_v1 (R233): flow books A, B and X2 traded only in some trend x volatility regimes, and a regime-wise choice among them (MacroHFT's sub-agents and hyper-agent), against constant size, as set ...
- [`run_reserved_batch.py`](run_reserved_batch.py): Reserved batch 1 (docs/GATES.md): every candidate the earlier lanes pre-committed, read once on the reserved samples and decided together.
- [`run_rnfade.py`](run_rnfade.py): rnfade_v1 (R249): fade the day's first close through a round-number level (two- or one-significant-figure grid), held 4 h or 24 h, against the same book on a half-step-shifted grid, on the crypto ...
- [`run_rrskew.py`](run_rrskew.py): R307 rrskew_v1: does the Deribit 25-delta risk reversal time BTC and ETH perps week by week (M174), as set out in experiments/rrskew_v1/PREREG.md.
- [`run_seesaw.py`](run_seesaw.py): seesaw_v1 (R219): do the five most liquid coins' last hours predict the altcoins (lead-lag and catch-up), as set out in experiments/seesaw_v1/PREREG.md.
- [`run_settle.py`](run_settle.py): settle_v1 (R223): hold across one funding settlement to collect an extreme rate, as set out in experiments/settle_v1/PREREG.md.
- [`run_sizecarry.py`](run_sizecarry.py): sizecarry_v1 (R281): confidence-sized carry books, as set out in experiments/sizecarry_v1/PREREG.md.
- [`run_sizing.py`](run_sizing.py): sizing_v1 (R217): confidence-scaled multipliers on the flow books against a constant size, as set out in experiments/sizing_v1/PREREG.md.
- [`run_slow_trend.py`](run_slow_trend.py): R229: frozen, bounded daily spot trend screen.
- [`run_tradesize.py`](run_tradesize.py): tradesize_v1 (R226): trade count and mean print size as 72 h spread books, tested for information beyond quote volume, as set out in experiments/tradesize_v1/PREREG.md.
- [`run_tradlead.py`](run_tradlead.py): tradlead_v1 (R261): does the last hour of TradFi perps (commodities CMD, US equities EQ) lead crypto? A market-timing book (TS) and a beta cross-section (XS), holds 1/4/24 h, sign chosen in ...
- [`run_trendpull.py`](run_trendpull.py): trendpull_v1 (R284): Visser's trend pullback on 10 world indices and every Binance perp, long after the 63-day rate of change resets near zero inside a rising 200-day trend, as set out in ...
- [`run_tsbattery.py`](run_tsbattery.py): tsbattery_v1 (R242): week-open bias, pre-FOMC drift, ETH/BTC regime and vol-managed trend on the top-50 perps, as set out in experiments/tsbattery_v1/PREREG.md.
- [`run_tsmom.py`](run_tsmom.py): tsmom_v1 (R237): cross-asset time-series momentum on equity ETFs, FX, metals and bond futures, as set out in experiments/tsmom_v1/PREREG.md.
- [`run_unlocks.py`](run_unlocks.py): unlocks_v1 (R265): the old session's unlock short (E01, S1) on 2021-26 Binance perps, as set out in experiments/unlocks_v1/PREREG.md.
- [`run_usindex_calendar.py`](run_usindex_calendar.py): usindex_calendar_v1 (R235): turn-of-month and overnight drift on SPY and QQQ, as alpha against buy-and-hold of the same ETF, as set out in experiments/usindex_calendar_v1/PREREG.md.
- [`run_venue_gap.py`](run_venue_gap.py): venue_gap_v1 (R216): the flow books' PnL split into crypto and TradFi contracts, in the archive and on the forward replay, as set out in experiments/venue_gap_v1/PREREG.md.
- [`run_vixpanic.py`](run_vixpanic.py): vixpanic_v1 (R283): long SPY, QQQ and the BTCUSDT perp after VIX-panic onsets (VIX above VIX3M, VVIX in its top 5%, or both), tested against random dates, as set out in ...
- [`run_volrisk.py`](run_volrisk.py): volrisk_v1 (R241): SVXY in VIX contango, SVXY in contango with calm VIX, and R239's VIXREV-QQQ on 2013-2026, as set out in experiments/volrisk_v1/PREREG.md.
- [`run_vpin.py`](run_vpin.py): vpin_v1 (R291): does VPIN, the order-flow toxicity measure of Easley, López de Prado and O'Hara, forecast the realized volatility of the BTC, ETH and SOL perps beyond volume and past volatility? ...
- [`run_vrp.py`](run_vrp.py): vrp_v1 (R209): implied minus realized volatility as a BTC/ETH timing signal, as set out in experiments/vrp_v1/PREREG.md.
- [`run_weekendlink.py`](run_weekendlink.py): weekendlink_v1 (R244): BTC's weekend move sets long/short on QQQ and SPY for the first session of the week, as set out in experiments/weekendlink_v1/PREREG.md.
- [`run_weekly_rotation.py`](run_weekly_rotation.py): R230: finite, registered weekly spot rotation search; no network access.
- [`run_xsalt.py`](run_xsalt.py): xsalt_v1 (R222): slow altcoin cross-sections (low beta, residual momentum, MAX, premium net of funding), as set out in experiments/xsalt_v1/PREREG.md.
- [`run_xsbattery.py`](run_xsbattery.py): xsbattery_v1 (R238): eight cross-sectional features as one-week spread books, as set out in experiments/xsbattery_v1/PREREG.md.
- [`run_xsrev.py`](run_xsrev.py): xsrev_v1 (R245): 1-day and 7-day reversal books inside the most and least liquid terciles of the top-50, as set out in experiments/xsrev_v1/PREREG.md.

## Check: parity, audits and integrity (13)

- [`audit_fee_routes.py`](audit_fee_routes.py): R317 fixed fee-route decomposition on already-seen sealed R316 books.
- [`audit_levcarry.py`](audit_levcarry.py): levcarry_v1 (R280) audit: are the legs liquidated at L = 1 real moves, or one venue's trade prints?.
- [`audit_xfund_lt.py`](audit_xfund_lt.py): R288 xfund_lt_v1 audit, as committed in its PREREG before the result: Lighter's funding sign and units against Binance's, funding recomputed from the raw files for 2 random trades per set, ...
- [`check_carry_venues.py`](check_carry_venues.py): Diagnostic for carry_fwd (R220): do Binance and MEXC settle the same funding on the same coins? Compares trailing 72 h funding APR per hour over the forward grid for symbols mapped to a MEXC ...
- [`check_continuation_control.py`](check_continuation_control.py): Independent rational policy enumeration and saved-account audit for R323.
- [`check_dependent_null.py`](check_dependent_null.py): Independent literal R321 binomial/OBM/selected-bootstrap arithmetic audit.
- [`check_funding_prefix.py`](check_funding_prefix.py): Literal rational audit of R322 saved component fixtures; no market validation.
- [`check_method_intake.py`](check_method_intake.py): Validate source/alias/queue metadata without reading outcomes or contacting providers.
- [`check_owner_acceptance.py`](check_owner_acceptance.py): R320 independent literal risk-target/forecast and paper-report audit.
- [`check_paired_account.py`](check_paired_account.py): Independent arithmetic for R319 reports, standard library only.
- [`check_paper_account.py`](check_paper_account.py): Independent Decimal oracle for linear simulated-account integration.
- [`check_research_integrity.py`](check_research_integrity.py): Audit the research register and local preregistrations without changing files.
- [`xfund_parity.py`](xfund_parity.py): lab.xfund (the Python twin of qx spread) against a frozen engine run's output on the archive.

## Build: tables, views and symbol maps (7)

- [`build_daily.py`](build_daily.py): Build the daily point-in-time panel (lab/daily.py): one row per (day, Binance perp) from every source the lab holds, plus the market-wide series, into data/daily/.
- [`build_engine.py`](build_engine.py): Build qx from the locked dependency graph and bind binary/source/toolchain.
- [`build_extra_views.py`](build_extra_views.py): Extra feature tensors next to data/research/bins.npy, same [V, T, S] int8 layout and binning conventions.
- [`build_views.py`](build_views.py): Build the point-in-time research universe and the int8 feature-bin tensor, and save them under data/research/.
- [`venue_symbols.py`](venue_symbols.py): Cross-venue symbol table: one row per Binance USD-M perp, with the file stem of the same coin on Gate, Hyperliquid and MEXC (empty where it is not listed or has no history file).
- [`venue_symbols_kd.py`](venue_symbols_kd.py): Symbol table for the KuCoin / dYdX venue replication of R275 and R276: one row per Binance USD-M perp with the file stem of the same coin on Gate, KuCoin and dYdX (empty where it is not listed or ...
- [`venue_table.py`](venue_table.py): Write a qx spread symbol table from lab.venues: one row per Binance perp found on at least one of the venues asked for, columns `key`, `binance` and one per venue (the venue's symbol, '' where it ...

## Research: videos, podcasts and transcripts (docs/VIDEO_DIG.md) (5)

- [`dig_comments.py`](dig_comments.py): Comment sections as searchable text: where practitioners answer each other, not where they present.
- [`dig_podcasts.py`](dig_podcasts.py): Practitioner podcasts as searchable text: the people of docs/VIDEO_DIG.md through their shows' RSS feeds.
- [`dig_talks.py`](dig_talks.py): What traders with a proven record say about where their money came from (owner, 2026-10-21: "they can at a time make a mistake on words or phrasing that lets us infer how they proceed").
- [`dig_videos.py`](dig_videos.py): Dig YouTube for deep, little-watched practitioner videos and keep their captions as searchable text.
- [`transcribe_audio.py`](transcribe_audio.py): One audio file to plain text with faster-whisper on CPU (used by scripts/dig_podcasts.py).

## Tools and everything else (38)

- [`announce_events.py`](announce_events.py): Legs for the announcement-family scan (R271) from Binance's three notice catalogs (data/recorders/notices/binance_{news,delisting,listing}.csv, scripts/record_notices.py).
- [`atlas_replication.py`](atlas_replication.py): atlas_v1 (R185): score the frozen discovery lists on validation (same sign and |t| >= 2), as the PREREG says.
- [`benchmark_evaluation.py`](benchmark_evaluation.py): Bounded synthetic engineering benchmark, never an edge/outcome search.
- [`catalog.py`](catalog.py): Plain-language catalogs of the repository's folders, rebuilt from what the files already say.
- [`check.py`](check.py): One offline unittest entry point: full release gate or bounded feedback.
- [`dashboard_data.py`](dashboard_data.py): Export the lab's state as the dashboard's datasets: dashboard/data/<id>.json, one array of row objects each.
- [`dashboard_jobs.py`](dashboard_jobs.py): Read-only operational job metadata for the control room.
- [`dashboard_perf.py`](dashboard_perf.py): The control room's performance and coverage datasets (docs/BENCHMARK.md build items 2-3), used by dashboard_data.py.
- [`data_provenance.py`](data_provenance.py): Provenance record for a downloaded data folder (docs/DATA_PROVENANCE_AUDIT.md): every file's size and sha256, a combined digest, file counts per subfolder, and for hourly parquet folders the bar ...
- [`delist_events.py`](delist_events.py): Legs for the delisting-notice short (E03, docs/OLD_SESSION_EDGES.md S2) from the Binance delisting catalog (data/recorders/notices/binance_delisting.csv, scripts/record_notices.py) and the ...
- [`funding_events.py`](funding_events.py): Extreme-funding events on every Binance USD-M perp, as event legs for the qx engine (R273 fundext_v1).
- [`lighter_table.py`](lighter_table.py): qx spread symbol table with a Lighter column, for the Lighter carry lane (docs/VENUE_STRUCTURE.md, plan item 4).
- [`montag_events.py`](montag_events.py): Legs for the Monitoring Tag short (R269) from Binance's news and delisting catalogs (data/recorders/notices/binance_{news,delisting}.csv, scripts/record_notices.py; one tag notice was filed under ...
- [`orchestrate_forward.py`](orchestrate_forward.py): Plan or run the existing paper collectors with explicit dependencies.
- [`panel.py`](panel.py): The project's one panel: docs/PANEL.md, rebuilt from the registry, the methods queue and the forward lanes' status files at the end of every tick.
- [`paper_account.py`](paper_account.py): One offline account command: account, lifecycle, controls or funding component.
- [`paper_account_view.py`](paper_account_view.py): Offline French view of an explicit simulated-account report; no calculations or orders.
- [`paper_status.py`](paper_status.py): Read-only paper/account view over registered evidence; no runner is started.
- [`pitfac_factors.py`](pitfac_factors.py): Factors for qx factors (R282 pitfac_v1) from the daily point-in-time panel (lab/daily.py): what the panel's new sources say about a Binance perp at 00:00 UTC.
- [`probe_depth_quotes.py`](probe_depth_quotes.py): R314 finite public depth probe: capture, seal, then report fixed cost controls.
- [`probe_funding_values.py`](probe_funding_values.py): R315 fixed fair-value snapshot diagnostic; no orders or strategy scoring.
- [`probe_pair_quotes.py`](probe_pair_quotes.py): R312 bounded first-seen public REST evidence: capture -> seal -> report.
- [`probe_stream_quotes.py`](probe_stream_quotes.py): R313 bounded public WS quote-access measurement: capture -> seal -> report.
- [`probe_warm_values.py`](probe_warm_values.py): R316 finite matched prestarted/cold fair requests on identical paired books.
- [`project_status.py`](project_status.py): Read-only project status using the Control Room's existing execution receipts.
- [`prop_cost_map.py`](prop_cost_map.py): How much trading can a book afford inside a prop firm? Synthetic map for queue M211, next to prop_edge_map.py.
- [`prop_edge_map.py`](prop_edge_map.py): How much edge does a prop challenge need? Synthetic map for queue M211, from lab/propfirm presets.
- [`repair_equation_funding.py`](repair_equation_funding.py): Recover only missing Lighter page seams into a new copy; never edit R310 inputs.
- [`repository_index.py`](repository_index.py): Query tracked repository metadata without importing runners or reading outcomes.
- [`reserved_legs.py`](reserved_legs.py): Funding-onset event legs on the reserved 2020 rows, for reserved batch 1's R273 and R274 candidates (docs/GATES.md).
- [`speed_test.py`](speed_test.py): Timing check for lab.search on the research universe: how long the condition catalog, the single-condition rules and a 512-rule evaluation take on the discovery rows.
- [`squeeze_events.py`](squeeze_events.py): Negative-funding onsets on two venues, as event legs for the qx engine (R274 squeeze_v1).
- [`unlock_events.py`](unlock_events.py): Unlock events for the unlock-short lane (E01, docs/OLD_SESSION_EDGES.md S1) from a DefiLlama emissions snapshot (scripts/fetch_unlocks.py).
- [`unlock_market_data.py`](unlock_market_data.py): Immutable public funding/mark archive acquisition and portable data bundle; no PnL.
- [`unlocks_daily_check.py`](unlocks_daily_check.py): R258: bounded Binance daily-bar cross-check of the fixed R265 unlock events.
- [`unlocks_funding_bounds.py`](unlocks_funding_bounds.py): R259: fixed-cohort funding bounds and necessary isolated collateral; no fills.
- [`xbook_archive.py`](xbook_archive.py): xbook_fwd (R285) archive context: the three families of the cross-family book (carry, flow, events) rebuilt as daily series from the archive results of the lanes that feed it.
- [`xvenue_factors.py`](xvenue_factors.py): Cross-venue factors for qx factors (R276 xvfac_v1): what another venue says about a Binance perp at 00:00 UTC.
