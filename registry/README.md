# Research registry

[Repository home](../README.md) · [Human reading guide](../docs/guides/START_HERE.fr.md)

This folder contains canonical structured records. Use their identifiers to
connect an idea, its source and the experiments that examined it.

| File | Meaning | Update contract |
|---|---|---|
| [methods.csv](methods.csv) | Live method queue; `M…` identifiers, availability, status and linked rounds | Coordinate changes to the relevant row |
| [rounds.csv](rounds.csv) | Registered experiments; `R…` identifiers, trial counts and recorded verdicts | Append through registry code; retain history |
| [methods_aliases.csv](methods_aliases.csv) | Source records and aliases mapped to existing methods | Reuse the existing method before adding another |
| [candidates.csv](candidates.csv) | Candidate records and their gates | Read alongside native lane evidence |
| [data_manifest.csv](data_manifest.csv) | Dataset inventory and source paths | Inventory is not proof of complete/live data |
| `method_id_reassignment_*.json` | Explicit historical identifier corrections | Preserve provenance |

`M…` is an idea or method; `R…` is a registered round. A method may have several
rounds with different frozen designs. Each experiment's PREREG and FINDINGS
define its exact scope; a registry snapshot does not replace them.

From the repository root, inspect existing records without starting work:

```sh
.venv/bin/python -m lab find --trace M290
.venv/bin/python -m lab find R400
.venv/bin/python -m lab integrity
```

Working rules: [AGENTS.md](../AGENTS.md). The generated panel/catalogs and dated
queue notes are views of these records, not separate live queues.
