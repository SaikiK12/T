# R225 forward implementation notes

## 2026-10-19 (input integrity fixes; no tickets recomputed)
- Validate the R217 seed before writing anything: required A_C0, B_C0, and X2 arrays, each a finite numeric daily
  vector for 2021-01-01 through 2026-09-30 (2,099 days). Their 1x discovery, validation, and holdout summaries
  must match the committed R217 results.csv. The SHA256 is recorded in R225 status and checked on later runs.
- The seed file is absent from this checkout, GitHub Actions artifacts, and GitHub releases. The owner must restore the
  original experiments/sizing_v1/results/daily.npz; it cannot be recreated here because the original research panel
  and sizing run inputs are also absent. Until then, the forward sizing script exits before changing days.csv or
  status.json.
- Validate source days as unique, contiguous canonical UTC dates with replay/ontime labels matching the frozen
  2026-10-20 cutoff, and finite 1x/2x/3x nets and gross exposure.
- Recompute prior rows from the saved seed and current source tickets before appending. A changed saved row or any
  backfill at or before the journal high-water mark stops the run. r1 remains causal: each day's multiplier uses
  only the prior days.
- These are code checks only. No R225 ticket, multiplier, status, or preregistration was changed during this audit.
