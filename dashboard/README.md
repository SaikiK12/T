# Control room

This is a view of the canonical methods registry, registered experiments and paper journals. It cannot authorize
live trading. Stable method/round IDs and physical research paths are preserved; readable names are display labels.

- **Overview / Candidate follow-ups:** selected follow-ups, not another queue. Compare evidence scope and units
  before comparing statistics.
- **Method queue:** canonical rules with status, missing mechanics and source text available to search.
- **Forward paper:** replay/on-time observations, per-book decision counts and the actual frozen decision horizon.
- **Data and loop:** collectors, paper studies, execution measurements, evidence decisions, integrity and reporting.
  Filter by responsibility or recorded state; keep the stable task ID and log reference for diagnosis.

Run `python scripts/dashboard_data.py` to export the existing dataset IDs. To display already-recorded orchestrator
states, explicitly supply `--jobs-state-dir /absolute/external/state-directory`. This only reads reports; it never
starts the orchestrator. Current legacy logs appear as `UNKNOWN` even when recently modified. Structured `SUCCESS`
requires recorded exit code zero; staleness is separate, and neither certifies complete or on-time observations.
No process command lines, environment values or raw log contents are exported.

The data inventory uses readable dataset labels and purpose/scan-state filters, retaining original folder names.
Unknown folders remain unclassified. Symbolic links are excluded and scan errors produce partial counts rather
than aborting on a concurrently replaced file. File modification time is activity metadata only: it does not
certify observation timestamps, complete history or valid provenance. Empty/partial inventories and future clocks
have unknown activity freshness; historical datasets have no live-activity deadline. A provenance flag means a
note exists, not that its claims were checked.

The live shell is unchanged. In particular, adopting the orchestrator for execution needs its own compatibility
review of the notice lock shared with the five-minute notice loop. Do not infer that the optional report reader
deploys or changes the scheduler.

Unknown returns stay unknown, including cumulative totals after a missing row. A completed interval without a score
is `awaiting score`; a future frozen ticket is not an open position. R225's decision is at 365 on-time days; R272's
two books each need 12 notices. A milestone at day 90 for the MEXC positioning books is futility review only.

The page is hosted through Claude's existing Artifact adapter (`dash`, D3 and host theme variables). Repository
changes and local synthetic browser tests do not publish or update that private artifact. Existing upload commands
are documented in `scripts/dashboard_data.py`; review and publication remain separate from these draft changes.

Checks: `python -m unittest tests.test_dashboard_data tests.test_dashboard_jobs tests.test_dashboard_view
tests.test_forward_orchestrator`. The browser fixture uses Playwright and system Chromium when available; it tests
table filters and missing-value behavior with a synthetic host, not live feeds or the private Artifact service.
