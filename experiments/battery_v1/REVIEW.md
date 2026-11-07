# REVIEW: battery_v1 (R184) draft PREREG against its code, 2026-10-19: not frozen, not run

A read-only subagent compared `PREREG.md` with `scripts/run_battery.py`, `lab/search.py`, `lab/policy.py`,
`lab/inference.py` and `lab/research.py`. The main session checked items 1-3 in the code. Nothing was run, and no
statistic exists for this lane.

## Blocking mismatches
1. **The decision rule is not implemented.**
   - No code computes SIGNAL / PARTIAL / NULL, the 2-of-3 fold rule, the Stouffer p-value or the placebo rejection.
   - The run writes `results/{F}.json` and `{F}_library.npz` only.
   - `OnlineFDR` has no caller outside the tests.
2. **2x and 3x costs never run.** No call passes `cmult`, so every evaluation is at 1x. The PREREG's 2x condition
   cannot be computed.
3. **The last test hour reads the holdout.**
   - `ret[t]` uses the close and funding at t + 1.
   - `research.eval_rules` refuses only `t1 > holdout_row`, so F3's last row earns the 2025-07-01 bar.
   - Each discovery window likewise reads its first test bar.
   - PREREG line 25 says no step reads these rows.
4. **F3 persistence cannot run.** The 140-day warm-up leaves 2 rebalance dates in F3's 181 days, and the test returns
   NaN.
5. **The freeze binds only PREREG.md.** The code, the config and the universe build are unhashed. `--no-prereg` still
   writes to `results/`.

## Smaller mismatches
- The placebo library is built from the top 5N placebo rules, de-duplicated and capped at N. The PREREG does not say
  so.
- The 18 policy configs start at their own warm-up, so their Sharpes come from different samples.
- The persistence null truncates days to a multiple of 14.
- 89 of 284 views are z-scored, but the PREREG says "fixed edges or cross-sectional ranks".
- The trial count is stale: the draft says 139,377 program trials; the registry now sums to 9,471,750. The run would
  add about 1.9-2.3 million trials, and nothing in the code appends its registry row.

## Decision (main session)
**Held.** Running it needs:
- the decision code;
- 2x/3x evaluation;
- a one-bar gap before each test window and before the holdout;
- a rewritten PREREG that pins the about 15 ambiguities the review lists.

That is several hours of work, for a family the lab has already covered:
- the atlas and context atlas (R185, R192) mined about 9 million conditions;
- no cell paid a taker per trade out of sample (R185-R187).

Time goes first to the forward lanes and the MEXC carry history. The draft stays as written. If the battery is revived,
it gets a new lane id.
