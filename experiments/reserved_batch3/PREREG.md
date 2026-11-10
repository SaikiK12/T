# PREREG: reserved_batch3

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R392
- **Owner (single writer):** Claude (worker for the session that holds R392; the orchestrator sends GO)
- **Date registered (UTC):** 2026-11-10

RESERVED-2020-READ RESERVED-GATE-READ (the engine checks `RESERVED.md`, listed in the inputs block; `lab.panel` checks
this file for the 2020 read)

## Owner decision on timing
On 2026-11-09 the owner chose, in the session, to read batch 3 now instead of on or after 2026-11-17, because the
subscription ends before 11-17 (`docs/GATES.md`, "Owner decision, 2026-11-09"). The two-week spacing is shortened
once: batch 1 (R286) read the 2020 and Gate samples on 2026-11-03. The budget of 4 reads per sample is unchanged, and
this file is frozen before any reserved row is read.

## Question
Do three pre-committed books, unchanged, earn a positive net return at executable API costs on data no lane has read
for these questions?
- **C17** and **M319** on reserved 2020 (Binance perps; read 2 of 4 of the 2020 sample).
- **GLT** on the Gate long tail (read 2 of 4 of the Gate sample).

## Candidates (3 trials)
| Id | From | Rule | Sample | Archive evidence (already read) | Unit |
|---|---|---|---|---|---|
| C17 | R300 `intrars_v1` (M318), its pick | "us10 n3 follow": at 10:00 New York on NYSE days (14:00 UTC in EDT, 15:00 in EST), long the 3 top-50 perps that rose most since the 00:00 UTC close and short the 3 that rose least; flat at the last traded close at or before 24:00 UTC | 2020 NYSE days | discovery 2021-23 +34.6 bp/day (R300 t 1.88), validation 2024-26 +38.7 (t 1.28; without the 10 best days -3.3); 2021-26 +36.6, NW t (lag 10) 2.11, 1,439 days | day |
| M319 | R300 FINDINGS, the 08:00 placebo clock's pick | "k8 n3 follow" on the 08:00 UTC day: at 16:00 UTC, long the 3 strongest and short the 3 weakest top-50 perps by their move since the 08:00 UTC close; flat at the last traded close at or before 08:00 UTC the next day | 2020 days | validation +84.6 bp/day (t 2.37), picked post hoc from 9 clocks x 24 books; 2021-26 +64.6, NW t 3.14, 2,091 days | day |
| GLT | R275 `xfund_v1`, the book R391 confirmed on the KuCoin, dYdX and Lighter long tail | "gate+mexc L14d th5% K20": `qx spread` on `spec.toml`, every rule R275's | Gate long tail + MEXC, 2021-01-01..2026-09-30 | R275 on Gate's open coins: +14.87%/yr, NW t 6.71, 507 days; R391 on the other venues' long tail: +2.48%/yr, NW t 3.90, 526 days, 5.3 of 20 slots | day |

Read the results against `registry.program_trials()`: 9,784,969 trials before this round, 9,784,972 with its 3.

## Rules, exactly
### C17 and M319 (`scripts/run_reserved_batch3.py`, using `scripts/run_intrars.py`'s own `Grid`, `rows_for` and `day_books`)
- **Grid:** hourly bars on [2020-01-01 00:00, 2021-01-01 00:00) UTC; row r opens at 2020-01-01 + r h. A bar is
  traded when its close is finite and its volume positive. Funding is every Binance settlement in the window, rounded
  to the minute, summed over (entry close, exit close].
- **Universe:** R300's rule (`scripts/build_views.py`, `lab.research.make_universe(elig_top=50, col_top=50)`): the
  rank of `lab.panel.liquidity_rank` (trailing 720-bar mean quote volume, at least 180 bars from the window start,
  bars through the decision row only) over every Binance perp in `data/klines_1h` with a bar in the window; columns are
  those ever ranked in the top 50. Eligible at a decision: rank <= 50 and traded at the start and decision closes. A day
  with fewer than 30 eligible names has no book. Delisted coins are included; nothing after the decision is used.
- **Book:** the signal is the decision close over the start close, minus 1. Long the 3 highest, short the 3 lowest,
  equal weight, ties broken by 1e-12 x a seeded uniform draw (seed (300, 0, 10, 3) for C17, (300, 8, 8, 3) for M319,
  R300's). Each leg exits at the last traded close at or before the end of the hold (at entry if none). A long leg pays
  its funding and a short leg earns it.
- **Sample days:** the day's clock starts on or after 2020-01-01 and its hold ends by 2021-01-01 00:00 (R300's
  `in_window`). So C17 has at most the 2020 NYSE days from 2020-01-02, and M319 the days from 2020-01-01 08:00 to
  2020-12-30 08:00. No 2021 row is read.
- **Cost:** 8.5 bp per side at 1x, 4 units of turnover a day, so 34 / 68 / 102 bp a day at 1x / 2x / 3x.

### GLT (`spec.toml`, through `scripts/qx_run_verified.py experiments/reserved_batch3`)
- **Rule:** R275's spread book, unchanged (`engine/src/spread.rs`): long the coin on the venue with the lower funding
  and short it on the higher; the signal is the gap in funding settled over the last 14 days, annualized; 20 slots take
  the widest gaps >= 5% a year and hold while the pair's gap stays >= 2.5%; a pair is eligible only when the two
  venues' daily returns over 30 days correlate >= 0.9 on >= 20 observations; legs are priced on each venue's 1 h bars,
  1/40 of capital per leg; costs 7 / 14 / 21 bp per leg per side. Rows before `start` are dropped as they are read. Only the Gate folders (`reserved/`),
  the symbol table, the end date, the seed (392), `recent_from`, `keep_daily` and the hurdle (0) differ from R275's
  spec; none changes a trade.
- **Universe:** `symbols.csv`, 31 bases built by `scripts/run_reserved_batch3.py --symbols` from contract lists and
  file names only: Gate contracts on the `reserved` route with 1 h bar and funding files (744 bases, none with a
  Binance perp), matched by base with MEXC contracts that have hourly bars and funding (`reserved_venue_table.mexc`,
  which drops the MEXC-only reserved set).
- **Overlaps:**
  - **MEXC-only reserved set:** 6 Gate long-tail bases (AGI, FLR, PEAQ, RHEA, VELO, XDC) are R265's MEXC-only
    contracts. They have no row, so no MEXC-only bar is read.
  - **KuCoin, dYdX and Lighter reserved:** 25, 31 and 20 Gate long-tail bases are also in those venues' `reserved/`
    folders. Those folders are not in the spec and are not read. R391 read them; the bases are listed in
    `prefreeze/symbols_overlap.json` (the `--symbols` printout).
  - **R391's MEXC partner bars:** some of the 31 MEXC contracts were R391's partner legs. MEXC's open folder is not
    a reserved sample.
- **Window:** 2021-01-01..2026-09-30. MEXC's history starts on 2025-04-01 (`docs/provenance/mexc_hist.json`), so
  the book can trade only from about mid-May 2025 (R275's gate+mexc book on open coins started on 2025-05-12).

## Statistics (computed once, at 1x unless stated)
- **C17, M319:** the daily net. Newey-West t at lag 10 over the calendar days of the sample (`lab.stats.newey_west_t`;
  days without a book are gaps), one-sided normal p. The 10% trimmed mean (`scipy.stats.trim_mean(x, 0.10)`). The mean
  without the two coins whose shares added most: a coin's share of a day's net is +-(its leg return net of
  funding) / 3 - 2 x 8.5 bp / 3; the shares add up to the day's 1x net exactly. Means at 2x and 3x.
- **GLT:** `scripts/decide_reserved_batch2.py`'s `stats` on qx's tables: the engine's NW t (lag 10) at 1x with a
  one-sided normal p, n = the 1x daily rows, the 10% trimmed mean, the mean without the two coins whose trades added
  most (a trade's share is (price pnl + funding pnl - 4 x 7 bp) / 40), and the 2x and 3x means.
- **N_min:** 60 book days. Below it a candidate is UNREADABLE and its alpha goes to the readable ones in proportion.

## Decision
Weighted Bonferroni over the batch, total 0.05:

```alpha
C17 0.001
M319 0.001
GLT 0.048
```

A readable candidate **PASSES** when all hold: one-sided p <= its alpha; 2x mean > 0; 10% trimmed 1x mean > 0; 1x mean
without the two best coins > 0. Otherwise it **FAILS**. The verdicts are the only decision; everything below is
reported, not decided on.

## Power (how the weights were set)
Expected t = archive t x sqrt(expected n / archive n) x a shrink for having been picked. The weights maximise the
expected number of passes, sum of Phi(E[t] - z(alpha_i)), with a floor of 0.001 per candidate (grid in 0.0005 steps).

| Id | Expected n | Shrink | E[t] | alpha | Power |
|---|---|---|---|---|---|
| C17 | about 200 NYSE days (2020 had 81 Binance perps, fewer early in the year, so some early days have < 30 names; the 180-bar warm-up skips the first week) | 0.5 (R300's pick of 24; validation t fell from 1.88 to 1.28) | 0.39 | 0.001 | 0.004 |
| M319 | about 280 days | 0.4 (post hoc pick of 216 books) | 0.46 | 0.001 | 0.004 |
| GLT | about 500 days (MEXC's history) | 0.5 of R391's long-tail t 3.90 (31 bases on one venue pair, few slots will fill) | 1.91 | 0.048 | 0.60 |

- **Expected passes:** about 0.61. GLT's power is 0.25 at E[t] 1.0 and 0.91 at 3.0.
- **C17 and M319 have almost no power to pass.** Even unshrunk (E[t] 0.79 and 1.15) a pass needs t >= 3.09. Their
  2x condition is also hard: on 2021-26, C17's 2x mean was +2.6 bp/day and M319's +30.6. They are read because the
  record promised C17's 2020 read and M319's row reserves it for unseen data; their sign and size on 2020 are reported
  as the main information.

## Diagnostics (reported, not decided)
- C17, M319: R300's own report on the sample (`scripts/run_lotcap.series_stats`, NW lag 5, best-10-day share, mean
  without the 10 best days), gross, price-only, long and short legs, the equal-weight basket, median and minimum
  eligible names, break-even cost per side, means by month and by half, the two dropped coins.
- GLT: days, first book day, average slots held, trades, halves, max drawdown, top-10-day share, funding share, net by
  coin, trades by long and short venue.
- The bars-read digest of the 2020 grid and the qx run receipt.

## What the author has seen
- R300's FINDINGS and `results/summary.json` (both windows, all 24 books and 9 clocks), the M318/M319 rows, R275's
  family, R391's PREREG and FINDINGS, batch 1's FINDINGS and the archive numbers above.
- **Disclosed partial reads of 2020** (`docs/GATES.md` and batch 1): batch 1 read C14 (Binance + Gate carry), C11a/b
  (an RSI book and a walk-forward stream on the top 20's 2020 hourly bars), C01 and the event candidates; R244 used
  BTCUSDT's 2020 weekends; the old session's prop sims started in 2020. None computed an intraday cross-sectional
  relative-strength book. Batch 1's statement that 2020 had 81 Binance perps (file listing) is the only 2020 count used
  here.
- **The Gate long tail:** the contract list, file names, the coverage-month columns of `data/gate_hist/contracts.csv`
  and the overlap counts above. No long-tail bar, funding or return was read.
- **The dry run** (`--dry`, `prefreeze/dry.json`), archive only:
  - the loader rebuilt R300's universe (499 columns, rank equal to `data/research/rank.npy` element for element);
  - C17 reproduced R300's discovery and validation 1x rows (periods, mean, t, mean without the best 10) and M319
    R300's 08:00-clock validation t 2.372 and +84.62 bp/day, to 1e-6;
  - qx on Gate's open folders with R275's table reproduced R275's gate+mexc L14d th5% K20 row (days 507, window from
    2025-05-12, ann 1x/2x/3x, t, NW t, trimmed, trades) to 1e-4; p_rc differs (0.0005 vs 0.002) because it is the
    reality check over the strategies in one spec (R275 ran its family, this spec one book);
  - the guards refused: `lab.panel.check_reserved` and `load_grid` without a PREREG and with a frozen PREREG lacking
    the token; qx on this spec without `reserved_prereg` ("this spec reads reserved samples (RESERVED-GATE-READ)");
  - `data/mexc_hist` matched its provenance by hash; `data/gate_hist` matched by path and size, with no file newer
    than its record (no Gate file was opened).
- **The rehearsal** (`--rehearse`, `prefreeze/rehearsal.json`) ran the `--run` code end to end on stand-ins under a
  throwaway frozen PREREG, in 6 s: C17 and M319 on 2021 (248 and 357 days, NW t 0.74 and 1.93: FAIL, FAIL at these
  weights) and GLT on R275's open Gate coins, 2025-05-01..2025-12-31 (224 days, t 4.40: PASS). These are archive
  numbers already read; they show the path works and say nothing about the reserved samples.
- `tests/test_run_reserved_batch3.py` (synthetic): the guards, the books against brute force, the 10:00 New York
  hours, the statistics, the decision and the symbol table.

## What a result earns
- **GLT PASS:** measure the Gate long tail's executable book costs (spread and depth on Gate and MEXC) before a forward
  paper lane with a new id. **FAIL:** the long-tail carry lead stays with R391's venues; nothing is built on Gate's.
- **M319 PASS:** a frozen forward paper lane with a new id, labelled API. **FAIL:** M319 is TESTED with no forward lane
  from this read.
- **C17 PASS:** gate-1 evidence for M318; R371 `usopen_fwd` keeps running on its own frozen rules and is not pooled
  with 2020. **FAIL:** R300 stays NULL and R371 reaches its own futility read.
- Nothing here is gate 2 or a trade. No order, money or credential is involved.

## Runtime
One run of `python scripts/run_reserved_batch3.py --run` after GO. It verifies this file, `RESERVED.md` and every
input, refuses if results exist, runs `scripts/qx_run_verified.py experiments/reserved_batch3` (which hashes
`data/gate_hist` and `data/mexc_hist` against their provenance before and after), then loads the 2020 grid behind
`lab.panel.check_reserved`, and writes `results/batch3.json` and `results/decisions.csv`. Estimated under 5 minutes on
one core and under 2 GB. If it fails after reading data, it is reported, not retried, and no frozen file is edited.

## Inputs
Every file the run reads or depends on, with its sha256 at the freeze (qx_run's format). `--run` and
`scripts/qx_run_verified.py` refuse to run if any differs.

```inputs
scripts/run_reserved_batch3.py 3fc0196a3f79248c3e4d8266e6f8f866edc6dee39a26090ccda0eb2bead05b36
tests/test_run_reserved_batch3.py e8c3bbe55dbdf32e443842681ee8361fd8263c92c1848b079a96d1d44c780967
scripts/run_intrars.py 4db33b243bf832e0d4b0356a92cf103eed282241d10b1d8a3b1bfdadfa742eb6
scripts/run_lotcap.py d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d
scripts/run_clockflow.py 3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba
scripts/decide_reserved_batch2.py f98d4c52cdb3e350b39495f2fd9459cc90af0a541367bc1e25c6f05411ac0f27
scripts/reserved_venue_table.py c778e3354b1e7f73d8188d47b7f16e633f059f8c10680630acaea18e19bbccc8
scripts/qx_run.py 37d95b72580f5f91ab272d1223bc30b0235d1b8e9c4cce1e9d53c9b9607b9cef
scripts/qx_run_verified.py 0eda951060e2df881f6af9807b37ffaad658e8fc1d1b999b16282cea8dda4362
scripts/build_engine.py 93cacf172fc0f88da4e4cdbdb4b1b0cfe097aa15cdcebbe55959ebdb0c7f1d70
lab/__init__.py da4d03db9b753aa99ad4ce309fa20b767963ab714f97018ecfaf9693b1498487
lab/panel.py fee9835bcc73e14ec277c93d0edf2a1b3f6f1ad739b15e1895dec28a4a186db6
lab/data.py a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe
lab/prereg.py 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508
lab/sessions.py 831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d
lab/stats.py bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34
lab/inference.py 96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f
lab/runtime.py e41bd2df1746e9e7db037ed7f7e8100f5b0ebd08872d3a6c1c8334a0157251ce
lab/registry.py 8f24ac21c3dbf3073b9fc9b9c3421e6105464166f2bbf23477cc9b1ff26f62ce
experiments/reserved_batch3/spec.toml 04fdf2e4334a747ead283a74fb88a910de08f3f2c8b53c29cadde6fcf842e4b6
experiments/reserved_batch3/symbols.csv 3a044645faa8e91aedce5515550275c87542680871cd4818ee5cbc2e74a5fe84
experiments/reserved_batch3/RESERVED.md f4c7099482f20fd93567da927dd978690aacfbaf0c7219380cdbf12457708fa4
experiments/reserved_batch3/prefreeze/dry.json e23e97a11b61930522dfc37b075523621e329f2aeaf1522462fe66e2bc0b0e20
experiments/reserved_batch3/prefreeze/rehearsal.json c3d7ac03a1cf27b987cd0aa1881af64f73e559d8b4d3753fdfcb8618cf54c507
experiments/reserved_batch3/prefreeze/symbols_overlap.json 475e8db7273a5c27521b468815a70a1c6c85441b6ce1abc122082bb9ec933d37
docs/provenance/gate_hist.json e496f80737a33ccffd3be5fb2d119310d91930021f7477338e124290950563c0
docs/provenance/mexc_hist.json 5fb2f74b0ffbfde94f9a73830b728e22387bce12475802fba01ac42fb7898c55
docs/provenance/klines_1h.json 55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6
docs/provenance/fundingRate.json 84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de
experiments/unlocks_v1/events.csv 24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e
data/gate_hist/contracts.csv f1c7c8ba10b2252fc3b26728619f3527766a308083f3406fa6a0b40463219995
data/kucoin_hist/contracts.csv 40305369e6d881fcc5c66a2964b57048aa1d12d63fbe5861fc3ffc14d13e2695
data/dydx_hist/contracts.csv 1bfe30b536324749ede88b488a290b2d3869ddbd2130008058d6be659ed93b1a
data/lighter_hist/contracts.csv bd040f363ec869ffc6aeacd58f66bece070471b56b7fcf122269319a6df2e398
experiments/intrars_v1/results/summary.json 2f7604e04e951772b37b649337b1fbb7952e707fd0b4747fb9f40d1d2b4d0dbc
experiments/xfund_v1/results/strategies.csv 0ecfa28be6ec176d0eec715e2cd9a976443b0428e306a6992ff74da1bfec50dc
experiments/xfund_v1/symbols.csv 78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0
engine/Cargo.toml af64b8d2d3aa9b9e179615432249a058b5669c2e4c79b9fe4bc9a2a64b3c8d2c
engine/Cargo.lock 9fc3e3a75a0275d0f3af29e1bfd901d358977e47fc9fe3413ef3318be791e11f
engine/src/data.rs 4f4ea1ae3047da42db6c248bee0aeb192ac2eb9fb0709cbfa43a96005fb3a146
engine/src/events.rs 47e4160e525fadc15dc5ec9d53c713a0d07e92397c9ddd07f779ad1896ddb58d
engine/src/factors.rs 636eaef71ea28cedac413e728ba71470933b9f719a3ac40880b80a19ed65c31f
engine/src/main.rs 2e523e2bd1d251096b10ee92bd9bca002a8afc1300aa8c0d3aa8281a5e107f45
engine/src/reserved.rs 02397aa28548fea14eaac24d311b0f658f74055eadab5cf6b3712375732d4ee6
engine/src/spread.rs 3f49b5c545fdaf0c03185d15da8b6c0adc0fec417463e5f4e93b80d8f22414d5
engine/src/stats.rs bbf7615e3fee7f523e5984f83cee841316f2fb77d465d2ea2afa42f3b0724c47
rust-toolchain.toml 9cbde07377abdce69bc9580adb0315d52e2a09d6494a2005550a7e6733d9688b
```
