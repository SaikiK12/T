# Registry labels that overstate, and what supersedes them (2026-11-25; the registry rows stay as written)

The registry is append-only, so its rows are not edited. When a verdict label reads stronger than the evidence,
it is listed here.

| Round | Label | What it really is | Evidence |
|---|---|---|---|
| R197 flow72_v2 | CONFIRMED | in-sample pass; its single holdout R198 is NULL (t 1.22) | registry notes of R197 and R198 |
| R185 atlas_v1 | CONFIRMED | "In-sample, gross" | registry notes |
| R192 atlas_ctx, R195 atlas_mtf | CONFIRMED | replication-rate signals in sample (SIGNAL vs placebo), not tradable net results | registry notes |
| R304 mlrank_v2 | PARTIAL | superseded by R332 (NULL): the pick nets −16.5 bp/day on complete metrics; a metrics-presence rule alone earns +50.3 | `experiments/mlrank_v3/FINDINGS.md:1-5` |
| R299 mlrank_v1 | PARTIAL | "INVALIDATED BY AUDIT" in its own notes | registry notes |
| R462, R468, R349 | PARTIAL | gate-0 PASSes recorded as PARTIAL by convention | each FINDINGS |

- **From now on, every FINDINGS states which of these it is:** in sample, out of sample (with the holdout id),
  measurement, or null.
