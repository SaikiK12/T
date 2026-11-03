# R400 — path_response_v1

Status at the 2026-11-03 freeze: **REGISTERED / PENDING**. No market equation,
forecast statistic or PnL has been computed in this environment. The local
[prepare receipt](results/local_prepare_preflight_20261103.json) reports BLOCKED
because the four raw files are absent; this is not a NULL market result and does
not consume the first market look.

The [PREREG](PREREG.md) and [source identities](training_manifest.json) are frozen.
Parent mechanism scopes are M430/M433. The raw grammar has 1,476 engineering
attempts, 623 retained forms and 564 candidate forms using area/refill; the
registry charges the full planned 1,478, including baseline/refit. These counts
are not evidence of independent bets or a successful strategy.

## Implemented and exercised

- Arrival-ordered, past-only features with explicit source masks, cross-stream
  tie rejection and same-price replenishment. Classical OFI is in the baseline.
- Train-only normalization and removal of the candidate's baseline projection,
  closed formula selection and one final refit; complete search dispositions.
- Delayed two-sided quote replay at $100, fixed $1,000 reference capital, 5 bp
  per taker leg **as a declared scenario**. Full spread/fee cost stress is 1x,
  2x and 3x, using the same action rule. Actual owner fees/fills/impact unknown.
- Future unavailable capacity/exits remain unresolved; their PnL/intervals are
  unknown and cannot produce a positive verdict. No skipped losing trades or
  silently zero-filled measurements.
- Exclusive preparation/scoring guards, code/data hashes and calendar cutoffs.
  No interim forward scoring, late training or next-best rescue after a failure.

The synthetic contracts recover a planted interaction and independently check
path area, both trade directions, costs, source masks and future-data isolation.
They are engineering tests, not observations about market profitability.

## Data/operator handoff

Claude confirmed in [room #7](https://github.com/SaikiK12/T/issues/7#issuecomment-6600455035)
that Oct 29 is the only complete raw 13:00-17:00 window, and that the recorder is
currently running (0.72 GB of a 4 GB cap). Later missing windows came from
container outages. No R400 price/return output was requested before the freeze.
Claude agreed to execute the frozen command against his local copy after merge
and commit the small outputs and source-hash receipts.

The exact command, from the merged checkout and before Nov 4 00:00 UTC:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_path_response.py prepare --data data/rawtape
```

Publish `results/model.json`, `model.sha256`, `development_inputs.json`,
`development_samples.csv` and `prepare.started.json`; do not edit frozen inputs.
The four development parquet files must match the manifest exactly. A hash or
QC mismatch needs a reported refusal, not a silent substitution/retry after
outcomes. No raw export is needed for this handoff.

The artifact is trained on 13:00-14:59:30, selected on 15:00:30-17:00, and then
refit on combined development rows. This historical calendar has been used by
other program lanes; it is not fresh confirmation. If no expression exceeds the
fixed selection improvement, the lane stops with NO_NEW_EQUATION and does not
open forward data.

For a prepared nonempty model, retain complete future raw windows Nov 4-10.
After **Nov 11 00:00 UTC**, execute once:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_path_response.py score --data data/rawtape
```

This is a prospectively frozen replay. It does not record strict on-time
predictions or establish private execution. The historical `off` field is int32:
only stable relative timing is used; absolute monotonic/UTC is unqualified.
The full baseline is linear, so superiority to nonlinear parent models is not
claimed. Lane-native significance cannot establish program-wide adaptation
control. Gate admission and real orders remain blocked regardless of result.

## Market results

Pending. Actual market fits: **0 here**; prospective observations: **0**.
Market 1x/2x/3x PnL: **unknown**. No positive-return or novelty claim.

## Prepare run, 2026-11-03 (executed by Claude on the raw-tape host)

- Code: branch head `7573f72` (PR #69 merge); `tests.test_path_response` 23 OK before the run.
- Command, run once: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 nice .venv/bin/python scripts/run_path_response.py
  prepare --data data/rawtape`, 10:24:52-10:25:09 UTC. Log: `results/prepare.log`.
- The frozen inputs and `training_manifest.json` passed: all four 10-29 files matched bytes and SHA256.
- **Result: REFUSED**, exit 2: `label coverage below 99%: 2026-10-29/BTCUSDT`, raised in `load_windows`.
- The first look is consumed. `prepare.started.json` and `development_inputs.json` were written; no
  `development_samples.csv`, `model.json` or `model.sha256` exists.
- Per this lane's protocol, the run was not retried, no file was substituted and the coverage was not diagnosed on
  the market data. Nobody read a price, label value or coverage fraction beyond the refusal line.
- Market fits: 0. Prospective observations: 0. 1x/2x/3x PnL: none, since there is no model. R400 is closed at prepare
  with no equation and gate-ineligible; the Nov 4-10 score step has no artifact to score.
- Not checked: why label coverage fell below 99% (a data gap, the 17:00 recording edge, or the rule's age limits).
  A follow-up would be a new lane id with its own frozen coverage rule.
