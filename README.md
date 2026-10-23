# T

A pre-registered strategy-discovery lab for crypto perpetual futures. The goal is the best net PnL the owner can trade
(MEXC perps first), proven on data the search never saw and handed over through the gates in
[`docs/GATES.md`](docs/GATES.md). Nothing counts as an edge until it survives pre-registration, its family's reality
check, an unread sample or forward paper days, and costs at 1x, 2x and 3x.

## Where things are

| Path | What it holds |
|---|---|
| [`AGENTS.md`](AGENTS.md) | The hard rules for anyone working here, human or AI |
| [`docs/PANEL.md`](docs/PANEL.md) | Live status: objective, forward lanes, next decisions (`scripts/panel.py`) |
| `registry/` | `rounds.csv` (every round and its trial count, append-only), `methods.csv` (the method queue), `candidates.csv` (edges still alive) |
| [`experiments/`](experiments/README.md) | One folder per lane: `PREREG.md` (frozen before any statistic), `FINDINGS.md`, `results/`; forward lanes keep a `journal/`. The catalog lists every lane with its round, status and verdict |
| [`lab/`](lab/README.md) | Python research library: data, panel, features, backtester, inference (DSR, SPA/MCS, PBO), prereg, registry, gates, live paper |
| `engine/` | `qx`, the Rust engine: event, factor and cross-venue spread families from one TOML spec ([`engine/README.md`](engine/README.md)) |
| [`scripts/`](scripts/README.md) | Fetchers (`fetch_*`), recorders (`record_*`), lane runners (`run_*`, `qx_run.py`), the forward and notice loops, the dashboard export |
| `dashboard/` | The Control Room page; `scripts/dashboard_data.py` exports its datasets |
| `data/` | Downloaded and recorded data (not in git). Reserved samples sit under `reserved/` folders and are read only by a frozen batch PREREG |
| `templates/lane/` | Starting point for a new lane |

## Docs

Read by task instead of loading this entire list. The authority for current method status is
[`registry/methods.csv`](registry/methods.csv), and for recorded round status/trials/verdicts it is
[`registry/rounds.csv`](registry/rounds.csv). Read the linked lane's PREREG and FINDINGS for exact scope. The panel
is a timestamped generated snapshot; consult fresh claims in [issue #7](https://github.com/SaikiK12/T/issues/7)
for active writers. Dated proposals, audits and source notes below retain history, not a second current queue.

**Start here**
- [`PANEL.md`](docs/PANEL.md): live status.
- [`DIRECTION.md`](docs/DIRECTION.md): the plan the owner approved.
- [`MAP.md`](docs/MAP.md): what is known, lane by lane.
- [`EDGE_SCOREBOARD.md`](docs/EDGE_SCOREBOARD.md): the evidence for each edge.

**Rules and process**
- [`FOUNDATION.md`](docs/FOUNDATION.md): conventions.
- [`GATES.md`](docs/GATES.md): gates and reserved samples.
- [`ROOM.md`](docs/ROOM.md): the Claude and Codex protocol, issue #7.

**Data**
- [`DATA_SOURCES.md`](docs/DATA_SOURCES.md): every folder, its source and digests; `docs/provenance/` holds the records.
- [`DATA_PROVENANCE_AUDIT.md`](docs/DATA_PROVENANCE_AUDIT.md).
- [`BENCHMARK.md`](docs/BENCHMARK.md): the lab against the best open-source quant projects and free data.

**Methods and research notes**
- Queue and claims: [`METHODS_QUEUE.md`](docs/METHODS_QUEUE.md), [`CLAIMS.md`](docs/CLAIMS.md),
  [`OLD_SESSION_EDGES.md`](docs/OLD_SESSION_EDGES.md).
- Sources and literature: [`SOURCES.md`](docs/SOURCES.md),
  [`QUANTPEDIA_RESEARCH_REVIEW.md`](docs/QUANTPEDIA_RESEARCH_REVIEW.md),
  [`CRYPTO_CROSS_SECTION_EVIDENCE.md`](docs/CRYPTO_CROSS_SECTION_EVIDENCE.md), [`CONCEPTS.md`](docs/CONCEPTS.md).
- Dated proposals and coverage reviews: [`NEXT_SEARCH_SPACE.md`](docs/NEXT_SEARCH_SPACE.md),
  [`RESEARCH_FRONTIER.md`](docs/RESEARCH_FRONTIER.md),
  [`RESEARCH_COVERAGE_LEDGER.md`](docs/RESEARCH_COVERAGE_LEDGER.md),
  [`RESEARCH_HANDOFF.md`](docs/RESEARCH_HANDOFF.md).
- Topic briefs: [`ALTCOIN_LEADS.md`](docs/ALTCOIN_LEADS.md), [`FOREX_AND_INDICES.md`](docs/FOREX_AND_INDICES.md),
  [`MARKET_DIRECTION_AND_REGIME.md`](docs/MARKET_DIRECTION_AND_REGIME.md),
  [`VOLATILITY_AND_TAIL_RISK_FORECASTS.md`](docs/VOLATILITY_AND_TAIL_RISK_FORECASTS.md),
  [`QUARTER_HOUR_AGGRESSOR_FLOW_PROPOSAL.md`](docs/QUARTER_HOUR_AGGRESSOR_FLOW_PROPOSAL.md),
  [`REELS_TRANSCRIPT.md`](docs/REELS_TRANSCRIPT.md), [`VIDEO_DIG.md`](docs/VIDEO_DIG.md) (the owner's TikToks and
  practitioner podcasts: what to trade, news recording, the cross-family book),
  [`COMMENT_DIG.md`](docs/COMMENT_DIG.md) (Hacker News, Reddit, Stack Exchange, YouTube and TikTok comments and podcast
  transcripts: ideas M288+ and what the lab already tested),
  [`AUCTION_AND_FLOW.md`](docs/AUCTION_AND_FLOW.md) (the owner's 21 terms: auction market theory, order flow, dealer
  gamma/delta/vanna/charm exposure; critique, our own terminal, the AI council, questions for the owner),
  [`QUANTDATA.md`](docs/QUANTDATA.md) (QuantData's options-flow metrics mapped to crypto data we hold; VPIN tested,
  R291 NULL), [`TRADER_TALKS.md`](docs/TRADER_TALKS.md) (received practitioner talks and their extraction scope).

**Trading, execution and capital**
- The owner's venue: [`MEXC_EDGES.md`](docs/MEXC_EDGES.md). Other venues and their fees (Lighter's zero-fee API,
  Paradex, Hyperliquid) and the prop trader's three edges: [`VENUE_STRUCTURE.md`](docs/VENUE_STRUCTURE.md).
- Execution and carry: [`PERP_EXECUTION_AND_RISK.md`](docs/PERP_EXECUTION_AND_RISK.md),
  [`PERP_CARRY_ACCOUNTING.md`](docs/PERP_CARRY_ACCOUNTING.md), [`OPERATIONAL_API_RISK.md`](docs/OPERATIONAL_API_RISK.md).
- Paper and sizing: [`PAPER_REFINEMENT.md`](docs/PAPER_REFINEMENT.md), [`SIZING_EVIDENCE.md`](docs/SIZING_EVIDENCE.md).
- Capital: [`CAPITAL_GATE_REVIEW.md`](docs/CAPITAL_GATE_REVIEW.md), [`PROP_FIRMS.md`](docs/PROP_FIRMS.md).

**Audits and reviews**
- Program-level: [`AUDIT.md`](docs/AUDIT.md), [`CRITIQUE.md`](docs/CRITIQUE.md),
  [`SELECTION_AND_TRIAL_ACCOUNTING_AUDIT.md`](docs/SELECTION_AND_TRIAL_ACCOUNTING_AUDIT.md),
  [`CONFIDENCE_REVIEW.md`](docs/CONFIDENCE_REVIEW.md),
  [`CONFIDENCE_AND_SIZING_AUDIT.md`](docs/CONFIDENCE_AND_SIZING_AUDIT.md).
- Data and code integrity: [`IMPLEMENTATION_INTEGRITY_REVIEW.md`](docs/IMPLEMENTATION_INTEGRITY_REVIEW.md),
  [`FEATURE_VINTAGE_INTEGRITY.md`](docs/FEATURE_VINTAGE_INTEGRITY.md),
  [`TARGET_INTEGRITY_FIX.md`](docs/TARGET_INTEGRITY_FIX.md),
  [`CONTRACT_LIFECYCLE_INTEGRITY.md`](docs/CONTRACT_LIFECYCLE_INTEGRITY.md),
  [`POSITIONING_AND_ORDERFLOW_VALIDITY.md`](docs/POSITIONING_AND_ORDERFLOW_VALIDITY.md).
- Forecast evaluation: [`FORECAST_EVALUATION_PLAYBOOK.md`](docs/FORECAST_EVALUATION_PLAYBOOK.md),
  [`ADAPTIVE_SELECTION_AND_DRIFT.md`](docs/ADAPTIVE_SELECTION_AND_DRIFT.md).

Docs stay at their paths because frozen PREREGs link to them. Topic overlap alone does not establish duplication:
source receipts, proposed mechanics, a frozen test and its verdict answer different questions. Add new facts to the
existing intake, lane or process document before creating another review. Generated folder catalogs come from
`scripts/catalog.py`; edit their registry/docstring sources, not the generated text.

## Use

`python -m lab` is the common entry point. `lab/operations.py` supplies the task graph, lane descriptions and
paper projections to the orchestrator, panel and dashboard. Methods remain in the canonical CSV; runtime descriptors
are not another research queue. Per-run receipts live outside the checkout. A successful process, complete declared
checks and admission through the research gates are separate states.

```sh
python -m pip install uv==0.12.23
uv venv --python 3.12.14 .venv
uv pip sync --require-hashes --python .venv/bin/python requirements-test.lock
.venv/bin/python -m lab                               # commands; does not start work
.venv/bin/python -m lab find funding                  # existing metadata index
.venv/bin/python -m lab integrity                     # register/spec + canonical intake
.venv/bin/python -m lab check --suite fast            # feedback; explicit simulations deferred
.venv/bin/python -m lab check --suite full            # required commit gate, simulations retained
.venv/bin/python -m lab forward                      # offline plan; no collector/writer starts
.venv/bin/python -m lab engine                       # offline locked-build plan
```

The lock captures the tested Python 3.12 stack, including scikit-learn and the optional browser-test dependency.
System Chromium is required for the browser fixture; unavailable archive/parity/browser checks report explicit skips.
Historical lanes retain their recorded environments; this lock does not reproduce every old study automatically.
Keep native thread pools bounded during checks (`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1`).

Explicit operator actions, when ready to run (none installs a scheduler):

```sh
.venv/bin/python -m lab engine --execute --state-dir /absolute/external/build-runs --run-id unique_build
cargo test --locked --release --manifest-path engine/Cargo.toml
.venv/bin/python -m lab forward --execute --state-dir /absolute/external/paper-runs --run-id unique_tick
.venv/bin/python -m lab panel --jobs-state-dir /absolute/external/paper-runs
.venv/bin/python -m lab export --jobs-state-dir /absolute/external/paper-runs
```

`forward_all.sh` is a compatibility delegate to that same orchestrator. The optional `forward_loop.sh` requires
`FORWARD_STATE_DIR` outside the checkout, owns a singleton lock and reports success/failure from the run. Starting it
is an explicit deployment action; merging a patch does not establish that a host changed scheduler. All wrappers share
`.forward.lock` with old ticks; do not kill an existing owner process. A blocked partial signal hour requires inspection,
not automatic history repair. Funding checks expose partial venue snapshots; unimplemented checks remain UNVERIFIED.

Dashboard exports are immutable `dashboard/data/generations/<generation>/<dataset>.json`; `manifest.json` is the
atomic latest pointer. `lab export --changed` returns `{generation, files}`. Upload those exact files, then acknowledge
with `lab export --record dataset=/_blob/returned-id --generation <that-generation>`. `lab export --docs` rebuilds the
store documents from acknowledged receipts. A new export cannot silently change the hash/clock of an earlier upload.
Old upload files lack this proof and require a new explicit acknowledgement; they are never guessed into validity.
Exports bind uploaded bytes, not an atomic snapshot of every upstream collector or successful remote delivery.

The bounded engineering benchmark uses invented arrays only:
`python -m lab benchmark --report /absolute/external/new-benchmark.json`. It is not a market experiment.
The original `python -m unittest discover -s tests -t .` remains the same full gate. No framework migration is required.

New lane: copy `templates/lane/`, write the PREREG, claim its id on issue #7, freeze it with `lab.prereg.freeze()`,
then run.
