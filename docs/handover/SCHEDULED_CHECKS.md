# Operational checks and preserved session reminders

**Operator update, 2026-11-07:** follow [current operations](../OPERATIONS.md)
and [R420's actual deployment evidence](../../experiments/ops_takeover_v1/FINDINGS.md).
Claude's operational assignment has ended. The single GitHub writer and its
canonical state branch replace the old hourly-host assignment for admitted
tasks. Continuous tapes, missing warm data and dated native reads remain
separate dependencies. Do not execute the old local loop as a second writer.

Current procedure reviewed **2026-11-04**, against repository commit `99e9ba1`.
This review inspected code and published metadata; it did not check the capture host,
restart a daemon, restore an archive or score a market event. Fresh ownership comes
from [issue #7](https://github.com/SaikiK12/T/issues/7), and exact study rules come
from each frozen PREREG. The session reminders copied on 2026-10-29 are retained
below as **inactive historical evidence**.

## Inspect before recovery

1. Read [AGENTS.md](../../AGENTS.md) and the latest [room claims](../ROOM.md).
   Identify the capture host, its active writers, checkout revision and external
   state directory. Work in a separate persistent worktree for integration.
2. Inspect the declared task graph, existing run receipts and data classification:

   ```sh
   .venv/bin/python -m lab forward
   .venv/bin/python -m lab status --state-dir /absolute/external/forward-state --strict
   .venv/bin/python scripts/handover.py status
   ```

   Use the actual state directory. A clean clone, process success or registry
   `RUNNING` status does not establish complete, on-time observations. Missing
   local data and unknown receipts remain explicit.
3. Coordinate any controlled reload with the file/process owner. Preserve journals,
   process ownership and the executed revision; never stash, reset or switch an
   active writer's tree, or kill another writer. Starting a second notice loop can
   duplicate work. Adoption of the optional orchestrator still requires the
   [shared-notice-lock review](../../dashboard/README.md).
4. Only on the capture host, after ownership and existing-process checks, use the
   recovery entry point documented in [HANDOVER](../HANDOVER.md#4-keep-the-forward-lanes-and-recorders-running).
   Verify each daemon's executed revision, last receipt, coverage and errors after
   recovery. Keep missed/late decisions labelled; replay cannot create an on-time
   observation that was never recorded.

## Record outcomes without rewriting round history

`registry/rounds.csv` is append-only. **Do not edit an existing R369, R367 or other
round row in place, and do not append the same id again.**
[`lab.registry.append`](../../lab/registry.py) registers a genuinely new round and
rejects duplicate ids; it is not a status-transition API. There is no published
in-place or follow-up-row convention for closing the existing RUNNING rows.
Record an existing lane's authorized result in its native FINDINGS and declared
artifacts, retain any deviation in that lane's record, and coordinate in issue #7.
See [R286's published explanation](../../experiments/reserved_batch1/FINDINGS.md)
for the retained registry status. A changed study requires a new id and freeze.

## Calendar and one-read guards

The following are **planned conditions recorded at this review**, not evidence
that the host is running or that a sample is ready. Recheck the native protocol
and latest ownership before executing an allowed step.

| Study | Condition and next permitted action |
| --- | --- |
| [R286 reserved batch 1](../../experiments/reserved_batch1/FINDINGS.md) | Completed its one read on 2026-11-03. Do not rerun `run_reserved_batch.py --run`, remove its read guard, or recreate the historical bins placeholder. FINDINGS records the placeholder's removal. |
| [R391 reserved batch 2](../../experiments/reserved_batch2/FINDINGS.md) | Published after its one read on 2026-11-03. Its completed sample is not a new blind sample. |
| [R367 HFT lead](../../experiments/hftlead_v1/PREREG.md) | Recheck coverage on/after 2026-11-05 00:30 UTC, the rescheduled date reported after the outage. The frozen rule needs at least three usable finished UTC days (80% coverage for both coins); it permits coverage-only retries when fewer qualify. No current day is scored, no day beyond 2026-11-08 is added, and insufficient days at the cutoff mean INCONCLUSIVE. Only the allowed one outcome read follows qualification. |
| [R389 BRENTOIL roll](../../experiments/lighter_roll_fwd/PREREG.md) | First November step window starts 2026-11-06 23:29 UTC. Step 1 establishes direction and is not traded; steps 2-5 follow the frozen rule. Primary decision is on the first 20 traded steps, with its declared mechanism stop and May 2027 cutoff. |
| R392 reserved batch 3 | [LEADS](../LEADS.md) records a planned read on/after 2026-11-17 and a PREREG not yet frozen at that snapshot. Confirm current registration and freeze before any read; reaching the date alone does not authorize opening the sample. |
| [R369 EIA lag](../../experiments/eventlag_fwd/PREREG.md) | Keep reference/quote coverage and session-gap receipts for each frozen calendar event. The published next schedules are crude 2026-11-04 15:30 UTC and gas 2026-11-05 15:30 UTC; scheduled time does not prove actual publication or valid feeds. Score and read only as its protocol permits. |
| [R390 Binance+Gate carry](../../experiments/xfund_bg_fwd/PREREG.md) | First forward day planned 2026-11-04. Preserve the frozen book and ticket clocks; use its native scored-day looks rather than a reminder date. |

R400 remains [terminal REFUSED](../../experiments/path_response_v1/FINDINGS.md).
Its earlier November 4-10 score window has no model artifact to score and is not
armed by this calendar.

## Backup checks on the capture host

Inspect `scripts/handover.py status`, the archive receipts and the actual budget
before a pack. [archive_recordings.sh](../../scripts/archive_recordings.sh) defaults
to 900 MB; HANDOVER records a historical explicit 1,800 MB run. Neither number
establishes current free capacity or permits an automatic budget increase. Use
the agreed `ARCHIVE_BUDGET_MB` and an archive worktree without an active writer.
The wrapper packs, commits and pushes; it is not a read-only status command.

Retain the source of every unarchived file: over budget, oversize, too young,
excluded or failed. The existing packer skips files above 95 MB. Public archives
exclude third-party `data/news` text; licensed inputs and credentials remain
outside them. Verify chunk/file hashes and a restoration receipt before calling
a recording protected. A later refetch is not proof of identical frozen inputs.

## Historical reminders (inactive)

The original text below preserves what the session intended, including the
superseded in-place-edit advice, deletion command, old caps, dates and session
restrictions. Apply the current procedure above and the latest owner instructions;
these archived commands must not be executed as a recovery checklist.

<details>
<summary>Original reminders copied 2026-10-29, with later historical annotations</summary>

> # Scheduled checks held in Claude's account (copied 2026-10-29, because the scheduler is not in the repo)
>
> These are the reminders Claude set for itself. They disappear with the session or the account, so the text is kept here
> as a to-do list anyone can follow by hand. Each one names the script that does the work; none of them places an order.
> Times are UTC. A check that has already run is marked in its heading when this file is next edited.
>
> ## 2026-10-29 15:20: R369 first event check
> The natural-gas storage release at 14:30 UTC should now be scored. Run `.venv/bin/python scripts/run_eventlag.py` if the
> ops tick has not, read `experiments/eventlag_fwd/journal/events.csv` and `results/summary.json`, then run
> `.venv/bin/python scripts/eventlag_gaps.py`. Report validity (reference, quotes on all three venues), the status counts, t*
> and c for the event, and whether any feed had a session gap inside [T - 10 s, T + 65 s]. If the event is valid, set the
> R369 row in `registry/rounds.csv` to RUNNING (edit in place, by precedent). If invalid, say why and do not retune anything
> (the lane is frozen). Re-measure the size of `data/commodity_perps` (`du -sb`) against its 4,000 MB cap.
>
> ## 2026-10-29 17:30: raw tape first window
> The first raw-tape window (13:00-17:00 UTC) is closed. Check `data/rawtape/status.json` and
> `python scripts/record_raw.py status`: rows per kind, MB per kind, bytes per row (about 5 for bbo), `rawtape_gb` against the
> cap and `free_gb` against 2.5, `u_back`, `seq_back`, `max_gap_ms`, `parse_err`, reconnects in `sessions.csv`, `trades` and
> `trades_with_rpi` (a feed property, not a strategy outcome). Say if a stream gapped or the cap ended the window early. Do
> not compute any markout, lead or fill statistic: M430-M432 need a frozen PREREG first. If `trades_with_rpi` is 0 after
> the window, note it in M432; if above 0, note which symbols. Then plan the PREREG for M430 (one primary rule, hourly-block
> power) once at least 3 windows exist.
>
> ## 2026-11-02 00:40: R367 run and FINDINGS (not run: only 2026-10-29 was usable after the 3.1-day outage; repeat on or after 2026-11-05 00:30 UTC, last chance 2026-11-08)
> Verify the PREREG (`experiments/hftlead_v1`), confirm `data/hft` has compacted whole days 2026-10-29 .. 2026-11-01 and that
> the 2026-11-01 merge is done, run `.venv/bin/python scripts/run_hftlead.py` once (re-run only if INCONCLUSIVE for too few
> days), then write `experiments/hftlead_v1/FINDINGS.md` (1x/2x/3x, program trials from `registry.program_trials()`). State
> prominently the number of independent hourly blocks next to the fills (the Holm hurdle over 16 rules is p <= 0.003125), and
> that the L = 200 ms rules sit below the measured 233-255 ms websocket round trip (`rtt` rows in `data/rawtape`,
> `docs/DIRECTION.md`), so only the 500 ms rules are executable from that container. Then update the R367 registry row and
> M427 through code, run integrity, regenerate the catalog and panel, commit, push, and post the verdict on issue #7. A null
> closes M427 as registered only (the successor family is M430-M433, new ids); a PASS only requests owner-placed calibration
> orders. Also check `data/rawtape/status.json` and report the RPI pilot count.
>
> ## 2026-11-03 01:07: reserved batch 1 (R286)
> **Found by the dry run on 2026-11-02:** the runner's dry parity (repeated inside `--run`) loads `data/research/bins.npy` for C11, which had been compressed to `bins.npy.xz` (6.8 GB uncompressed; 7.8 GB free, 2.5 GB recorder floor). C11 discards the bins, so a sparse placeholder with the true header (`data/research/bins.npy`, see `bins.npy.PLACEHOLDER.txt` beside it) stands in. Remove it after the batch has run: `rm data/research/bins.npy data/research/bins.npy.PLACEHOLDER.txt`, and say in FINDINGS that the placeholder was used. Never run `run_battery.py`, `speed_test.py` or `build_extra_views.py` while it exists.
>
> First refresh the post-archive bars: `.venv/bin/python scripts/fetch_binance_recent.py --unlock-post-archive --end <yesterday>`.
> Then run `.venv/bin/python scripts/run_reserved_batch.py --run` in the background. It verifies the frozen PREREG and the
> inputs and re-runs the dry parity check before the read. Afterwards write `experiments/reserved_batch1/FINDINGS.md`
> (1x/2x/3x, read against the program trials), record the outcome without editing the R286 row (`rounds.csv` is
> append-only: follow the convention the forward lanes use for RUNNING rows and say so if there is none), post the result on
> issue #7 and update `candidates.csv`. The sample is read once; see `docs/GATES.md` ("Reserved samples").
>
> ## Every hour at :43: the lab tick (a session job, 7-day limit)
> 1. Check the forward loop and notice loop are alive and the recorder daemons are running. After a container restart run
>    `scripts/<x>.py ensure` for each daemon, `FORWARD_STATE_DIR=/home/user/forward_state setsid nohup sh scripts/forward_loop.sh`
>    and `setsid nohup sh scripts/notice_loop.sh`.
> 2. Check downloads and background jobs and disk (`df -h`; start nothing new under 2 GB free; `data/commodity_perps`
>    against its 4,000 MB cap).
> 3. Read issue #7 and the open PR comments.
> 4. Advance `docs/DIRECTION.md` as `AGENTS.md` allows (freeze before measuring, one writer per file, a null is a result;
>    1x/2x/3x; read against `registry.program_trials()`).
> 5. Run `python scripts/handover.py status` (an UNCLASSIFIED line is an error: add it to `registry/data_manifest.csv`). Once a
>    day (the 00:43 tick), run `ARCHIVE_TRAILERS="<the two Claude trailers>" sh scripts/archive_recordings.sh`: it packs the
>    recordings into the `data-archive` branch and pushes it. Check the "of 900 MB" figure it prints.
> 6. Commit and push to `claude/yo-9a1k5w`. No Workflows, no subagents, no orders, no keys in the repo.
>
> ## The older hourly loop (disabled since 2026-10-23, kept because its steps still describe the housekeeping)
> "Check the forward loop is alive; run the collectors `scripts/scrape_hyperliquid.py` and `scripts/scrape_leaderboards.py`.
> Check background jobs and disk; for each finished job write FINDINGS (1x/2x/3x of its execution mode's cost, read against
> `registry.program_trials()`), append its registry row through `lab.registry.append`, and update `registry/methods.csv`,
> `registry/candidates.csv`, MAP and EDGE_SCOREBOARD. Refresh the Control Room dashboard
> (`scripts/dashboard_data.py --changed`; it was published as a Claude artifact, which will not survive the account).
> Read new comments on issue #7 and answer NEED-CLAUDE items briefly. Advance the next step of `docs/DIRECTION.md`. Run the
> tests before committing `lab/`, `scripts/` or `engine/` changes (`cargo test --release` in `engine/` too). Commit and push.
> Do not run Workflows or subagents."
>
> ## Not scheduled anywhere but due
> - R371 `usopen_fwd`: a daemon (`scripts/forward_usopen.py`, restarted by `ensure` in the forward tick) writes a ticket at
>   10:00 New York (14:00 UTC until 2026-11-01, then 15:00) on each NYSE day and scores it after 24:00 UTC. After a container
>   restart run `.venv/bin/python scripts/forward_usopen.py ensure` before the next 10:00 New York. A missed day is logged and not made up.
>   Futility is read at 125 scored days, PASS or NULL at 500; `experiments/usopen_fwd/journal/status.json` has the table.
> - R369 `eventlag_fwd`: scoring is an ops task that runs on the forward tick; the first read is about 2026-12-23 (8 valid
>   events per type and 6 lag-filtered trades). Calendar in `experiments/eventlag_fwd/`.
> - R364 `settlelit_fwd`: futility at 20 / 40 hops, PASS at 40 or 80 (rule in its PREREG).
> - Weekend closure 2026-10-30 21:00 to 2026-11-01 23:00 UTC: the first re-anchoring capture for M447.
> - EIA crude 2026-11-04 15:30 UTC (after the US clock change).

</details>
