# R419 status: raw data collector ready for handoff; not activated

Status recorded **2026-11-07 UTC**; the planned window has opened, elapsed
unobserved slots remain missing and will not be backfilled.

**No recorder invocation, forward tick or campaign journal exists here.**
This is source collection plumbing, **0 predictive trials**, not a profitable
paper strategy or a completed source week. Program trials remain **9,784,345**.
**Costs 1x/2x/3x: N/A, not zero.** No return, funding cash or execution score.

Why this work follows R418: the fully funded Kraken spot/perp version did not
clear its capital hurdle. CBFSE's newly located primary fee schedule and venue
disclosure establish a different public-data route for a future two-perp
question: Coinbase CDE and Kraken. Historical CDE access returned401 without
authentication, so historical cashflow testing has not been substituted with
live/predicted rates. Raw scale/fixing/cash-credit semantics remain open.

The inactive implementation preserves full raw named books/rate/mark metadata,
independent UTC and monotonic receipts, SHA-256 body hashes, protocol/config
provenance and daily Kraken EEA risk rules. No financial normalization or score.
Each packet also waits three seconds after the first request group, then
reobserves the four books; actual per-book delays are recorded, not assumed.
This enables a later disappearing-depth execution test, not an allegation of
spoofing or proof that an order would fill. No depth statistic is measured.
The original cumulative acquisition caps remain unchanged, so the extra book
observations may shorten capture.
One writer/UTC-hour bucket, append-only request reservations, crash debit,
bounded request/body/disk counts and permanent block/schema stops are enforced.
Existing forward files and lab/operations.py are unchanged.

[Source qualification](../../research/intake/funding_notional_20261103/coinbase_eea_sources_20261106.md)
links the dated primary fee/venue/KID documents and exact probe receipts.
[Preflight](preflight_counts.json) checks nine **already captured**, asynchronous
source shapes/identities only. This is not a new live packet or a depth/return
measurement. Tests use invented bodies and temporary directories, including
rejection of source-identity drift and preservation of zero/missing data.
Final validation: **2,475 tests OK, 3 skipped, exit0**, including **20** new
synthetic acquisition-control tests. Prior R417/R418 frozen closures remain
exact. Source arithmetic inconsistencies are recorded, never used as settled
funding scale. See [validation](validation.json) for the dated test-code hashes
and final metadata checks.

## Post-freeze source qualification, still no economic run

After the immutable collector commit, the official public dashboard exposed a
separate [MDA history route](../../research/intake/funding_notional_20261103/coinbase_public_history_20261107.md).
Two small HTTP200 responses preserve 2,160 BTC and 2,160 ETH hourly rate rows
from Aug9..Nov7, with one missing grid slot each. Schema/identity/date counts
only; rate values were not summarized or scored. The earlier FairX401 remains
true for that resource, not all Coinbase history. Cash scale/fixing and missing
historical marks are still open. This removes a data-access obstacle for M488.
No frozen input/code/allowlist is changed; a successor test needs a new R-id.
The paired-book collector remains inactive and useful for execution evidence.

## Operational handoff, only to Claude's existing writer

After reviewing the fresh issue-7 claim and frozen commit, Claude may invoke
`python scripts/record_eea_pair.py --execute` from his single existing hourly
loop during **2026-11-07..2026-11-14 UTC**. The default CLI is inactive and no
loop entry is added by this PR. Output is solely
`data/recorders/eea_pair_capture_v1/`, with a counts-only `packet.json` per hour
and append-only `requests.jsonl`; no competing daemon. Window and cumulative
caps bind even after restarts. An occupied lock/hour causes no network.

Before any future economic test, qualify CDE rate scale and fixing identity,
cash settlement timing, current SID/rule drift and account availability, book quantity units,
effective venue maintenance rules and all costs. Freeze that trading experiment
separately. Raw collection before a strategy freeze earns no gate-1 alpha days.
Owner account/legal confirmation belongs before execution; no account is
requested or created for this work. No real stakes.
