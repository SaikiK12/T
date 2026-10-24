# R311: source-only correction of R310's twelve equation policies

- **Registry id:** R311
- **Owner (single writer):** Codex, `codex/lab-consolidation`, existing draft PR #49
- **Date registered (UTC):** 2026-10-24
- **Canonical method:** M409
- **Decision group:** the same funding/basis family as R310, one possible paper comparison

Input manifest SHA-256: aa304575aec8241fb15189e4a627e03d78dfaaf3610352c2bb303cb9cc16d599

## Inherited frozen economic specification

The complete economic rule, universe, event clocks, cash accounting, risk matching,
selection, costs, inference and admission rules are **exactly** R310's frozen
`../equations_v1/PREREG.md`, SHA-256
`ad89c67ec5eb7508cdbc46175d31235b94e8a6c854a1df18aa3eae0847dce663`.
This document changes only input acquisition lineage and the round/trial metadata.
The unchanged R310 implementation is imported by `scripts/run_equations_v2.py`.
The wrapper rejects any changed economic settings, split, cost or extra parameter.

Explicitly retain F0/F1/F0+B/F1+B x H=1/7/14 days (12 policies), the fixed 117
R288 pairs, 2025-04-27..2025-12-31 calibration, 2026-01-01..2026-09-30 validation,
$10,000 total initial capital split $5,000 per venue, fixed underlying quantities,
20 slots, $250 base per new leg, 1x/2x/3x 10bp-MEXC/4bp-Lighter costs, 2x decisions,
calibration-only downsizing/selection, all source/identity guards, exact state-score
choice with deterministic admission, terminal exits, missing-data/risk flags and
the full R310 pass/fail rule. No inherited validation winner is selected by hand.

## Why a corrective round is necessary

R310 was computed, preserved and registered INCONCLUSIVE. Its preselected F0_h7
proxy total was +$14.90/-$38.04/-$90.97 at 1x/2x/3x. Only 238/273 common days
remained, so its frozen inference did not run. Ten policies never traded.
All **1,318** absent interior Lighter funding hours were exact 700-hour query
seams. An interior public query recovered a missing BTC event; a synthetic
noninclusive-boundary fixture reproduces the acquisition fault. This is a source
correction, not evidence to change a threshold, model, horizon or fee scenario.

R310's original files, bad cache, outputs and 12-trial row are never rewritten.
The prior result has been seen; neither this repeat nor its validation dates are
fresh evidence. Report R310's failure beside this result and do not reset history.

## Exact source correction and budget

Start from an exact separate copy of `data/equations_v1` into `data/equations_v2`.
`scripts/repair_equation_funding.py` fixes the target list from the **parent's
missing timestamps**, without reading strategy returns: within each observed
funding span, an absent UTC hour must be START+700*k hours, k a positive integer.
Any absence away from that lattice is unexplained and cannot be silently repaired.
The fixed target set has 1,318 (market, timestamp) cells.

Query the public endpoint with each target strictly inside a narrow request.
Add only its actually returned row, preserving its exact timestamp, signed rate
and uninterpreted raw value. Require a unique target and agreement of any observed
neighboring rates/cycles. Never interpolate, substitute zero, overwrite an old
rate, refetch a new universe, or alter MEXC funding or either price dataset.

Retain the original raw pages/receipts and append the new public pages in the
separate cache. The inherited counters enforce the **same combined** 8,000-request,
250-MiB-response-body budget: R310 used 6,428 requests/229.6 MiB; the 1,318 narrow
queries project 7,746 requests total. On exhaustion or an unresolved/revised source
event, halt acquisition and report the blocker; do not expand the budget.
Source requests retain the machine-wide Lighter lock and standard-account pacing.

`inputs.json` pins all corrected files, acquisition plan/receipt, exact original
data identity and unchanged economic code, this wrapper, repair code, tests and
settings. Preflight checks the parent's frozen files, unchanged original rows,
unmodified prices/MEXC funding and complete repair. Freeze/commit/push this
specification and all identities **before** R311 outcomes. Verify both parent and
new identities before and after the run; use a fresh output and one-writer lock.

## Multiplicity, verdict and future evidence

This corrective repeat records **12 additional trials**, even though there are
no new economic variants. Program trials before R311: **9,478,770**; after it:
**9,478,782**. R310 and R311 are one decision group, not independent chances.
Their spent dates, current-survivor universe/rules and adaptive lineage remain
gate 0. Conditional family SPA/Bonferroni are not program-wide error control.

Apply R310's exact INCONCLUSIVE/NULL/PARTIAL decision code, dependent bootstrap,
minimum sample, no-gap requirement, preselected-candidate test, risk and robustness
gates. Preserve every policy and cost path, including nulls and inactivity.
Do not rescue a validation winner, rerank the family after results, or run another
parameter search because this correction did not pass.

Even a PARTIAL result only permits a **newly frozen** prospective comparison
under R310's stated conditions: genuinely new on-time days, delayed executable
quotes/depth, actual fair/index-notional funding, dependent-null calibration of
90-day futility and 180/365-day looks, 80%-power days, trimming and leave-two-coins-out.
If these are not ready or the historical gates fail, no paper activation occurs.
No trade, leverage increase, real capital or recurring research job is authorized.

## Verification and limitations

Archive all result components and independently reconstruct every venue/day/tier
from signed tickets and strictly-before-event inventory. Reproduce to a fresh
directory and compare every result byte. Append the registry using its code,
reconcile a lost append reply without a duplicate, and retain the original byte
prefix. Put the result in this FINDINGS and the existing canonical queue; no new
queue or panel is created.

The fair/index price, historical lot/margin, USDT/USDC parity, liquidity, partial
fill and venue/counterparty limitations in R310 still apply. An actual missing
observation remains unknown even after fixing our query seams. Exact restoration
of a source event is not proof that closing-price proxy fills were executable.

Gates policy SHA-256: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926
