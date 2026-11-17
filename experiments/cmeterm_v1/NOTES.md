# cmeterm_v1 (R503): superseded by R504 before any statistic

- **2026-11-17.** R503's frozen `fetch` could not finish.
  - Its first request asked for 16 years of continuous-symbol definitions for CL in one stream.
  - Databento generates that stream day by day. After about 15 minutes, at 2020-05, the response was cut
    (`ChunkedEncodingError`).
  - Out-of-window timing showed that none of R503's 16-year definition requests can finish under that limit.
- **No statistic was computed.** The partial file held only contract identities (2010-06..2020-05), and it is deleted.
- **What replaces it.** R503's script cannot change. [`cmeterm_v2`](../cmeterm_v2/PREREG.md) (R504) imports R503's
  frozen rule unchanged and replaces only the data plumbing:
  - daily ranks from symbology.resolve;
  - contract details from quarterly snapshots of the mapped contracts;
  - settlements one root-year per request, with retries.
- The R503 row in `registry/rounds.csv` stays as registered: the journal is append-only, and R504's row records the
  supersession. R503 counted the rule's single trial; R504 counts 0.
