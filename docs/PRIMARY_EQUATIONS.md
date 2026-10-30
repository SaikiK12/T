# Primary equations and execution prerequisites — 2026-10-24

Bounded reading by five specialist researchers and an independent verifier. This
note compacts the received sections into the existing [source intake](../research/intake/source_methods_20261020.json)
and [canonical queue](../registry/methods.csv). It is source evidence, not another
queue, a claim to have read whole books, a strategy result or permission to trade.
Twelve mathematical sources plus official Lighter documentation/code were
examined at the scopes below; empirical studies, proofs and inaccessible pages
outside those scopes remain unread/unreproduced.

R311 remains INCONCLUSIVE on 224/273 common validation days. Its **preselected**
F0+B_h14 loses at 2x/3x; other observed 2x positives cannot replace that choice.
All active policies lose at 3x. R313 supplies only 7/144 eligible cost observations,
with no delayed altcoin cost row. Nothing below repairs those results or supplies
new prospective paper days.

## Equations worth carrying forward

**1. A funding clamp can support a price band even at zero fees.** He et al.
define premium `p=(F−S)/F` and continuous funding cash `Φ(p)F dt`. If the financing
rate satisfies `Φ⁻¹(r)=[x−,x+]`, the corresponding roots give

`λL=(1−x−)⁻¹, λU=(1−x+)⁻¹; F ∈ [λL S−C, λU S+C]`.

For `Φ(p)=κp+clamp(ι−κp,−γ,γ)`, the flat region at `r=ι` survives when C=0.
The financing clock, borrowing access, hedge ratio λ, exit and solvency assumptions
matter. A premium exceeding fees is not this theorem's full test. The paper's
high-fee illustration uses **VIP1 maker** fees, not our retail taker path.
This refines open M047/SRC-PERP-NOARB; it is not the 72-hour C09 rule or R311.

**2. Forecast settlement cash, not just a percentage.** For fixed signed base
quantity q, positive rate f charges a long `−q I f`, with the contract's actual
fair/index notional I. In general `E[If]=E[I]E[f]+Cov(I,f)`; a predictable rate
does not fix future dollar payment. Ackerer et al. explicitly distinguish these
cash-flow conventions. For a consistent midpoint-mark convention, an own
accounting decomposition is

`G_H(q)=Σ_v q_v E[ΔP_v−Σ_k I_vk f_vk]−C_entry(q−q_old)−E[C_exit(−q)]−B_H`.

Use actual settlement times, assets and funded inventory; B includes financing.
If actual bid/ask fills already enter price PnL, crossing is already paid and must
not be subtracted again. Flat includes the cost of closing old inventory. This
belongs to M409's unresolved exact cash ledger, not a new source of alpha.

**3. Entry and retention need different thresholds.** With one-way paired cost c,
unchanged horizon, equal lot and no binding portfolio constraint, entry from cash
requires forecast gross `F_H>2c`; holding an existing position versus exiting now
can be preferred when `F_H>0`, since both alternatives pay a remaining exit.
R310/R311 already implement this kind of one-step hysteresis. Gârleanu–Pedersen
derive partial adjustment toward an anticipated aim under **quadratic** costs;
their solution cannot simply replace proportional fees with a constant fraction.

The distinct open extension is a fixed-deadline continuation value:

`V_t(q_old,z)=max_q {g_t(q,z)−C_t(q−q_old)+E[V_(t+1)(q,z')]}`,
`V_T(q,z)=−C_T(−q)`.

This own application keeps terminal liquidation and both venue accounts in z.
It is **M410**, not another label for the twelve tested forecasts. De Lataillade's
published linear-cost recursion has different terminal treatment; do not import
its threshold while silently imposing a mandatory close. No controller was run.

**4. Pair selection and optimal stopping are different methods.** Leung–Li's OU
model solves `V(x)=sup_τ E[e^(−rτ)(X_τ−c)]` and entry value
`J(x)=sup_ν E[e^(−rhatν)(V(X_ν)−X_ν−chat)]`. Separate entry/liquidation boundaries
follow, with likelihood and hedge-ratio fitting as prerequisites. Perpetual
waiting, constant costs and stable OU parameters do not represent forced margin
exits or a rolling deadline. This exact policy is **M411**, untested; R250's
weekly distance/Engle–Granger NULL is not its exact exclusion.

**5. Toxicity also changes inventory pressure.** GLFT's execution-linked adverse
selection extension adds approximately `ξ/2` per side and amplifies the Gaussian
inventory-skew slope by `exp(kξ/4)`. A spread-only surcharge misses reduced
ability to unwind. Finite-horizon matrix-exponential, stationary eigenvector,
Gaussian and constant-drift variants remain distinct open scopes under M058/M227.
Their arrival intensity/fill/utility assumptions are not calibrated by public BBO.

CJR separates arrival intensity λ from own-fill probability `h(δ;κ)`, and models
short-lived alpha and mutually exciting arrivals. These do not identify FIFO
fills, influential latent event types or our cancel latency. Its two printed
power families are genuinely different:

| Source location | Fill family | Maximizer of `δ h(δ)` for a>1 |
|---|---|---|
| Main §3 | `1/[1+(κδ)^a]` | `1/[κ(a−1)^(1/a)]` |
| Appendix C.1 | `(1+κδ)^−a` | `1/[κ(a−1)]` |

Do not borrow one family's feedback formula for the other. Exponential/power
control, stochastic depth, alpha-only drift, utility and variable-size extensions
are retained separately in the intake, including missing mechanics.

**6. Fitted microprice is not the weighted midpoint.** The author notebook uses
`g1=(I−Q)⁻¹R1K`, `B=(I−Q)⁻¹R2`, `p6=m+Σ_(j=0..5) B^j g1` from fitted state
transitions. Six iterations is an implementation choice, not a universal horizon
or convergence guarantee. Cent-based K, whole-sample quantile bins, row-shift clocks
and omitted big moves need causal crypto-specific treatment. M264 remains open;
R185's coarse imbalance and the existing weighted midpoint do not test it.

**7. A risk equation cannot manufacture positive net expectancy.** For feasible
positive wealth factors, own Jensen reasoning gives
`E log(1+fX) ≤ log(1+f E[X])`. Cash weakly dominates positive stake if the true
net mean is nonpositive; a sample PnL sign alone does not establish that premise.
Busseti et al.'s sufficient constraint `E[(rᵀb)^−λ]≤1`,
`λ=log β/log α`, bounds drawdown below **initial** wealth under fixed IID bets.
It is not a rolling-peak drawdown guarantee for leveraged, dependent carry.

Sun–Boyd's robust Kelly varies probabilities over fixed payoff support. It cannot
repair missing execution outcomes or supply calibrated ambiguity radii. Boyd's
box mean-error penalty is

`min_|δ|≤ρ (μhat+δ)ᵀv = μhatᵀv−ρᵀ|v|`.

The adjacent source prose reverses long/short endpoint signs; direct minimization
confirms the displayed expression. An own entry prerequisite is
`q(μhat_H−ε_H)>C_entry+exit^hi(q)`, with μ/ε in dollars per base unit on the same
horizon. Return quantiles are not automatically conditional-mean confidence bounds.
These constraints/uncalibrated hypotheses do not rescue R217/R281/R309 or R311.

## Actual reading ledger

| Primary source/version | Close-read scope; limitations |
|---|---|
| [He et al., 2212.06888v7](https://arxiv.org/html/2212.06888v7), 2026-09-17 | §3, Table1, Props1–3/Eqs1–15; §4.3–4.4/Eqs20–23; selected appendices. Most empirical/proof work unread. |
| [Ackerer et al., 2310.11771v2](https://arxiv.org/html/2310.11771v2), 2024-09-04 | §§2–3, §6 Prop3, cash-flow appendix; selected comparison with corrected [published version](https://doi.org/10.1111/mafi.70018). Full version diff/inverse/quanto work unread. |
| [BIS Crypto Carry, work1087](https://www.bis.org/publ/work1087.pdf) | Received 54-page PDF dated 2023-03-24, not advertised 2025 revision; basis/margin/financing sections. No strategy replication; reported Sharpe excludes costs/financing spreads. |
| [Gârleanu–Pedersen author copy](https://nbgarleanu.github.io/DynTrad.pdf), March2012 | §§2–3/Eqs1–17; empirical work and appendix proofs unread. |
| [de Lataillade et al., 1203.5957v1](https://arxiv.org/pdf/1203.5957v1), 2012-03-27 | §2, §§3.1–3.4; later OU/cube-root excerpts not adopted. |
| [Leung–Li, 1411.5062v3](https://arxiv.org/pdf/1411.5062v3), 2015-05-15 | §2, §3.1–3.4, Thms4.2/4.5 and selected proofs; §5 solved stop-loss boundaries not extracted. |
| [GLFT, 1105.3115v5](https://arxiv.org/html/1105.3115v5), 2012-08-03 | §§2–5, exact/approximate controls; no fitted intensities or market reproduction. |
| [CJR Oxford-Man manuscript](https://www.oxford-man.ox.ac.uk/wp-content/uploads/2020/05/Algorithmic-Trading-Stochastic-Control-and-Mutually-Exciting-Processes.pdf), 2018-12-24 | §§2–5 and Appendix C.1; closed 2014 copy not accessed. |
| [Stoikov notebook](https://github.com/sstoikov/microprice/blob/94205fe5bedb98b627b43e4abeb59f91fa6d7075/Microprice%20-%20Big%20Data%20Conference.ipynb), 94205fe5… | Code read; sample CSV/notebook execution absent. SSRN abstract only, full paper403; convergence conditions unread. |
| [Busseti–Ryu–Boyd author PDF](https://web.stanford.edu/~boyd/papers/pdf/kelly.pdf), 2016-03-19 | §§2–5.3/Eq11, AppendixA Lemma1; numerical studies not reproduced. |
| [Sun–Boyd author PDF](https://web.stanford.edu/~boyd/papers/pdf/robust_kelly.pdf), 2018-12-08 | §§1–2.4 and appendix; distinct from later arXiv revisions. Printed dual discrepancy remains unimplemented. |
| [Boyd et al. author PDF](https://web.stanford.edu/~boyd/papers/pdf/cvx_portfolio.pdf), copyright2017 | §§2.3/2.5/2.7/4.1/4.3; later chapters/software not audited. |

The independent verifier rechecked five high-impact claim groups, including clamp
bands, control/terminal distinctions, Kelly wealth floor, robust-error signs and
the Lighter SDK. No closed/private corpus, full book or full internet coverage is
claimed. Source dates/hashes/access gaps and all distinct submechanisms are retained
in the structured intake; no market outcome, large dataset or model was acquired.

## Concrete engineering consequence

[The new book assembler](../lab/lighter_depth_state.py) maintains absolute depth,
nonce linkage and increasing nonadjacent offsets atomically. The pinned official
[SDK example](https://github.com/elliottech/lighter-python/blob/a7a9ba88514d38a863a33642acd41f8adf442e5c/lighter/ws_client.py)
updates levels but leaves nonce/offset/timestamp state stale. Reset epochs, malformed
frames, gaps, shutdown and disconnect handling therefore need explicit guards.

Its [tests](../tests/test_lighter_depth_state.py) cover an independent level-map
oracle, deletions/replacements, stale epoch frames, sticky faults and the existing
1x/2x/3x cost interface. Pong, repeated or ineffective batches cannot renew the
selected event-age clock. This is deterministic consistency validation with
invented inputs, not a live depth test, idle heartbeat guarantee or a filled trade.
No R310–R313 specification or result was changed and no prospective lane activated.
