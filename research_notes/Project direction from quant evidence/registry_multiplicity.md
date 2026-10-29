# Registry multiplicity: how much the search has done and what survived

Repo: /home/user/T (branch ccr-23562535-bd0mr3), audited 2026-10-20, read-only. No market data read; no statistic recomputed. Paths are repo-relative.

## Verdict

Probably noise: the one full-pipeline null in the registry (R182) returned NOISE (p_search 0.22), about 20 rounds have read the holdout, and the only holdout pass (R191, carry, t 2.07 at 1x) is below every family-wise bar the registry's counts imply (about 3.0 at 20 looks, 5.8 at the 9.47M raw total).

## Evidence

### Counts and status
- registry/rounds.csv: 77 rows, R143 to R256, 77 unique IDs. Verdicts: NULL 54, PENDING 11, CONFIRMED 7, PARTIAL 3, DATA_PASS 2. Status: DONE 66, RUNNING 7, REGISTERED 2, ARMED 1, PLANNED 1.
- lab/registry.py `program_trials()` over rounds.csv = 9,472,034 (recomputed). docs/EDGE_SCOREBOARD.md line 3 states 9,472,031; docs/RESEARCH_COVERAGE_LEDGER.md (search accounting section) states 9,471,756 after R226. Both are older snapshots. The 3-trial gap to the scoreboard is unexplained.
- registry/methods.csv: 233 methods. TESTED 83, BLOCKED 74, UNTESTED 33, PARTIAL 31, N/A 12. Twenty-two R-numbers cited there have no rounds row: R142, R152-R162, R165-R170, R174, R176-R179, R227.

### Trial concentration
- Three atlas rounds hold 9,302,782 trials (98.2%): R185 338,240 (line 14), R192 8,320,806 (line 23), R195 643,736 (line 24).
- R182 hypermine adds 139,377 (1.5%, line 6). Maker R193 and R194 add 24,800 (lines 12-13). Merges R186 and R187 add 4,572 (lines 18-19).
- The other roughly 70 rounds total 503 trials. Excluding atlas and hypermine gives N = 29,875.
- docs/SELECTION_AND_TRIAL_ACCOUNTING_AUDIT.md ("The registry total is not an effective trial count") says the total is not an effective N.

### Stage tallies
- The shared gates and null in lab/config.py (discovery n>=120, t>=3.5; validation t>=2; holdout t>=2; N_NULL=60; FW p<0.05) and lab/nulls.py are not called by any run script. Only tests/test_lab.py imports them.
- Lanes use their own gates. experiments/amihud_v1/PREREG.md lines 35-38 set discovery t>=2 and validation t>=1.5. experiments/xsrev_v1/PREREG.md line 38 sets validation t>=1.5. The counts below therefore use lane rules, not one scale.
- Candidate level: 25 lanes publish a `stages` dictionary in verdict.json, covering 138 candidates. Furthest stage reached: discovery 120 (all failed there), validation 16, holdout 2 (both failed). Holdout passes in these files: 0.
- Round level, from registry notes and verdict files:
  - 16 rounds failed discovery for every candidate: R219, R222, R223, R226, R234, R235, R237, R238, R243, R244, R245, R246, R247, R250, R252, R256.
  - 6 rounds failed after a discovery pass: R211, R236, R239, R241, R242, R251.
  - 3 rounds were validation-only by their own PREREG: R240 (experiments/posimpulse_v2/PREREG.md line 32), R248, R249.
  - 10 more reached validation and failed or were not run: R193, R212, R228-R233, R253, R255.
- Holdout: 20 rounds report holdout numbers: R189, R191, R198, R202, R204, R205, R207, R208, R209, R210, R213, R216, R217, R228-R232, R239, R241.
- Registered holdout passes: 1 (R191). Ambiguity: R205's Binance top-vs-crowd (t 2.08 over 157 days, line 29) meets t>=2 but was a same-window comparison, not a registered holdout test. The registry marks R205 NULL. If it counts, passes = 2.
- Null: one round ran the 60-replica full-pipeline null. R182 (line 6): n_disc 1777, n_val 2 against a null q95 of 4, p_search 0.2167, 0 candidates, verdict NOISE. Its folder is absent, so this is unverified here. Placebo comparisons in R185, R192 and R195 use a different reference (for example R185: 47.6% replication against 9.1% placebo).
- Family-wise: no round met p<0.05. Three report a figure: R182 p=0.2167 (line 6), R253 p=0.544 (line 76), R230 max-stat over 96 rules p=1 (line 53).

### Thresholds against recorded holdout t
Bonferroni, two-sided 5%, |t| required:

| N basis | N | required \|t\| |
|---|---:|---:|
| registry program total | 9,472,034 | 5.84 |
| excluding atlas and hypermine | 29,875 | 4.79 |
| candidate-level stage entries | 138 | 3.57 |
| rounds | 77 | 3.41 |
| holdout-reading rounds | 20 | 3.02 |

Recorded holdout t-statistics:
- R216 (line 40): crypto-only top_vs_crowd t 2.74. A post hoc subset, described in the scoreboard as the best of 7 series. Returns 1x +18.25, 2x +17.4, 3x +16.5 bp/day (docs/EDGE_SCOREBOARD.md, top_vs_crowd row).
- R198 (line 17): all-symbol top_vs_crowd t 2.72, reported not decided. Flow book A t 1.22 (fails).
- R205 (line 29): Binance top-vs-crowd t 2.08, 157 days.
- R191 (line 11): carry t 2.07 at 1x (+1.45%). 2x +0.66%, t 1.14 (scoreboard). 3x not found: unverified.
- R241 (line 64): SVXY-CONTANGO holdout t 1.70. R239 (line 62): VRP holdout t 1.11.

None reaches 3.02 at 20 reads. A t of 2.74 clears a 5% two-sided bar only if the effective number of looks is at most about 8. Bonferroni is conservative for correlated candidates, so these are rough bars, not calibrated thresholds.

### Hygiene
- Missing trial counts: R143, R144, R180, R181 (CONFIRMED, t 4.06, no count), R183, R184.
- Missing dates: R143, R144 (docs/FOUNDATION.md open items; the ROADMAP it names is not in the checkout), and R253. The integrity audit does not flag R253.
- Missing prereg_sha: R143, R144, R180, R183, R184.
- Missing lane folders (6): R143 funded, R144 challengeoption, R180 unlocks_sf, R181 unlocks_deep, R182 hypermine, R183 hypermine_expand.
- Folders with no rounds row: copylead_data, forward_lag, propsim_v1.
- Status conflict: R199 is REGISTERED (line 21), but R200 notes say R199 was ABANDONED (line 22).
- ID reassignments: R253 became R255 (experiments/cascmkt_v1) and R254 became R256 (experiments/dow_v1), documented in REGISTRY_REASSIGNMENT.json in both folders. R227 is reserved for Kronos (line 51) and has no row.
- `scripts/check_research_integrity.py --json` (read-only): 0 errors, 12 warnings (6 EXPERIMENT_MISSING, 5 REGISTRY_SHA_MISSING, 1 REGISTRY_ID_MISSING). 70 of 71 local specs verified frozen; 1 PLANNED draft (battery_v1).

### Widening or repeating
- Rounds per 24-ID block: R143-R190 has 13 rounds; R191-R212 has 22 (8,989,479 trials, mostly atlas); R213-R233 has 20 (188 trials); R234-R256 has 22 (141 trials).
- Since R213 each round averages under 10 trials, while the lanes move into new markets and rule types (TradFi calendar, FX, LMW patterns, pairs, ICT levels). This is widening in families that program_trials() cannot see.
- Repetition: top_vs_crowd underlies R197, R198, R211, R212 (headcount book "mostly top_vs_crowd" per the scoreboard), R213, R215, R216, R234 and R240. The flow-book holdout window was read by at least seven rounds: R198, R202, R208, R213, R216, R217 and R228.

## Open questions
1. Should the atlas count (9.3M, 98%) enter any correction? Atlas winners fed R192, R195 and later books. A per-candidate ledger with every filter stage would settle it; none is in the repo (docs/SELECTION_AND_TRIAL_ACCOUNTING_AUDIT.md, minimum ledger).
2. Can R182's null be reproduced? experiments/hypermine is absent, and it is the only frozen full-pipeline null result.
3. Which gate set governs? lab/config.py (t>=3.5, 60 replicas) is unused. Lane PREREGs use t>=2 and t>=1.5. The choice changes every stage count above.
4. Is R205's Binance top-vs-crowd (t 2.08) a holdout result? If yes, passes = 2.
5. How many looks has the holdout had? The notes give 20. A single effective N for the holdout is needed before any holdout t is read.
6. The remaining out-of-sample tests are forward: R215, R218 and R220 decide at 90 on-time days (about 2027-01-18, docs/GATES.md dates), and R221 at 182 and 365 days.

Not checked: market data, recomputed t-statistics, FINDINGS for about 40 lanes (stages from notes), R209's 6-of-8 versus 7-of-8 conflict, and docs/ROOM.md issue #7 (not posted to, since this task is read-only).
