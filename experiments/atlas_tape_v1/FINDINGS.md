# FINDINGS: atlas_tape_v1 (R386), a gate-0 screen of seconds-to-minutes conditional returns

**Answer: NULL by the frozen rule. No cell is a candidate, so nothing goes to reserved batch 2 from this screen.**
- 303,520 cells were counted as trials. The best validation net-1x t is 4.21. The 95th percentile of the best t a break-even world produces over the same grid is 5.25. The best cell's family-wise p is 0.87.
- The best real t (4.21) is below the median placebo maximum (A 4.39, B 4.19). The max statistic sees nothing a grid this size would not produce by itself.
- A weaker, non-decisive count test does see a surplus, and it sits in one place: fading extreme taker flow and returns on SOL, BTC and ETH at 3-15 minutes. That is the area R349 already read in these same years.

## Verdict by the frozen rule
A candidate needed all five: eligible, discovery net 1x > 0, validation net 1x t >= 2, validation net 2x > 0, and a family-wise p <= 0.05 against the 300-replica shifted-signal max statistic over the whole grid.

| Step | Cells |
|---|---|
| Trials (every cell) | 303,520 (A, minute bars: 172,480; B, 1-second tape: 131,040) |
| Eligible (>= 100 trades and >= 10 clusters in each period) | 199,448 (A 164,978; B 34,470) |
| Eligible and discovery net 1x > 0 | 34,499 |
| Eligible with validation net-1x t >= 2 | 1,450 |
| Rules 1-4 (discovery > 0, t >= 2, 2x > 0) | 1,218, all in A; B has none |
| Rule 5 (family-wise p <= 0.05; needs t >= 5.25) | 0 |

- Registry: R386, status DONE, verdict NULL, trials 303,520, PREREG sha256 `6bdaae6a1c91e5606192f4110f010060401f58ec34091c953c7127a9867c8406`.
- PARTIAL needs a candidate. There is none, so NULL. Never CONFIRMED.

## Top cells, priced at each coin's measured Lighter walk (bp per trade, validation days)
1x is the round trip at the coin's median $1k walk (BTC 0.54, ETH 0.45, SOL 0.60, maj3 0.53 bp); 2x and 3x scale it. Ranked by validation net-1x t. These are what the screen saw. They are not candidates: every p_fullgrid is >= 0.87.

| # | Block, feature, side, coins, gate, q, hold | Trades (val) | Gross | 1x | 2x | 3x | t val | t disc | p full grid |
|---|---|---|---|---|---|---|---|---|---|
| 1 | A rel_1 follow, maj3, hi_act, .995, 1m | 21,932 | +1.39 | +0.87 | +0.34 | -0.19 | 4.21 | 0.35 | 0.87 |
| 2 | A ret_1 fade, ETH, hi_act, .995, 1m | 7,954 | +2.37 | +1.92 | +1.47 | +1.02 | 3.96 | -0.98 (fails rule 2) | 1.00 |
| 3 | A flow_3 fade, SOL, us, .98, 10m | 4,608 | +4.10 | +3.50 | +2.91 | +2.31 | 3.96 | 3.60 | 1.00 |
| 4 | A ret_1 fade, BTC, us, .995, 1m | 4,431 | +1.77 | +1.23 | +0.69 | +0.15 | 3.95 | 0.72 | 1.00 |
| 5 | A flow_3 fade, SOL, hi_act, .99, 5m | 6,735 | +3.11 | +2.51 | +1.92 | +1.32 | 3.94 | 4.09 | 1.00 |
| 6 | A flow_3 fade, maj3, none, .99, 5m | 20,141 | +2.11 | +1.58 | +1.05 | +0.52 | 3.91 | 3.89 | 1.00 |
| 7 | A flow_5 fade, SOL, none, .995, 10m | 2,444 | +6.98 | +6.39 | +5.79 | +5.20 | 3.85 | 3.92 | 1.00 |
| 8 | B bret_3 fade, maj3, none, .90, entry 3 s, hold 300 s | 1,213 | +1.99 | +1.47 | +0.94 | +0.41 | 2.63 | -1.80 (fails rule 2) | 1.00 |

- Block B (1-second tape) is empty. Its best cell (row 8) has t 2.63 on two validation days and points the other way in discovery. No B cell meets rules 1-4.
- The largest 1x nets with t >= 2 (+25 to +33 bp) are 60-minute fades inside the New York window on about 150-360 trades each. Their t is 2.1-3.2 and their p_fullgrid is 1.0.
- Files: `results/top200_by_val_t.csv` (top 200 eligible cells); `results/grid.csv.gz` (all 303,520, with MEXC web 3 bp and API 8.5 bp a side columns).

## How many passed against how many a null passes
- Placebo count: in each of 300 replicas the signal is moved against the returns by a whole circular shift, every cell is re-scored as if break-even, and cells are counted that point the same way in discovery, have centred t >= 2 and beat the round trip (the 2x analogue of rule 4). Null mean 558, 95th percentile 899, max 1,311. Real count 1,218. `lab.nulls.search_verdict` says SIGNAL (real above the 95th percentile).
- Max statistic: the placebo maximum t over all eligible cells and both sides has a 95th percentile of 5.25 (A 5.11, B 5.05) and a 99th of 6.15. The real best is 4.21. Discovery-selected p-values (best 0.28) and block-only p-values (best 0.78, A) agree.
- Reading: the count test is not decisive by the PREREG and should not be over-read. It counts highly correlated cells (nested thresholds, overlapping windows), so 1,218 is a few families, not 1,218 findings. Where the surplus sits (rules 1-4):
  - 1,011 of 1,218 are fades (83%); by feature kind 655 flow, 296 return, 137 rel, 71 imb, 59 div;
  - by coins: SOL 461, maj3 326, BTC 185, ETH 115, everything else 131 (alt walk costs are several times larger);
  - by hold: 3-15 min 978, 30-60 min 177, 1 min 63;
  - 958 stay positive at 3x, 122 keep t >= 2 at 3x, 148 have t >= 3 at 1x, 40 have t >= 3.5.
- This is R349's neighbourhood. R349 chose fading the top 0.5% 5-minute signed taker flow on BTC, ETH and SOL after 57 trials on the same bars and recorded PARTIAL. This grid re-finds that family (rows 3, 5, 6, 7) on the same years, so it is not independent evidence. R351 found the rule negative on nine alts at their own costs, and the alts barely appear here.

## Trials read against the program
- This lane adds 303,520 trials. `registry.program_trials()` was 9,479,320 before R386 and is 9,782,840 after it.
- The raw sum is bookkeeping, not an effective count. The cells are heavily correlated, which is why the lane used a placebo max over the whole grid and not Bonferroni.

## Candidate list
`results/candidates.csv` is empty (header only). The PREREG forbids promoting a near miss, and none is promoted. `top200_by_val_t.csv` is a table of what the screen saw. Whether the flow-fade family on the majors goes into batch 2 under R349's existing lane is a separate decision for the lead; this screen does not earn it a place.

## Not checked
- Live fills, queue position and partial fills. Costs are Lighter's median $1k walk applied to mid-to-mid returns.
- Latency. This box's websocket round trip is about 233-255 ms and Lighter's zero-fee takers wait 300 ms. Block A enters at the open of the next minute as if the order were already at the book (1-minute holds are the most exposed). Block B starts at 1 s. Nothing shorter was tested.
- Prices before 2026. Block A uses Binance prints for 2021-2026 and prices the trade at Lighter's October 2026 book. Lighter's real quote path in earlier years is not known.
- Capacity above $1k and the effect of trading the same extremes on several coins together.
- Funding on holds (none charged; holds are <= 60 minutes) and tick rounding.
- Block B power: two validation days (about 140,000 recorded seconds) and about 80 half-hour clusters. It can screen, not confirm.
- Unmet admission items from the PREREG: strict on-time clock, 10-day trimming, leave-two-coins-out, an 80%-power calculation, cross-family control beyond this grid.
- Stability by year or regime of the surplus cells; the runner does not report it.
- The tables above were transcribed by the lead from the lane agent's report. The lead re-read the verdict, trial count, candidate count, the joint and per-block max-statistic 95th percentiles, the best validation t, its full-grid p and the null-count 95th percentile from `results/summary.json`; the other cells were not individually re-checked.

## Lane details
- Run: `nice -n 10 python scripts/run_atlas_tape.py --run --workers 3 --placebos 300`, started 22:56 UTC on 2026-11-02, done 00:00 UTC on 2026-11-03 (3,834 s). About 5 GB proportional memory when sampled, 21 MB of outputs. No recorder or forward process was touched. No download, key or order.
- Inputs: all 52 matched their frozen sha256 at the start. PREREG.md still hashes to its sidecar after the run.
- Gate: 0 (research screen), on seen data for Block A (the minute bars were read for R349/R351) and on unread days for Block B.
- Run log provenance: the lead's `git stash`/`pop` replaced `run.log` with a new inode at about 22:58 UTC while pid 12044 kept writing to the old, unlinked file. The run was not restarted; results were written by path and are intact. `run.stdout.follow.log` (the lead's follower, byte 0 to process exit) is the authoritative run output. `run.fd1.copy.log` is a second full copy from the same open descriptor and is byte-identical (checked with `cmp`). `run.log` (a partial mirror up to 23:28) and `run.stdout.recovered.log` are left as they were.
- Reproduce: `python scripts/run_atlas_tape.py --run` rewrites `results/`. Placebo seeds 386 (A) and 387 (B).
- Files: `PREREG.md`, `PREREG.sha256`, `results/{grid.csv.gz, candidates.csv, top200_by_val_t.csv, placebo.csv, summary.json}`, `run.stdout.follow.log`, `run.fd1.copy.log`, `run.log`, `run.stdout.recovered.log`, `FINDINGS.md`.
