# R231 partial_execution_v1: fixed partial adjustment of the unchanged R229 spot trend target

- **Registry id:** R231
- Exploratory historical-reuse study, 2026-10-20. Freeze specification and all dependencies below before parsing any cached market prices for this lane. R229's NULL and its already-viewed splits are known inputs, not fresh out-of-sample evidence.
- Two new policy trials: adjustment fraction alpha=0.5 and alpha=0.25. Alpha=1 is the unchanged R229 control, not another strategy search. Do not add fractions, thresholds, horizons, universes, filters or cost assumptions after results.

## Question, source and duplication

Does slower execution of the identical delayed R229 volatility-scaled long/cash target improve returns after costs, without merely looking better because of less risk? R229 tested full daily adjustment versus passive; R213 concerns delayed entries, R217 sizing, and R228 static flow-book blends. Those tests do not settle partial adjustment from drifted holdings. This lane adapts the execution mechanism to R229 because its complete tiny daily cache and self-financing targets are reproducible; the original slow-flow-book version still requires unavailable raw flow targets.

Primary source: Garleanu and Pedersen, *Dynamic Trading with Predictable Returns and Transaction Costs*, NYU public manuscript, cover current version July 21, 2009, https://archive.nyu.edu/bitstream/2451/28346/2/DynamicTrading.pdf . PDF SHA-256: 57dfb02b14775cf6ef79aafc6c55869593df98b0815bb87df63e27c9a456d42a . Verified public PDF, 513,117 bytes. Its abstract and discrete-time proposition describe a weighted combination of current holdings, a no-cost portfolio and expected future targets; its theory uses quadratic costs. Our fixed convex adjustment under proportional crypto fees does not replicate or inherit optimality from that solution. Quantpedia's review in docs/QUANTPEDIA_RESEARCH_REVIEW.md supplied discovery context, not independent evidence.

## Unchanged market inputs, signal and delay

Reuse ONLY the already collected R229 source snapshot: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT Binance spot daily closes, 2021-01-01 through 2026-09-30, exactly 2,099 daily candles per symbol. No network requests, additional history, credentials, model weights or real orders.

Use R229's exact verified loader, complete-calendar/checksum rules, nine stateful close-channel components (5/10/20/30/60/90/150/250/360 days), prior-stop/reset logic, capped 25%/90day sample-volatility multiplier and six equal sleeves. Obtain the unchanged `trend_vol` target matrix from its frozen runner. Do not use the unscaled diagnostic. The return ending at close C[i] trades at C[i-1] using only target[i-2]; no timing acceleration.

Original cache is /workspace/quant-small-data/slow_trend_v1/raw. Verify original frozen R229 spec, pinned data manifest, every source archive and the new frozen runner/dependencies before parsing values. Preserve R229 files and old result provenance unchanged.

## Exact partial-adjustment accounting

Initialize each split/cost account independently with cash=1, units=0. Before the return ending at C[i], mark existing holdings at C[i-1]. Pretrade NAV V=cash+sum(units_j*price_j), drifted pre-cost weights d_j=units_j*price_j/V. For alpha in {1,0.5,0.25}, desired POST-COST weights are

`w_j=(1-alpha)*d_j+alpha*target_j[i-2]`.

Then use the unchanged R229 exact self-financing solver:

`NAV_after + c*sum(abs(w_j*NAV_after-current_dollar_holding_j)) = V`.

Set post-cost holdings to w_j*NAV_after. This is a convex adjustment in pretrade portfolio weights followed by exact post-cost sizing. It is not an assertion that every dollar trade equals alpha times its full-adjustment trade after fees. The old holdings drift before each calculation; do not smooth yesterday's target instead. Target cash is implicit. Scale control targets as specified below, never old holdings. Long-only, no borrowing/leverage/shorts, cash yield zero. All daily executions and initial entries pay costs. If a component target becomes zero, the partial policy decays that holding rather than forcing an immediate signal exit; this residual risk is intentional. All accounts liquidate their remaining units immediately at the final split close, paying full exit costs.

One-way modeled costs c=0.0012/0.0024/0.0036 at 1x/2x/3x (R229's assumed 10bp fee+2bp slippage at 1x). Re-simulate all tiers exactly; do not subtract average costs from a saved return path. These are cost assumptions, not live fee/fill or capacity measurements. Gross contribution and costs each normalize by the account's own preceding NAV, with exact daily identity net=gross-cost_fraction. Report cost savings and foregone gross against both unscaled and risk-scaled full adjustment. They are paired differences of normalized account returns, not common-notional dollar PnL attribution.

## Selection, frozen splits and comparator

Keep R229 splits: discovery 2022-01-01 through 2023-12-31 (730 days); validation 2024-01-01 through 2025-06-30 (547); descriptive known_holdout 2025-07-01 through 2026-09-30 (457). Calendar 2021 supplies warm-up only. Indicators continue through boundaries; holdings always restart cash-only. All dates are historically spent, including the named holdout. No split is a fresh confirmation.

Select exactly ONE new candidate alpha using the highest discovery Sharpe at 2x costs (population-standard-deviation Sharpe, sqrt365 annualization). Compare alpha 0.5 and 0.25 only; exact ties favor 0.5. Zero/undefined risk is INCONCLUSIVE, not permission to choose another policy. Alpha=1 is not in the selection pool.

At discovery 1x only calculate `k=min(1, sample_sd(selected_alpha_net)/sample_sd(full_adjustment_net))`. Nonfinite/zero risk is INCONCLUSIVE. Re-simulate a separate full-adjustment control with target k*R229target, alpha=1, fixed k across all future splits and all cost tiers. This training-fixed cash scale may not match validation realized risk; report actual annual volatility and exposure. The cap prevents leverage; if selected risk is greater than unscaled control risk, report the remaining mismatch instead of fitting a validation scale. Use the scaled FULL-adjustment control for the sole primary validation screen. The unscaled control remains descriptive, and neither unselected alpha nor known_holdout may rescue the primary.

Run four policies (`full`, `half`, `quarter`, `full_matched`) times three splits times three cost tiers: 36 complete accounts and 20,808 daily rows. Compare every unscaled full-adjustment day against the frozen R229 trend_vol archived result for all tiers/splits, all return/cost/turnover/exposure/NAV fields and units; maximum absolute discrepancy must be <=1e-11 or INCONCLUSIVE.

## Primary decision and uncertainty

A PARTIAL exploratory screen requires ALL of:

1. selected alpha's validation 1x Sharpe >= risk-scaled full-adjustment control Sharpe +0.15;
2. selected alpha's validation additive mean net return >0 at 2x costs;
3. selected alpha's validation 1x compound NAV maximum drawdown <= risk-scaled control's;
4. lower endpoint of paired validation 1x mean-net-difference 95% bootstrap interval >0.

Otherwise NULL. Any contract/data/numeric failure is INCONCLUSIVE. No parameter changes or rescue with a different diagnostic after outcomes. PARTIAL is conditional exploratory evidence requiring a new prospective registration; it is not an edge validated for live trading.

Paired circular moving-block bootstrap on selected-minus-risk-scaled-control validation 1x daily net differences: 5,000 replicates, 30-day primary block; fixed seed 20261020231+block. Uniform block starts, wrap within split, concatenate ceil(n/block) blocks, truncate to n. Report nondecisive 10/60day block sensitivities with the same seed rule and 5,000 replicates each. Percentile 2.5/97.5 endpoints. Selection uses only discovery, but prior historical reuse and the project's millions of previous trials prevent interpreting these conditional intervals as selection-corrected significance.

## Saved evidence, verification and limits

Save LF daily CSV with net, gross, normalized/absolute costs, turnover, NAV/cash, exposure, held units, pretrade drifted weights, delayed original targets and executed post-cost weights. Save 36-account metrics with additive mean bp/day, annual arithmetic mean, annual volatility, population-SD Sharpe, NW(10) t, compound DD including initial NAV=1, costs, turnover, mean exposure, ending NAV and coverage. Save paired daily return/gross/cost differences and mean decomposition for both partial policies versus each control at every split/tier, selection scores, train-fixed risk scale, bootstrap/check/verdict JSON, source hashes, software versions and output hashes. Outputs never overwrite; reruns need a fresh --out directory. Integrity failures retain INCONCLUSIVE.

Synthetic tests must cover adjustment from drifted holdings, full-control equivalence to R229, exact post-cost fee/cash equations, initial/final costs, residual holdings, full signal delay, training-only selection/scale and tie rules, paired gross-cost identity, invalid inputs, provenance/output guards and deterministic bootstrap. Independently verify at least one separate fee-solver implementation or original control accounting. Report full test evidence and limitations in FINDINGS.

Fixed six surviving liquid coins, spot traded-close proxies, no point-in-time broader altcoin universe, no funding/futures or measured live fills, no latency/orderbook capacity. This is a cost/execution engineering study of a historical NULL strategy; a positive result cannot turn R229 into a fresh signal discovery. It neither closes the unavailable-flow version nor other execution mechanisms. Register two trials, preserve old frozen specifications and journals, preserve NULL.

## Bound executable and source bytes

Runner SHA-256: 877bd5f471a09c553dbefcfdb075827109f04b11a5a5835827130e85c07560e3
R229 runner SHA-256: 3f5b658dbb9bc6991e2c59507f457e6ff5c5720ef1228d1f2cc23cb83cbf724b
R229 fetcher SHA-256: 3377186f143bcc322d5e3b4bf67adca62edf8087700deef76cdcdfe0f0853f82
R229 specification SHA-256: ad247ec8676b8ae817fea41a6a6a82303cedf298e49cdaaea35bfd55625f169b
Statistics SHA-256: bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34
Preregistration helper SHA-256: 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508
R229 data manifest SHA-256: fc90fe4886608cbc090231374bcaf593082d54959bdc25de2ed1566d86fd42cd
R229 data lock SHA-256: 6abb626838107a3c6755f518f91b09011351a56d75dbf6bf13953275a08e9bda
R229 archived daily SHA-256: 4d879c17c61f3100e7af6ace0d5b5cef22eef7afca24941219f19139d16700fe
