# Event recorder and concurrent-run review, 2026-11-02

Scope: snapshot e653b7568c60c4cdcf6f9367c23c48b4a193c163. Synthetic
recorder tests and a frozen-input/error-only check of R386; no real strategy
run, interim candidate/result read, reserved sample or public data request.

## Recorder corrections

Three issues were reproduced before changing code:

1. `poll_one` passed the loop's starting time to the event diff, even after a
   slow fetch. A scheduled timestamp of 1000 seconds was written before a
   response requested at 1030 seconds could be available. Event rows now use
   local time after fetch/parse and state validation. Poll-attempt rows use
   completion time, and elapsed duration uses the monotonic clock. The scheduled
   bucket and monthly attempt file remain unchanged. A backwards wall clock
   produces an error attempt without new event rows.
2. A Nasdaq earnings response for the wrong `asOf` date became an empty list,
   while the requested date remained in the covered scope. With ten valid
   records from another date, the shrink guard passed and one unchanged event
   was falsely marked `gone`. Invalid/mismatched partitions now fail the
   earnings source poll. Missing rows, malformed rows and an explicit failed
   status are errors; explicit empty/null rows with a matching date remain
   parseable. A single invalid partition discards that source's other dates
   for this attempt; the failure is logged, and other independent sources can
   continue. This is intentionally conservative coverage, not a complete
   per-partition collection protocol.
3. `ensure` could fail on its first start when multiple parent directories were
   absent. Free-space checks now use the nearest existing ancestor without
   creating data during the check. The normal lock/bootstrap path creates the
   recorder directory afterwards.

The CSV schema and existing journal bytes are preserved. Earlier pass-start
timestamps cannot be repaired into response-receipt times. New timestamps are
also local observations, not independently verified UTC, first public release
times or durable-publication/deadline evidence. Neither version qualifies a
prospective trading observation without a separately frozen admission policy.
No SEC endpoint/contact address or fee/execution assumption is added.

Validation: 15 new contracts pass on the correction. Against the original
three modules, the final tests produce 8 failures and 6 errors (including
malformed-payload subtests). After integrating the recorder agent's changes,
all 50 focused checks pass: 15 new contracts, 23 recorder tests and the 12
unchanged frozen R386 synthetic tests. Zero-delay legacy fixtures now mock
their observation clock as well as the scheduled time; the delayed-fetch and
retry tests independently check actual completion semantics. The local full
suite before that integration passed 2,035 tests with 3 skips; final-head CI
checks the combined tree. Tests use temporary journals and mock network and
process startup.

## R386 snapshot and stash limits

PREREG SHA256:
`6bdaae6a1c91e5606192f4110f010060401f58ec34091c953c7127a9867c8406`.
All ten available non-data inputs match their declared hashes, including the
frozen runner and its tests. The 42 data input files are unavailable in this
workspace and were not verified. The published log has only two startup lines
and no error match; this is insufficient to establish live process health or
rule out a later file-access error. No live worker status is available here.

The frozen runner loads arrays and warms Numba (`cache=False`) before forking
its workers. That reduces subsequent dependence on source/data files, but
does not establish that a transient filesystem change was harmless.

In particular, stash/reset/checkout can replace a redirected log's inode.
A process may continue normally while stdout/stderr write to an unlinked or
replaced inode instead of the visible `run.log`. The process owner should
compare `/proc/<parent-pid>/fd/{1,2}` targets and device/inode numbers with the
visible log. If they differ, preserve the old descriptor into a NEW recovery
log without overwriting files, reopening the writer or restarting the run.
A one-time copy does not preserve later messages: keep a reader descriptor
open or follow that descriptor until the producer finishes. Inspect errors
only while the experiment is in flight; outcome admission follows its PREREG.
These are diagnostic steps for the owning runtime, not checks completed here.

Follow-up at owner commit `55a9c3b`: the process did have an unlinked output
descriptor, and its owner preserved an 11-line snapshot in
`run.stdout.recovered.log`. Error-only scans of that copy and the published
`run.log` find no listed exception/error pattern. This confirms the logging
side effect, not the health of the entire numerical run. A snapshot alone
does not preserve subsequent output; the descriptor still needs to be kept
open/followed until the producer exits. No interim statistics were inspected.

Integrations use a separate persistent worktree. An active writer's tree is
not stashed, reset or switched; its uncommitted state and open descriptors
remain in place. Only the owning session restarts its event collectors after
review, recording the cutover and retaining legacy journals. R386 and the
other forward daemons are not restarted for these recorder fixes.
