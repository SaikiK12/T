# Perpetual carry: forecasts, settlements and exact PnL

Reviewed 2026-10-19. The project has Binance spot–perpetual carry experiments, but its own findings already describe paired fills and squeeze risk as assumptions. This note updates the outside reading and highlights accounting needed before transferring any result to another venue. It is research guidance only; no frozen lane or return result is changed.

## New evidence worth carrying forward

- Schmeling, Schrimpf and Todorov’s peer-reviewed [*Crypto Carry*](https://doi.org/10.1287/mnsc.2024.05069), *Management Science* (online 2026; earlier BIS paper in the repository), documents large and volatile crypto futures–spot carry. The authors link variation to leveraged trend-following demand and limits to arbitrage. This frames high carry as compensation for risk and financing frictions, not a dependable yield. The study does not validate the project’s venue, fills or altcoin capacity.
- Inan’s [“Predictability of Funding Rates”](https://doi.org/10.1016/j.irfa.2026.105464), *International Review of Financial Analysis* (2026), evaluates BTCUSDT funding on Binance and Bybit over 384 out-of-sample periods from 2024-11-10 to 2025-03-17. Double-autoregressive models improve one-step rate forecasts against a no-change benchmark, with stability varying across periods. Forecasting the next rate is not forecasting net return: realized basis movement, funding settlement, fees and funding-cycle changes still matter.
- Erez and Smirnov’s [May 2026 SSRN working paper, “Funding Timing and No-Arbitrage Bounds in Decentralized Perpetual Markets”](https://ssrn.com/abstract=6805838) distinguishes funding known or guaranteed when a trade opens from funding determined later. Only the former belongs in a one-period bound. Its empirical venues are Drift and dYdX, so its key use here is the information-timing principle, not a CEX return result. As of this review date, the retitled journal version is assigned to the November 2026 issue and is not counted here as already published evidence.
- Zhivkov’s [“The Two-Tiered Structure of Cryptocurrency Funding Rate Markets”](https://doi.org/10.3390/math14020346) studies 26 exchanges over eight days; reported large cross-venue funding spreads often do not survive costs and spread reversal. The window is too short to establish persistence, but it cautions against treating a displayed funding difference as locked arbitrage.
- Ackerer, Hugonnier and Jermann’s peer-reviewed [“Perpetual Futures Pricing”](https://doi.org/10.1111/mafi.70018) (2025/2026) treats linear, inverse and quanto contracts and shows funding conventions affect no-arbitrage pricing. It is a contract-pricing framework, not empirical evidence of a strategy edge.

## Venue accounting to freeze

For a linear USDT contract, let `q` be signed base quantity (long positive, short negative), `P` fair price, and `r` a positive settled funding rate. The account cash flow is `−q × P × r`: longs pay, shorts receive. For a contract-denominated venue, first convert contracts into the contract’s base or quote exposure using its current contract-size and quantity-step fields. Do not reuse this linear formula for inverse/quanto instruments without the correct multiplier and settlement asset.

Use the rate known at entry only for an entry-time forecast. For realized PnL, apply each actual settled rate to the position exposure that was open at that settlement, with the contract’s own cycle and fair price. Do not charge a full interval to a trade that closed beforehand. Record event time, funding cycle, symbol, position side/quantity, settlement price and fee. A current/next predicted rate and a historical settled rate are different data fields.

MEXC documents that positive funding is paid by longs to shorts and exposes `collectCycle` per contract; the public endpoint supplies current rate and next funding time, while the history endpoint records settled rates. The exchange says settlement can be delayed by up to 15 seconds. Do not assume every instrument settles every eight hours. See the official [funding guide](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280), [current rate endpoint](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate), [funding history](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history), and [contract metadata](https://www.mexc.io/api-docs/futures/market-endpoints/get-contract-info).

There is a second accounting distinction in the current repo: the R190 implementation uses `−Δ(perp/index − 1)` as a basis component, a small-move proxy rather than a leg-by-leg account ledger ([`lab/carry.py`](../lab/carry.py)). In a synthetic example with spot 100→110 and premium 1%→5%, the proxy is −4% of initial spot notional, while buying one spot unit at 100 and shorting one perp at 101, then closing at 110 and 115.5, yields exact paired price PnL of −4.5% of initial notional. This does not show that R190’s finding changes; it identifies the approximation and motivates exact contract-level quantities for a future account-PnL test. Leave the frozen lane untouched.

## Synthetic checks (no market data)

MEXC’s contract-info example uses a BTC contract size of 0.0001 BTC. Twenty thousand such contracts represent 2 BTC; at a hypothetical fair price of 50,000 USDT, notional is 100,000 USDT. At a positive settled rate of 0.01%, a short receives 10 USDT and a matching long pays 10 USDT before fees. A short closed before settlement receives no payment under the ordinary rule, subject to the venue’s documented settlement delay.

The arithmetic was checked with synthetic values only. It is not a MEXC statement, historical rate, or profitability estimate. The R190 proxy comparison above was also synthetic.

## Practical next use

For any future carry lane, compute position PnL from actual entry/exit prices and quantities, separately add each settled funding cash flow and fee, and report gross basis, realized funding, execution and net PnL independently. Store funding-cycle metadata and use venue-specific fair/mark prices. Freeze these choices before the test. A paper result still needs capacity and liquidation modeling; carry does not cap drawdown.

## Sources

- [Crypto Carry](https://doi.org/10.1287/mnsc.2024.05069)
- [Predictability of Funding Rates](https://doi.org/10.1016/j.irfa.2026.105464)
- [Funding Timing and No-Arbitrage Bounds in Decentralized Perpetual Markets](https://ssrn.com/abstract=6805838) (working paper, posted 2026-05-21)
- [The Two-Tiered Structure of Cryptocurrency Funding Rate Markets](https://doi.org/10.3390/math14020346)
- [Perpetual Futures Pricing](https://doi.org/10.1111/mafi.70018)
- [MEXC funding guide](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280)
- [MEXC current funding rate](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate)
- [MEXC funding history](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history)
- [MEXC contract metadata](https://www.mexc.io/api-docs/futures/market-endpoints/get-contract-info)
