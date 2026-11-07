# PREREG: reserved_batch2

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R391
- **Owner (single writer):** Claude (claim: #7 comment 6616810675, 2026-11-03)
- **Date registered (UTC):** 2026-11-03

RESERVED-VENUE-READ (the declaration the engine checks is `RESERVED.md`, listed below)

## Why this batch, and why now
The owner asked for backtests "like live paper, on existing data nobody has seen". The lab's reserved samples are that
data (docs/GATES.md). The KuCoin and dYdX long tail have had 0 of 4 reads. Lighter's `reserved/` folder, built under the
same rule, has had none either.
- **Cadence.** Batch 1 (R286) read the 2020, Gate and MEXC-only samples on 2026-11-03 at 08:45 UTC. This batch reads
  none of those, so no sample is read twice inside the two-week cadence. Their second read is batch 3 (R392), on or
  after 2026-11-17.
- **The candidate is the lab's best-replicated edge:** R275's carry book. It replicates on the archive (R275), on
  KuCoin and dYdX open coins (R277), on Lighter (R288) and on Binance+Gate 2020 (batch 1, C14 PASS).
- **What is untested** is whether it holds on coins no carry lane has read: the long tail with no Binance perp.

## Question
Does R275's carry book, unchanged, earn a positive net return on the reserved long-tail contracts of KuCoin, dYdX and
Lighter, paired with each other and with MEXC?

## Universe
`experiments/reserved_batch2/symbols.csv`: 28 bases, built by `scripts/reserved_venue_table.py` from contract lists and
file names only. No price, funding or timestamp row was read to build it.
- **A row:** a base listed by at least two of KuCoin reserved (18), dYdX reserved (9), Lighter reserved (9) and MEXC
  (25), with at least one reserved venue.
- **Excluded:** the six MEXC-only reserved contracts of batch 1 (`AGI FLR PEAQ RHEA VELO XDC` on MEXC). XDC stays as
  KuCoin + dYdX.
- **Not coins, kept by the mechanical rule:** EUR and TRY (dYdX FX), WTI (dYdX and Lighter oil) and KIOXIA (KuCoin and
  Lighter stock).
  - WTI is also traded by forward lanes R369 and R389, on prices from live recorders. Their `reserved/` history files
    were not read by those lanes.
- **Gate overlap, named and not read:** 18 bases are also in Gate's reserved long tail: `ANSEM AURORA BLEND BP CASHCAT
  CORE CP CRO CTC DATA KIOXIA MNT NEIROCTO NES PI STONK XDC XDP`. No Gate file is read.
- **Delisted contracts:** included wherever their files exist. The engine's identity guard drops a pair whose returns do
  not correlate, at 0.9 over 30 days with 20 observations.

## Data
- **KuCoin:** `kucoin_hist/reserved/candles_1d` and `funding`, daily bars.
- **dYdX:** `dydx_hist/reserved/candles_1h` and `funding`.
- **Lighter:** `lighter_hist/reserved/candles_1h` and `funding`.
- **MEXC:** `mexc_hist/klines_1h` and `funding`. These are open folders.
- **Provenance:** every folder is hashed against `docs/provenance/<folder>.json` by `scripts/qx_run_verified.py`,
  before and after the run.
  - `lighter_hist.json` is new and was recorded on 2026-11-03. Its hourly coverage covers `open/` only, so no reserved
    timestamp was read to make it.
  - The KuCoin, dYdX and MEXC records matched their folders on 2026-11-03 before this freeze.
- **Window:** 2021-01-01 to 2026-10-19, the last full day before the earliest fetch (MEXC, 2026-10-20).

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| 14-day funding spread between two venues | settled funding rates | venue archives, per-contract rate per settlement | trailing 14 days to the day close | settled rates, published at settlement | yes (engine uses days before the decision) | contracts as fetched 2026-10-20/21, delisted included where files exist | missing settlement = no rate (engine), never zero-filled as a price |
| Leg returns | close prices | venue candles (1d KuCoin, 1h others) | daily marks | bar close | yes | as above | missing bar = no mark; engine rules (R275) |

The membership is the venues' own lists as of the fetch. That is a venue-own-universe limit: a pass earns a forward
paper lane, not a claim about coins listed after 2026-10-21.

## Rule
R275's book, every parameter unchanged (`spec.toml`):
- **Lookback and signal:** 14 days. Enter when the trailing 14-day funding spread is at least 5% a year; exit below
  half of that.
- **Slots:** 20. Each leg's notional is 1/(2K), reset daily.
- **Positions:** long the venue that pays less funding, short the one that pays more.
- **The set is one four-venue set**, kucoin+dydx+lighter+mexc. Per coin and day, the engine takes the widest eligible
  pair.
- **Seed** 391, for the engine's report-only reality check.

## Splits and cost
- **No split.** The whole window is the out-of-sample read.
- **Cost per leg per side:** 7 / 14 / 21 bp at 1x / 2x / 3x, R275's cost.
  - The long tail's book costs are not measured. The 2x check is part of the decision, and 3x is reported.

## Decision (one candidate, alpha 0.05)
Batch 1's rule, from `scripts/decide_reserved_batch2.py` (`stats`, `decide`):
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided p of the Newey-West t (lag 10) at 1x is at most 0.05;
  - the 2x mean daily net is above 0;
  - the 10% trimmed mean of the 1x daily net is above 0;
  - the 1x mean without the two coins whose trades added most is above 0.
- **FAIL:** anything else.

**Reported but not decided on:** the engine's own gates and verdict, halves, 3x, the drawdown, the top-10-day share,
the funding share, per-coin contributions and the trades per venue.

**What a PASS earns:** a frozen forward paper lane on the long tail, at measured book costs, with a new id. It earns
no money: `go_real()` rules apply.

**Power.** The rehearsal below gave NW t 4.89 on 161 eligible open coins. With 28 contracts the book holds fewer
slots, and the expected t is lower. A FAIL here does not overturn R275, R277 or R288. It says the long tail did not
carry the book on this sample.

## Rehearsal before the freeze (open data, already read; not evidence)
The same spec was run with the venues' `open/` folders and R288's open symbol table (KuCoin, dYdX, Lighter and MEXC
columns), 2025-02-07 to 2026-09-30, to check the plumbing.
- **Book:** +7.31 / +5.88 / +4.44 %/yr at 1x / 2x / 3x, NW t 4.89, from 2025-02-28 over 580 days, 20.0 slots held.
- **Decision rule on that output:** PASS, so the decision code runs.

## Trials
- **This round:** 1 trial.
- **Program trials before it:** 9,784,329 (`registry.program_trials('registry/rounds.csv')`). After it: 9,784,330.

## Order
1. `RESERVED.md` frozen.
2. This file frozen, then committed and pushed.
3. A RUNNING registry row.
4. `python -I scripts/qx_run_verified.py experiments/reserved_batch2`, once.
5. `python -I scripts/decide_reserved_batch2.py`.
6. FINDINGS, with 1x/2x/3x read against program trials.

```inputs
scripts/qx_run.py 37d95b72580f5f91ab272d1223bc30b0235d1b8e9c4cce1e9d53c9b9607b9cef
scripts/qx_run_verified.py 0eda951060e2df881f6af9807b37ffaad658e8fc1d1b999b16282cea8dda4362
scripts/build_engine.py 93cacf172fc0f88da4e4cdbdb4b1b0cfe097aa15cdcebbe55959ebdb0c7f1d70
experiments/reserved_batch2/spec.toml 93793406675618dc0db5231bd633a3393d50ea9bf4f8b3abdb92100299fd88a2
experiments/reserved_batch2/symbols.csv 5ebfaec83a5c2c47831ec5fbf9b0e683ac3bdf0e88562caf99bfbb834c9ed748
experiments/reserved_batch2/RESERVED.md 98e962a03960ea3bf37792e43b86f52f3a65d9b244e94b8bc70951dac92bd2e2
scripts/reserved_venue_table.py c778e3354b1e7f73d8188d47b7f16e633f059f8c10680630acaea18e19bbccc8
scripts/decide_reserved_batch2.py f98d4c52cdb3e350b39495f2fd9459cc90af0a541367bc1e25c6f05411ac0f27
docs/provenance/kucoin_hist.json bc5abe62d763042bd2e01fe88f7b5bf367bdda263200c1cec67486fed19a4b13
docs/provenance/dydx_hist.json ebedb4c8f8297c602c9e095764f4c7d728bed40d4cfe8297c5b350c2f80e3a8b
docs/provenance/lighter_hist.json b630601c1374fc6ff1c9f7b3cb678a3013a324c764d16e0f572bb8a77e657577
docs/provenance/mexc_hist.json 5fb2f74b0ffbfde94f9a73830b728e22387bce12475802fba01ac42fb7898c55
experiments/unlocks_v1/events.csv 24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e
data/kucoin_hist/contracts.csv 40305369e6d881fcc5c66a2964b57048aa1d12d63fbe5861fc3ffc14d13e2695
data/dydx_hist/contracts.csv 1bfe30b536324749ede88b488a290b2d3869ddbd2130008058d6be659ed93b1a
data/lighter_hist/contracts.csv bd040f363ec869ffc6aeacd58f66bece070471b56b7fcf122269319a6df2e398
engine/Cargo.lock 9fc3e3a75a0275d0f3af29e1bfd901d358977e47fc9fe3413ef3318be791e11f
engine/Cargo.toml af64b8d2d3aa9b9e179615432249a058b5669c2e4c79b9fe4bc9a2a64b3c8d2c
engine/src/data.rs 4f4ea1ae3047da42db6c248bee0aeb192ac2eb9fb0709cbfa43a96005fb3a146
engine/src/events.rs 47e4160e525fadc15dc5ec9d53c713a0d07e92397c9ddd07f779ad1896ddb58d
engine/src/factors.rs 636eaef71ea28cedac413e728ba71470933b9f719a3ac40880b80a19ed65c31f
engine/src/main.rs 2e523e2bd1d251096b10ee92bd9bca002a8afc1300aa8c0d3aa8281a5e107f45
engine/src/reserved.rs 02397aa28548fea14eaac24d311b0f658f74055eadab5cf6b3712375732d4ee6
engine/src/spread.rs 3f49b5c545fdaf0c03185d15da8b6c0adc0fec417463e5f4e93b80d8f22414d5
engine/src/stats.rs bbf7615e3fee7f523e5984f83cee841316f2fb77d465d2ea2afa42f3b0724c47
rust-toolchain.toml 9cbde07377abdce69bc9580adb0315d52e2a09d6494a2005550a7e6733d9688b
```
