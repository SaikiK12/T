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

The repository's `forward_all.sh` already delegates to the orchestrator. The configured
notice tasks share `.notices.lock` with the five-minute notice loop, with synthetic
compatibility coverage. This does not establish which revision runs on a capture host.
Check that host and its active writers before any controlled reload; the optional
report reader never deploys or changes a scheduler.

Unknown returns stay unknown, including cumulative totals after a missing row. A completed interval without a score
is `awaiting score`; a future frozen ticket is not an open position. R225's decision is at 365 on-time days; R272's
two books each need 12 notices. A milestone at day 90 for the MEXC positioning books is futility review only.

The original page supports Claude's Artifact adapter (`dash`, D3 and host theme
variables). Repository changes do not publish or update that private artifact.
Existing upload commands are documented in `scripts/dashboard_data.py`.

## Independent static bundle

`scripts/build_dashboard_standalone.py` reuses that same view with a local adapter,
theme and pinned D3 asset. It accepts one explicitly selected schema-v2 immutable
export generation; it never runs the exporter, scans lanes, starts jobs or uploads.
Every declared dataset identity, row count and generation identity is checked before
publication. The browser independently checks dataset bytes before displaying them.
Missing/error values remain unknown. An export clock is not live-feed freshness.

First inspect an existing generation (replace GENERATION with its full64-character id):

```sh
python scripts/build_dashboard_standalone.py \
  --export-dir /absolute/export/dashboard/data/generations/GENERATION \
  --generation GENERATION \
  --d3-asset dashboard/vendor/d3.v7.9.0.min.js \
  --d3-sha256 f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539
```

The default is a read-only plan. To build, add `--build --out /absolute/new-bundle`;
its parent must exist and the destination must be new, outside the export directory.
Publication uses Linux atomic no-overwrite rename. The [vendored dependency record](vendor/README.md)
preserves D3's version, source, identity and license. No runtime CDN is required.
Serve only that bundle directory on localhost or an explicitly chosen host; WebCrypto
requires localhost or HTTPS. Opening it directly as `file:` is unsupported. Building
does not deploy a site or install a recurring refresh.

```sh
python -m http.server --bind 127.0.0.1 --directory /absolute/new-bundle 8000
```

Checks: `python -m unittest tests.test_dashboard_data tests.test_dashboard_jobs tests.test_dashboard_view
tests.test_forward_orchestrator tests.test_dashboard_standalone`. Browser tests use
Playwright and system Chromium when available. The standalone test serves invented
export rows with the real pinned D3 asset, exercises filters/unknown/calculation
states and refuses tampered bytes; it does not validate live feeds or publication.
