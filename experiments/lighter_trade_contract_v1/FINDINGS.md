# R427: recorded position identities support the existing Lighter maker-side convention

**SAMPLED_ROLE_CONTRACT_PASS.** The existing interpretation,
`is_maker_ask=true` means ask maker / buyer taker, matches every tested
signed base-position identity in both retained source fragments. The
opposite interpretation, found in the primary agent-kit example, matches
none. No price, markout, return, rate magnitude or strategy PnL was read.

| Fixed source | Rows | Recurring account IDs | Position transitions | Existing convention exact matches | Opposite convention matches |
|---|---:|---:|---:|---:|---:|
|WTI, Oct29 fragment|102|24|169|169|0|
|BRENTOIL, Oct29 fragment|32|10|50|50|0|

There are **219 source transitions**, reused under both hypotheses, not438
independent observations or successful trades. The independent
[Fraction/account-history checker](results/independent_accounting.json)
reproduces all438hypothesis-labelled comparisons, including the219retained
mismatches under the opposite convention. It checks the original report;
it is not another convention search or economic run.

## Meaning for the strategy work

This supports the source-role assignment used in R426 and the existing tape
parser for these observed files. A source warning alone was not a reason to
flip signs or reopen all historical nulls. The old parser, R426 code/inputs
and report are unchanged; its negative before-funding outputs and unpriced
exits remain. No new maker profit or source-qualified own fill is claimed.

M441's untested participant-flow work can use this sampled qualification
when specifying how public maker/taker positions map to account IDs. It
still needs sufficient unseen day blocks, receipt-time features, completed
markout horizons, real costs and execution evidence. Account IDs are not
people; concentration and dependence cannot be turned into independent bets.
Do not tune a toxicity or inventory filter on this short fragment.

## Scope and limits

The question is a source contract, not a prediction. All134ordinary trade
rows are used in the fixed transaction-microsecond/trade-ID order. Required
coverage was fixed before measurement:8transitions,2accounts and2previous
ask/bid transitions per market. Nothing was excluded to improve consistency.
Signed positions and quantities recover on the declared current lot grid
under the fixed serialization allowance; subsequent identities are exact
integers with zero residual tolerance.

Trade-ID gaps remain explicit. Their counter scope and complete capture
are not certified. Public positions are same-provider reports, not private
order/fill acknowledgements, independent cleared cash or proof of the
deployed Oct29 serializer/circuit. Current lot precision may differ from
historical rules. A sampled match does not guarantee global field stability,
clock calibration, queue priority, fill probability, source continuity,
France eligibility, funding cash, future profit or safe leverage.

**OOS/live strategy:no. Costs1x/2x/3x:N/A, not zero.** There is no financial
outcome or alpha evidence grade to upgrade. The separate M449 funding gap
is unchanged: the official historical-funding issue still has no maintainer
cash-unit answer in the retained Nov7thread. A chart normalization or a
secondary package's claimed live ratio is not that answer.

## Immutable lineage and validation

The [37-input manifest](inputs.json), [PREREG](PREREG.md) and frozen code
were committed and pushed at **90bdd6c67e86e096ce94135c9d839856cc116217**
before the single source-position run. PREREG digest:
`0fee5b2ae640d28f7a6ce95edc26d4ae6e6c26dbe16d2d52c62e50751e6c3a05`.
[Run marker](results/RUN_STARTED.json) and [original report](results/report.json)
are retained. Report SHA256:
`279547c5c8255660365975980bfc01267a1e8fea6bfe74cbfcf6e8b66d7324b9`.

Before the freeze, the full locked-environment suite passed
**2587tests,3skipped,430.716seconds**, including12new synthetic source-contract
tests. Integrity0errors/14legacy warnings and staged catalogs match. No
actual source relationship was used by those synthetic tests.

**0predictive/economic trials**; program total **9784361** through
`registry.program_trials`. The original accumulated historical allowance
retains every old reservation plus the conservative static-document cap:
**7819calls/251220970bytes**, not a new grant. No new market source, native
tick, recorder, daemon, real order, money, account, credential, protected
sample, frozen-file edit or subagent.
