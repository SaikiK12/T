# PREREG: literal expected-admission correction for R357's independent checker

- **Registry id:** R358
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-28
- Existing M409 accounting dependency and consolidation draft56; M267/R355/R356
  and every frozen R357 file remain read-only.
- Claim: issue7 comment6463891198.

## Why this separate correction

R357 was committed924a57e before its72invented accounting cells were run.
Its native runner completed. Its original independent checker failed on the
expectation that every `separate_capital_shortfall` cell must be blocked.
The original failure is retained byte-for-byte as R357/checker_failure.txt.
The expected-admission label was coded as a case-name equality, rather than
the registered per-venue notional+fee arithmetic at that cell's stressed price.
For a short entry, a lower stressed price reduces reserved entry notional for
the SAME fixed base quantity. This can change a boundary admission, despite
fees increasing. This correction is to the checker expectation, not the
financial policy, quantity, capital, input, cost or risk requirement.

Only ONE assignment expression in the original checker's AST is replaced IN
MEMORY: `blocked = case['id'] == 'separate_capital_shortfall'` becomes a call
to the independently implemented Fraction expression below. An absent,
different or repeated original expression is an error. No on-disk source edit
or other AST modification is permitted. The original checker is hashed,
unchanged and remains expected to fail when called directly on this output.
Its financial/journal/capital/unknown/risk reconstruction is otherwise identical.

For each venue independently: read the frozen fixed q, entry mid, original
entry fill, fee and capital. Price = mid+k*(fill-mid); notional=abs(q)*price;
fee=k*fee_bp*notional/10000. Block if EITHER venue requires notional+fee greater
than its own capital. Never borrow the other venue's money or change q/costs.
These are exactly the ORIGINAL R357 entry-reservation terms, not a more lenient
rule or an entry filter selected from profits. No cell or failure is removed.

## Finite verification

Freeze and COMMIT this spec, tiny checker adapter, tests and inputs manifest
before invoking the corrected checker. It imports no production financial,
quote, risk, source-rule or reporting algorithm. The wrapper verifies every
hashed input and the committed spec/manifest, then executes the separately
implemented original stdlib/Fraction checker with that one literal expression
corrected. Standard invocation is `--out PATH` with separate arguments.

Use the SAME72R357cells:12invented cases x2directions x1x/2x/3x. Original
results/journal compressed identities are frozen inputs. R357's original input
verification remains active. R358 also binds the resulting input packet identity;
no arbitrary new data can be supplied. Original1e-65financial,2e-12source-float
fraction/2e-9source-normalized quote tolerances remain UNCHANGED. A PASS means
only that all registered arithmetic/identity checks pass, not market efficacy.
Write an outer R358review receipt naming R357, the exact one-expression change,
original failure and zero financial changes; keep the original audit label.

Run/check in two fresh output directories. R357's financial runner is unchanged;
compare results/journals/audit/R358review byte-for-byte. Reopening native account
and risk journals must preserve exposures, pending cash and prior stops. A copy
with one native money field changed by0.01 must be rejected by the independently
corrected financial check; the original artifacts stay untouched. Preserve that
expected failure receipt. No new market/history/private request or process.

Three new unit controls verify the boundary arithmetic, one-expression-only
AST replacement/unchanged original, and rejection of unknown/multiple expressions.
Full suite is run before publication; the R357 lab-code commit already passed
1609tests with3existing skips. Actual final execution counts are reported later.

## Interpretation and records

All controls are INVENTED and have been seen in R357; they are not independent
unseen observations. R358 is a checking correction with0predictive variants and
0prospective days. R357/R358 remain PARTIAL engineering/source-contract evidence;
actual expected net, margin/execution/fee/session qualification and live cash are
unknown. Record BOTH rounds and original failure without editing old journals,
source code, rules or provenance. Native risk limits, all72cells, 1x/2x/3x costs,
10000total segregated capital and original frozen specimens remain intact.

The financial findings belong to R357; R358 explains only why its original
checker failed and what the independently reconstructed accounting supports.
It does not amend R355 scoring or upgrade a past ticket into prospective evidence.
Any corrected forward strategy needs its own frozen protocol and on-time new
inputs. R310/R311 findings, historical budget7757/8000requests and reported
229.85/250MiB, every closed source scope and immutable trial reservations remain.
No strategy activation, order, money, secret-value access, merge/closure or
promise of permanent execution.

## Frozen manifest

d267cb8830ed923d9302f43db5978231b2c3750127d4e9b6e8261909bb92e0ec  inputs.json
