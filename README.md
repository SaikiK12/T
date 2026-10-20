# T — quant research lab

The objective is net executable MEXC altcoin-perpetual strategies, followed by genuinely new prospective paper
evidence. Spot, prop challenges, forex and index futures extend the research when their data and execution can be
tested. A historical return is a research result; it earns confidence through the gates below.

Development currently lives on [`claude/yo-9a1k5w`](https://github.com/SaikiK12/T/tree/claude/yo-9a1k5w), tracked by
[PR #1](https://github.com/SaikiK12/T/pull/1). Proposed changes target that working branch. Active writers and
handoffs are recorded in [issue #7](https://github.com/SaikiK12/T/issues/7).

## Start here

| Question | Canonical source |
|---|---|
| Where are we now? | [Panel](docs/PANEL.md), generated from committed registries and lane status |
| Where is a document, command or experiment? | [Repository navigation](docs/README.md); `python scripts/repository_index.py --find funding` |
| What is the current direction? | [Direction](docs/DIRECTION.md) |
| What has been tested, and what remains open? | [Live methods queue](registry/methods.csv); [queue conventions and original snapshot](docs/METHODS_QUEUE.md) |
| What would justify paper or real execution? | [Gates](docs/GATES.md) and [critique](docs/CRITIQUE.md) |
| What evidence supports each result? | [Round registry](registry/rounds.csv), [map](docs/MAP.md) and [scoreboard](docs/EDGE_SCOREBOARD.md) |
| Who owns the next change? | [Coordination room](https://github.com/SaikiK12/T/issues/7) and [room protocol](docs/ROOM.md) |

Use the existing panel and queue when adding ideas. A method's record names its exact tested scope, aliases,
remaining mechanics and data blockers. NULL results remain part of the evidence.

## Repository layout

- `lab/`: data, accounting, inference and gate primitives.
- `scripts/`: explicit acquisition, study, recorder and paper-runner commands.
- `experiments/<lane>/`: frozen `PREREG.md` and digest, findings and reproducible result artifacts.
- `registry/`: append-only research rounds and the canonical methods queue.
- `research/intake/`: versioned source extraction and aliases for reconciliation with that queue.
- `docs/`: current navigation, research interpretation and historical provenance.
- `tests/`: offline unit and synthetic checks; `templates/lane/`: a starting point for a new lane.

Bulk source archives and caches stay outside Git. Each study states the required local inputs and hashes;
opening this repository does not make Claude's separate sandbox data available here.

## Local checks

```sh
python3 -m venv .venv
.venv/bin/pip install numpy pandas numba scipy pyarrow
.venv/bin/python -m unittest discover -s tests -t .
.venv/bin/python scripts/check_research_integrity.py
.venv/bin/python scripts/repository_index.py --check
```

Use the package versions recorded in a study's manifest when reproducing its artifacts. Fetching data and running
market studies are separate operations; read the lane's frozen protocol and input requirements first. Reserved
samples follow their explicit read budget in [GATES](docs/GATES.md).

Navigation is generated from tracked files. After adding documents, commands or lanes, stage the new paths and run
`python scripts/repository_index.py --write`. Existing filenames remain stable because frozen studies and source
hashes depend on them. New research sources go through `research/intake/`, then reconcile with `registry/methods.csv`;
keep historical notes as dated provenance and use the panel for current operating status.

Contributor rules: [AGENTS.md](AGENTS.md). Freeze and commit a finite specification/code before measuring outcomes;
retain cost sensitivity, controls, exclusions and provenance. Existing frozen files and append-only journals remain
intact. The owner places any real trades only after the required gates.
