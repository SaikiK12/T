# Evidence integrity: can the survivors and nulls carry the direction decision?

**Verdict:** No for the survivors. They rest on in-sample selection, a spent holdout, a TradFi-driven forward replay and pipeline fixes that have not been re-run, so they cannot base the decision yet. The nulls are more usable, because most open defects can only inflate results (zero-latency fills, free exits from gapped or delisted coins). Neither side can be recomputed here: the checkout has no market data (`data/` and `cache/` are absent).

**Checks run.** `scripts/check_research_integrity.py`: 77 registry rows, 71 local specs, 70 hash-verified, 0 errors, 12 warnings (missing legacy folders, blank digests). Unit tests: the checkout's own Python lacks numba and scipy (17 import errors); in a scratch venv (numpy 2.3.5, pandas 2.2.3, numba 0.68.0, pyarrow 26.0.0, scipy 1.18.1) all 343 pass. `research/r221_sequential_null.py` (no market data) reproduces the table in `docs/SELECTION_AND_TRIAL_ACCOUNTING_AUDIT.md`.

## Open problems, ranked by effect on the verdict

1. **The forward decision sample is 95% replay.** R200 journal (`experiments/flow72_fwd2/journal/tickets.csv`): 19 days, 18 flagged `late`. Replay sums of daily net, 1x/2x/3x: A +22.2/+21.0/+19.7%, B +9.5/+9.2/+9.0%. The one on-time day (10-19) gives A +0.05%, B −0.26%. `scripts/forward_tick.py:210-221` scores all tickets, ignores `late`, and sets the verdict at 90 tickets. The PREREG decision counts replay days. `scripts/forward_lag.py` says frozen decisions are unchanged. CRITIQUE row 6 ("done: only strict on-time days count") is wrong for the frozen verdicts.

2. **The headline forward book is not the in-sample book.** R200's universe includes `TRADIFI_PERPETUAL` (its PREREG, "Frozen rules"), though it is labelled "R197's construction". `experiments/venue_gap_v1/FINDINGS.md` §1: TradFi is 49% of A's replay gross and all of B's replay profit; crypto-only A is +8.7% at 1x, B −0.5%. The archive has no TradFi before 2025-12 (§2), so the TradFi book has no in-sample test. The owner's target is MEXC crypto.

3. **Holdout selection feeds a decided book.** R216 chose crypto-only B as "best holdout t" (+18.25 bp/day, t 2.74). R221 (`experiments/mexc_seq/PREREG.md` lines 24-25) decides on that book, but its Bonferroni family covers only the three frozen books. R221's boundaries are also miscalibrated under its own statistic: with iid normal returns and NW lag 10, one book crosses at 1.17% against an allocation of 0.833%; the 3-day-overlap case gives 1.52%. My run reproduces the audit table.

4. **The engine zero-fills gaps, funding and exits.** `lab/engine.py:165-168` and `:91` add nothing when a return is NaN, so a held coin with a missing bar earns zero and stays held. `:38` maps missing funding to zero. `lab/slices.py:64` (legacy `nan_to_num`) and `:92` do the same. `positions()` (`:13`) ignores eligibility, so slices in a coin that leaves the top 50 or stops trading keep earning and pay no exit cost. Delisting is valued at the last close. The sign depends on the path; the size is unmeasured. The TARGET fix does not reach this path.

5. **Nulls are thin; the ledger overstates.** `lab/nulls.py` (60 replicates, `search_verdict`, `familywise_p`) is called by no script, only by tests. `scripts/run_atlas.py:113` and `scripts/run_battery.py:85` use two placebo shifts, so placebo rates and FDR rest on two draws, not 60. Program trials (sum of `registry/rounds.csv`, computed here) = 9,472,034, 88% from R192 (correlated atlas cells). Seven rows read CONFIRMED (R181, R185, R190, R191, R192, R195, R197); several are in-sample only, and R191's 2x t is 1.14 (`experiments/carry_holdout/FINDINGS.md`). EDGE_SCOREBOARD.md:116 says so, but the append-only ledger cannot be corrected in place. Six trial counts are blank (R143, R144, R180, R181, R183, R184); R202 records 0 despite a best-of-10 size choice.

6. **Freeze order is not provable from git.** History begins at root commit `611943d` (2026-10-19 14:41 UTC, 376 files). 34 lanes first appear there with their `PREREG.sha256` and first results. No `PREREG.md` has a second commit, and all 70 sidecars verify, so specs have not changed since freeze. Freeze-before-measure cannot be shown for any lane before that commit.

7. **Timing is optimistic, and the R200 spec is infeasible as written.** `lab/panel.py:3`: a signal at row i uses bar i and earns close_i to close_(i+1), with zero latency. R200's PREREG requires computation "at least 12 minutes" after the close, yet sets the position "at the close of t". On flow books a 1-hour delay costs about 1% (R213: A in-sample +12.10 to +11.99 bp/day). Other books are untested.

8. **Survivorship on the venue side.** `lab/data.py:88` lists archive perps, delisted included, so archive backtests include delisted names. But `lab/mexc.py:49` `contracts()` is a snapshot of today's listings, and `map_symbols` (`:66`) matches only those. MEXC coverage is today's survivors, and no MEXC history has been downloaded (CRITIQUE ask 2). R200 drops coins delisted before each tick (disclosed).

9. **The stated cost is not the cost used.** `lab/config.py:13` (`COST = 0.002`) is referenced nowhere. The engine charges tiered one-way costs of 6/8/12/20 bp by trailing rank (`lab/engine.py:42-47`), with `cmult` for 2x and 3x. A round trip is twice one-way.

10. **Forward gate and sampling.** `go_real` is called without `entry_days`, so `n_clusters` is None (`journal/status.json`). The R200 data gate tested common coins only (99.5-99.98%); the all-coin bins the book uses agree 87-93% (DEVIATIONS.md, "Known and not changed"). `parity.json` was last committed in `611943d`, before the `737448d` fixes; whether it was re-run is unverified.

**Reported survivors at 1x / 2x / 3x (returns)**

| Result | 1x | 2x | 3x | Source |
|---|---|---|---|---|
| R197 flow book, in-sample (t 3.25) | +42.6%/yr | +26.9%/yr | +11.3%/yr | registry R197 |
| R198 flow book, holdout, spent (t 1.22) | +82.9%/yr | +61.8% (t 0.91) | +40.7% (t 0.60) | `experiments/flow72_holdout/FINDINGS.md:29` |
| R216 holdout, crypto-only A | +22.3 bp/day | +17.3 | +12.3 | `experiments/venue_gap_v1/FINDINGS.md` §2 |
| R216 holdout, crypto-only B (t 2.74) | +18.3 bp/day | +17.4 | +16.5 | same |
| R191 carry, holdout (t 2.07 at 1x) | +1.2%/yr | +0.5%/yr (t 1.14) | not reported | `experiments/carry_holdout/FINDINGS.md` |
| R200 replay, A (18 days) | +22.2% | +21.0% | +19.7% | `journal/tickets.csv`, my sums |
| R216 replay, crypto-only A / MEXC-mapped A | +8.7% / +4.7% | +7.8% / +3.8% | +6.8% / +2.9% | venue_gap §1 |
| R186 merge_v1, net | −32.6%/yr | break-even at 0.42-1.01x cost | | registry R186 |

**Pipeline or no edge?** Most open defects can only inflate results. Two can deflate them: the atlas's legacy NaN-bridging, and zero-filled moves in short books into delisting (a short that gains into delisting is scored flat). Their size is unmeasured, so a null is informative only up to that share. R196 (primary −20%/yr, t −2.73) and R197 (+42.6%/yr, t 3.25) use related flow cells with opposite signs. That is either a sign or timing defect or a noisy search; no test in the repo separates the two. Check it before reading either as evidence.

## Fixed problems and whether they touched past results

- **Atlas label bridging and the holdout-equality guard** (`docs/TARGET_INTEGRITY_FIX.md`): in code, but opt-in. Defaults are unchanged, so archived atlas results (R185, R192, R195) still bridge gaps. The guard sits only in `lab/research.py:60-62`. `scripts/run_atlas.py:142-143` validates up to the holdout row, so its last return uses the 2025-07-01 01:00 close. This is one hour per coin per window at the boundary, not quantified. No archived result has been recomputed.
- **Strict cache verification** (DATA_PROVENANCE #1, PR #11): strict mode checks SHA-256; `lab/data.py` `build` still defaults to non-strict. Partial.
- **Forward-pipeline fixes** (`experiments/flow72_fwd2/DEVIATIONS.md` 1-4, commit `737448d`, after the freeze): newest-hour window, hour waiting, aborting on fetch failure (funding failures had scored as zero), duplicate protection, stop rule recorded. Journal rows are append-only, so affected signals remain, and the replay totals (computed before the fix) are not known to be unaffected. The stop rule is recorded but not applied to the verdict (`forward_tick.py:217-221`): open.
- **Registry id allocation** (AUDIT #10): fixed by the locked `append`. **Trial-ledger gaps** (AUDIT #1, CRITIQUE #12): open.
- **Flat cost** (AUDIT #3): superseded in the engine by rank tiers. The flat constant survives only in `config.py`.
- No fix has been re-run on archived outputs, so none is shown to change a past number.

## Unverified

- No number was recomputed; every figure comes from docs, registry, journals or code.
- R179-R183 (unlock short, hypermine): no code, PREREG or data in this repo, and no git ref contains them (`docs/OLD_SESSION_EDGES.md:35`). The strongest old edge cannot be checked here, and its cost sensitivity is unknown.
- Not measured: holdout-boundary effect size; funding zero-fills before the 10-19 fix; the "900 perps" count; MEXC coverage of 56%/33% (R215); zero-latency effect on non-flow books; the R196-vs-R197 sign question.
- The "holdout read by more than ten lanes" figure is from CRITIQUE and was not re-derived.
- Timeline support: `tick.log` prints the PREREG hash at 09:56:06 UTC and the first replay totals at 10:14:48 UTC on 2026-10-19. That supports "not looked at before freeze" but does not prove it.
- Housekeeping: my first unit-test run left gitignored `__pycache__` folders in `lab/`, `scripts/` and `tests/`. Deleting them was refused by the permission check, so they remain for the owner to remove. This note is the only file written.
