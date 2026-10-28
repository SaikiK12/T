# R366: receipt-time and prepaid-capital correction

**Decision: PARTIAL engineering.** The correction addresses defects found in
R365's constructed-input guard. It does not test the owner’s ALO strategy or
prove the validity of any real quote, receipt, fee, fill or clock bound.

R365's original [specification](../alo_cost_guard_v1/PREREG.md),
[results](../alo_cost_guard_v1/results.json) and
[failure discussion](../alo_cost_guard_v1/FINDINGS.md) remain intact. R366
reuses the same four invented cases and adds eight adversarial examples. Its
source-scoped terminal attestation binds the action counts, final signed fill
quantity, order identity and complete-fill-history assertion. First-seen
monotonic time must precede the economic fill under the **supplied** clock
uncertainty bound; the quote's source and receipt clocks must also agree with
that bound. Timely separately attested assumed costs remain visible even when
the full component is unknown. Prepaid action and extra costs reduce the same
segregated capital available at entry.

| Constructed adversarial case | R365 behavior | R366 behavior |
|---|---|---|
| Quote received after fill receipt | Scored | Rejected |
| Quote after economic fill, before delayed fill receipt | Scored | Rejected |
| Source time after projected first receipt | Scored | Rejected |
| As-of before clock anchor | No fill scored | Unknown |
| Canceled order with incomplete fill history | No fill scored | Unknown |
| Prepaid costs make entry underfunded | Scored | Rejected |
| Hypothetical close would leave negative capital | Scored | Insolvent counterfactual retained |
| No-fill prepaid costs exhaust capital | No fill scored | Insolvent counterfactual, -100% retained |

For the original invented $1,000 fill and $2,000 capital, the corrected
midpoint-exit components remain -$0.0400465/-$0.390093/-$0.7401395 at
1x/2x/3x with 100 hypothetical paid entry actions. With no assumed paid actions
they remain +$0.0099535/-$0.290093/-$0.5901395. The complete no-fill case now
reports -0.25/-0.50/-0.75 bp of capital. The unresolved case preserves the
assumed action-cost component while leaving the total unknown. The exit has
no verified fill, slippage or incremental action cost; the fee and paid-action
assumptions are conditional rather than the owner's actual account terms.

Spec, correction code, original fixture and prior results were frozen before
the run in `5be315c911cdb1561d4a82193fcd136d0f2e3c6d`. All 12 cells and eight
adversarial cases reproduced byte for byte, and an independent rational
checker passed **104 checks**; deliberately corrupted cash and duplicate-case
artifacts were rejected. Thirty focused guard/account tests passed, and the
complete project-environment suite passed **1,685 tests, 3 skipped**. An initial
system-Python run was stopped after missing `numba` and `pyarrow` became clear;
it was not counted as a completed validation.
The independent pre-freeze review also checked uncertainty-window boundaries;
the accepted zero/10 ns bounds were constructed assumptions. No strategy
variant, market acquisition, order or prospective paper day was added.

The wrapper relies on the caller's BBO, complete receipt history, timestamp
bound and prepayment attestations. It does not verify them against the venue,
reconstruct queue priority or simulate liquidation. `path_solvency_unknown`
therefore remains true even when a hypothetical endpoint balance is positive.
Real first-seen market and receipt evidence, realistic exit and fee details,
funding, capital risk and separate prospective validation remain prerequisites
to any claim of executable expected net return.
