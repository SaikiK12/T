# FINDINGS: anytime_monitor_v1

**Verdict: METHOD_VALID (gate 0 diagnostic).** The e-process monitor keeps its size at or below
alpha on both synthetic nulls and on the dependence-robust block mode; applied to the lab's
already-committed forward-lane and audited-carry series it rejects H0: mean <= 0 on **zero** of 66
series-cost cells at the dependence-robust reading, so it changes no existing verdict. This is a
monitoring tool, not a new signal, and it adds no prospective evidence.

- **Registry row:** R489 (trials: 0 strategy trials; program trials before this lane: 9,785,313)
- **Reproduce:** prereg sha `439a75a6471350a695454070b909d8b6ea3f477eb08db9b524331d9dc730d0b2`;
  runner `scripts/run_anytime_monitor.py`; data manifest sha: concatenated per-file sha256 in
  `experiments/anytime_monitor_v1/receipt.json` (`inputs`)

## Numbers

**Method validation (the headline).** Fixed-seed synthetic calibration, 400 seeds x 365 days, alpha
= 0.05, reject the first day the running max capital reaches 1/alpha = 20. Monte-Carlo slack
(alpha + 3 x sqrt(alpha(1-alpha)/seeds)) = 0.083.

| mode | i.i.d. zero-mean size | AR(1) phi=0.7 size | within slack? |
|---|---|---|---|
| bet (raw daily) | 0.000 | 0.018 | yes |
| block (5-day means) | 0.000 | 0.000 | yes |
| mixture (raw daily) | 0.000 | 0.000 | yes |

Both modes are valid. Development found the raw `bet` mode inflates under strong dependence at a
*wider* bound and shorter sample (phi=0.7 gave 0.112 with lo/hi = +/-0.30 and sd 0.01 in an earlier
probe), which is why the PREREG reads a series as evidence only when the `block` mode agrees. On
this lane's own calibration the raw mode stayed inside slack, so the block mode is the conservative
reader, not a correction of a broken one.

**Monitor reads (already-seen committed series).** 66 (series, cost) cells across
`carry_v2_audit_v1`, `carry_v2_audit_kc_v1` (engine v1 and v2 separately), `carry_fwd`, `mexc_fwd`
and `xfund_fwd`. Result: **0 MONITOR_REJECTS, 1 MONITOR_BET_ONLY, 65 NULL.**
- The single BET_ONLY cell is `binance+gate+hyperliquid+mexc L14d th10% K20|v2, net_1x`
  (bet e = 21.3, block e = 1.88): the raw mode alone crosses 20, the block mode does not, so per
  the PREREG this is **not** evidence. This is exactly the case the two-mode rule exists to catch.
- Closest block-mode e-values on the v2 engine: `binance+gate+hyperliquid+mexc ... net_1x` 1.88,
  `net_2x` 1.78; `gate+kucoin L14d th5% K20 net_1x` 1.76. All far below 20.

## Cost sensitivity
The monitor is run at each committed cost column: 1x, 2x and 3x. On the audited carry books the
raw-mode e-value falls as cost rises (e.g. binance+gate+hyperliquid+mexc L14d th10% K20: net_1x
bet e = 21.3, net_2x 15.8, net_3x 11.8), and the block-mode e-value falls likewise (1.88, 1.78,
1.67). No cell rejects in the block mode at any cost level, so the 1x/2x/3x distinction does not
change the verdict.

## What this does not show
- **No prospective evidence.** Every monitored series was already committed before this lane ran.
  A gate-0 diagnostic cannot be prospective; it re-reads seen history.
- **No strategy validation.** The monitor tests the *sign of the mean* of whatever series it is
  given. It says nothing about look-ahead, survivorship, universe gaps or a mis-specified book; if a
  series were biased, the monitor would still reject. That remains gate 1's job.
- **Power is low at realistic Sharpe.** The monitor pays for anytime validity with width; a
  +10 bp/day edge on a 60 bp/day series is detected about 73% of the time in 365 days, and a
  realistic perp-carry Sharpe (0.5-1.5) is detected slowly. It is a futility/monitoring device, not
  a fast PASS detector, and it does not replace a lane's frozen fixed-look decision.
- **The bound is declared, not estimated.** lo/hi = +/-0.30. A wider honest bound costs power; if a
  future day falls outside it the lane is re-registered, never silently clipped.
- **A reader bug was found and fixed mid-lane.** The two `carry_v2_audit*` files interleave engine
  v1 and v2 rows per book. The first run grouped by book only, corrupting the series (66 -> 39
  cells, 0 robust rejections but a wrong stream). The fix groups by (book, engine) and sorts by
  date. The frozen PREREG names the `engine` column, so this is a reader correction, not an idea
  change; it is recorded here rather than hidden.

## Next
- A future forward lane whose PREREG wants a daily read without inflating error fixes alpha, the
  [lo, hi] bound and the mode (`block` when the series is autocorrelated), freezes that block, and
  appends `{day, e_value, reject}` to its own `journal/anytime.csv`. `lab/sequential.lane_monitor`
  is the single call.
- The keystone value is process: it lets the lab watch the R215/R218/R220 forward lanes every day
  at a fixed level, which the fixed-look PREREGs cannot do, without spending alpha. It creates no
  new chance to declare an edge.
