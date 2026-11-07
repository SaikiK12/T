# Perpetual carry: forecasts, settlements and exact PnL

Originally reviewed 2026-10-19; settlement-accounting addendum 2026-10-29. The project has Binance spot–perpetual carry experiments, but its own findings already describe paired fills and squeeze risk as assumptions. This note updates the outside reading and highlights accounting needed before transferring any result to another venue. It is research guidance only; no frozen lane or return result is changed.

## New evidence worth carrying forward

- Schmeling, Schrimpf and Todorov’s peer-reviewed [*Crypto Carry*](https://doi.org/10.1287/mnsc.2024.05069), *Management Science* (online 2026; earlier BIS paper in the repository), documents large and volatile crypto futures–spot carry. The authors link variation to leveraged trend-following demand and limits to arbitrage. This frames high carry as compensation for risk and financing frictions, not a dependable yield. The study does not validate the project’s venue, fills or altcoin capacity.
- Inan’s peer-reviewed [“Predictability of Funding Rates”](https://doi.org/10.1016/j.irfa.2026.105464), *International Review of Financial Analysis* (2026), studies BTCUSDT funding on Binance and Bybit. The publisher’s accessible text reports 912 initial observations and 384 out-of-sample observations (2024-11-10 to 2025-03-17), with univariate double-autoregressive forecasts; its selected orders are DAR(4) for Binance and DAR(6) for Bybit. Rolling estimates have lower MSPE while expanding estimates have higher directional accuracy, and the reported predictability varies by venue and market regime. The article also describes a cross-exchange exercise evaluated with certainty-equivalent returns against a no-change benchmark, and reports statistical and economic predictability over that OOS period. Its full text returned 403 in this review, so the exact fee schedule, leverage, account-level margin path and intraperiod solvency assumptions could not be verified. This is a useful forecast-and-utility design reference, not proof of executable MEXC altcoin PnL; do not transfer its fitted order or economic result to this project.
- Pindza’s open-access 2026 [CEX–DEX funding-arbitrage risk study](https://doi.org/10.1007/s42521-026-00213-3), *Digital Finance*, provides a useful accounting checklist and a cautionary headline. Its reported 102.75% annualized net result comes from Binance BTC/ETH/SOL funding paired with **synthetically constructed** DEX rates, a baseline 3× leverage, 5 bp slippage per transaction and $50 per DEX trade; observed dYdX funding is only a narrower 1,104-window robustness exercise, without venue-specific execution, collateral or transfer costs. The paper itself says these returns are assumption-sensitive and not directly achievable live PnL. Its transferable value is to separate funding, basis, liquidity, liquidation and settlement risk; the return number is not a Lighter result or a MEXC opportunity.
- Erez and Smirnov’s [May 2026 SSRN working paper, “Funding Timing and No-Arbitrage Bounds in Decentralized Perpetual Markets”](https://ssrn.com/abstract=6805838) distinguishes funding known or guaranteed when a trade opens from funding determined later. Only the former belongs in a one-period bound. Its empirical venues are Drift and dYdX, so its key use here is the information-timing principle, not a CEX return result. As of this review date, the retitled journal version is assigned to the November 2026 issue and is not counted here as already published evidence.
- Zhivkov’s [“The Two-Tiered Structure of Cryptocurrency Funding Rate Markets”](https://doi.org/10.3390/math14020346) studies 26 exchanges over eight days; reported large cross-venue funding spreads often do not survive costs and spread reversal. The window is too short to establish persistence, but it cautions against treating a displayed funding difference as locked arbitrage.
- Ackerer, Hugonnier and Jermann’s peer-reviewed [“Perpetual Futures Pricing”](https://doi.org/10.1111/mafi.70018) (2025/2026) treats linear, inverse and quanto contracts and shows funding conventions affect no-arbitrage pricing. It is a contract-pricing framework, not empirical evidence of a strategy edge.

## Venue accounting to freeze

For a linear USDT contract, let `q` be signed base quantity (long positive, short negative), `P` fair price, and `r` a positive settled funding rate. The account cash flow is `−q × P × r`: longs pay, shorts receive. For a contract-denominated venue, first convert contracts into the contract’s base or quote exposure using its current contract-size and quantity-step fields. Do not reuse this linear formula for inverse/quanto instruments without the correct multiplier and settlement asset.

Use the rate known at entry only for an entry-time forecast. For realized PnL, apply each actual settled rate to the position exposure that was open at that settlement, with the contract’s own cycle and fair price. Do not charge a full interval to a trade that closed beforehand. Record event time, funding cycle, symbol, position side/quantity, settlement price and fee. A current/next predicted rate and a historical settled rate are different data fields.

MEXC documents that positive funding is paid by longs to shorts and exposes `collectCycle` per contract; the public endpoint supplies the current rate, next funding time and current fair price, while the history endpoint records settled rates and `settleTime`. Do not assume every instrument settles every eight hours. The official guide says settlement may be delayed by up to 15 seconds, and a position opened shortly after the scheduled time can still be included. See the official [funding guide](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280), [current rate endpoint](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate), [funding history](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history), and [contract metadata](https://www.mexc.io/api-docs/futures/market-endpoints/get-contract-info).

There is a second accounting distinction in the current repo: the R190 implementation uses `−Δ(perp/index − 1)` as a basis component, a small-move proxy rather than a leg-by-leg account ledger ([`lab/carry.py`](../lab/carry.py)). In a synthetic example with spot 100→110 and premium 1%→5%, the proxy is −4% of initial spot notional, while buying one spot unit at 100 and shorting one perp at 101, then closing at 110 and 115.5, yields exact paired price PnL of −4.5% of initial notional. This does not show that R190’s finding changes; it identifies the approximation and motivates exact contract-level quantities for a future account-PnL test. Leave the frozen lane untouched.

## Settlement-price scaling and missing settlement records

For a linear contract with signed base quantity q (long positive), positive funding rate r when longs pay, and
settlement reference price P_s, settled cash is -q × P_s × r. If a report normalizes this cash by entry notional
|q| × P_0, its return contribution is -sign(q) × r × (P_s / P_0). Apply each venue's settlement price and
position quantity separately. Adding ±r directly to a return on entry notional assumes the settlement price equals
the entry price. Lighter's official [funding overview](https://docs.lighter.xyz/trading/funding) and [funding-rate
calculation](https://docs.lighter.xyz/trading/funding#funding-rate-calculation) specify settlement payment using the
index price; its rate is hourly and is not interchangeable with an 8-hour quote.

MEXC's official [funding guide](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280)
states that for stablecoin-margined contracts, funding fee is position value × rate and position value is base-asset
quantity × fair price. Thus signed cash is `−q × P_f × r`, where `P_f` is the fair price used for that funding event;
normalized by entry notional `|q| × P_0`, it is `−sign(q) × r × (P_f / P_0)`. Convert API contract counts to
base-asset quantity using the symbol's `contractSize`. Coin-margined futures use MEXC's separately documented
inverse formula. The MEXC history endpoint returns rate, `settleTime` and cycle, but not position-specific cash or a
historical event fair-price field. The formula is established; an event-aligned fair price, exact inclusion boundary
and account ledger still require evidence. The guide also says settlement can be delayed up to 15 seconds and
positions opened just after scheduled settlement can still be included, so a nominal timestamp alone does not
establish whether a position crossed funding.

A missing settlement row is not evidence that the rate was zero. Resolve it against an authoritative settlement record,
or retain it as unknown and block the affected score. If a frozen rule has already chosen a fallback, keep its journal
and verdict rule intact; any corrected accounting is a new, pre-registered lane.

## M090: prospective MEXC rate-forecast validation

The existing queue item [M090](../registry/methods.csv) is already the relevant project lane: “MEXC next-funding-rate
revision vs no-change forecast of the settled rate.” Do not add a duplicate method. The paper above forecasts next
period rates from settled BTC histories; M090 instead needs a point-in-time archive of MEXC's displayed rate and a
settled-rate label for the same contract and settlement event. That is a related hypothesis, not a direct replication.

The repo's [`record_mexc_ticker.py`](../scripts/record_mexc_ticker.py) writes a MEXC snapshot when invoked, at most
once per UTC hour. It stores the displayed `fundingRate`, minimum and maximum rates, `collectCycle`,
`nextSettleTime`, exchange timestamps, `recv_ms`, and ticker fair/index prices and top bid/ask. The script does not
schedule itself, and an hourly snapshot cannot establish the fair price at every settlement event. The official MEXC
API exposes the current rate separately from settled-rate history, whose records carry `settleTime`; MEXC does not
expose history for past displayed-rate snapshots. Code and a field list do not establish continuous, timely data:
the latest panel still marks `REC_TICKER` data UNVERIFIED, so M090 remains blocked until receipts, coverage, symbol
identity, event prices and settlement joins are checked.

Before a forecast test, freeze one lead-time rule and one event-level scoring unit. Join each pre-settlement snapshot
to the subsequent settled rate, compare a proposed forecast with the no-change forecast using the same as-of snapshot,
and report the loss difference per settlement event. Do not treat every hourly snapshot of one settlement as an
independent label or fill missing settlements with zero. A forecast can improve a carry ledger's expected funding
cash; it is not a trading signal until a separately registered policy shows that any changed holding or exit decision
improves net account PnL after actual exposure, basis, execution, fees, margin and liquidation risk.

**Read-only review of the current forward rules (2026-10-29):** R355's scripts/settlehop_rule.py sums raw settlement
rates into entry-notional returns; an absent row contributes zero through sum([]). R364's
scripts/settlelit_fwd_rule.py likewise applies raw Lighter rates without the settlement-index / entry-price ratio,
and after its fixed 24-hour wait it scores a missing row as zero while flagging it. Its current journal reports no
scored hop yet; this note does not change either frozen rule or any result. R355 also includes MEXC rates, and its
raw-rate return scaling omits the fair-price-to-entry-price factor in MEXC's stablecoin-margined funding formula.
The event fair price and actual inclusion timing have not been reproduced for R355. A separate freeze and owner
review are needed before any accounting correction can be tested.

## Synthetic checks (no market data)

MEXC’s contract-info example uses a BTC contract size of 0.0001 BTC. Twenty thousand such contracts represent 2 BTC; at a hypothetical fair price of 50,000 USDT, notional is 100,000 USDT. At a positive settled rate of 0.01%, a short receives 10 USDT and a matching long pays 10 USDT before fees. A short closed before settlement receives no payment under the ordinary rule, subject to the venue’s documented settlement delay.

The arithmetic was checked with synthetic values only. It is not a MEXC statement, historical rate, or profitability estimate. The R190 proxy comparison above was also synthetic.

## Practical next use

For any future carry lane, compute position PnL from actual entry/exit prices and quantities, separately add each settled funding cash flow and fee, and report gross basis, realized funding, execution and net PnL independently. Store funding-cycle metadata and use venue-specific fair/mark prices. Freeze these choices before the test. A paper result still needs capacity and liquidation modeling; carry does not cap drawdown.

## Sources

- [Crypto Carry](https://doi.org/10.1287/mnsc.2024.05069)
- [Predictability of Funding Rates](https://doi.org/10.1016/j.irfa.2026.105464)
- [CEX–DEX funding-rate arbitrage risk study](https://doi.org/10.1007/s42521-026-00213-3)
- [Funding Timing and No-Arbitrage Bounds in Decentralized Perpetual Markets](https://ssrn.com/abstract=6805838) (working paper, posted 2026-05-21)
- [The Two-Tiered Structure of Cryptocurrency Funding Rate Markets](https://doi.org/10.3390/math14020346)
- [Perpetual Futures Pricing](https://doi.org/10.1111/mafi.70018)
- [MEXC funding guide](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280)
- [MEXC current funding rate](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate)
- [MEXC funding history](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history)
- [MEXC contract metadata](https://www.mexc.io/api-docs/futures/market-endpoints/get-contract-info)
- [Lighter funding overview and rate calculation](https://docs.lighter.xyz/trading/funding)
