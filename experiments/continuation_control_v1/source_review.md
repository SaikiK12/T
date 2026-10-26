# R323 bounded primary-source review — continuation, terminal trade, resources

2026-10-26. Read-only source work for M410/R323; no market or return measurement,
account/RPC request, model/dataset download, controller execution, or paper activation.
The root writer owns production, canonical queue, preregistration and issue #7.
The source models are research references, not evidence of executable alpha.

## Receipt and exact reading scope

1. **Boyd, Busseti, Diamond, Kahn, Koh, Nystrup and Speth, _Multi-Period Trading
   via Convex Optimization_**, author-hosted final PDF:
   https://web.stanford.edu/~boyd/papers/pdf/cvx_portfolio.pdf . Cover: vol.3(1)
   (2016), copyright2017, DOI10.1561/2400000023. One ordinary GET received all
   756,268 bytes/79 PDF pages. SHA256
   `e7bda0c607fcac4c431cba010f6bfd9ef92f6357f3aa3c71f9023b160bf7ac67`
   exactly matches the prior reading ledger. The Last-Modified header is
   2026-05-05, but that header does not establish a new paper revision.
   The body was parsed in memory, not retained as another full-text mirror.

   **New close-read scope:** printed p.45, §5.1 first page; printed pp.49–50,
   selected §5.2 dynamics/optimization/interpretation passages including
   Eqs(5.1)–(5.2); printed pp.52–53, §§5.4–5.5. These were previously unread
   according to the 2026-10-24 ledger. Cover/contents and PDFpp1–12 were also
   output/viewed as context, including the abstract, introduction and beginning
   of Chapter2; they are not the new contribution of this review.
   **Still unread:** printed pp.46–48 and51, so this is explicitly not a full
   Chapter5 read; §4.4/4.5 constraints, the rest of Chapters2/4 beyond the old
   recorded scopes, Chapters6–7, software and cited articles. Prior close-reading
   remains §§2.3/2.5/2.7/4.1/4.3, not a whole-paper reading.

2. **Gârleanu–Pedersen, _Dynamic Trading with Predictable Returns and
   Transaction Costs_**, March2012 author manuscript:
   https://nbgarleanu.github.io/DynTrad.pdf . Reused legally received cache
   `.cache/research_batch_20261024/gp.pdf`, 525,150 bytes/69 PDF pages, SHA256
   `30584d6dbf7c8443573ecf9fa93f199a681ff59aa607e4c48e7f61c8fededc3d`;
   it matches the prior receipt. No GET. **New close-read:** printed pp.15–16
   and the first paragraph of p.17, §4 persistent-price-impact continuation,
   Eqs(18)–(21)/Proposition6. Also viewed pp.17–18's beginning of §5,
   Eqs(22)–(26), without adopting those examples. A document-wide keyword
   location check found no finite-horizon/terminal-treatment section; that check
   does not constitute full reading. Prior scope remains §§2–3/Eqs(1)–(17).
   Remaining theory/examples, empirical sections and appendix proofs are unread.

3. **de Lataillade et al., arXiv1203.5957v1**, 2012-03-27:
   https://arxiv.org/pdf/1203.5957v1 . No cached full body found in this task's
   local source-cache inventory; no new GET or new primary-page reading.
   Previously read §2/§§3.1–3.4 and terminal distinction are carried forward
   solely from `docs/PRIMARY_EQUATIONS.md` and the existing cost-control note.
   Later OU/cube-root sections remain unadopted. No body hash is invented.

Network allowance used: **1/4 static GETs, 756,268/2,097,152 total body bytes,
756,268/1,048,576 maximum body bytes, 1.106/90 acquisition seconds**. Normal
inherited proxy and verified TLS; redirects disabled; no retry/login/bypass.
HTTP200 author-hosted primary source. No request was made to a market/history,
account, model, dataset or RPC endpoint. See receipts.json for machine details.

## What the new sections actually establish

**A terminal trade has a cost.** Boyd §5.5, printed pp.52–53, explicitly adds
a terminal benchmark constraint `w_(t+H)=w_b`. Its sparse trading plan allows
trades only at `t`, `t+T_med`, `t+T_long`, and `t+H−1`. The final trade is
determined by the terminal constraint; p.53 expressly includes an additional
objective term for its transaction cost. This is useful direct primary support
for charging the remaining terminal trade. Choosing an all-cash benchmark to
mean zero risky inventory is **our specialization**, not a source instruction
that every portfolio must liquidate at a fixed deadline.

**Multiperiod transaction costs couple today's and tomorrow's decisions.**
Eq(5.1), printed p.49, maximizes the sum over the planning horizon of forecast
return less risk penalty, holding cost and transaction cost, subject to trade
and holding sets and simplified dynamics. Eq(5.2) eliminates the trade variables
and charges `phi_trade_tau(w_tau−w_(tau−1))`; this makes the coupling explicit.
Printed p.50 describes executing only the first trade and replanning later.
Those are receding-horizon plans; a fixed absolute R323 deadline is our separate
constraint and must not be silently postponed whenever a new decision is made.

**The convenient MPO state propagation is an approximation.** Printed
pp.49–50 use `w_(tau+1)=w_tau+z_tau` and `1' z_tau=0`. The exact normalized
return update printed on p.50 is
`w_(t+1)=((1+r_t) o (w_t+z_t))/(1+R_t^p)`.
The text explicitly says that zero-sum planned trades ignore transaction and
holding costs in state propagation while retaining them in the objective; the
realized self-financing identity instead has
`1' z_tau=−phi_trade_tau(z_tau)−phi_hold_tau(w_tau+z_tau)`.
These planning simplifications must not replace a dollar cash ledger, create
collateral, or make per-venue post-cost feasibility pass in R323.

**Additional price-impact memory is a distinct state extension.** GP Eq(18)
has `D_(t+1)=(I−R)(D_t+C Delta x_t)`. Eq(20)'s expected excess-price change
from this distortion is `−(R+r_f)(D_t+C Delta x_t)`; its value function uses
the enlarged state `(x_(t−1),f_t,D_t)`. Proposition6/Eq(21) retains partial
adjustment toward an aim depending on both forecasts and distortion. Thus if
own persistent impact is modeled, inventory plus the public predictor alone
is not a sufficient state. This remains their linear/quadratic price-impact
model: it supplies neither proportional-fee bands nor our terminal liquidation,
separate venue wallets, contract-specific cash settlement or verified fills.
R323 should exclude this uncalibrated mechanism explicitly rather than borrow
its closed-form trading fraction.

## Direct consequences for the small exact R323 scenario tree

The following are our accounting/finite-control deductions, not newly proved
claims attributed to either paper:

* Use an absolute final index T. A state sufficient for exact accounting
  contains old quantity, separate venue cash/equity, and every modeled variable
  affecting future cash flows, costs or feasible actions. At a tree node choose
  one shared action before observing which child occurs. Only information
  available at that node may enter the choice; distinct histories may be merged
  only when their full sufficient states agree.
* For an existing position and action set hold/reduce/close, let stage cash be
  marked price PnL plus signed funding less financing, and C be the cost of the
  actual inventory change. An own Bellman convention is
  `V_t(q_old,z)=max_q {−C_t(q−q_old)+sum_j p_j[g_tj(q,z)+V_(t+1)(q,z'_j)]}`,
  with `V_T(q,z)=−C_T(−q)`. An equivalent explicit final close action is valid;
  using both conventions would double charge the terminal exit. If realized
  execution prices already include crossing/slippage, C must not charge it
  again. Flat-from-existing-inventory pays the current exit; it is not zero.
* Enforce resource constraints separately for every venue and reachable child.
  An opposite profitable leg cannot fund a losing wallet. The post-cost ledger
  must debit each venue's own fills/fees/financing and signed settlement cash.
  Capital reserves used only to test feasibility must not be charged as actual
  fees or profits. The exact capital rule comes from the declared paper-account
  contract, not Boyd's single fungible cash weight or GP's risk penalty.
* If a policy's model selection uses 2x costs, replay that same node-to-action
  policy at declared 1x/2x/3x actual costs to expose sensitivity. Reoptimizing
  separately changes the comparison. Report infeasible stress paths explicitly;
  one stress scenario's profitable wallet must not repair another's shortfall.
* Finite enumeration can check the numerical optimum **under the supplied
  tree**, including terminal close and feasibility. It does not verify the tree
  probabilities, future settlement notionals, executable prices or edge.

## Missing mechanics and weak alternatives

Neither newly read scope supplies causal transition probabilities, conditional
forecast-mean error bounds, executable bid/ask/depth after latency, fee/session
contracts, settlement timing/units, exchange margin/forced-exit rules, contract
lots, partial fills or failures, or two segregated collateral accounts. Boyd's
§5.4 requires forecasts as inputs and allows constant forecasts; that is not an
uncertainty calibration. The already recorded §4.3 box-error penalty remains
separate and was not newly close-read here. Nominal expected-value dynamic
programming is not distributionally robust unless an ambiguity set and its
time-consistency semantics are separately declared and checked.

Weak substitutes rejected: GP's stationary quadratic-cost controller cannot
supply a mandatory-terminal proportional-fee policy; the old de Lataillade
terminal trading date is not forced liquidation; Boyd's terminal benchmark and
MPO approximation are not an exact segregated-account Bellman solution.
These references support implementation choices and exclusions only. This
review does not reopen R311, supply new prospective evidence, establish a
positive net executable return, claim private Jane Street/Citadel strategies,
or claim whole papers/books read.
