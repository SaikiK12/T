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
- What to test next: [`NEXT_SEARCH_SPACE.md`](docs/NEXT_SEARCH_SPACE.md),
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
  transcripts: ideas M288+ and what the lab already tested).

**Trading, execution and capital**
- The owner's venue: [`MEXC_EDGES.md`](docs/MEXC_EDGES.md).
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

Docs stay at their paths because frozen PREREGs link to them.

## Use

```
python3 -m venv .venv && .venv/bin/pip install numpy pandas numba scipy pyarrow websockets
.venv/bin/python -m unittest discover -s tests -t .              # before every commit to lab/ or scripts/
cargo test --release --manifest-path engine/Cargo.toml           # before every commit to engine/
.venv/bin/python -m lab.data build klines 1h                     # Binance archive (also fundingRate, premiumIndexKlines)
.venv/bin/python scripts/qx_run.py experiments/<lane> --register # run a frozen qx lane and append its registry row
sh scripts/forward_loop.sh                                       # hourly forward paper ticks and recorders
.venv/bin/python scripts/dashboard_data.py                       # export the Control Room datasets
```

New lane: copy `templates/lane/`, write the PREREG, claim its id on issue #7, freeze it with `lab.prereg.freeze()`,
then run.
