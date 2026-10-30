# PREREG: settlelit_v1 (R363). Short Lighter across a deep Binance settlement, cover a minute later

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R363
- **Method:** M267 (settlement-window cross-venue carry), its Lighter-route form: the capture crowd's exit after T,
  traded on the hourly venue.
  - R354 (PASS at gate 0, recorded PARTIAL) found the hop. R356 (PASS at gate 0, recorded PARTIAL) found its whole
    price giveback inside the first minute after T. R362 (NULL) traded it on Binance from T + 15 s and found the move
    already done: about 85 bp against the receiving side within 15 s of T. R355 runs the hop forward on paper,
    unchanged by this lane.
- **Owner (single writer):** the Claude session that froze it. R363 was claimed on issue #7 (comment 6471423185)
  before the freeze.
- **Date registered (UTC):** 2026-10-28
- **Code:** `scripts/run_settlelit.py`, tested by `tests/test_settlelit.py` (9 tests on invented bars and files).
  - It imports these frozen runners unchanged:
    - R353's `scripts/run_settlehop.py`: `frozen_inputs`, the symbol table, the log and the day length;
    - R356's `scripts/run_settlehop_exit.py`: `check_data` and `last_traded`;
    - R355's rule `scripts/settlehop_rule.py`: the cluster-robust t, the trimmed mean and the leave-two-coins-out mean.
  - The runner calls `verify()` on this file first and checks every input below.
  - Before and after the run, it checks that `data/settlelit_1m` holds exactly the files listed in
    `docs/provenance/settlelit_1m.json`, each with its listed sha256.
  - Every Lighter funding file it reads must match R354's `data_files.csv`.
- **Gate:** 0. The decided hops are R354's 134 θ 0.3-0.5% hops outside R356's book.
  - R354 read them at the hour, and R362 read their Binance seconds. The move after T on Binance is known for them.
  - No lane has read their Lighter minutes or Lighter's settlement at T alone.
- **Execution mode:** API on Lighter (fee 0): one order before T, one at T + 1 min. The orders need no speed.

## Why this lane
- **The owner (2026-10-28, 13:42 UTC):** "We need a hft trading with good pnl troughout the day".
- **R356's minute path** (its 87 hops, in the hop's favour, from the entry an hour before T):
  - Lighter's part (the short leg) went from +87.6 bp at the last trade before T to +182.2 at the close of T + 1 min.
  - So on those hops the coin fell about 0.95% on Lighter in the minute after Binance paid a deep lump.
  - Binance fell 37 bp more than Lighter, and the hedged hop lost that.
- **R362's ticks** (all 221 hops, in the position's favour, from the last Binance trade before T):
  - +44.4 bp at T + 1 s, +65.4 at 2 s, +84.6 at 15 s and +89.3 at 60 s on average; on the 134 decided hops, +64.6 at
    15 s and +60.8 at 60 s.
  - A Binance taker entering at T + 15 s, the first safe second, nets −11.6 bp a hop at 1x. The Binance route is
    closed.
- **Why Lighter:**
  - A position against the receiving side on Binance or MEXC must wait out the settlement's 15-second deviation
    (Binance's FAQ), or it may pay the whole lump.
  - Lighter settles every hour, so a position held across T pays one hour of Lighter's own rate.
  - Lighter charges no fee, and an order placed before T needs no speed.
- **The question:** the move exists (R362). Does a Lighter position against the receiving side, opened before T and
  held across it for one minute, keep it at Lighter's minute closes, net of Lighter's own settlement at T and its book
  cost? Lighter follows Binance within a second (R348), but its settlement, its book and its prints are its own.

## What the author has seen
- **R354 and R356 in full,** including R356's minute path on its 87 hops. That path is why this lane exists, so those
  87 hops are reported and not decided on.
- **R354's per-hop columns for the 134 decided hops,** at the hour: e, direction, costs, and the hedged price over two
  hours. Not their minutes, and not Lighter's settlement at T alone.
- **R362 in full (NULL),** including its path on the 134 decided hops (above). This lane was drafted before R362 ran.
  R362 ran first because these minutes were still being fetched. So this lane cannot test whether the move exists:
  it tests whether Lighter's minute closes carry it, net of Lighter's settlement at T and its book cost.
- **The Lighter minutes,** fetched by `scripts/fetch_settlelit_1m.py`, which prints counts only:
  - 221 windows (1.2 MB), recorded 2026-10-28 14:25 UTC through the lab's shared Lighter limit; none missing and
    none with fewer than 20 bars;
  - untraded bars, by the minute they open: 27 at T − 6, 23 at T − 1, 5 at T, 11 at T + 1 and 21 at T + 4 (of 221).
- **Plumbing** (`--plumbing`; counts only):
  - 221 hops on 34 coins at 204 settlement times: 87 in R356's book, 134 outside it (at 127 times). Every Binance
    coin maps to a Lighter symbol; every window and every Lighter settlement at T is found, each funding file
    matching R354's manifest.
  - Hops traded, stale entries and stale exits, by trial (all 221): in0_out1 221 / 23 / 5, in0_out2 221 / 23 / 11,
    in0_out5 221 / 23 / 21, in5_out1 214 / 20 / 2, in5_out2 214 / 20 / 9, in5_out5 214 / 20 / 17.

## Inputs (frozen)

```inputs
35e095fff0734c0ceabdb100a9e54a95cae9aba363c3fc94f949a988b2bdef11  scripts/run_settlelit.py
009145b050e50f4394499e318737fe4ef86a00ef21136fb327658d4072c86829  scripts/run_settlehop.py
f81769a74f97074ea32d44ee927bd342272672157cebe81be9d39f8c8cd47e44  scripts/run_settlehop_exit.py
bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c  scripts/settlehop_rule.py
ca7b6583d28ea9512d08a469f93a3e687b214a16dd7a0167d4a491a883c0ae35  scripts/fetch_settlelit_1m.py
23c0a198737a90049460ba60a08f477ba07f4081b379fa7397709a6d8700db02  tests/test_settlelit.py
c1a56b86965711c6dd8316582392267a5a7a664bcf0241564005b8935f77cc43  tests/test_settlehop.py
85f95bbbb9c8bfbaee010e2187b9280032b9819db97e217ca3c8a271b4761c71  tests/test_settlehop_exit.py
d1e6d7f0c515b451986b2567c3bef5929f8289413a1ea0738a9054780bf8f71e  experiments/settlehop_pred_v1/results/hops.csv.gz
79d7d5dd081bd08272d2616d6b35c66a7402f018fb2aa96d9d60f7b286e67a00  experiments/settlehop_pred_v1/data_files.csv
aa34e5e4586bdc5f2adf4bb744cf1a6c78f6e72627565e950763465a2e4c94b3  experiments/settlehop_v1/symbols.csv
5d3cbd5538f7413eadf89fc773acc6cf240c8e215f30656b058934105f4db42d  docs/provenance/settlelit_1m.json
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926  docs/GATES.md
```

## Data
- **Lighter minutes:** `data/settlelit_1m/lighter/<Lighter symbol>/<T ms>.parquet`, one per hop.
  - Lighter's public 1-minute candles for bars opening in [T − 10 min, T + 10 min), keeping only bars that had closed
    when they were fetched (2026-10-28).
  - The columns are mapped as for the lab's hourly Lighter archive: o, h, l, c, v and V become open, high, low, close,
    volume and quote_volume.
- **Data identity:** `docs/provenance/settlelit_1m.json` lists the sha256 of every file. The run stops if the folder
  holds any other file, or if a file is missing or changed.
- **Lighter funding:** `data/lighter_hist/open/funding/<Lighter symbol>.parquet`, each file matching R354's
  `data_files.csv`. Rate at T is positive when longs pay. A missing settlement at T stops the run.
- **R354's frozen `hops.csv.gz`:**
  - the θ 0.3% Binance + Lighter book's 221 hops (coin, T, d, e, Lighter side cost);
  - the θ 0.5% book's 87, which mark the hops R356 read.
- **R353's `symbols.csv`** maps each Binance perp to its Lighter symbol.
- **Nothing reserved is read:** no 2020 row, no MEXC-only coin and no `reserved/` row.

## The rule
For each hop (coin, T, d; d = −1 means Binance's longs received the lump at T):
- **Position:** d on Lighter's perp, against the side that received Binance's lump: short when longs received it.
- **Entry:** the close of the last traded Lighter minute bar opening at or before T − j − 1 min, for j in {0, 5}. That
  is the last trade before T − j. A bar is traded when its close and its volume are above 0. With no traded bar
  from T − 10 min, the hop is not traded.
- **Exit:** the close of the last traded bar opening at or before T + x − 1 min, and not before the entry bar, for x in
  {1, 2, 5}. That is the last trade before T + x.
- **Funding:** the position holds Lighter's settlement at T: −d · rate(T). Nothing else settles before the exit.
- **Net:** d · (exit / entry − 1) − d · rate(T) − 2 · m · c, where c is R354's Lighter side cost for the hop (its
  trailing 24 h volume band: 26.67 / 7.27 / 4.17 / 1.09 / 0.51 / 0.26 bp), at m = 1, 2, 3.

## Costs (a side, 1x)
- **Lighter (fee 0):** the hop's band cost from R354, a $1k order's book cost from the October 2026 snapshots.
- **2x and 3x:** doubled and tripled.

## Trials
- **Entries** before T and before T − 5 min, **exits** at T + 1, 2 and 5 min: **6 trials**, all counted.
- **The primary enters before T and exits at T + 1,** fixed here before any return. It holds the one minute R356 named,
  and nothing before T beyond the settlement.

## Decision (the primary, on the 134 unseen hops only)
Per hop, with errors clustered by settlement time (CR1). **PASS** if all five hold:
1. the CR1 t of the 1x net is ≥ 2.0;
2. the 2x mean net is > 0;
3. the 1x mean net is > 0 in both halves of their calendar (two equal runs of days);
4. without the coin with the largest summed 1x net (all its hops removed), the 1x mean net is > 0;
5. GATES' trimmed mean of the 1x net (without the 10 best and 10 worst hops) is > 0.

**NULL** otherwise. A PASS is recorded as PARTIAL (gate 0).

**What each verdict earns:**
- **PASS:** a forward paper lane on Lighter under a new id, frozen before its first ticket. It reads the predicted
  rates point-in-time at T − 1 h, as R355 does, places a paper ticket before T, and scores it on Lighter's live book.
  No money moves: that needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **NULL:** the minute move after a deep settlement is not worth trading on Lighter at θ 0.3-0.5%.

**Power** (no Lighter return read; R362's Binance scalps had per-hop standard deviations of 35 to 132 bp):
- 134 hops at 127 settlement times. With a per-hop standard deviation of s, the t ≥ 2 bar needs a 1x mean net of about
  2s/√127.
- At s = 80 / 120 / 160 bp: +14.2 / +21.3 / +28.4 bp net. The round trip costs about 2 × 1.7 bp at R356's average
  band, and Lighter's hour is a few bp. Below that the test is a screen. The run reports the standard deviation.

## Reported (not decided on)
- **Every trial, on the unseen 134, the seen 87 and all 221:**
  - hops traded, the price and funding parts, gross, round-trip cost;
  - net 1x / 2x / 3x with the CR1 t and hit rate at each;
  - halves, best coin and without it, the trimmed and leave-two-coins-out means, the median, the standard deviation,
    bp a calendar day, and stale entry and exit bars.
- **Family:** how many of the 6 trials on the unseen hops reach a CR1 t of 2.39 (Bonferroni, one-sided 5% over 6) and
  of 2.0.
- **Read against** `registry.program_trials()`: 9,479,100 on this branch after R362, and 9,479,106 after this lane.

## Outputs
`experiments/settlelit_v1/results/`:
- `summary.json`: the verdict, the checks, the family counts and the input hashes;
- `trials.csv`: every trial's statistics on each subset;
- `hops.csv.gz`: every hop's price, funding and stale flags in every trial.

FINDINGS.md is written after the run, with 1x/2x/3x costs.

## Evidence lineage and admission
- **Method:** M267.
- **Parents:**
  - R354, for the hops and costs;
  - R356, for the minute path that motivates this lane;
  - R362 (NULL), the Binance seconds form, whose path on the decided hops was read before this freeze;
  - R355, the hop forward, which this lane leaves unchanged;
  - R348, for Lighter following Binance within a second.
- **Decision group:** this lane decides M267's Lighter-route form.
- **Samples:**
  - Decided: the 134 hops whose Lighter minutes nobody has read (R362 read their Binance seconds).
  - Seen: R356's 87.
  - Fresh: any later forward lane.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa…a926`.

## Known limits (written before the result)
- **A bar close is not a fill.** The close is the last trade, on either side of the spread. The band cost comes from
  October 2026 snapshots, not from the minutes around a settlement, when the book may be thin.
- **Lighter's settlement timing:** the run charges the settlement stamped at T to any position held across T. Whether
  Lighter has its own timing deviation is not checked.
- **The events are Binance's:** the rate is Binance's prediction an hour before T, as R354. A live lane must read it
  in time.
- **Concentration:** 130 of the 134 decided hops are shorts before deeply negative settlements.
- **The 87 seen hops** carry R356's known +94.6 bp minute move. They are reported only, so they cannot carry the
  decision.
- **The decided hops are not blind.** R362 read their Binance seconds before this freeze, so a PASS here says Lighter's
  closes carried a move already known on Binance. Only a forward lane on fresh settlements can test the route.
- **Margin and liquidation:** not modelled. A trade lasts at most 10 minutes.
