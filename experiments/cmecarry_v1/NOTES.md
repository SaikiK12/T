# cmecarry_v1 (R501): superseded by R502 before any statistic was read

- **2026-11-17.** `run` stopped at its first summary.
  - Cause: `lab.stats.newey_west_t` returns `(n, mean, t)`, and the script cast the whole tuple to a float.
  - The traceback printed no number, and `results/` stayed empty.
- R501's frozen script cannot change. [`cmecarry_v2`](../cmecarry_v2/PREREG.md) (R502) runs the same rule with that one
  line fixed. Its new test runs the whole `run` on a synthetic world.
- R501's Databento pulls stay where they are and are reused: `data/databento/cmecarry/`, 125 files, $0.2452 quoted.
- The R501 row in `registry/rounds.csv` stays as registered: the journal is append-only, and R502's row records the
  supersession.
