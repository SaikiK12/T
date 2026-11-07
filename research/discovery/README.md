# Discovering equations without counting aliases as discoveries

Engineering workbench, 2026-11-03. No market fit, forecast result, PnL or
prospective observation. This note is a design and source receipt, not a frozen
market experiment or another method queue.

## What remains discoverable

The [canonical global edge map](../../docs/EDGE_MAP.md) places all methods and
rounds in32families. The [data/equation lenses below](#global-mechanism-data-equation-map)
complement that generated view with observation requirements; they are not
a second family placement or queue.
The [source capability receipt](../intake/market_inputs_20261104/source_capabilities.json) separates documented,
qualified and acquired data, retaining unknown retention, clocks and settlement
mechanics. R403 qualifies two fixed archive objects only, not a full history.

We have not interpreted every useful aspect of charts. Two distinct limits
matter: a representation may hide information that the underlying observations
contain, and an observation may never have recorded the information at all.

For example, the invented price sequences `100,110,90,105` and
`100,90,110,105`, each with four unit-volume trades, have identical OHLCV:
`100,110,90,105,4`. Their order and total variation (45 versus 35) differ. No
function of that single candle alone can always reconstruct which sequence
occurred. Finer tape can distinguish them; a new indicator on the same candle
cannot recover the lost order. Neither distinction proves future predictability.

New representations can still help a restricted model exploit information it
already observes. A sequence of candles has information beyond one candle;
cross-market context, book additions/cancellations, arrival times and public
events supply other observations. More elaborate formulas alone do not supply
new observations or establish an executable edge.

The project's completed [R386 screen](../../experiments/atlas_tape_v1/FINDINGS.md)
closed its declared 303,520-cell grid with a NULL verdict. It did not test every
path representation, conditional model or equation. Its scaled return/flow
divergence already covers part of a simple "price versus flow residual" idea;
renaming that idea would not open a new mechanism. The frozen R310/R311
`equations` lanes are fixed funding/basis models, not a general symbolic search.
The live queue remains [registry/methods.csv](../../registry/methods.csv).

## Distinct equations, distinct information, distinct bets

These are three separate questions. Algebraic differences can be cosmetic.
Writing `L=(C-Low)/(High-Low)`, close location value is `CLV=2*L-1`.
Consequently `L > 0.8` and `CLV > 0.6` select exactly the same observations when
the range is nonzero and the same inputs are available. Counting them as two
independent signals manufactures diversity. Correlation on a particular sample,
however, is not a proof of an identity, and algebraically different signals may
still produce highly dependent bets.

There is also the useful meaning of repetition: a state or event sequence
recurs and its subsequent response is sufficiently stable to predict. Search
for conditional transitions (pressure, absorption, refill, continuation or
reversal), not merely visually similar shapes. Compare response distributions
and waiting times against matched baseline states. A frequent pattern can have
zero expected net payoff; a rare one may be impossible to establish with the
available sample. Regime and scale stability must be measured, not assumed.

[lab/formula_space.py](../../lab/formula_space.py) supplies a small exact rational
grammar with `+,-,*,/`, declared units, nonnegative lags and a common clock.
It proves identities through polynomial cross multiplication and can prove
positive affine threshold aliases. Required input sets and nonzero-denominator
guards must match: `x/x` does not become an unconditional `1`, and `x-x` does
not turn a missing observation into an observed zero. Invalid inputs remain
unknown. Guard proofs are deliberately incomplete; some equivalent formulas
will remain separate. Arithmetic equivalence is rational, not IEEE bit equality.

The deterministic factory accepts primitive expressions and budgets, never a
target or return series. Limits cover expression nodes, polynomial terms and
operator attempts. It counts admissions, rejected operations and duplicates.
Pruning parent aliases defines this generator's bounded space; it is not an
exhaustive listing of every raw expression tree. Counts cannot retroactively
erase any historical program trials. Units and clocks are caller declarations,
not authentication of feeds, availability or causal joins.

Run the entirely invented demonstration with:

```sh
python scripts/demo_formula_discovery.py
python -m unittest tests.test_formula_space
```

The [saved receipt](formula_demo_20261103.json) records 471 attempted admissions
or operations: 132 retained forms, 210 proven duplicate attempts and 129 invalid
attempts. The family was generated before the invented target was inspected.
Ranking on nine invented points recovers `x/(1+z)` and agrees exactly on nine
additional invented points. These 132 forms are not 132 statistically independent
signals, nor a proof of global uniqueness. The example confirms a narrow
engineering capability, not market discovery. An optional `--output NEW_PATH`
writes exclusively and refuses to replace an existing receipt.

## Mechanism to investigate next

An interesting question is whether the **order of pressure and price response,
conditional on liquidity recovery**, adds information beyond existing state
variables. Does buying precede a move, or chase it? After consumption, does
opposite-side depth recover before the next decision? Does the apparent effect
remain after conditioning on spread, volatility, venue disagreement and feed
freshness? These are hypotheses, not observed effects.

For dimensionless price and cumulative-flow paths `p_i,q_i` observed by the
decision cutoff, an elementary representation is the oriented area closed back
to its start. With `u_i=p_i-p_0` and `v_i=q_i-q_0`:

```text
A_t = 1/2 * sum_i (u_i*v_(i+1) - v_i*u_(i+1))
```

In the toy example, flow first gives area `-1/2` and price first `+1/2` for the
same endpoints. Swapping coordinates changes the convention. The sign does
not prescribe a trade or prove causation. `signed_area` is polygon geometry,
not an invention of new mathematics or a full signature library. It cannot
certify event ordering; interpolation, simultaneous updates and arrival-time
joins must be fixed by a causal adapter. Area alone also discards speed;
recorded elapsed time and freshness need separate treatment.

A prospective model could ask whether `A_t` and an explicitly defined refill
state add incremental prediction to the frozen baseline of returns, order-flow
imbalance, spread and depth. Equation search would then operate over a small,
mechanism-specific grammar, rather than every indicator combination. A
contemporaneous fit explaining a completed price move is insufficient: the
target must begin after decision, computation and feasible order arrival.

This belongs near the existing **M430** competing-event transition and **M433**
arrival-state execution scopes; it is not a new duplicate method id. M431's
latency frontier is binding for fast candidates. Recorded public depth cannot
establish our private queue position. No market adapter, new lane or scoring
run is included here, and no reserved sample has been opened for this work.

## From an original idea to credible evidence

Before the first market fit, a new preregistration must freeze the exact input
availability rules, units/scales, path construction, event/missingness masks,
mechanism baseline, grammar, operator and complexity budgets, all tuning and
selection rules, chronological splits, labels, null procedure and cost model.
Record the whole search, including unsuccessful attempts. A fixed training
procedure can then select an expression; freeze its resulting artifact by the
declared rule before evaluating untouched observations. Existing inspected
history cannot be relabeled untouched by changing the formula.

Evaluate incremental prediction and executable net returns against the parent,
simple controls and cost stress, including spread, walking the book, fills,
latency and comparable capital/risk. Use clustered evidence and effect-size
intervals: overlapping trades are not independent observations. Plan the
minimum detectable effect and stop rules before seeing results. Repeat only
according to that plan, then require genuinely prospective paper evidence under
the project's existing gates. A NULL closes that tested scope; it cannot justify
unregistered threshold rescue.

Originality has levels: new to this repository, absent from the public sources
actually checked, and unknown to every other trader. Only the first two can be
investigated here; private strategies make the third impossible to certify.
The useful objective is a distinct, reproducible mechanism with incremental net
value, whether its mathematical tools are old or new.

<a id="global-mechanism-data-equation-map"></a>

## Data and equation lenses for the canonical edge map

Added2026-11-04, reconciled with the32-family map at `ea75165`. These fourteen
observation/representation lenses cut across the canonical families; they are
not exhaustive and do not assign an alternative family or status to a method.
[methods.csv](../../registry/methods.csv) and native PREREG/FINDINGS govern status.
Every row links an information requirement to a mechanism and a falsifiable
model. An equation can describe a market without predicting its future.

Let `t` be decision time using information actually received by then, and
`tau=t+computation+feasible order arrival`. Predictive targets start after `tau`.
The common clock, units, identity, missingness and source vintage require an
explicit input contract; a provider's timestamp is not automatically that clock.

| Family / existing method anchors | Minimum observations | Equation or quantity to investigate | What could invalidate it |
|---|---|---|---|
| **Path order / geometry** (B1/B4/L2/M3) — M299, M430/M433; M201/M412 controls | Ordered prices and signed flow, receipt clocks, sequence/gap flags; completed bars for coarser controls | The signed area already defined above, plus elapsed time and refill state | Adds no held-out prediction beyond returns/OFI/spread/depth, or effect disappears by order arrival. Same OHLCV cannot reveal lost event order. R400 remains terminal REFUSED. |
| **Conditional price dynamics** (B1/B2/R3) — M014/M298/M314/M412 | Prior prices, extrema, volatility and causally fitted residuals | `E[Delta z(tau,h) | z_t,X_t] = -b_h*z_t + gamma_h*X_t` | Reversion/continuation fails on later data or cannot pay turnover. A fitted restoring coefficient is not proof of an economic restoring force. |
| **Flow and impact** (F1/L2) — M081/M084/M264 | Sequenced bid/ask prices AND sizes, trades and aggressor semantics | Forward hypothesis `E[Delta m(tau,h)] = a_h + b_h*OFI(t-w,t)/D_t` | Only concurrent explanation survives, or delay/spread removes net value. Trade delta is not book-event OFI; coarse bars cannot reconstruct it. |
| **Refill / depletion / absorption** (P4/L2) — M087/M227/M306/M433/M437 | Same-price book changes and trades; order IDs and initial state when claiming queue mechanics | `E[D(t+u)|D_t] = Dbar_t + (D_t-Dbar_t)*exp(-kappa*u)` after a fixed depletion event | Refill adds no forward information beyond activity/spread/volatility. Public net L2 changes do not identify cancellation location or our fills. |
| **Cross-venue discovery / quote basis** (L1/L2/R1/R2) — M056/M239/M425/M430/M431/M434/M443/M447 | Arrival-ordered executable books, units, quote-currency instrument, mark/index and sessions | `x_a=log(m_a,USDT/m_a,USDC)`; separate common quote component `c_t` from residual `x_a-c_t` | Residual is stale feed/common currency movement, or disappears after feasible latency. USDCUSDT perp is not spot FX; convergence is not assured arbitrage. |
| **Funding formation / revision** (P3/E1) — M090/M172/M409/M410 | Displayed-rate vintages, premium samples, contract interval/caps, next payment and first receipts | `fhat_T(t)=g_venue,version(Pbarhat_T(t), interest, interval, caps)` | Cannot beat the locked previous-settled baseline; forecasting skill still needs a separate costed policy. Hourly premium bars do not reproduce exact fine-sample integration. |
| **Carry / lifecycle / capital** (P1/P2/M1/M2/V1) — M047/M059/M134/M244/M265/M409; M468–M470 corrections | Fixed signed quantities, executable entry/exit, payment marks/rates, lifecycle and separate venue balances | Linear-contract cash identity: `Pi=sum_v q_v*(Pout-Pin)-sum_v,k q_v*M_v,k*f_v,k-C` | Vanishes with fixed quantities, actual coin costs, dead-leg splits or collateral requirements. Inverse contracts need another cash converter; margin neutrality is not risk neutrality. M468 is Claude's claim. |
| **Settlement / roll / expiry / dividend** (E1/E5/R2) — M135/M303/M317/M440/M460–M463; M471/M472 | Official schedules AND revisions, actual eligibility/payment times, index weights, books, named timezones/DST | Published roll identity `Delta I_T=Delta w_T*(Fnext-Ffront)` | Adjustment precedes entry or funding/premium/full cashflow offsets the apparent gain. A known index move is not free wealth. Frozen R389 windows remain authoritative. |
| **Public information / revisions** (E3/E4/E6) — M057/M060/M279/M280/M290/M444/M453/M454 | Original release/notice, local first-seen, consensus available before release, revisions and symbol map | `E[r(tau,h)] = beta_h*(release-consensus_before)+gamma_h*revision_surprise` | Fails matched-clock/placebo controls, first-seen delay, event clustering or cost. Archive dates and final revised data do not prove historical availability. |
| **Volatility / risk sizing** (P5/M2) — M018/M185/M455; M131 overlays | Completed fine returns or an explicitly coarse RV proxy, funding vintage and forecast origin | `RVhat(t+1)=b0+bd*RV_t+bw*mean_5(RV)+bm*mean_22(RV)+bf*f_t` | No out-of-sample loss improvement over locked baseline; separately no risk-matched net sizing improvement. Variance forecast is not direction or expected return. |
| **Options / hedge inventory** (F3/P5/P4) — M058/M099/M300/M308/M309/M310/M456 | Full timestamped chain, bid/ask IV, Greeks, OI, multiplier/trades; own inventory for own controller | Hedge-response hypothesis `Delta H ~= -G*Delta S - V*Delta sigma - C*Delta t` with declared units | Entire effect depends on invented dealer side or adds no forward information. OI does not identify dealer ownership or opening/closing flow. Own-inventory models cannot infer others' positions. |
| **Liquidation / margin feedback** (E2/M2) — M021/M031/M070/M140/M176/M177/M265/M435 | Forced prints with side semantics, mark/index, OI, depth, maintenance tiers, collateral and receipt clocks | Account barrier `equity_v - maintenance_v - close_cost_v <= 0`; separate burst-response hypothesis | Apparent effect is lag/volatility or a margin breach occurs first. Wicks/OI do not uniquely identify liquidation; batched feed order is unresolved within a batch. |
| **Regime / adaptation** (M3/M2) — M026/M032/M041/M158/M287 | Past errors, feature distributions, returns/risk and switching costs | Causal filter `P(state_t|x_<=t)` from prior transition probabilities and current likelihood | Switching fails random-off or fixed-parent controls after costs. Full-sample smoothing leaks future data. Latent states and feature drift do not establish a positive parent. |
| **Attention / supply / on-chain segmentation** (L3/E3/E4/F4) — M091/M092/M270/M271/M288/M294/M297/M464/M465 | Versioned wallet labels, actual transfer states, vesting/float, chain finality/reorgs, pool observations and receipt times | Local projection of future returns on `net_exchange_inflow/PIT_float` and a fixed attention innovation | Fails price/volume/delay/label-drift/event controls or gas/borrow/slippage. A transfer is not necessarily a sale; addresses are not users and sampled pool quotes are not continuous depth. |

No equation above is an invitation to reread a spent sample, lower an old gate
or change a frozen lane. Existing MIDs are anchors, not claims that the exact
new equation has already been implemented or tested. Aliases must be checked
against the exact parent scope before proposing any distinct finite variant.

### What data can and cannot identify

Keep **source observations**, **derived quantities**, **proxies** and **latent
assumptions** explicit. A derived value can itself be a proxy. Repeated candles
do not identify private inventory; a depth snapshot does not reveal future
fills; a current download does not prove what was available years ago. Unknown
funding marks, contract multipliers, revisions or fees do not become zero.

Incentive
and collateral yield terms (canonicalV1/M475) also need dated eligibility,
haircuts, vesting and realized valuation; hoped-for points are not cash PnL.
A family marked closed describes its tested/prioritized scope, not a theorem
that every conditional policy or combination is impossible. New combinations
still require matched-risk/cost parent controls and an independently assessed
finite specification.

The source capability receipt has ten documented source families. Documentation
does not imply endpoint access, acquired bytes, historical coverage or causal
availability. Current public metadata does not automatically reconstruct old
contract status or multipliers. The [R403 protocol](../../experiments/metrics_archive_qualification_v1/PREREG.md)
limits its actual acquisition to two dated Binance metrics ZIPs and checksums;
the label ranges alone cannot establish their start/end-period semantics.

`lab/input_contracts.py` adds a **declaration-consistency check** beside the
formula workbench. It checks supplied clock/unit/source/vintage assertions,
freshness and lineage, rejecting future receipts/revisions and incomplete bars.
It does not authenticate their truth, clock transformations, historical
availability, causal identification or executable trades. Its passing fixtures
are engineering evidence only. No frozen formula or market runner is changed.

### Refinement loop

For each existing family, specify one binding unknown, a parent/control, the
candidate mechanism, required source resolution, cutoff and arrival delay,
effect size worth detecting, independent evidence unit and full cost/capital
model. Obtain or qualify the missing inputs first. Freeze the finite family,
all attempts, splits and stopping rules before market outcomes. Compare to the
parent and simple controls, then require preserved or prospective evidence.

Use failures to refine the next distinct study, preserving every old NULL and
spent sample. Repeated coins, overlapping horizons and one shared notice or
funding episode do not manufacture independent observations. Broadness of the
map is not a reason to brute-force an unbounded expression space. Useful new
equations must add incremental net information under feasible execution.

### Additional bounded primary reading, 2026-11-04

- [Futter, Horvath and Wiese, 2308.15135v2](https://arxiv.org/pdf/2308.15135v2),
  2023-08-30: abstract, selected time-augmentation/signature definitions, PnL
  statements, theorem3.1 and approximation statementA.13. Supports keeping time
  structure and stochastic integration conventions explicit. Not a complete
  proof/empirical reproduction or authentication of a later publication.
- [Avellaneda and Stoikov](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf),
  2008: introduction, sections2.1–2.2, equation8 and bounded arrival assumptions.
  Reservation price uses known own inventory under a model; it does not reveal
  private dealer positions or establish our real arrival/fill intensities.
- [Binance funding FAQ](https://www.binance.com/en/support/faq/detail/360033525031)
  and [dated formula announcement](https://www.binance.com/en-PH/support/announcement/detail/c00588a7e8504b3eb28d02a2da00530b):
  only eligibility, sampling/weighting, caps/intervals and effective-time passages.
  The announced scaling change starts2025-09-18 08:01UTC. Preserve rule vintage;
  the audit's daily cutoff needs code checking before alleging another bug.
  These Binance definitions do not establish MEXC funding mechanics or alpha.

## Primary reading and exact scope

These readings informed the design. They do not supply evidence that this
workbench or a proposed crypto strategy earns money. No complete-paper reading,
implementation reproduction or exhaustive novelty search is claimed.

| Source | Read scope and use | Limit |
| --- | --- | --- |
| Cont, Kukanov & Stoikov, [The Price Impact of Order Book Events](https://arxiv.org/abs/1011.6402), v3 | Abstract, bounded introduction and section 2.3, equations 2–3: price change related to order-flow imbalance and depth. Supports a mechanism baseline and observing book events beyond trade volume. | Contemporaneous relation on NYSE stocks, not a forward crypto forecast or net-profit result. |
| Cranmer, [Interpretable Machine Learning for Science with PySR and SymbolicRegression.jl](https://arxiv.org/html/2305.01582v3), v3 | Abstract, introduction, section 2.1 and bounded Additional Features passages on constraints/operators/losses. Supports explicit complexity and grammar constraints. | No Julia/PySR installation or benchmark reproduction; this standard-library rational factory is substantially narrower. |
| Chevyrev & Kormilitzin, [A Primer on the Signature Method in Machine Learning](https://arxiv.org/html/1603.03788v2), v2, 2025-01-17 | Abstract, geometric intuition for the first two levels, and section 2.1 signed-area/relative-movement passages. Supports order-sensitive path representation. | Only elementary polygon area implemented; no signature-learning experiment or predictive evidence. |
