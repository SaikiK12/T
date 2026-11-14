# PREREG: anytime_monitor_v1

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R489
- **Owner (single writer):** OpenHands root agent (M479 implementation)
- **Date registered (UTC):** 2026-11-14

## Question
Can the lab read each forward paper lane's daily net series on *every* new day, at a fixed level
alpha, without inflating the type-I error, using an e-process monitor — and what does that monitor
say about the lab's already-recorded forward-lane series today?

## Universe
The lane reads only committed artifacts already in the repository, by exact path:
- the audited cross-venue carry daily nets `experiments/carry_v2_audit_v1/results/daily.csv`
  and `experiments/carry_v2_audit_kc_v1/results/daily.csv` (columns `book,engine,date,net_1x,net_2x,net_3x`);
- the forward paper-lane ticket journals `experiments/*/journal/tickets.csv` that carry a daily
  `net` column (e.g. `carry_fwd`, `xfund_fwd`, `mexc_fwd`, `usopen_fwd`).
No manifest is downloaded. The file set is fixed at freeze time by the `SERIES` list in
`scripts/run_anytime_monitor.py`; each file's sha256 is recorded in the run receipt.

## Data
All inputs are repository-committed CSV files read at run time. No market data, no network, no
new acquisition. The data-manifest sha256 in the receipt is the concatenated per-file sha256 in
the order listed by the runner.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| daily net series r_d | `net*` column of a committed lane result | the lane that produced it; return units per UTC day | the lane's own frozen window and close rule | already committed before this lane runs | yes (the lane's history) | the lane's own universe | NaN days are skipped, never zero-filled |
| support bound [lo, hi] | declared below, from the warm-up extremes x 3 | this lane | fixed at freeze | fixed at freeze | yes | n/a | an out-of-bound day raises, never clips |

## Rule or search space
Closed, no search. For each series and each cost column (`net_1x`, `net_2x`, `net_3x` where present),
compute the monitor under three modes on a fixed grid:
- `bet`: adaptive hedged-bet e-process on the raw daily series;
- `block`: the same on non-overlapping 5-day means (the dependence-robust form);
- `mixture`: the method-of-mixtures e-process on the raw daily series.
alpha = 0.05 in all cases. Reject H0: mean <= 0 the first day the running max of the capital
process reaches 1/alpha = 20. Support bounds: lo = -0.30, hi = +0.30 (a 30% single-day move; the
audited carry books' observed extremes are within this, and a delta-neutral carry book cannot lose
its whole notional in a day after fair-price liquidation). This bound is deliberately wide so it is
honest; the PREREG notes it costs power.

## Splits and cost
No discovery/validation/holdout split is used: this lane does not fit a model and does not select a
strategy. It reads already-computed daily nets at their own 1x/2x/3x cost levels and reports the
monitor for each. `lab/config.py` program version 1.

## Gates
This is a **gate 0 diagnostic**, not a gate-1 test. It reads only already-seen committed series, so
nothing it finds is prospective evidence. Verdicts:
- **METHOD_VALID**: the monitor's size is at most alpha on a synthetic zero-mean series (checked in
  the lane run over many seeds) AND on the dependence-robust `block` mode under an AR(1) null.
- **NULL** for a given series if no mode rejects H0.
- **MONITOR_REJECTS** for a given series if the `block` mode (the dependence-robust one) rejects; a
  `bet`-only rejection that `block` does not confirm is reported as MONITOR_BET_ONLY and is NOT
  read as evidence, because the raw mode's guarantee is inexact under autocorrelation.
The lane's headline verdict is METHOD_VALID / METHOD_INVALID, reported separately from the
per-series monitor reads.

## Null
Two synthetic nulls, both fixed-seed, run inside the lane:
1. i.i.d. zero-mean Gaussian (sd 0.006, bounded to [-0.30, 0.30]), 400 seeds x 365 days;
2. AR(1) null with phi = 0.7 (the strongest dependence the raw mode failed on in development),
   400 seeds x 365 days.
Verdict rule: the empirical rejection rate must be <= alpha + Monte-Carlo slack (alpha + 3 x
sqrt(alpha(1-alpha)/seeds)). If it is, the method is valid for that null; otherwise invalid.

## Multiplicity
No strategy variants are generated: the "search space" is 3 modes x (series x cost columns), and
every cell is reported. This lane's registry count is the number of (series, cost, mode) cells it
reports, stated in FINDINGS. Program trials so far: read from `registry.program_trials()` at run
time and recorded in the receipt. This lane adds **0 strategy trials** (it fits no model on market
data); its synthetic calibration cells are diagnostics, as in R321.

## Evidence lineage and admission (future lanes only)
Canonical method ids: M479 (anytime-valid monitoring). Parent rounds: none for the monitor itself;
the monitored series belong to R278/R279/R294/R390 (cross-venue carry) and R191/R200/R215/R371
(forward paper lanes). One decision group this feeds: the *monitoring* of forward lanes, not a new
signal — it does not create a new chance to declare an edge. Samples already seen: all of them (this
is a gate-0 diagnostic on seen series). Proposed fresh sample and overlap: none. Current
`docs/GATES.md` requirements met: none claimed; this lane is exploratory/diagnostic and claims no
gate-1 or gate-2 evidence. Dependent-null calibration: the AR(1) null above. Strict on-time clock,
10-day trimming, leave-two-coins-out, 80%-power: not applicable to a monitor (documented as a
limit). Across-family selection control: none; the result is diagnostic only. This section does not
authorize reserved reads or real orders.

## Stop rules
One run over the fixed series set. No new series, no new modes, no parameter tuning after seeing a
result. A change is a new lane with a new id.
