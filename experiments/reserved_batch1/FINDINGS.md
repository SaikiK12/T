# FINDINGS: reserved_batch1 (R286), the first read of the reserved samples

**Answer: 1 PASS (C14, cross-venue funding carry binance+gate), 5 FAIL, 4 UNREADABLE.** Read once on
2026-11-03 at 08:45-08:58 UTC with `scripts/run_reserved_batch.py --run`. PREREG sha256
`706b6ca4ab62c62cbed8a55071713bce1640714353809558849f1581378f4b9a`; the runner verified it
and every frozen input, and the dry parity on the archive reproduced each lane's frozen numbers before the read.

- **C14 passes every frozen check, but at about a quarter of its archive size.**
  - 2020 at 1x: +2.86%/yr against +10.05%/yr on 2021-26.
  - This confirms the sign of the binance+gate carry on a sample nobody had read. It does not confirm the archive's size.
- **The unlock short (C01) fails on its reserved events.**
  - Pooled mean -3.45% per event, week-cluster t -0.87.
  - Four 2020 events lost -55.7% on average.
  - The 15 post-archive events made +3.36%. They are too few to decide on alone.
- **The other candidates were read because they were promised.** None had real power (PREREG power table), and none
  passed.

## Decision table (one-sided p against the reallocated weighted-Bonferroni α; PASS also needs 10% trimmed mean > 0, leave-two-coins-out mean > 0 and 2x mean > 0)
UNREADABLE candidates (C09, C12a, C12b, C12c: 0 observations, N_min 8) passed their α to the readable ones in
proportion. So C14 0.0273 → 0.0297, C01 0.0147 → 0.0160, and each other readable candidate 0.001 → 0.00109. The total
stays 0.05.

| Id | Rule | n | Mean 1x | t | p (one-sided) | α | Trimmed | L2CO | 2x | 3x | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C14 | carry binance+gate L14d th10% K20 | 345 days | +0.78 bp/day (+2.86%/yr) | NW 4.03 (plain 2.68) | 2.8e-5 | 0.0297 | +0.68 bp | +0.59 bp | +0.51 bp (+1.86%/yr) | +0.23 bp (+0.85%/yr) | **PASS** |
| C01 | unlock short D-7 → D | 57 events, 34 weeks | -3.45% | -0.87 | 0.81 | 0.0160 | +0.63% | -4.59% | -3.65% | -3.85% | FAIL |
| C09 | pre-listing notice short +168 h | 0 | | | | | | | | | UNREADABLE |
| C10 | earn-product add short +168 h | 11 clusters | -1.28% | -0.36 | 0.64 | 0.00109 | +0.37% | -4.40% | -1.68% | -2.08% | FAIL |
| C11a | R263 strategy 330, RSI(14) 10/90 1 h long | 366 days | +1.95 bp/day | 1.09 | 0.14 | 0.00109 | 0.00 bp | +1.53 bp | +1.88 bp | +1.81 bp | FAIL |
| C11b | R263 walk-forward stream L6 K20 | 184 days | +1.53 bp/day | 0.39 | 0.35 | 0.00109 | +8.03 bp | +0.08 bp | +0.27 bp | -0.98 bp | FAIL |
| C12a | negative-funding onset ≤ -2% long +72 h | 0 | | | | | | | | | UNREADABLE |
| C12b | the same, +24 h | 0 | | | | | | | | | UNREADABLE |
| C12c | onset ≤ -1% long +24 h | 0 | | | | | | | | | UNREADABLE |
| C12d | onset ≤ -0.3% short +168 h, 10% cover | 90 clusters | -2.93% | -1.66 | 0.95 | 0.00109 | -6.08% | -4.27% | -3.33% | -3.73% | FAIL |

Source: `results/decisions.csv` and `results/batch.json`. Event means are per cluster, in % of notional. Daily means
are in bp of capital per day.

## C14 in detail (the only pass)
- **Rule (unchanged from R275):**
  - Short the perp leg and long the other venue's perp when the 14-day mean funding gap exceeds 10%/yr, with up to 20 slots.
  - Binance and Gate only.
  - 2020-01-22 to 2020-12-31 (345 days; the first 14 days are lookback). `results/carry/` holds the engine's tables.
- **Net at 1x, 2x and 3x:**
  - +2.86 / +1.86 / +0.85 %/yr.
  - NW t (lag 10) 4.03 / 2.50 / 1.07; plain t 2.68 / 1.70 / 0.76.
- **The statistic used.**
  - The frozen statistic is the NW t, with p 2.8e-5.
  - The plain t's p (about 0.004) is also below α, so the PASS does not hinge on the NW correction.
  - The NW t exceeds the plain t, which means the daily nets are negatively autocorrelated.
- **Shape:**
  - The first half averaged +0.31 bp/day and the second half +1.26 bp/day.
  - Maximum drawdown -0.23% at 1x. Volatility 1.04%/yr.
  - The 10 best days hold 62% of the 1x sum (94% at 2x).
- **Breadth:**
  - 32 coins ever qualified. A mean of 6.4 candidates per day passed the 10% threshold.
  - The engine's coin list held 48 Gate symbols for 2020 (`results/carry/report.json`).
  - Without BNB and ONT, the two largest contributors, the mean is still +0.59 bp/day.
- **Reading.** On a sample nobody had read, the archive's best carry set earns a positive, significant net. It is about
  28% of its 2021-26 size, on a thinner 2020 market with fewer coins and smaller funding gaps. At 3x it is near zero.
  This is gate-1 evidence that the mechanism is real. It is not evidence for the +10%/yr level.

## C01 by window
| Window | n | Mean 1x |
|---|---|---|
| reserved_2020 | 4 | -55.74% |
| reserved_mexc | 38 | -0.64% |
| post_archive | 15 | +3.36% |
| Pooled | 57 (34 week clusters) | -3.45% (median +3.12%, hit 59.6%) |

- The PREREG expected about 65 priced events. 57 were priced; 2020 gave 4 of its 30 events, against about 15 expected.
- The 2020 loss is concentrated in squeezes. That is the tail risk R265's archive did not show at this size.
- The trimmed mean is positive (+0.63%), but the leave-two-coins-out mean (-4.59%, without AGT and 2Z) and the 2x mean
  are not. It would fail the robustness checks even at a smaller p.

## What the result earns (PREREG "What a result earns")
- **C14 PASS: a gate-1 confirmation.**
  - It earns a new frozen forward paper lane (new id, API).
  - None of the running carry lanes trades this exact set:
    - R278: gate+hyperliquid, binance+mexc, gate+mexc;
    - R279: gate+kucoin, binance+kucoin;
    - R294: mexc+lighter.
  - R278's Binance book reads funding through `www.binance.com` and has decided every day through 2026-11-02, so the
    data path exists.
  - Real money stays behind paper proof and `lab.gate.go_real()`, placed by the owner.
- **C01 FAIL.**
  - R286 does not add a PASS to R266 `unlocks_fwd`'s gate-2 decision.
  - R266 continues on its own frozen rule (decision at 120 scored tickets).
- **C09 UNREADABLE.** R272 `announce_fwd` continues; its prelist book has no reserved-sample support either way.
- **C10, C11a, C11b, C12a-d.** Not read on these samples again. Their own lanes' gate-0 verdicts stand.
- **Read budget.** This batch spent read 1 of 4 of the 2020, Gate-2020 and MEXC-only samples.

## Trials read against the program
- R286 counts 10 trials (one per candidate), as frozen.
- Program trials were 9,478,421 before the batch (PREREG) and are 9,782,840 now (`registry.program_trials()`, which
  includes R386's 303,520 trials registered since).
- The batch controls its own family-wise error at 0.05 by weighted Bonferroni over 10 pre-committed candidates.
- C14's p of 2.8e-5 would also clear a Bonferroni bar over the whole program only at about 5e-9 per test. It does not,
  and it is not meant to. The PREREG's α weights were set before the read, and the candidate was pre-committed before
  its own lane's result. The raw program sum is bookkeeping across correlated searches, not an independent-test count.

## Recording the outcome
- `registry/rounds.csv` is append-only with one row per id. The R286 row stays as registered (RUNNING, PENDING,
  10 trials).
- No RUNNING row in the registry has ever been closed in place or by a follow-up row: the forward lanes R214, R266 and
  R278 all stay RUNNING. So there is no convention to follow.
- The verdict lives here, in `results/decisions.csv` and in `registry/candidates.csv`.

## Process notes
- **Container restarts.** The read was due at 01:07 UTC. The container restarted at about 01:08 and again at about
  08:41, so it ran at 08:45 after the daemons were restored.
- **Post-archive bars.** Refreshed first with `scripts/fetch_binance_recent.py --unlock-post-archive --end 2026-11-02`:
  16 symbols, 549 daily files, manifest sha `08d2a4ae11bd`. No 451 from data.binance.vision.
- **The bins placeholder was used.** C11's dry parity loads `data/research/bins.npy`. A sparse placeholder with the
  true header stood in (see `docs/handover/SCHEDULED_CHECKS.md`); C11 discards the bins. It was removed after the
  read (`rm data/research/bins.npy data/research/bins.npy.PLACEHOLDER.txt`). The real data stays in `bins.npy.xz`.
- **No re-run.** The runner refuses a second read because `results/batch.json` exists.
- **Nothing else.** No key, order, money or download beyond the post-archive bars.

## Not checked
- **C14 fills.** 2020 Gate books and fill quality. Costs are R275's model at 1x/2x/3x, not 2020 measured spreads.
- **Funding.** 2020 funding intervals and caps per venue, beyond what the archive rows hold.
- **C14 GATES items.** Strict on-time clock, dependent-null calibration and capacity were not run in this batch.
- **C01's 2020 losers.** Their identities were not inspected beyond the window means.
- **The forward lane C14 earns.** It is not built or registered yet; that is the next step.

## Files
`PREREG.md`, `PREREG.sha256`, `carry.toml`, `run.log`, `results/{batch.json, decisions.csv, carry/}`, `work/` (legs and
specs built by the runner), `FINDINGS.md`.
