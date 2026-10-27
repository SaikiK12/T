# PREREG: R341 exact-type correction of R340's independent checker

- **Registry id:** R341
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-27
- Claim: https://github.com/SaikiK12/T/issues/7#issuecomment-6434478095

## Known failure and strictly limited change

R340 economic freeze d24b05f produced its full finite report, but its independent
oracle stopped on `Fraction(25000,25941) != 0.9637253768166224`. The zero-charge
branch creates exactly1.0 by integer division; its reference hurdle then becomes
a binary float. Preserve the original code, results and failure text.

The NEW checker-only adapter normalizes q, residual, settlement price, delivery
fee, sale fee, spent cash and capital to exact Fractions BEFORE invoking the
UNCHANGED original hurdle helper. Reject every noninteger/nonfinite binary float;
the only float produced by the existing zero-fee branch is exactly1.0. Keep all
original exact equality assertions; no tolerance, rounding, gate, fee, threshold,
source rule or economic result is changed. A scoped one-process function binding
is restored on exit; no frozen source file or persistent runtime is altered.

The original independent audit imports no production financial/account/selection
code. Invoke every original audit check, not a selected subset. The adapter's
regressions reproduce the old error on a literal rational hurdle, verify its
same-value repair, reject noninteger floats/NaN/infinity and still reject an
incorrect ratio. New and relevant old targeted tests must pass before commit.
R340's new lab module already passed the full1,537test suite before its commit;
R341 changes no lab module. No repeated market/historical computation is needed.

## Frozen exact scope

- code_inputs.json SHA256 5d038d1e1c42a05bd03a6102fc3f3fbbf29682dede4fdf07c0fac6781b7105cc
- data_inputs.json SHA256 cfba5b79e66e0b54e3ebf84d4f861a9f4e7f38686ece3ad7782a29937fb6d148
- fixtures.json SHA256 df6a5967d2ad05d48dd9b433f9b162f6261ec0b73bfb3c7b2c5a2ca921ccc586

Pin R340's whole closure plus this checker and its tests, original failed audit
text, compressed report, summary, parent spec/sidecars/manifests and fixture.
R341 fixtures.json is byte-identical to R340. Freeze and commit BEFORE running
the corrected audit. Verify both complete closures before/after auditing.

The SAME R340 result bytes retain12missing current slots,72old guard slots and
1,548normalized algebra cells from129rounded published R335 ticket rows, at fixed
1x/2x/3x with zero-charge and old-rate/base/quote-fee controls. No row, family,
quantity, payoff, cost or null is selected or recomputed. Current source metadata
access is still blocked; no actual margin, owner fees, exit-price/FX or expected
return is certified. R335 returns and original DATA_PASS stay as published.

Audit in two fresh directories containing identical R340 result/summary bytes;
require identical audit JSON. Preserve any failure rather than editing frozen
code. PARTIAL means checked fee-reserve/cash-hurdle component on known inputs,
not alpha, independent strategy performance, a new historical sample, prospective
day or activation. Every unknown actual income and false activation stays.

Predictive trials0; program9,479,013 unchanged. These dependent diagnostic cells
do not count as new profitable variants or owner enhancements. Source/current
budget stays CLOSED at2attempts/362actual bytes,1MiB/16s reserved; no new request.
Historical7757/reported229.85MiB and closed66-request source batch unchanged.
Append R340/R341 via registry helper, old bytes retained; reconcile exact open
scope in existing M244, no duplicate queue/panel. R337/forward files remain
Claude's. No orders, money, secret values, login/region/API bypass, downloads,
PR merge/closure or permanent/scheduled execution promise.
