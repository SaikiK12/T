# Discovering equations without counting aliases as discoveries

Engineering workbench, 2026-11-03. No market fit, forecast result, PnL or
prospective observation. This note is a design and source receipt, not a frozen
market experiment or another method queue.

## What remains discoverable

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

## Primary reading and exact scope

These readings informed the design. They do not supply evidence that this
workbench or a proposed crypto strategy earns money. No complete-paper reading,
implementation reproduction or exhaustive novelty search is claimed.

| Source | Read scope and use | Limit |
| --- | --- | --- |
| Cont, Kukanov & Stoikov, [The Price Impact of Order Book Events](https://arxiv.org/abs/1011.6402), v3 | Abstract, bounded introduction and section 2.3, equations 2–3: price change related to order-flow imbalance and depth. Supports a mechanism baseline and observing book events beyond trade volume. | Contemporaneous relation on NYSE stocks, not a forward crypto forecast or net-profit result. |
| Cranmer, [Interpretable Machine Learning for Science with PySR and SymbolicRegression.jl](https://arxiv.org/html/2305.01582v3), v3 | Abstract, introduction, section 2.1 and bounded Additional Features passages on constraints/operators/losses. Supports explicit complexity and grammar constraints. | No Julia/PySR installation or benchmark reproduction; this standard-library rational factory is substantially narrower. |
| Chevyrev & Kormilitzin, [A Primer on the Signature Method in Machine Learning](https://arxiv.org/html/1603.03788v2), v2, 2025-01-17 | Abstract, geometric intuition for the first two levels, and section 2.1 signed-area/relative-movement passages. Supports order-sensitive path representation. | Only elementary polygon area implemented; no signature-learning experiment or predictive evidence. |
