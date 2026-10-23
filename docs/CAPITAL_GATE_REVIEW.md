# Capital gate: current gap between paper evidence and an owner decision

Reviewed 2026-10-19 from the repository's current R226 snapshot. Static review only: no returns were recalculated, no positions were opened, and no changes were made to frozen gates or forward journals. This is a research-governance review, not authorization for trading.

## The current gate is a weak screen

`lab.gate.go_real()` passes when at least 20 finite tickets have a positive mean, at least 55% are positive, and no ticket is below -40% unlevered (`lab/config.py:21`, `lab/gate.py:7-29`). It reports shared entry-day clusters only when callers provide them, but does not gate on them. R215 and the delayed forward script call it without `entry_days`.

That rule does not test whether the mean is distinguishable from zero, whether the sample contains independent market episodes, or whether the paper path can be executed at the owner's intended size. It has no maximum drawdown, leverage/gross exposure, symbol concentration, margin, liquidation, capacity, or maximum account-loss criterion. A passing result permits consideration by the owner; it is not a complete capital-risk approval.

## Forward decision rules do not yet line up

- `docs/FOUNDATION.md` describes consideration after 20 scored tickets.
- R215/R218 use a 90-on-time-day `go_real()` decision; R221 adds a separate sequential statistical decision at 182/365 days, positive 2x net return, and still requires `go_real()`.
- R220 has a different combined condition: positive total, Newey–West t at least 2, and `go_real()` on invested days.

This creates a risk that a 90-day operational pass is treated as enough for capital before the stronger research decision. Define separate, named stages for **signal evidence**, **target-venue execution evidence**, and **account-risk approval**. State which active lane must pass each stage. The 18 replayed days in the Oct 19 snapshot were backfilled; R215's genuinely on-time stream was scheduled to begin Oct 20. Replay history is not a record of contemporaneous operation.

R221 is frozen, so its written result must not be retrofitted. Its power table assumes independent daily returns although the tested 72-hour books overlap, and it applies sequential boundaries to finite-sample Newey–West statistics without a dependence-aware calibration (`experiments/mexc_seq/PREREG.md:35-58`, `scripts/forward_seq.py:22-59`). The runner also compresses on-time dates before calculating HAC statistics and silently drops duplicate days; a missing calendar day can therefore be treated as one ordinary lag. Treat the registered R221 decision as nominal evidence under its stated limitations. Any replacement or calibration is a new preregistered lane, not a change to R221 after seeing results.

R225's volatility-target sizing is a risk overlay, not evidence that the underlying signal predicts returns. Its annualized Sharpe assumes iid daily returns; its decision compares point estimates, and its registered drawdown is additive (`experiments/vt_fwd/PREREG.md:57-72`, `scripts/forward_vt.py:38-41`). Do not treat a lower historical drawdown as margin safety or a positive-edge result.

## Evidence still missing for the intended venue and size

The repository's MEXC price/funding replay does not model the full trading path. The execution review lists unresolved signal-to-order delay, partial/rejected orders, contract sizing, point-in-time fees, fair-price margin, tiered maintenance, liquidation, collateral currency and hedge failure (`docs/PERP_EXECUTION_AND_RISK.md`). R215 prices costs using Binance liquidity ranks rather than measured MEXC fills; R224 has only two depth snapshots per coin in its current journal. Neither result is a fill/capacity study at an owner-specified notional.

Prop-challenge expected payouts are not a substitute. R202 uses selected, not-confirmed strategy streams, chooses size from the same historical results, and the simulator evaluates one daily step rather than intraday rule breaches. Its estimates are scenario illustrations only, not a signal or capital gate.

## Separate gates to define before any capital discussion

1. **Research evidence:** one frozen primary portfolio on the intended return venue, scored on genuinely new on-time observations, with all dates retained, complete point-in-time data and a single final decision. Calibrate uncertainty to serial and regime dependence; do not count overlapping tickets as independent evidence. Require positive net results at the predeclared base and stress costs, with a clear null/inconclusive rule.
2. **Execution evidence:** paper or shadow capture at fixed owner-selected notionals with actual contract filters and account fee tier, signal-to-arrival timestamps, funding events, depth/impact, partials/rejections and stale-book handling. A displayed book walk remains a cost estimate, not a fill.
3. **Account-risk evidence:** replay the exact intended contract and collateral rules, including mark-price path, initial/maintenance margin tiers, liquidation, funding, short squeeze/gap risk and failed hedges. Predeclare maximum gross/leverage, per-contract exposure, daily stop, account drawdown and maximum loss before reviewing final performance.
4. **Owner authorization:** only after the first three gates are documented may the owner decide whether a very small, separately bounded stake is acceptable. The owner places any order; research code must not route it.

No threshold is assigned here to an owner's loss budget or leverage because those depend on the intended account and contract configuration. If changing the shared gate code or its interpretation, follow `AGENTS.md`: bump the program version and re-register dependent lanes rather than silently changing a frozen decision rule.

## References in this repository

- `lab/gate.py`, `lab/config.py`, `docs/FOUNDATION.md` — current return screen.
- `experiments/mexc_fwd/PREREG.md`, `experiments/mexc_seq/PREREG.md` — 90-day operational and longer statistical decisions.
- `experiments/vt_fwd/PREREG.md`, `scripts/forward_vt.py` — sizing diagnostic.
- `docs/CONFIDENCE_REVIEW.md`, `docs/PERP_EXECUTION_AND_RISK.md`, `docs/IMPLEMENTATION_INTEGRITY_REVIEW.md` — existing uncertainty, execution and risk reviews.
- `AGENTS.md` — owner-only real-order rule and versioning rules.
