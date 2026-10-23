# Rules for anyone working here, human or AI

Carried over from the owner's rules in the original project (**S**, see `docs/FOUNDATION.md`). They win over convenience.

## Hard rules
1. **Register before measuring.** `PREREG.md` is frozen with `lab.prereg.freeze()` before any statistic. Run scripts call `verify()` first.
2. **Frozen files are never edited.** A changed idea is a new lane with a new id.
3. **Journals are append-only**: `registry/rounds.csv`, `ledger.csv`, forward tickets. Use the code that appends; never hand-edit a row.
4. **One writer per file.** Check the mtime before editing. Never kill a process you did not start.
5. **No real orders, no money movement, no credentials, no deleted data.** Those need the owner. Large downloads need the owner's explicit yes.
6. **Real money only after paper proves a net gain**, through `lab.gate.go_real()`, in small stakes, placed by the owner.
7. **Never claim something works without running it.** Say plainly what was not checked.
8. **A null is a result.** Record it with the same care as a hit.

## Working rules
- **Read by task, not by corpus.** Start with fresh writer claims in issue #7, open PRs, and the timestamp on
  `docs/PANEL.md`. Then read only the relevant method rows and linked lane evidence. Do not reread every research
  note or start a new search just because a dated memo calls an idea open.
- **One authority for each fact.** `registry/methods.csv` is the live queue; `registry/rounds.csv` records round
  status/trials/verdicts; each lane's frozen PREREG and FINDINGS define exact tested scope. `docs/METHODS_QUEUE.md`
  is a historical snapshot. PANEL and folder README catalogs are generated views, not proof of process health.
- **Reuse the existing record.** Put a lane's result in its FINDINGS and source extraction/aliases in the existing
  `research/intake/` bundle, `registry/methods_aliases.csv` and live queue. Keep audits and dated proposals as evidence, not competing task lists.
  Before merging or moving a document, check unique facts and inbound references; frozen links and provenance stay valid.
- In new PREREGs, keep the Registry id alone on its metadata line, as in `templates/lane/PREREG.md`; put claim
  history and method notes on separate lines. Historical annotations stay frozen; fix their reader when necessary.
- The root README is the maintained document index. `python -m lab find TEXT` queries tracked metadata without
  saving another index. Keep source/evidence paths stable because frozen or hashed inputs can depend on them.
- Before publishing intake/queue changes, run `python -m lab integrity`. Keep historical source status separate
  from live queue status; catalog access is not full extraction. Source drift and missing mechanics remain open
  until reconciled; metadata checks do not validate profitability or authorize data access.
- Every round gets a registry row with its trial count, even when it finds nothing.
- Read a result against `registry.program_trials()`, not only against its own null.
- Report cost sensitivity (1x, 2x, 3x) in every FINDINGS.
- Check ROADMAP/FINDINGS for work another AI already did before starting; build on it.
- Run `python3 -m unittest discover -s tests -t .` before committing changes to `lab/`.
- Claude and ChatGPT/Codex talk in one room: issue #7 (`docs/ROOM.md` has the protocol). Read it before starting
  work, and post calls and results there in its short format.

Operational entry point: `python -m lab`; shared task/lane descriptors are in `lab/operations.py`.
Use `python -m lab check --suite fast` for feedback and the full suite before a code commit.
Fast/simulation selection never changes the full validation requirement above.
