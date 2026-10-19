# Perpetual execution and account risk: what the evidence supports

Reviewed 2026-10-19. This note connects the project’s target-venue question with current MEXC documentation and execution/risk literature. Published spot-BTC impact results are useful as hypotheses and measurement guidance; they do not price present-day MEXC altcoin-perpetual trades.

## Separate the claims

1. A feature predicts a later return.
2. A paper portfolio earns after modeled fees.
3. Orders at the target venue could realize that PnL at the intended size.
4. The account survives margin requirements and adverse intrabar paths.

These are separate questions. The current repository’s flat cost multipliers and hourly/daily PnL streams cannot alone establish order-book capacity, passive fill probability, cross-margin exposure or forced-liquidation behavior.

## Impact literature: useful but distant from the target

Donier and Bonart’s [metaorder study](https://arxiv.org/abs/1412.4503), already referenced in `docs/SOURCES.md`, uses MtGox spot-BTC trades from 2011–2013. Its square-root impact and near-decay result concern a selected subset of isolated, pseudo-random metaorders, not the project’s hourly positioning signal. It does not imply that fading the project’s flow captures decay.

Other studies also concern older spot markets: Schnaubelt, Rende and Krauss reconstruct BTC/USD books on Bitfinex with Coinbase/Bitstamp checks (2017–18) ([paper](https://doi.org/10.3390/jrfm12010025)); Angerer, Gramlich and Hanke compare books across spot exchanges and pairs (2019) ([paper](https://doi.org/10.3390/jrfm18030124)); Bundi, Wei and Khashanah model one-hour BTC/USD execution on Kraken ([paper](https://doi.org/10.1007/s42521-023-00103-y)); Brauneis et al. compare liquidity measures for BTC/ETH spot on three venues (2017–19) ([paper](https://doi.org/10.1016/j.jbankfin.2020.106041)). These support measuring liquidity by venue, pair, side, size and time. They are not capacity validation for a current perpetual portfolio.

Cakici et al.’s cross-sectional crypto study finds predicted returns concentrate in small, illiquid and volatile coins ([2024 article](https://doi.org/10.1016/j.irfa.2024.103244)). That raises the possibility that alpha may be largest where execution is hardest. It does not show the project has the same concentration or that any specific MEXC order would fail.

## What public MEXC data can and cannot tell you

MEXC publishes a live perpetual depth stream with 200 ms updates, matching-engine timestamps and version information. The trade stream is aggregated by default; REST endpoints provide bounded recent trades/depth history rather than a complete historical event archive. Reconstructed books require snapshot-plus-delta sequence maintenance and recovery after version gaps ([depth stream](https://www.mexc.com/api-docs/futures/websocket-api/order-book-depth), [trade stream](https://www.mexc.com/api-docs/futures/websocket-api/deal), [book maintenance](https://www.mexc.com/api-docs/futures/websocket-api/incremental-order-book-maintenance-mechanism), [recent trades](https://www.mexc.com/api-docs/futures/market-endpoints/get-recent-trades)).

This supports a prospective shadow capture. It does **not** reveal historical queue priority or passive order fill probability. A static book walk estimates the immediate cost conditional on displayed depth staying available; it is not an observed fill. Invalidate samples with unrepaired sequence gaps. Record both event and local receipt times, mark/index/local trade prices, contract size, quantity step, and the fee schedule in effect.

MEXC lists API Futures fees of 0.06% maker and 0.08% taker in its [June 2026 notice](https://www.mexc.com/announcements/article/updates-to-api-futures-trading-fees-jun-1-2026-17827791535742). A taker entry and exit therefore implies 16 bp before spread, book sweep, funding or slippage. The notice’s worked example still refers to an older fee schedule, and the contract-info example differs; verify current pair/account charges through the account-specific [fee endpoint](https://www.mexc.com/api-docs/futures/account-and-trading-endpoints/get-fee-details) or fill records before freezing the cost model.

## Account risk does not follow from mark-to-market portfolio returns

MEXC describes liquidation using fair price and maintenance-margin tiers. Isolated positions are evaluated separately; cross positions depend on shared account equity and the other positions. Funding also changes cash/equity, and the venue can change contract risk tiers. Official references: [liquidation FAQ](https://www.mexc.com/support/article/faq-on-liquidation-for-futures-trading-8123281969561), [margin guide](https://www.mexc.com/support/article/mexc-margin-calculation-guide-312054740132052992), [risk limits](https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-risk-limits), and [funding rules](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280).

Cheng et al.’s 2021 BitMEX study shows why normal-return margin calculations can understate tail requirements ([article](https://doi.org/10.1080/00036846.2021.1922597)); a 2026 Binance-perpetual study reports cross-coin liquidation cascades in a limited ten-asset sample ([article](https://doi.org/10.1108/SEF-04-2026-0367)). These studies motivate path-aware stress tests, not an MEXC liquidation parameter.

The project’s own review already notes that R198’s reported 47% drawdown and near-2x gross exposure have no contract-level margin or forced-close replay. A long and short can net to near-zero at each hourly close and still fail independently when one leg crosses a liquidation threshold intrabar.

## Synthetic checks (not venue or strategy estimates)

**Fee arithmetic.** The documented BTC contract-size example is 0.0001 BTC per contract. At a hypothetical price of 50,000 USDT, 1,000 contracts represent 0.1 BTC, or 5,000 USDT notional. An 0.08% taker fee is 4 USDT per side; a taker round trip is 8 USDT before other costs. This is arithmetic only.

**Book-walk illustration.** With a fictional mid of $1 and ask-side quote depth of $5,000 at $1.0005, $7,500 at $1.0010, $15,000 at $1.0050 and $30,000 at $1.0200, a static walk produces shortfalls of 5.00, 7.50, 29.02 and 107.26 bp for $5k, $10k, $25k and $50k target notionals. The convexity follows from walking further levels; the example assumes all quoted size remains and excludes fees, latency, cancellations and exit costs.

**Intrabar liquidation illustration.** In a synthetic $100k wallet, take a $100k long and $100k short as separate 10x isolated positions, each with $10k initial margin and an illustrative 0.5% maintenance rate. A temporary mark increase from 100 to 109.452736 crosses the short’s isolated liquidation threshold under a simplified linear-contract equation. If the price returns to 100 before the hourly close, close-only net PnL is zero. If the short was force-closed and does not reopen, the short loss remains realized while the long’s temporary gain disappears, leaving about $90,547.26. This is not an exact MEXC calculation or R198 estimate; actual tiers, fees, funding, liquidation penalties and execution change it.

## Preregistered measurement blueprint

After active frozen work and audit are complete, a new venue-specific lane can separately report (a) forecast/markout at MEXC local prices and (b) executable portfolio PnL. Freeze symbols, target notionals, signal-ready time, entry delay, book-age limit, fee tier, funding schedule and hedge before observation. Capture the sequenced book, trades, mark/index, funding events, contract metadata and local receipt times. For each order size and side, report book-walk VWAP versus arrival mid, fillable fraction, fees separately, funding, partial/rejected exposure and capacity as a share of nearby depth and venue turnover. For account risk, simulate fair-price paths, isolated/cross collateral, tiered IMR/MMR, funding debits, partial liquidation and residual hedge exposure. Keep all of this prospective; no new edge claim follows from the synthetic checks above.

No market book, prices or account data were downloaded or used for these examples, and no orders or backtests were run.
