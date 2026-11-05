# R406 notes (outside the frozen PREREG)

## 2026-11-05: R407 shows the native payoff is not exactly price-independent
Codex's R407 (`experiments/locked_carry_mechanics_v1/FINDINGS.md`, merged in PR #78) shows two sizing defects in
`scripts/lockcarry_rule.py`:
- **Best-bid sizing.** Q is sized at the best bid, so when the walk reaches deeper bids the hedge covers more coin than
  is held.
- **Fees after sizing.** The entry futures fee and the assumed delivery fee are taken in coin after Q is sized.

R407 also places the inverse delivery fee at face/P at delivery, not at the entry price. The rule is frozen and stays
unchanged. A corrected rule (R407's `lab/locked_carry.py`) needs its own frozen lane.

**Size of the effect on the two open locks.** This is read from `journal/locks.csv` with `unhedged_coins` as recorded
at entry. Settlement adds residual x (P - F_avg) x (1 - exit cost):

| Lock | F_avg | Residual coin | bp of coins | diff_bp at P = 0.5 F | at P = 1.5 F | \|diff\| > 10 bp needs |
|---|---:|---:|---:|---:|---:|---:|
| H0 BTC-25DEC26 | 78,900.2 | -0.000077 | -6.0 | +3.0 | -3.0 | \|P/F - 1\| > 1.66 |
| H0 ETH-25JUN27 | 2,406.8 | -0.003566 | -8.3 | +4.3 | -4.3 | \|P/F - 1\| > 1.20 |

**What follows for the first read.**
- Both locks are walked at one bid level; the residual is the 6 bp of entry fees taken after sizing.
- The remaining short exposure is a few bp per 50% move. It stays inside the frozen |diff_bp| <= 10 test unless the
  price moves more than 120-166%.
- So that test cannot detect this defect at normal moves. A MECHANICS PASS confirms the accounting identity and the
  delivery-price source, not exact price independence.
- The first read must report this alongside the verdict.
