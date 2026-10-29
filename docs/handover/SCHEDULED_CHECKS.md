# Scheduled checks held in Claude's account (copied 2026-10-29, because the scheduler is not in the repo)

These are the reminders Claude set for itself. They disappear with the session or the account, so the text is kept here
as a to-do list anyone can follow by hand. Each one names the script that does the work; none of them places an order.
Times are UTC. A check that has already run is marked in its heading when this file is next edited.

## 2026-10-29 15:20: R369 first event check
The natural-gas storage release at 14:30 UTC should now be scored. Run `.venv/bin/python scripts/run_eventlag.py` if the
ops tick has not, read `experiments/eventlag_fwd/journal/events.csv` and `results/summary.json`, then run
`.venv/bin/python scripts/eventlag_gaps.py`. Report validity (reference, quotes on all three venues), the status counts, t*
and c for the event, and whether any feed had a session gap inside [T - 10 s, T + 65 s]. If the event is valid, set the
R369 row in `registry/rounds.csv` to RUNNING (edit in place, by precedent). If invalid, say why and do not retune anything
(the lane is frozen). Re-measure the size of `data/commodity_perps` (`du -sb`) against its 4,000 MB cap.

## 2026-10-29 17:30: raw tape first window
The first raw-tape window (13:00-17:00 UTC) is closed. Check `data/rawtape/status.json` and
`python scripts/record_raw.py status`: rows per kind, MB per kind, bytes per row (about 5 for bbo), `rawtape_gb` against the
cap and `free_gb` against 2.5, `u_back`, `seq_back`, `max_gap_ms`, `parse_err`, reconnects in `sessions.csv`, `trades` and
`trades_with_rpi` (a feed property, not a strategy outcome). Say if a stream gapped or the cap ended the window early. Do
not compute any markout, lead or fill statistic: M430-M432 need a frozen PREREG first. If `trades_with_rpi` is 0 after
the window, note it in M432; if above 0, note which symbols. Then plan the PREREG for M430 (one primary rule, hourly-block
power) once at least 3 windows exist.

## 2026-11-02 00:40: R367 run and FINDINGS
Verify the PREREG (`experiments/hftlead_v1`), confirm `data/hft` has compacted whole days 2026-10-29 .. 2026-11-01 and that
the 2026-11-01 merge is done, run `.venv/bin/python scripts/run_hftlead.py` once (re-run only if INCONCLUSIVE for too few
days), then write `experiments/hftlead_v1/FINDINGS.md` (1x/2x/3x, program trials from `registry.program_trials()`). State
prominently the number of independent hourly blocks next to the fills (the Holm hurdle over 16 rules is p <= 0.003125), and
that the L = 200 ms rules sit below the measured 233-255 ms websocket round trip (`rtt` rows in `data/rawtape`,
`docs/DIRECTION.md`), so only the 500 ms rules are executable from that container. Then update the R367 registry row and
M427 through code, run integrity, regenerate the catalog and panel, commit, push, and post the verdict on issue #7. A null
closes M427 as registered only (the successor family is M430-M433, new ids); a PASS only requests owner-placed calibration
orders. Also check `data/rawtape/status.json` and report the RPI pilot count.

## 2026-11-03 01:07: reserved batch 1 (R286)
First refresh the post-archive bars: `.venv/bin/python scripts/fetch_binance_recent.py --unlock-post-archive --end <yesterday>`.
Then run `.venv/bin/python scripts/run_reserved_batch.py --run` in the background. It verifies the frozen PREREG and the
inputs and re-runs the dry parity check before the read. Afterwards write `experiments/reserved_batch1/FINDINGS.md`
(1x/2x/3x, read against the program trials), record the outcome without editing the R286 row (`rounds.csv` is
append-only: follow the convention the forward lanes use for RUNNING rows and say so if there is none), post the result on
issue #7 and update `candidates.csv`. The sample is read once; see `docs/GATES.md` ("Reserved samples").

## Every hour at :43: the lab tick (a session job, 7-day limit)
1. Check the forward loop and notice loop are alive and the recorder daemons are running. After a container restart run
   `scripts/<x>.py ensure` for each daemon, `FORWARD_STATE_DIR=/home/user/forward_state setsid nohup sh scripts/forward_loop.sh`
   and `setsid nohup sh scripts/notice_loop.sh`.
2. Check downloads and background jobs and disk (`df -h`; start nothing new under 2 GB free; `data/commodity_perps`
   against its 4,000 MB cap).
3. Read issue #7 and the open PR comments.
4. Advance `docs/DIRECTION.md` as `AGENTS.md` allows (freeze before measuring, one writer per file, a null is a result;
   1x/2x/3x; read against `registry.program_trials()`).
5. Run `python scripts/handover.py status` (an UNCLASSIFIED line is an error: add it to `registry/data_manifest.csv`). Once a
   day (the 00:43 tick), run `ARCHIVE_TRAILERS="<the two Claude trailers>" sh scripts/archive_recordings.sh`: it packs the
   recordings into the `data-archive` branch and pushes it. Check the "of 900 MB" figure it prints.
6. Commit and push to `claude/yo-9a1k5w`. No Workflows, no subagents, no orders, no keys in the repo.

## The older hourly loop (disabled since 2026-10-23, kept because its steps still describe the housekeeping)
"Check the forward loop is alive; run the collectors `scripts/scrape_hyperliquid.py` and `scripts/scrape_leaderboards.py`.
Check background jobs and disk; for each finished job write FINDINGS (1x/2x/3x of its execution mode's cost, read against
`registry.program_trials()`), append its registry row through `lab.registry.append`, and update `registry/methods.csv`,
`registry/candidates.csv`, MAP and EDGE_SCOREBOARD. Refresh the Control Room dashboard
(`scripts/dashboard_data.py --changed`; it was published as a Claude artifact, which will not survive the account).
Read new comments on issue #7 and answer NEED-CLAUDE items briefly. Advance the next step of `docs/DIRECTION.md`. Run the
tests before committing `lab/`, `scripts/` or `engine/` changes (`cargo test --release` in `engine/` too). Commit and push.
Do not run Workflows or subagents."

## Not scheduled anywhere but due
- R369 `eventlag_fwd`: scoring is an ops task that runs on the forward tick; the first read is about 2026-12-23 (8 valid
  events per type and 6 lag-filtered trades). Calendar in `experiments/eventlag_fwd/`.
- R364 `settlelit_fwd`: futility at 20 / 40 hops, PASS at 40 or 80 (rule in its PREREG).
- Weekend closure 2026-10-30 21:00 to 2026-11-01 23:00 UTC: the first re-anchoring capture for M447.
- EIA crude 2026-11-04 15:30 UTC (after the US clock change).
