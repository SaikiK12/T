# R358 — PARTIAL: literal checker correction passes; original failure retained

Frozen **8104c28** before invoking the corrected check.
PREREG SHA256 `0ed208eea2be1d6649b10503b111077cc78a39490f616d5e3a6b9e2e6f37a18b`.
This round changes ZERO R357financial files, source inputs, quantities, costs,
capital, output packets or risk limits. It replaces ONE expected-admission
expression in the independently implemented checker's AST in memory.

## The failure and exact correction

Original `scripts/check_settlement_account.py` assumed a case named
`separate_capital_shortfall` was always blocked. Its actual registered rule is
notional+entry fee <= EACH venue's own free capital, at the stressed entry
price of the SAME fixed base quantity. A lower stressed short entry price can
reduce reserved notional enough to cross that boundary. Four of the six cells
block; two remain admitted, with no hidden q, capital or fee change.

The original checker still fails and is not edited. The original error text,
source and all72results remain retained. The new tiny checker adapter first
verifies frozen identities and requires exactly the known original expression.
It computes the expected notional+fee with independent Fraction arithmetic.
Absent, unexpected or duplicate expressions fail closed. All other original
cell/cash/funding/fee/quantity/unknown/capital/risk/hash checks run unchanged.

## Executed result

- **6371checks PASS** over the SAME72invented cells and144native account/risk
  journals. The inner audit keeps its original R357label; review.json explicitly
  names R358, the one literal correction and zero financial/data changes.
- Results/journals/audit/review are byte-identical across two fresh output
  directories. Exact identities are in reproduction.json. R357's financial
  freeze preceded its outputs; R358's separate freeze preceded this correction.
- The0.01cash corruption control is rejected by the financial reconstruction at
  `native cash conservation`, not accepted by relaxing a numeric tolerance.
  The copied corrupt packet, expected assertion and unchanged original hashes
  are described in corruption_control.json.
- Three correction-specific unit tests pass; final full discovery executes
  **1612tests,0failures,3existing skips,198.912s**. The earlier1609test financial
  freeze pass and original failure are not replaced by these newer results.

All36unknown and4blocked-zero R357cells remain. Its1x/2x/3x outcomes and whole
capital/separate-venue risk analysis are in
[R357 FINDINGS](../settlement_account_v1/FINDINGS.md). This checking correction
has no independent market sample or positive-return inference. New predictive
variants=0; prospective strategy days=0; actual expected net stays unknown.
R355/R356and M267remain Claude's, unchanged. No market acquisition, process,
order, money, secret inspection, merge or activation.
