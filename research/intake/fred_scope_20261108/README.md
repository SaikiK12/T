# DTB3 source-scope plumbing, 2026-11-08

FRED public CSV endpoint, publication time unknown; accessed2026-11-08.
Original URL: https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3
Probe URL/date/bytes/raw and decoded hashes are in probe.receipt.json.
No authentication, custom User-Agent, redirect, provider retry or refusal
workaround. One GET under the original accumulated historical allowance.

Before R429 freeze/registration/commit, qualify_counts.py was run once and
read status, schema, date columns, resource counts and opaque hashes only.
Numerical rate values were neither inspected nor compared. The held source
body was opaque-stream-hashed and only its recent8192-byte tail date-filtered;
no protected2020 row was parsed. Raw full history remains in canonical
state; the recent view and lineage receipt are retained here.

The source-probe body gzip is an archive wrapper, not a claimed HTTP gzip
encoding. The receipt reports actual HTTP encoding separately. Bytes are
encoded application bodies, not measured TLS/network wire traffic.

The fixed source identity measurement, deployment gates and limitations
are in experiments/paper_quote_scope_v1/PREREG.md. Do not re-run plumbing,
compare values before the committed freeze, or use this source intake as
economic evidence. A successful short series response cannot prove future
availability, an investable rate, settled funding or positive net return.
