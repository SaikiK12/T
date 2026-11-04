# Operator guide

[Repository home](../../README.md) · [Guide de lecture en français](START_HERE.fr.md)

Run the commands below from the repository root. Reading the repository or its
status does not require starting a collector. For machine restoration, data
classes and scheduled-check history, see [HANDOVER](../HANDOVER.md).

## Setup, inspection and explicit execution

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
missing inputs and legacy reports. [R320](../../experiments/owner_acceptance_v1/PREREG.md) binds the exact
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

The [integrated account evidence](../../experiments/paper_account_v1/FINDINGS.md) joins positions, price PnL,
fees, funding, liquidation marks and missing-input controls in one offline report (`account.html` and
`account.txt`). Its account figures are invented engine validation; its size costs use already-seen
quotes. No live collection, prospective scoring or actual account fee/permission is implied.
`scripts/check_paper_account.py /absolute/new-output/results.json` checks the reported arithmetic.
The same command's [paired lifecycle protocol](../../experiments/paired_execution_v1/FINDINGS.md) retains
partial fills, cancel/reject totals, residual quantities and interrupted receipt/cash joins. Its
one-leg unwind and funding break-even figures are conditional costs, not observed profit.
`scripts/check_paired_account.py /absolute/new-paired-output/results.json` checks that integration.

The same entry point's [spot/perpetual component](../../experiments/spot_perp_inputs_v1/FINDINGS.md),
`python -m lab account --spot-perp --out /fresh/output`, spends physical spot principal,
tracks base/quote fees and joins both funded wallets once. It replays sealed public wire
receipts and constructed accounting controls; actual executable return remains unknown.
`scripts/check_spot_perp_account.py /fresh/output/results.json` checks literal cash/cost arithmetic.
For [source-aware spot/perpetual quote costs](../../experiments/spot_perp_costs_v2/FINDINGS.md),
use `python -m lab account --spot-costs-v2 --out /fresh/output` and
`python scripts/check_spot_costs_v2.py /fresh/output/results.json`. The original
R325 input failures are retained; corrected costs use the same sealed inputs.
Public-rate/depth assumptions remain conditional and funding keeps total PnL unknown.

The [dated inverse-futures component](../../experiments/dated_carry_v2/FINDINGS.md) uses
the same account entry point: `python -m lab account --dated-v2 --out /fresh/output`,
then `python scripts/check_dated_carry_v2.py /fresh/output/results.json`. It separates
USD face, coin collateral, daily realization and delivery, counting purchased
coins once. Its small BTC/ETH quote-based margins assume zero routing cost and
hypothetical terminal conversion; actual expected net return remains unknown.
The original R327 driver failure and all sealed inputs are preserved.

The [conditional close-level probability study](../../experiments/level_probability_v1/FINDINGS.md)
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

## Maintain catalog and provenance views

Folder catalogs use one commit-ready snapshot of the Git index. Stage intended
source, protocol and registry changes before regenerating them; untracked files,
unstaged edits, intent-to-add placeholders and source symlinks are excluded.

```sh
.venv/bin/python scripts/catalog.py
.venv/bin/python scripts/catalog.py --check
```

The check exits1 for stale/missing views and2 for invalid inputs/outputs. It does
not rewrite catalogs or the real index/object cache. Publication validates all
three views first and replaces changed files atomically; output symlinks are
rejected. Unchanged views retain their timestamps. This checks metadata
consistency, not observation freshness, on-time collection or a research verdict.
CI runs the same catalog check, so intended sources and regenerated views must
be included together in a publication.

`lab find --trace R389` reports supported frozen declarations from inputs JSON,
training manifests and `inputs` fences (both historical path/hash orderings).
Conflicts and unsupported/missing declarations remain explicit. Tracked-name
membership does not prove target availability or matching bytes; declared data,
results and journals are not opened or independently verified by this command.

The [funding-notional audit](../../lab/funding_notional.py) compares rate-sum and
fixed-quantity cash conventions with supplied eligibility, coverage and values.
Its [demo](../../scripts/audit_funding_notional.py) uses invented inputs only;
missing evidence remains unscored. It does not retrofit any frozen lane or prove
a historical gain. A market reanalysis needs a new frozen design.

## Integrated paper session and recovery tools

New paper consumers can use [PaperSession](../../lab/paper_session.py) to connect
the native cash account, persistent risk controls and `PaperSolvencyGuard`.
An admission persists an intent, never a fill. Pending/partial intents block
new entries across restart until explicit receipt identities join them. Old
receipts cannot discharge later intents, even with a refreshed delivery clock.
Observed receipts remain recordable after a risk stop. Close planning uses the
held base quantity and a supplied fee on exit notional; it does not execute.

```sh
python scripts/demo_paper_session.py --demo
```

That command uses invented inputs and temporary journals only. Source/forecast
authentication, live fills, cancellation reconciliation, scale/reversal entries
and exchange liquidation mechanics remain outside this narrow bridge. Historical
frozen runners have not been retrofitted or credited with new paper evidence.

For an oversized stable file classified `RECORDED`, the new segmented tool
supplements `handover.py`'s ordinary archive. It never uploads, deletes an original,
or replaces a destination. Replace the example source with an actual classified
file; archive and repository roots must be separate.

```sh
python scripts/recording_segments.py pack --root /absolute/repository \
  --source data/rawtape/selected-file.bin --out /absolute/external/new-bundle \
  --chunk-mb 50 --budget-mb 250
python scripts/recording_segments.py verify --archive /absolute/external/new-bundle \
  --expected-manifest-sha256 MANIFEST_SHA256 --budget-mb 250
python scripts/recording_segments.py restore --archive /absolute/external/new-bundle \
  --root /absolute/restore-repository --expected-manifest-sha256 MANIFEST_SHA256 --budget-mb 250
```

Keep the pack receipt's real manifest SHA256 outside the bundle. The destination
repository must already classify that path in `registry/data_manifest.csv`.
Budgets above are local bundle examples, not remote archive-capacity increases.
The tool refuses licensed/unclassified inputs, public news exclusions, unstable
sources, path/symlink ambiguity, corrupted segments and existing destinations.
Linux atomic directory publication is required. A synthetic round trip proves
recovery code, not the completeness of a capture host's actual backups.

The [standalone dashboard procedure](../../dashboard/README.md#independent-static-bundle)
builds a verified static bundle from an existing explicit export generation.
It does not scan research inputs, start a scheduler or publish a site.
The [current recovery checklist](../handover/SCHEDULED_CHECKS.md) separates
active instructions from historical reminders and completed reserved reads.

## Related integration records

The [mechanism/data/equation map](../../research/discovery/README.md#global-mechanism-data-equation-map)
links existing families to their minimum observations and falsifiers. Source
capabilities distinguish documentation from qualified or acquired inputs.
`lab.input_contracts` checks caller-declared metadata consistency only; its
passing result never authenticates timestamps, provenance or trading eligibility.

```sh
python -m scripts.qualify_metric_archives
```

This default command makes a dry plan with no requests. R403's explicit execution
is one-shot under its frozen published protocol. Its guard and accumulated
journal must not be removed or reset. Two source ZIPs do not reconstruct the
missing full metrics panel or establish when their observations were available.

Current carry source qualification is prospective and one-shot. The R401
inventory attempt is complete and must not be repeated. Its new targeted
successor plans without network by default:

```sh
python -m scripts.qualify_carry_costs_targeted
```

Execution requires its exact frozen and published protocol, an unused attempt
marker and an explicit new output path. The journal includes R401's2MiB inside
the same5MiB allowance. It never renews that allowance. Snapshot arithmetic
matches contract lots but establishes no account fee, future exit cost, actual
fill or pair PnL. See the native R402 protocol and findings in the experiment
catalog; a consumed attempt is not a recurring operational task.

The [M090/M322 implementation handoff](../../research/PROSPECTIVE_LEADS_DRAFT_20261029.md) describes
the prototypes and remaining admission requirements. The
[R374 signed-content capture](../../experiments/m090_content_v2/FINDINGS.md) adds a tested public adapter and replayable signed archive; UTC and forecast scoring remain disabled.
The [R372 ORB implementation and pilot](../../experiments/orb_index_v1/FINDINGS.md) contains the runnable four-account engine, frozen input contract, independently checked result and exact execution limits.
