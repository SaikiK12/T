# Repo hygiene plan (read-only audit)

Scope: the owner branch `claude/yo-9a1k5w` at `2e0efb9`, read from a snapshot in the scratchpad. Nothing was modified, merged or deleted. This plan is a proposal for the owner and the active writer.

Method: workflow `wf_c1dfaf39-072` (10 agents). Nine returned. The synthesis agent hit the session limit, so this plan was written by the coordinator from the journal. Every path in it was checked to exist, and the headline numbers were recomputed from `registry/rounds.csv`.

## 1. Headline

- 60 markdown files outside `experiments/` were read: 33 canonical, 15 current snapshots, 6 superseded, 6 stale.
- 69 overlap clusters were proposed. Verification verdicts: 24 approve, 44 modify, 1 reject (C64).
- No merge is safe as proposed. Each of the 44 "modify" verdicts needs facts copied into the canonical file first. C64 (Quantpedia into SOURCES) is rejected.
- The real problem is contradictory numbers, not duplicate prose. See section 2.

## 2. Contradictions that change verdicts (highest priority)

These are the `resolve_contradiction` clusters. They matter more than any merge.

- **Cost convention.** The lab's tier model (`engine.cost_matrix`, 6/8/12/20 bp one way) is the one the lanes use. FOUNDATION still states a flat 0.002. MEXC taker fee is stated differently across MEXC_EDGES, EDGE_SCOREBOARD and MAP (C44, C45).
- **Program trial total.** Raw registry sum is 9,478,495 (verified). EDGE_SCOREBOARD, PANEL and MAP quote other totals (C46, C47). Atlas-lane rows are 98.1% of the total (verified).
- **Gate day counts and forward decision rules.** GATES and the forward docs disagree on day counts and on whether replay days count (C48). This decides R200.
- **Data reachability.** FRED, liquidation data and the zero-trade denominator are described differently in DATA_SOURCES, FOREX_AND_INDICES, MAP and CLAIMS (C50, C51, C52).
- **Prop-firm facts.** PROP_FIRMS, SOURCES, CLAIMS, CONCEPTS and MAP disagree (C53). The owner's Claude has already corrected the Topstep eligibility rule in PROP_FIRMS.
- **Registry, PREREG and folder mismatches.** `xfund_lt_v1` names R288, which has no registry row (R287 is followed by R289). `battery_v1` (R184, PLANNED) has a PREREG but no sha256 file. Four folders lack a registry row (C60).
- **Holdout definition.** Some lanes use windows that overlap discovery. Only the 2025-07-01 holdout is a holdout (C61).

## 3. The quant lab: real use versus stated value

The live spine is real:
- `prereg.verify()` guards the lane runners, with 98 call sites.
- `registry.program_trials()` feeds the panel and the dashboard.
- `gate.go_real()` runs in the forward scripts that `forward_all.sh` calls hourly.

Scaffolding or unwired (verified where marked):
- **Full-pipeline null, `lab/nulls.py`.** No caller outside tests (verified). Lane runners build their own nulls. The rules require the full-pipeline null for any search verdict, so this is a gap.
- **Multiple-testing tools, `lab/inference.py`.** PBO/CSCV, MCS, LORD+, online FDR, BH and empirical-Bayes shrinkage have no caller outside tests. DSR is used by three lanes.
- **Shared constants, `lab/config.py`.** Not read by the lanes. Each lane redefines its own costs. `COST = 0.002` is not used by the research path (verified: only tests import the module).
- **Holdout guard, `allow_holdout=True`.** No opt-in exists anywhere in `scripts/` or `experiments/` (verified).
- **`lab/flow.py`.** No Python importer (verified). It is a CLI, and its output feeds `flowfeat`. The flow pipeline is the main forward book and has no test file.
- **Tests only:** `auction`, `exposure`, `microstructure`, `orderflow`. **One-offs:** `daily`, `levcarry`, `policy`, `sizecarry`.
- **Gate 3 is not built.** No margin-tier, liquidation or daily-stop replay exists for the directional MEXC books. The forward scripts compute drawdowns and never halt a book.

Verdict: the pre-registration, registry and forward spine is real. Most of the machinery FOUNDATION names is scaffolding, and the flow book, the main forward book, is the least tested code.

## 4. Registry facts

Verified by the coordinator from `registry/rounds.csv`:
- 106 rows: NULL 67, PENDING 19, PARTIAL 8, CONFIRMED 7, DATA_PASS 5.
- Program trials: 9,478,495. Six rows have unparsed trial counts.
- Atlas-lane rows: 9,302,782 (98.1%).

Not verified: the workflow's reading that no lane passes gate 1. Notes on the 7 CONFIRMED rows also need a check, since earlier notes showed they mark in-sample passes.

## 5. Experiment lanes

From the lane inventory (not re-checked by the coordinator):
- 106 folders. 100 have a registry row. Without one: `propsim_v1`, `recorders`, `xfund_lt_v1`, `copylead_data`, `forward_lag`, and `README.md`, which is the index and not a lane.
- Without a PREREG: `propsim_v1`, `recorders`, `copylead_data`, `forward_lag`.
- Without FINDINGS: about 22 folders, most of them forward lanes that keep tickets and journals instead. Decide whether FINDINGS is required for forward lanes.
- `scripts/catalog.py` lists non-lane folders as lanes (C43).

## 6. Proposed action plan (non-destructive first)

1. **Write one canonical facts table** for cost convention, trial total, gate day counts and data reachability. Put it in the canonical doc named in section 2. Copy each fact before any merge. Owner's Claude or the active writer does this.
2. **Repair the registry and PREREG gaps** with sidecar notes and new allocated IDs. Do not edit frozen PREREG files or append PLANNED rows by hand. Follow the room's ID-claim rule.
3. **Archive, do not delete.** Move superseded and stale docs to `docs/archive/` with a pointer, and only after step 1 has copied their facts.
4. **Delete candidates:** none recommended now. Decide after step 3.
5. **Lab:** wire `lab/nulls.py` into a lane runner before any new round. Add tests for `flowfeat` and `lab/flow.py`. Decide whether unused or one-off modules move to an archive.

## 7. OWNER DECISIONS

1. Confirm the holdout is spent for every lane, and set the guard policy.
2. Name `engine.cost_matrix` as the single cost convention, and retire `config.COST`.
3. Choose the headline trial total: the raw sum (9,478,495) or the total excluding atlas.
4. Approve archiving the 6 superseded docs, after the facts are copied.
5. Decide whether the full-pipeline null is wired into lane runners before the next round.
6. Decide whether `lab/flow.py` and `flowfeat` get tests before the flow book's next decision.

## 8. Not checked

- The synthesis agent did not run. This plan is the coordinator's reading of the journal.
- `data/` is absent, and the tests were not run.
- The lane verdicts and most lane inventory fields were not recomputed.
- The owner branch will have moved since `2e0efb9`.
- Verifier entries are as returned by the verifying agents. Only path existence and the headline counts were checked again.
