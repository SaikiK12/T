# vrpsell_v1 (R408): abandoned before any statistic

R408 was frozen on 2026-11-05 (`93c51ea`) and run once the same evening. The run stopped with a TypeError inside
`series_stats`: `lab.stats.newey_west_t` returns `(n, mean, t)`, and the frozen runner passed that tuple to `float()`.
The crash came before any statistic was computed, printed or written. `run.log` holds only the PREREG check and the
traceback, and no results file exists.

The same rule continues as R409, `experiments/vrpsell_v2`. Its runner is `scripts/run_vrpsell2.py`: R408's runner
with the t taken from the tuple, plus the lane path and the registry id. Nothing else changed: the costs, the window,
the entry, the hedge and the decision are the same.
