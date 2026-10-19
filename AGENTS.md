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
- Every round gets a registry row with its trial count, even when it finds nothing.
- Read a result against `registry.program_trials()`, not only against its own null.
- Report cost sensitivity (1x, 2x, 3x) in every FINDINGS.
- Check ROADMAP/FINDINGS for work another AI already did before starting; build on it.
- Run `python3 -m unittest discover -s tests -t .` before committing changes to `lab/`.
- Claude and ChatGPT/Codex talk in one room: the draft PR titled "ROOM" (`docs/ROOM.md` has the protocol). Read
  it before starting work, and post calls and results there in its short format.
