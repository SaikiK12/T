# T

A pre-registered strategy-discovery lab for crypto perpetual futures. The goal is the best net PnL the owner can trade
(MEXC perps first), proven on data the search never saw and handed over through the gates in
[`docs/GATES.md`](docs/GATES.md). Nothing counts as an edge until it survives pre-registration, its family's reality
check, an unread sample or forward paper days, and costs at 1x, 2x and 3x.

[Guide de lecture en français](docs/guides/START_HERE.fr.md) · [Operator guide](docs/guides/OPERATIONS.md) · [Complete document index](#docs)

## Start here

| I want to… | Open |
|---|---|
| Understand the project and the identifiers | [Human reading guide](docs/guides/START_HERE.fr.md) |
| See priorities and existing ideas | [Working direction](docs/DIRECTION.md), then the [live methods queue](registry/methods.csv) |
| Read an experiment's actual scope and result | [Experiment catalog](experiments/README.md), then its PREREG and FINDINGS |
| Find a source or a research design | [Research folder guide](research/README.md) |
| Set up, inspect or run the software | [Operator guide](docs/guides/OPERATIONS.md) |
| Make a change | [AGENTS.md](AGENTS.md), then fresh writer claims in [issue #7](https://github.com/SaikiK12/T/issues/7) |

## Current status

The [panel](docs/PANEL.md) is a generated snapshot: check its build timestamp.
[Issue #7](https://github.com/SaikiK12/T/issues/7) holds fresh writer claims and
operational handoffs; [room #71](https://github.com/SaikiK12/T/issues/71) holds
bounded Codex/subagent triage. The [live methods queue](registry/methods.csv),
[round registry](registry/rounds.csv) and each lane's native PREREG/FINDINGS
remain the authorities for ideas, registered work and exact tested scope.

Process success, complete on-time data and admission through the
[research gates](docs/GATES.md) are separate states. This page does not copy
changing returns, observation counts or process-health claims.

## Where things are

| Folder | Purpose and entry point |
|---|---|
| [docs/](docs/README.md) | Reading guides, operating rules, topic notes, provenance and dated reviews |
| [registry/](registry/README.md) | The canonical method queue, rounds, aliases and data manifest |
| [experiments/](experiments/README.md) | Frozen protocols, native findings and lane evidence |
| [research/](research/README.md) | Received sources, research designs, grouped reviews and bounded prototypes |
| [reports/](reports/README.md) | Preserved narrative reviews and owner briefings |
| [research_notes/](research_notes/README.md) | Supporting evidence for narrative reviews |
| [lab/](lab/README.md) | Python research and paper-account library |
| [scripts/](scripts/README.md) | Acquisition, recorders, runners, checks and navigation commands |
| [engine/](engine/README.md) | The locked Rust qx execution engine |
| [dashboard/](dashboard/README.md) | Control Room view and its data-publication contract |
| [templates/](templates/README.md) | Starting a lane or a source card |
| [tests/](tests/README.md) | Validation commands and test conventions |
| data/ | Local market inputs and recordings; bulk data is excluded from Git |

## Use

Reading documents on GitHub needs no environment setup. After following the
[operator setup](docs/guides/OPERATIONS.md#setup-inspection-and-explicit-execution),
these commands inspect existing metadata without starting a research run:

```sh
.venv/bin/python -m lab find funding
.venv/bin/python -m lab find --trace M290
.venv/bin/python -m lab find R400
.venv/bin/python -m lab status --state-dir /absolute/external/paper-runs --strict
.venv/bin/python -m lab integrity
```

The operator guide holds environment installation, complete test commands,
explicit execution, paper-account examples and dashboard-publication details.
Read [AGENTS.md](AGENTS.md) before writing; run the relevant checks and the full
suite before a code commit. Generated folder catalogs come from
`scripts/catalog.py`; stage intended registry/source changes before regenerating.
`python scripts/catalog.py --check` reports stale views without rewriting them.

## Docs

The maintained complete topic index is below. Folder READMEs explain where to
look; they do not maintain separate method queues or changing result counts.

<details>
<summary>Open the full document index: rules, data, methods, execution and reviews</summary>

Read by task instead of loading this entire list. The authority for current method status is
[`registry/methods.csv`](registry/methods.csv), and for recorded round status/trials/verdicts it is
[`registry/rounds.csv`](registry/rounds.csv). Read the linked lane's PREREG and FINDINGS for exact scope. The panel
is a timestamped generated snapshot; consult fresh claims in [issue #7](https://github.com/SaikiK12/T/issues/7)
for active writers. Dated proposals, audits and source notes below retain history, not a second current queue.

**Start here**
- [`HANDOVER.md`](docs/HANDOVER.md): how to get everything back without Claude: what is in git, what is not, the data
  manifest and archive commands, the keys (names only), and the scheduled checks ([`handover/`](docs/handover/SCHEDULED_CHECKS.md)).
- [`PANEL.md`](docs/PANEL.md): live status.
- [`DIRECTION.md`](docs/DIRECTION.md): the plan the owner approved.
- [`MAP.md`](docs/MAP.md): what is known, lane by lane.
- [`EDGE_SCOREBOARD.md`](docs/EDGE_SCOREBOARD.md): the evidence for each edge.
- [`EDGE_MAP.md`](docs/EDGE_MAP.md): every method and round placed in one of 32 edge families, each with who pays,
  its net P&L equation, the fake-edge checks, the gaps and the next refinement (generated by `scripts/edge_map.py`).

**Rules and process**
- [`FOUNDATION.md`](docs/FOUNDATION.md): conventions.
- [`GATES.md`](docs/GATES.md): gates and reserved samples.
- [`ROOM.md`](docs/ROOM.md): the Claude and Codex protocol, issue #7.

**Data**
- [`DATA_SOURCES.md`](docs/DATA_SOURCES.md): every folder, its source and digests; `docs/provenance/` holds the records.
- [`DATA_PROVENANCE_AUDIT.md`](docs/DATA_PROVENANCE_AUDIT.md).
- [`BENCHMARK.md`](docs/BENCHMARK.md): the lab against the best open-source quant projects and free data.
- [`FREE_AI_AGENT.md`](docs/FREE_AI_AGENT.md): running an AI coding agent from a phone through GitHub Actions.

**Methods and research notes**

- [Original equation discovery workbench](research/discovery/README.md): fourteen observation/equation lenses linked to the canonical edge map, source capabilities, declaration checks, bounded grammar and the protocol for a future market test. The canonical methods queue remains authoritative.
- [R400 path-response experiment](experiments/path_response_v1/FINDINGS.md): frozen raw-event equation search and its terminal source-coverage refusal; [timestamp-only diagnosis](scripts/audit_path_timing.py) reads no price or size columns.
- [Leading-strategy hybrid review](research/HYBRID_REVIEW_20261029.md): source reviews and the latest deep-batch decisions, ranked work paths, prior nulls, comparison controls and current data blockers.
- Queue and claims: [`METHODS_QUEUE.md`](docs/METHODS_QUEUE.md), [`CLAIMS.md`](docs/CLAIMS.md),
  [`OLD_SESSION_EDGES.md`](docs/OLD_SESSION_EDGES.md).
- Sources and literature: [`SOURCES.md`](docs/SOURCES.md),
  [`PRIMARY_EQUATIONS.md`](docs/PRIMARY_EQUATIONS.md) (bounded primary reading, exact equations and execution prerequisites),
  [`QUANTPEDIA_RESEARCH_REVIEW.md`](docs/QUANTPEDIA_RESEARCH_REVIEW.md),
  [HFT corpus intake note](research/intake/hft_corpus_20261028.md) (46 indexed sources, exact read scope),
  [`CRYPTO_CROSS_SECTION_EVIDENCE.md`](docs/CRYPTO_CROSS_SECTION_EVIDENCE.md), [`CONCEPTS.md`](docs/CONCEPTS.md).
- Dated proposals and coverage reviews: [`NEXT_SEARCH_SPACE.md`](docs/NEXT_SEARCH_SPACE.md),
  [`RESEARCH_FRONTIER.md`](docs/RESEARCH_FRONTIER.md),
  [`RESEARCH_COVERAGE_LEDGER.md`](docs/RESEARCH_COVERAGE_LEDGER.md),
  [`RESEARCH_HANDOFF.md`](docs/RESEARCH_HANDOFF.md).
- Owner digest of the best leads and what is left to read: [`LEADS.md`](docs/LEADS.md) (dated 2026-11-02).
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
- New paper consumers can combine the frozen risk engine with the external
  [`PaperSolvencyGuard`](lab/paper_solvency.py); the read-only
  [`snapshot capacity check`](scripts/check_paper_solvency.py) never admits entries by itself.
- For loss at the proposed size, [`PaperSession`](lab/paper_session.py) accepts a
  persistent [`EntryLossPolicy`](lab/paper_entry_risk.py), exact-size price/fee/funding
  scenarios and native loss/drawdown headroom. See the [scope and formulas](docs/PAPER_REFINEMENT.md#7-loss-at-the-proposed-size-engineering-2026-11-05)
  and [invented demo](scripts/demo_paper_entry_risk.py). These are paper vetoes,
  not profitable-strategy or real-order approval.
- Capital: [`CAPITAL_GATE_REVIEW.md`](docs/CAPITAL_GATE_REVIEW.md), [`PROP_FIRMS.md`](docs/PROP_FIRMS.md).
- Capital-level carry/spot comparison: [R309 findings](experiments/capital_mix_v1/FINDINGS.md), with fixed
  initial allocations, parent/passive/cash controls and all three cost tiers. Historical model evidence;
  `lab.capital` combines accounts with explicit capital denominators.
- Inverse carry mechanics: [R407 findings](experiments/locked_carry_mechanics_v1/FINDINGS.md)
  and [`locked_carry`](lab/locked_carry.py) size fixed orders after fees, model
  grid exits and retain unsold coin. Conditional cash bounds require explicit
  exit assumptions; the invented-input audit establishes no market edge.

**Audits and reviews**

- [Repository execution batch, 2026-11-04](docs/reviews/project_execution_20261104.md):
  new paper-session bridge, segmented recovery, independent dashboard bundle,
  funding schema evidence and bounded R401/R402 source qualification; the report
  separates shipped engineering from missing inputs and prospective dates.
- [Funding-notional audit](lab/funding_notional.py) and [invented sign-flip demo](scripts/audit_funding_notional.py):
  [R388's funding approximation](experiments/forcedswitch_v1/FINDINGS.md#engineering-clarification-funding-notional-2026-11-03-no-market-rerun)
  and [R333's fee/weighting clarification](experiments/level_probability_v2/FINDINGS.md#reporting-clarification-2026-11-03-no-new-market-statistic)
  preserve the frozen verdicts while narrowing claims to their actual scope.
- [Event-recorder review](docs/reviews/event_recorders_20261102.md): receipt-time semantics,
  calendar error handling and safe integration around active writers.
- [Room actions, 2026-11-03](docs/reviews/room_actions_20261103.md): external paper-capital veto,
  BLS schedule access/capture and native-findings navigation, coordinated in [issue #71](https://github.com/SaikiK12/T/issues/71).
- [Historical project-direction review](reports/Project%20direction%20from%20quant%20evidence.md)
  and [repository hygiene review](reports/Repo%20hygiene%20plan.md): preserved 2026-10-20/26 snapshots,
  with original-revision links; their numerical status and recommendations require current evidence.
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

</details>
