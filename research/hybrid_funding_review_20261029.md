# Hybrid funding forecasts and settlement hops: a bounded research path

**Research note, 2026-10-29.** This is a source-grounded design review, not a new lane, result, account simulation or profitability claim. No market outcomes were calculated and no frozen files or forward journals were changed.

## Recommendation

There is no evidence yet that combining a funding-rate forecast with a settlement hop increases executable account cash. The nearest coherent combination is a **single forecast overlay on the MEXC displayed-rate form of M267**, with the existing venue book, timing and risk gates held fixed. First finish M090’s separate forecast-quality question. Only if a frozen predictor beats both the native displayed quote and a no-change forecast on unseen settlements should it earn a new, separately frozen strategy test.

That sequence matters because R355 already uses MEXC’s native next-settlement `fundingRate`; layering an outside forecast on top without demonstrating incremental information would add complexity without a clear economic role. The closest research precedent, Inan (2026), tests BTCUSDT rates on Binance and Bybit, not MEXC altcoins. Its reported DAR(4)/DAR(6) specifications and certainty-equivalent result are hypotheses for forecast evaluation, not transferable MEXC coefficients or an altcoin profit estimate.

R354’s historical predicted-rate result is a useful context but not confirmation: it passed its frozen gate-0 rule at 1x and 2x, failed at 3x, and concentrated 72% of its sum in ten days. R362 found the Binance post-settlement move largely complete before a safe Binance entry, while R363’s positive Lighter result was not blind to that move. R355 and R364 remain the forward tests; their panels show no scored hops yet. None of these results justifies pooling strategy returns or revising either live rule.

## The one candidate family worth considering

Treat the existing frozen R355 rule as a reference, not as a file to modify. If M090 establishes forecast skill, preregister a new MEXC+Lighter lane on settlements that begin after the new freeze, with only two fixed arms:

| Arm | Signal at the same R355 decision time | Purpose |
|---|---|---|
| **C0 reference** | `e0 = F_displayed − 2h_last`, using MEXC’s point-in-time next rate and Lighter’s last hourly rate, repeated for the two-hour hold | Reproduce the current displayed-rate hypothesis on fresh, executable inputs |
| **C1 forecast overlay** | `e1 = F_hat − 2h_last`, where `F_hat` is the single causal MEXC settled-rate predictor that M090 first validates and then freezes | Ask whether forecasting MEXC’s final event rate changes net account cash beyond the venue quote |

Use the same event eligibility, candidate threshold, direction convention, entry and exit times, position size and hard execution/risk gates in both arms. Keep the displayed quote and every forecast’s first-seen time in the record. Do not add a second model, tune a blend weight, change the threshold, search exits, or select symbols after seeing the new sample. If M090 does not beat both the current displayed-rate forecast and no-change on unseen settled-rate observations, stop before C1’s strategy test.

This is a test of **incremental forecast value**, not a license to add forecast PnL to settlement PnL. For signed base quantity `q` (long positive) and event rate `r`, the event cash is venue-specific. For a linear MEXC position it is `−q × fair_price_at_event × r`; for Lighter it is `−q × index_at_event × r`. For inverse contracts use the venue’s contract-face conversion. Each observed settlement cash flow is posted once against the inventory actually held across its event window. Price PnL comes from the actual entry and exit quantities/fills; fees come from the actual route and executed notionals. Forecasts affect the decision or expected-cash estimate only. They are never a second cash item after the event is settled.

The price response around settlement is also part of PnL, not a second funding credit. The event’s funding payment and the price change that occurs while holding through it may oppose each other. A forecasting paper’s lower rate error, or a historical return around the event, cannot be added on top of realized price and funding cash as independent “yield.” The expected-funding component is `E_t[−q × P_event × r_event]`; if price and rate are related, forecasting rate alone does not estimate the product’s expected cash.

## Economic contract and execution gates

Use one canonical cash ledger, with one row per venue, symbol, position inventory and funding event. Require the event value, rate unit, signed exposure and effective event time to bind before cash is known. Unknown, delayed, conflicting or missing settlement evidence stays **unknown**, never zero. Do not infer a missed payment from an empty history page. Keep each venue’s cash and collateral separate; convert USDT/USDC or other quote assets into a common reporting currency only with a predeclared event-time FX source.

The hard gates should be common to C0 and C1 and fixed before any new forward sample:

- Match the MEXC current quote to its own contract, cycle and `nextSettleTime`; retain the distinct current quote and historical settled-rate records. MEXC documents possible up-to-15-second batch-inclusion ambiguity. Entry exposure must span the full applicable interval before modeling a payment.
- Match the Lighter instrument and funding configuration. Its published methodology is hourly and divides the hourly premium by eight. The funding-payment formula uses the position, event index and hourly rate. Public API field units/asset mapping and the actual application event still require source-bound verification; do not silently treat `market_stats` percent displays as account cash.
- Walk the fixed entry quantity through a sequence-valid, fresh book on each venue. At exit, close the quantity actually held, only against observed available depth. Preserve partial fills, refused exits and residual inventory. Never extend a thin book at its final price. Price the four sides from fills once; charge fees separately on the actual entry/exit quantities and values.
- Apply the actual user route and fee entitlement. MEXC’s June 2026 notice sets API fees at 6 bp maker / 8 bp taker and says API fees override website promotions; its October 26 regional notice says web fees can vary by region and pair. Lighter’s default Standard account has zero regular-order fees, while Plus and Premium/Advanced have nonzero schedules. A public default is not proof of this owner’s account rate.
- Admit a position only when each venue independently has enough funded capital for its own entry requirement, fee/funding reserve and a preregistered adverse-price reserve. Model mark/fair-price losses, initial and maintenance margin, liquidation, funding debits and an unfilled or partial hedge. No cross-venue collateral netting or assumed collateral transfer. Unknown margin/account inputs block an account-cash claim.

No exact account minimum can be stated from the public information reviewed: actual leverage, initial/maintenance margin, liquidation buffer, collateral haircut, route fees, transferability, and owner capital are account-specific or unavailable. For venue `v`, require `C_v >= Σ_i IM_v(N_i) + stress_loss_v + fee_reserve_v + worst_funding_debit_v`, with the per-event position quantities and venue margin schedule frozen before the test. Keep each venue’s required capital separate. For a one-pair-at-a-time paper pilot, **$10,000 total split $5,000 per venue, with one simultaneous $1,000-notional leg per venue** is merely a transparent accounting envelope to evaluate, not an established minimum or owner-approved configuration. It does not validate a five-hop simultaneous portfolio: R355’s five $1,000 same-time candidates use $5,000 nominal exposure per venue before fees and reserve. If actual funded capital cannot support the frozen stress, skip the trade; do not add leverage or top up after the fact.

Report 1x/2x/3x **execution-cost stresses** on spread/impact/fees while holding quantity and settled funding cash fixed. Do not multiply funding cash by the cost stress. Compare C0 and C1 on the same future event set and per-venue capital, cluster uncertainty by settlement time, and show net cash, per-venue NAV, drawdown, failed/partial exits, margin shortfall, and concentration. Use a flat/no-trade account as the capital baseline. A forecast-quality pass is not a strategy pass.

## Falsification and sample discipline

The proposal is falsified or blocked in this order:

1. **Forecast:** C1 does not improve out-of-sample settled-rate prediction versus both the native MEXC displayed quote and no-change, scored once per contract-settlement event with settlement-time dependence. Stop; do not fit another model on the same observations.
2. **Input completeness:** event value, rate units, settlement eligibility, position span, first-seen timing, fee entitlement, valid books or per-venue capital are unresolved. Keep the observation unknown or skip it; do not count it as zero or “on time.”
3. **Net economics:** in the later strategy sample, C1 fails the preregistered 1x/2x net-cash and paired-improvement gates versus C0, or succeeds only through one event/coin. Report 3x and the tail either way. The gate values, sequential looks and multiplicity correction must be set before the first strategy ticket.
4. **Risk:** any venue exhausts its reserved capital or an exit leaves unmodeled inventory. A positive combined mark is not a pass if one venue cannot fund or liquidates its own leg.

Keep the historical R354/R363 observations out of the C1 training and decision sample: their price/event paths and returns have already been read, and R362 read the Binance seconds around R363’s settlements. Keep all R355/R364 prefreeze plumbing and forward observations in their owner-controlled journals; do not train a correction on any forward outcome later used to evaluate it. Train/freeze the predictor on a distinct, explicitly identified past period, then evaluate C0/C1 only on new events first observed after the strategy freeze. If that clean history or a continuous recorder does not exist, the result is “not testable yet,” not a reason to widen the sample.

## Existing R357/R358 boundary

R357/R358 already cover the accounting-engineering gap that this hybrid would otherwise duplicate. They implement and independently check constructed event-bound cash, fixed inventory through exits, visible-depth refusals, fees on changed exit notionals, separate per-venue capital and unknown values. R358 corrects only the checker’s expected boundary admission. Both report zero predictive variants, zero market PnL and zero prospective strategy days; their inputs are invented accounting cases, not evidence of a funding edge. Use that machinery as an accounting prerequisite if adopted, but do not rerun its synthetic controls as strategy evidence or treat its model cash as exchange-account cash.

This audit also found a concrete reason not to reuse frozen R355/R364 scores as account truth: their current rule scores use raw rate fractions against entry notional; missing settlement rows become zero (R355’s empty sum; R364’s flagged 24-hour fallback). R357’s corrected model requires event fair/index values, actual fixed inventory and unknown-preserving cash. That correction belongs in a **new** preregistered prospective lane; R355 and R364 stay byte-for-byte frozen.

## Read scope and open data requirements

The comparison was bounded to `experiments/settlehop_fwd/PREREG.md` (R355: MEXC displayed next rate minus twice the last Lighter hourly rate; decision at `T−1h+20s`, entry after decision, exit at `T+1h`, $1,000 legs, up to five hops, and venue/account cost reporting), `experiments/settlelit_fwd/PREREG.md` (R364: Binance predicted-rate signal at `r−2h`, Lighter entry `T−10s`, exit `T+60s`, $1,000, with Binance signal-only), the R357/R358 description and checks in draft PR #56, `docs/PERP_CARRY_ACCOUNTING.md`, `docs/PERP_EXECUTION_AND_RISK.md`, and the M090/M267 entries in `registry/methods.csv`. The account-specific MEXC fee tier, actual route, Lighter user fee tier, symbol/contract multiplier, event-time index/fair-price observations, API units-to-account-payment bridge, per-venue margin schedule, collateral haircut, and funded capital are still required before any account-cash estimate. I did not fetch private account data, call trading APIs, or recalculate outcomes.

## Primary sources

**Official venue documentation**

- MEXC, [Funding Rate](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280), sections 4–5: positive-rate payer direction, contract-specific schedules, and batch-inclusion timing; and [Calculation Guide](https://www.mexc.com/support/article/mexc-futures-calculation-guide-312060306409668608), funding/trading-fee formula examples.
- MEXC API, [current funding rate](https://www.mexc.com/api-docs/futures/market-endpoints/get-funding-rate), [funding history](https://www.mexc.com/api-docs/futures/market-endpoints/get-funding-rate-history), [contract info](https://www.mexc.com/api-docs/futures/market-endpoints/get-contract-info). The live rate/cycle/next-time and the settled-rate history are separate records.
- MEXC, [API Futures fee notice, effective 2026-06-01](https://www.mexc.com/announcements/article/updates-to-api-futures-trading-fees-jun-1-2026-17827791535742), and [selected-region fee updates, effective 2026-10-26](https://www.mexc.com/announcements/article/adjustments-to-trading-fees-on-btc-wld-and-14-other-futures-in-selected-countries-and-regions-17827791539309).
- Lighter, [Funding](https://docs.lighter.xyz/trading/funding), sections Overview, Funding Rate Calculation and Funding Payment; [Trading Fees](https://docs.lighter.xyz/trading/trading-fees), account-type schedule; and [WebSocket API reference](https://apidocs.lighter.xyz/docs/websocket-reference). The public funding methodology is not, by itself, proof of the API field-to-account-cash unit bridge.
- Binance, [Funding Fee FAQ](https://www.binance.com/en/support/faq/detail/360033525031): the stated deviation of actual transaction timing from the nominal funding time. Relevant to event anchors, not a funding leg in R364.

**Primary research**

- Inan (2026), [“Predictability of Funding Rates”](https://doi.org/10.1016/j.irfa.2026.105464), *International Review of Financial Analysis*. The reported out-of-sample setting is BTCUSDT on Binance/Bybit, with DAR forecasts and a certainty-equivalent comparison to no-change. It motivates forecast-vs-baseline scoring, not model transfer to MEXC/Lighter alts.
- Schmeling, Schrimpf & Todorov, [“Crypto Carry”](https://doi.org/10.1287/mnsc.2024.05069), *Management Science*. Carry can compensate for leveraged trend demand and limits to arbitrage; a large funding spread is not a risk-free yield.
- Ackerer, Hugonnier & Jermann, [“Perpetual Futures Pricing”](https://doi.org/10.1111/mafi.70018), *Mathematical Finance*. The pricing framework distinguishes contract and funding conventions; it supports instrument-specific accounting, not an empirical strategy return.
- Albers et al. (2025), [live market-order execution study](https://doi.org/10.1080/14697688.2025.2515933), *Quantitative Finance*. Live Bybit/Binance results motivate separating arrival-price cost, fill probability and post-fill markout. Their venues and sizes do not calibrate a MEXC altcoin fill model.
- Erez & Smirnov (2026), [“Funding Timing and No-Arbitrage Bounds in Decentralized Perpetual Markets”](https://ssrn.com/abstract=6805838), working paper. Its key transferable constraint is information timing: a forecast of a later, uncertain funding event is expected cash, not guaranteed opening value.

**Project records:** [M267 and M090 status](../registry/methods.csv), [R355 specification](../experiments/settlehop_fwd/PREREG.md), [R364 specification](../experiments/settlelit_fwd/PREREG.md), [funding accounting review](../docs/PERP_CARRY_ACCOUNTING.md), [execution and risk review](../docs/PERP_EXECUTION_AND_RISK.md), and [draft PR #56, including R357/R358](https://github.com/SaikiK12/T/pull/56).
