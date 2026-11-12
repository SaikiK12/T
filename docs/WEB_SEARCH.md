# Web search protocol

One way to search the web for this lab, so searches are scoped, not repeated, honestly labelled and tied to the
existing record. The ledger is [`registry/web_searches.csv`](../registry/web_searches.csv), checked by
`python -m lab websearch check` (also part of `python -m lab integrity`). It is metadata only and needs no network.

## When to search
Only for a named binding constraint or a lane that is waiting on a fact (AGENTS.md: read by task, not by corpus). A dated
memo calling an idea open is not a reason to search. A search that finds nothing is still a result: record it.

## Before searching (dedupe)
1. `python -m lab websearch seen TEXT` for the query words or the URL (ledger plus `research/intake/source_catalog_*.csv`).
2. `python -m lab find TEXT`, then grep `registry/methods.csv` and `registry/methods_aliases.csv` for the idea.
3. If a hit exists, build on it instead of searching again.

## Allowed sources
Public, keyless pages and APIs only. No paywall or login bypass, no bot-check evasion, no large downloads (those need the
owner's explicit yes), no orders, no credentials.

## Source tiers (`source_tier`)
- `primary`: exchange documentation and rulebooks, official code, the paper itself.
- `secondary`: reviews, aggregators, textbooks citing the primary.
- `practitioner`: blogs, forums, social media, video.
- `search_summary`: only a search-result snippet was seen.

## Fetch status (`fetch_status`)
Say exactly what was read: `FETCHED_FULL`, `FETCHED_PARTIAL` (name the pages in `note`), `SEARCH_SUMMARY_ONLY`,
`BLOCKED` (throttle, 403, paywall; not bypassed), `NOT_FOUND`. A claim seen only in a summary stays unread.

## Verification (`verification`)
Any claim that changes the queue needs an independent re-fetch of the source by someone other than the finder:
`VERIFIED`, `CONTRADICTED` or `UNVERIFIED`. Subagent output is a claim, not evidence.

## Routing a result
Put it in the existing record, never in a competing task list:
- a read source: a card from [`templates/research_card.md`](../templates/research_card.md) and a row in the dated
  `research/intake/source_catalog_*.csv`;
- a new idea: a row in `registry/methods.csv`, or a row in `registry/methods_aliases.csv` if it is an existing method;
- a null: the ledger row alone (query, tools, `NOT_FOUND` or what was seen), and the lane's FINDINGS if a lane asked.
List the destinations in `routed_to` (`;` separated repo paths) and the affected ids in `queue_ids`.

## Recording
`python -m lab websearch add --date YYYY-MM-DD --agent NAME --lens TEXT --query TEXT --tool TEXT --urls-fetched "URL URL" --fetch-status ... --source-tier ... --verification ... --routed-to PATH --queue-ids "M001;M002" --note TEXT`
assigns the next `WSnnnn` id, validates, and appends one row. The ledger is append-only: never edit earlier rows. Rows
backfilled from older notes say so in `note`. Regenerating README catalogs is not required for this ledger.

## Subagent brief template
- Lens: one lens from `docs/loop/PROMPT.md`; the constraint table; the read-only rule.
- Spent families: the list of families already tested, so they are not rediscovered.
- Output: at most 900 words, a URL for every fact, `UNVERIFIED` where unsure, the nearest Mxxx or `NEW`.
- Ask for: mechanism, frequency, latency, fee and capital needed, public data, a falsifiable kill test.
- Run `seen` first; the orchestrator verifies queue-changing claims and writes the ledger row after.
