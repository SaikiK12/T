# referee (qwen4-max-preview)

**Verdict: every survivor here is one conditioning step from a null. The proposed next work inherits four false-positive engines.**

**1. Post-hoc conditioning — the dose filter.** `unlock/ADV < 0.82` was read off the six worst of 422 losses. That is outcome-dependent trimming: the cutoff is a fitted parameter with hidden degrees of freedom (thresholds × dose variables × loss-set sizes inspected). The claim "trimmed mean +4.06%, not tail-driven" is *exactly* tail-driven, and p=1.6e-8 / CI +1.21..+5.24% are void for the filtered strategy. To be admissible:

- **Freeze** the rule, threshold, ADV lookback, unlock definition, and point-in-time computability (trailing ADV only; Gate-0 calendar issue applies) in a pre-registration before any new statistic.
- **Burn all 422 events for confirmation.** Discovery sample only. Confirmation requires never-read events or on-time forward days (R266) with the filter applied *prospectively*, pre-specified N and stopping rule, no interim peeking without alpha-spending. Applying the filter mid-lane after seeing losses burns the lane.
- If any in-sample reuse is claimed, correct for the search: Hansen SPA / Reality Check over the full grid of cutoffs actually inspected, disclosed honestly; Bonferroni at minimum.
- Re-estimate max DD, CVaR, worst-event loss on the fresh sample; −4.62% DD does not transfer to a rule that deleted its own worst losses.
- Pre-specify the falsifier: forward filtered net mean ≤ 0 at 1x cost, or sign test failing at adjusted α.

**2. Selection on the same sample.** Atlas "replication 47.6% vs placebo 9.1%" is circular if cells were chosen on the same data; 9.1% placebo is what noise looks like under mass testing. The 2025-07..2026-09 holdout is spent — any "new" test touching it is contaminated. Maker-cost proposals assume fills: 0bp web maker with queue risk and adverse selection is a cost *model*, not an edge; fill toxicity must be measured, not assumed.

**3. Tail risk masquerading as edge.** Unlock short is short convexity: the sign test ignores magnitude; one squeeze cluster erases years. Week-bootstrap assumes independence; unlocks cluster by token, sector, and date. Funding carry dying at 2x (t=1.14) is the tail speaking. Demand event-cluster bootstrap, CVaR, short-leg funding/borrow, and liquidation-cascade stress before calling 4.22%/yr "survivable."

**4. Multiplicity.** 9,785,317 program trials. Any new survivor must be deflated against the *program-wide* count (deflated Sharpe/SPA), not this session's. New options data (snapshots from 2026-10-21; EOH 5 coins, 6 months) cannot support a backtest — coin/window choice is another search axis.

**Bottom line:** no edge is currently admissible. Only a frozen, prospectively filtered forward lane with multiplicity-adjusted falsifiers can change that.
