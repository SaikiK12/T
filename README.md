# T

A pre-registered strategy-discovery lab for crypto perpetual futures. The goal is the best net PnL the owner can trade
(MEXC perps first), proven on data the search never saw and handed over through the gates in
[`docs/GATES.md`](docs/GATES.md). Nothing counts as an edge until it survives pre-registration, its family's reality
check, an unread sample or forward paper days, and costs at 1x, 2x and 3x.

## At a glance (2026-10-28)

**Money:** no strategy has passed paper trading, and no real money has moved. No paper lane has a strict on-time day
that counts toward a decision yet ([PANEL](docs/PANEL.md)). The owner now wants short-hold futures trades only.

**Alive.** Every lead below is gate 0 on data the lab has seen, or still in forward paper:

| Lead | Best evidence so far | Now |
|---|---|---|
| **Settlement scalp on Lighter:** short Lighter at the last trade before a deep negative Binance settlement, cover a minute after | +23.4 bp a hop at 1x (t 4.34), +15.8 at 3x, on 134 hops held out from R356 but not blind: R362 had read their Binance seconds. About one event every two days ([R363](experiments/settlelit_v1/FINDINGS.md)) | R364 paper on Lighter's live book, from 2026-10-28 20:00 UTC ([PREREG](experiments/settlelit_fwd/PREREG.md)) |
| **Settlement hop:** hold the side that receives a deep funding lump on Binance, hedged on Lighter, from T − 1 h to T + 5 min | +50.5 bp a hop at 1x, t 4.08, about one hop a week; most of the gain over R354's T + 1 h exit is a funding hour not paid ([R354](experiments/settlehop_pred_v1/FINDINGS.md), [R356](experiments/settlehop_exit_v1/FINDINGS.md)) | R355 paper on MEXC + Lighter |
| **Funding carry** (short perp, long spot) | The only holdout pass, at 1x only, about 1%/yr ([R191](experiments/carry_holdout/)) | R220 paper |
| **Flow books A, B, X2** (72 h order-flow shorts) | Strong in-sample; holdout not confirmed ([R198](experiments/flow72_holdout/), [R216](experiments/venue_gap_v1/)) | R200, R215, R218, R221 paper, all negative so far |
| **Event lanes** (unlocks, delisting notices, Monitoring Tag, announcements) | The unlock short replicated at gate 0 ([R265](experiments/unlocks_v1/FINDINGS.md)). The three notice studies were NULL at gate 0 (R267, R269, R271); their forward lanes test the best variants as hypotheses | R266, R268, R270, R272 paper |
| **Sub-second cross-venue family** (Binance USDC against USDT and Bybit books, Retail Price Improvement flow, Bybit liquidations) | No result yet, recording only. About 250 ms of round trip from this container sets the floor, so only slower rules are executable | R367 screen runs once on or after 2026-11-02 ([PREREG](experiments/hftlead_v1/PREREG.md)); M430-M435 wait for the raw tape from 2026-10-29 13:00 UTC ([intake note](research/intake/hft_corpus_20261028.md)) |

**Closed** (NULL, kept on record):
- Lighter taker scalps toward Binance's quote (R348).
- Minute flow fades on liquid perps: they decayed to about 0 since 2025-07 (R349, R351).
- The level model's automated route (R337).
- Unhedged settlement capture (R223), and the hop on the last settled rate (R353).
- A Binance taker against the receiving side after a deep settlement: the price moves about 85 bp within 15 s of T,
  before Binance's stated funding deviation lets a position open safely (R362).
- 5,472 chart rules (R263), the cross-sectional battery (R238) and intraday relative strength (R300).
- The full list is [`docs/EDGE_SCOREBOARD.md`](docs/EDGE_SCOREBOARD.md).

**Working here:**
1. Read [`AGENTS.md`](AGENTS.md), then the fresh claims in [issue #7](https://github.com/SaikiK12/T/issues/7).
2. Read the "Now" section of [`docs/DIRECTION.md`](docs/DIRECTION.md) for the plan.
3. Start a lane from `templates/lane/`, claim its id on #7, freeze its PREREG, run it, write FINDINGS and append the
   registry row.
4. Before a commit, run `python -m lab integrity`, `python -m lab check --suite fast` and the full
   `python -m unittest discover -s tests -t .`.

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
| `templates/` | `lane/` is the starting point for a new lane; `research_card.md` is the card for a source that was read |

## Docs

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
- Capital-level carry/spot comparison: [R309 findings](experiments/capital_mix_v1/FINDINGS.md), with fixed
  initial allocations, parent/passive/cash controls and all three cost tiers. Historical model evidence;
  `lab.capital` combines accounts with explicit capital denominators.

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

R266 now has an external journal guard around its unchanged writer: unique ticket/skip/score identities, frozen entry/exit cutoffs, retained snapshot hashes and score arithmetic. Postflight also requires matching native status/book outputs and a status no older than15 minutes. Missing snapshots or damaged appends block execution; no historical repair occurs. Passing these structural checks does not certify the raw price/funding feed, original calendar availability or statistical gates.

`lab status` reads the same receipt adapter as the Control Room. Pass the existing external run directory; it lists process state, declared data checks, stale receipts and required/optional task dependencies (`--json`). `--strict` exits nonzero for missing, failed, stale or unverified observations; it never authorizes trading or starts a collector. It also shows the canonical queue counts and engine build binding.

```sh
python -m pip install uv==0.12.23
uv venv --python 3.12.14 .venv
uv pip sync --require-hashes --python .venv/bin/python requirements-test.lock
.venv/bin/python -m lab                               # commands; does not start work
.venv/bin/python -m lab status                        # read-only; missing receipts stay unknown
.venv/bin/python -m lab status --state-dir /absolute/external/paper-runs --json
.venv/bin/python -m lab find funding                  # existing metadata index
.venv/bin/python -m lab find --trace M018             # method → registered specs/code/data identities
.venv/bin/python -m lab integrity                     # register/spec + canonical intake
.venv/bin/python -m lab check --suite fast            # feedback; explicit simulations deferred
.venv/bin/python -m lab check --suite full            # required commit gate, simulations retained
.venv/bin/python -m lab forward                      # offline plan; no collector/writer starts
.venv/bin/python -m lab engine                       # offline locked-build plan
.venv/bin/python -m lab account --out /absolute/new-output  # frozen offline account/cost integration
.venv/bin/python -m lab account --lifecycle --out /absolute/new-paired-output  # partial fills and residual exposure
.venv/bin/python -m lab account --controls --restore-input --out /absolute/new-controls-output # R320; one small pinned portable input
```

The Control Room's **Compte simulé** tab separates model amounts from observed money, currencies,
missing inputs and legacy reports. [R320](experiments/owner_acceptance_v1/PREREG.md) binds the exact
owner100 requirements and their bounded acceptance evidence. That coverage is not another methods
queue or a claim that100 improvements or profitable strategies are complete. Shared views never start
a collector or an order; the reproduction command verifies frozen calculation/input identities first.

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

The [integrated account evidence](experiments/paper_account_v1/FINDINGS.md) joins positions, price PnL,
fees, funding, liquidation marks and missing-input controls in one offline report (`account.html` and
`account.txt`). Its account figures are invented engine validation; its size costs use already-seen
quotes. No live collection, prospective scoring or actual account fee/permission is implied.
`scripts/check_paper_account.py /absolute/new-output/results.json` checks the reported arithmetic.
The same command's [paired lifecycle protocol](experiments/paired_execution_v1/FINDINGS.md) retains
partial fills, cancel/reject totals, residual quantities and interrupted receipt/cash joins. Its
one-leg unwind and funding break-even figures are conditional costs, not observed profit.
`scripts/check_paired_account.py /absolute/new-paired-output/results.json` checks that integration.

The same entry point's [spot/perpetual component](experiments/spot_perp_inputs_v1/FINDINGS.md),
`python -m lab account --spot-perp --out /fresh/output`, spends physical spot principal,
tracks base/quote fees and joins both funded wallets once. It replays sealed public wire
receipts and constructed accounting controls; actual executable return remains unknown.
`scripts/check_spot_perp_account.py /fresh/output/results.json` checks literal cash/cost arithmetic.
For [source-aware spot/perpetual quote costs](experiments/spot_perp_costs_v2/FINDINGS.md),
use `python -m lab account --spot-costs-v2 --out /fresh/output` and
`python scripts/check_spot_costs_v2.py /fresh/output/results.json`. The original
R325 input failures are retained; corrected costs use the same sealed inputs.
Public-rate/depth assumptions remain conditional and funding keeps total PnL unknown.

The [dated inverse-futures component](experiments/dated_carry_v2/FINDINGS.md) uses
the same account entry point: `python -m lab account --dated-v2 --out /fresh/output`,
then `python scripts/check_dated_carry_v2.py /fresh/output/results.json`. It separates
USD face, coin collateral, daily realization and delivery, counting purchased
coins once. Its small BTC/ETH quote-based margins assume zero routing cost and
hypothetical terminal conversion; actual expected net return remains unknown.
The original R327 driver failure and all sealed inputs are preserved.

The [conditional close-level probability study](experiments/level_probability_v1/FINDINGS.md)
shares that entry point: `python -m lab account --levels --out /fresh/output`, then
`python scripts/audit_level_probability.py /fresh/output`. Its training-only model
was committed before later periods. It distinguishes probability from payoff,
uses one capital account across coins, and retains inactivity, costs and gaps.
This exact model found no probability improvement or net edge. The first audit's
signed-notional guard failure is preserved; the named audit-only correction does
not change financial results. Reproduction requires the eight pinned held inputs.

The bounded engineering benchmark uses invented arrays only:
`python -m lab benchmark --report /absolute/external/new-benchmark.json`. It is not a market experiment.
The original `python -m unittest discover -s tests -t .` remains the same full gate. No framework migration is required.

New lane: copy `templates/lane/`, write the PREREG, claim its id on issue #7, freeze it with `lab.prereg.freeze()`,
then run.
