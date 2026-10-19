# Hyperliquid copy-lead data integrity

The existing collector in [`scripts/scrape_hyperliquid.py`](../scripts/scrape_hyperliquid.py) deliberately keeps a
change log: `positions_at(day, hour)` carries the last row for an account and filters only on `hour_utc`. That behavior
is preserved. It does not prove that the state was known at the requested wall-clock time.

The opt-in [`lab.copylead`](../lab/copylead.py) helpers add that check. `strict_rebuild` and `strict_positions_at`
return `StrictSnapshot(positions, availability)`. Require `availability.available` before using the positions. The
report exposes `missing_hour`, `missing_accounts`, `late_server_time` and `stale_state` reasons, plus future-row and
untimed-row counts. Returned rows carry `source_hour_utc`, `source_time_ms`, `state_fresh` and `state_stale` flags.

The default cutoff is the requested hour's start. A later cutoff is valid only when the caller has frozen that receipt
time as part of its information set. Rows observed after the cutoff are excluded, even if their `hour_utc` label is at
or before the requested hour. The accounts file supplies the exact-hour completeness check; pass the as-of expected
`(address, account)` keys so a failed pick cannot disappear silently. Missing hours may still return carried rows for
diagnosis, but they are stale and the availability decision is false. Future-row counts include rows whose label is after
the requested hour as well as rows whose server timestamp is after the cutoff.

The committed 2026-10-19 sample has leaderboard-to-pick reconstruction that is deterministic (87 picks), and its three
recorded account hours reconstruct their position counts exactly. It has only 10:00, 11:00 and 14:00 UTC observations;
12:00 and 13:00 are absent. Server timestamps are about 41--44 minutes after the 10:00 label and 34--37 minutes after
the 14:00 label. Those are data-availability facts, not return or signal results.

## Provenance boundary

The repository was reconstructed from a Claude Code compaction summary; the original Windows data and earlier transcript
context were not imported ([`FOUNDATION.md`](FOUNDATION.md)). A real locator is recorded in GitHub [PR #1](https://github.com/SaikiK12/T/pull/1):
[`https://claude.ai/code/session_01SNoRQbwZuX9qSfWE3gaq3C`](https://claude.ai/code/session_01SNoRQbwZuX9qSfWE3gaq3C). An unauthenticated request reaches the shared-session shell but does not expose the transcript; this is not evidence that the session was read.

The original R180/R181 unlock work cannot be reproduced from this checkout. Before treating it as evidence, recover the
authenticated transcript or the original `experiments/unlocks_sf` and `experiments/unlocks_deep` artifacts, including the
frozen PREREGs and hashes, code commit, point-in-time unlock and volume inputs, universe/data manifest, trial count, and
the 364-ticket forward ledger with venue timestamps, costs and funding. The registry summary alone is not an unlock
dataset or a confirmation of the edge.
