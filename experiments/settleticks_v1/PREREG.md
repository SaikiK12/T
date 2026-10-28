# PREREG: settleticks_v1 (R362). The seconds after a deep Binance funding settlement

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R362
- **Method:** M267 (settlement-window cross-venue carry), its seconds form: the capture crowd's exit after T, traded
  against.
  - R354 (PASS at gate 0, recorded PARTIAL) found the hop; R356 (PASS at gate 0, recorded PARTIAL) found its whole
    price giveback inside the first minute after T. R355 runs the hop forward on paper, unchanged by this lane.
- **Owner (single writer):** the Claude session that froze it. R362 was claimed on issue #7 (comment 6471157448)
  before the freeze. R357-R361 are Codex's.
- **Date registered (UTC):** 2026-10-28
- **Code:** `scripts/run_settleticks.py`, tested by `tests/test_settleticks.py` (13 tests on invented ticks and
  files).
  - It imports R353's frozen runner `scripts/run_settlehop.py` unchanged for `frozen_inputs`, the log and the day
    length, and R355's frozen rule `scripts/settlehop_rule.py` unchanged for the cluster-robust t, the trimmed mean and
    the leave-two-coins-out mean.
  - The runner calls `verify()` on this file first and checks every input below. Before and after the run, it checks
    that `data/settle_ticks` holds exactly the files listed in `docs/provenance/settle_ticks.json`, each with its
    listed sha256.
- **Gate:** 0. R354's hops have been read at the hour, and R356's 87 at the minute. No lane has read these ticks.
- **Execution mode:** API (two taker orders within 5 minutes after T). Not placeable by hand.

## Why this lane
- **The owner (2026-10-28, 13:42 UTC):** "We need a hft trading with good pnl troughout the day". Market making and
  latency arbitrage need colocation and rebates the owner does not have (R348: Lighter's makers close a gap to
  Binance within a second). A flow that arrives at a known time and lasts longer than our delay is within reach.
- **R356's minute path** (87 hops, in the hop's favour, from the entry an hour before T):
  - Binance's part fell from −62.1 bp at the last trade before T to −194.3 at the close of T + 1 min, then to −214.1 at
    T + 5 and −337.5 at T + 60: the coin kept falling on Binance after the settlement.
  - The hedged price fell 37.6 bp in that first minute and stayed flat after.
- **The question:** how much of the post-settlement move is still there when a position against the receiving side
  can be opened safely? Binance's funding FAQ: "There is a 15-second deviation in the actual funding fee transaction
  time. For example, when you open a position at 08:00:05 (UTC), the funding fee could still apply". A position
  opened against the receiving side before T + 15 s may pay the whole lump (R354's e: 0.3% to 6%). So the decided
  scalp enters at T + 15 s.

## What the author has seen
- **R354 and R356 in full,** including R356's minute path above. The Binance part of that path is the coin's move, not
  this lane's statistic: no tick, no price inside a minute and no return after T + 15 s has been computed.
- **Binance's settlement stamps:** the funding history stamps each Binance settlement 0-26 ms after the hour (PIPPINUSDT,
  5,023 settlements, checked while designing this lane). The 15-second deviation is in the fee's transaction, not the
  stamp.
- **The ticks,** fetched by `scripts/fetch_settle_ticks.py`, which prints counts only:
  - 139 Binance coin-days (1.23 GB of zips), each checked against its published sha256 and streamed through
    memory;
  - 221 windows kept (75.4 MB), recorded 2026-10-28 14:19 UTC;
  - trades a window: min 1,354, median 16,866, max 224,804;
  - every window has trades in [T, T + 5 min). The longest trade-free gap in [T − 1 min, T + 5 min) has a median of
    1.5 s, a 90th percentile of 3.8 s and a maximum of 20.1 s.
- **Plumbing** (`--plumbing`; counts only):
  - 221 hops on 34 coins at 204 settlement times: 87 in R356's book, 134 outside it (at 127 times).
  - Directions: 216 short scalps (d = −1), 5 long. Funding intervals: 215 hops on 4 h, 6 on 8 h.
  - Every one of the 7 scalps finds its entry trade in all 221 hops. Exits on the other side: 1 at T + 30 s and 1 at
    T + 300 s. Stale exits: none.

## Inputs (frozen)

```inputs
937c5e22de386e8cf98d203263628a2f82fe405bd8f213f8c8e07f38bad0e148  scripts/run_settleticks.py
009145b050e50f4394499e318737fe4ef86a00ef21136fb327658d4072c86829  scripts/run_settlehop.py
bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c  scripts/settlehop_rule.py
20a9c9d5e87efdf90f8c2dcc0cd4c2496f7a199222b99e686983d107b221be30  scripts/fetch_settle_ticks.py
d0a7b716f9182f305cf8d6bdf1606085d1e271f5b3a729994cef856d21d1e61c  tests/test_settleticks.py
c1a56b86965711c6dd8316582392267a5a7a664bcf0241564005b8935f77cc43  tests/test_settlehop.py
d1e6d7f0c515b451986b2567c3bef5929f8289413a1ea0738a9054780bf8f71e  experiments/settlehop_pred_v1/results/hops.csv.gz
67579d8645d08a1b8266ee900db31a0769eb88f16c56b9e4868393ffa3aa761d  docs/provenance/settle_ticks.json
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926  docs/GATES.md
```

## Data
- **Ticks:** `data/settle_ticks/binance/<Binance perp>/<T ms>.parquet`, one per hop.
  - The source is data.binance.vision's USD-M daily aggTrades, each zip checked against its published `.CHECKSUM`
    sha256 and kept only in memory.
  - Columns: t (transact time, ms), price, qty, buyer_maker (True when the seller took liquidity), agg_id.
  - Rows: every aggregated trade in [T − 10 min, T + 15 min).
- **Data identity:** `docs/provenance/settle_ticks.json` lists the sha256 of every kept file and of every zip read.
  The run stops if the folder holds any other file, or if a file is missing or changed.
- **R354's frozen `hops.csv.gz`:** the θ 0.3% Binance + Lighter book's 221 hops (coin, T, d, e, f_hat, interval_h),
  and the θ 0.5% book's 87, which mark the hops R356 read.
- **Nothing reserved is read:** no 2020 row, no MEXC-only coin and no `reserved/` row.

## The rule
For each of R354's 221 θ 0.3% hops (coin, T, d; d = −1 means Binance's longs received the lump at T):
- **Position:** d on Binance's perp, against the side that received the lump: short when longs received it.
- **Entry at T + 15 s:** the price of the first trade at or after T + 15 s whose taker traded on the entry's side (a
  sell takes the first seller-initiated trade, a buy the first buyer-initiated one), before the exit time. With no
  such trade before the exit time, the hop is not traded.
- **Exit at T + x,** for x in {30, 60, 120, 300} s: the first trade at or after T + x on the exit's side within 5 s;
  else the first trade of either side within 60 s (flagged); else the last trade before T + x (flagged).
- **Gross:** d · (exit price / entry price − 1). **Net:** gross − 2 · m · 8.5 bp at cost m = 1, 2, 3.
- **Funding:** none. The position opens after Binance's stated deviation and closes before the next settlement
  (at least an hour later).

## Costs (a side, 1x)
- **Binance API:** 8.5 bp, R354's charge (taker fee and slippage). The fills are side-specific trade prices, so part of
  the spread is charged twice: the 1x cost is conservative.
- **2x and 3x:** 17 and 25.5 bp a side.

## Trials
- **Decided exits:** T + 30, 60, 120 and 300 s, each entered at T + 15 s.
- **Reported only:** entries at T + 1, 2 and 5 s, closed at T + 60. They sit inside Binance's 15-second deviation, so a
  real position may pay the lump; they show what waiting costs.
- **7 trials,** all counted.
- **The primary is entry T + 15 s, exit T + 60 s,** fixed here before any return. It spans the rest of the minute
  in which R356 saw the giveback.

## Decision (the primary only)
Per hop, over every traded hop, with errors clustered by settlement time (CR1). **PASS** if all five hold:
1. the CR1 t of the 1x net is ≥ 2.0;
2. the 2x mean net is > 0;
3. the 1x mean net is > 0 in both halves of the calendar (two equal runs of days);
4. without the coin with the largest summed 1x net (all its hops removed), the 1x mean net is > 0;
5. the 1x mean net is > 0 on the 134 hops outside R356's book, whose post-settlement path nobody has read.

**NULL** otherwise. A PASS is recorded as PARTIAL (gate 0).

**What each verdict earns:**
- **PASS:** a settlement tape recorder (books and trades from T − 2 min to T + 5 min on MEXC, Lighter and Binance
  around each deep settlement), then a forward paper scalp lane on the cheapest venue under a new id, frozen before
  its first ticket. No money moves: that needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **NULL:** no seconds scalp on Binance after the deviation. The reported early entries and the path still say where
  the move went.

**Power** (no return read):
- 221 hops at 204 settlement times. With a per-hop standard deviation of s, the CR1 standard error is about
  s/√204; the t ≥ 2 bar needs a 1x mean net of about 2s/√204.
- At s = 60 / 80 / 120 bp: a net of +8.4 / +11.2 / +16.8 bp, so a gross of +25.4 / +28.2 / +33.8 bp. Below that the
  test is a screen. The run reports the standard deviation it finds.

## Reported (not decided on)
- **Every scalp:** hops traded, gross mean and median, net 1x/2x/3x, CR1 t and hit rate at each, halves, best coin,
  without it, the 134 unseen hops and the 87 seen, GATES' trimmed mean, the leave-two-coins-out mean, the standard
  deviation, bp a calendar day, and the flagged exits.
- **Family:** how many of the 4 decided exits reach a CR1 t of 2.24 (Bonferroni, one-sided 5% over 4) and of 2.0.
- **The path** (`results/path.csv`): at 30 points from T − 600 s to T + 899 s, the mean and median of
  d · (price at T + s / last trade before T − 1), for all hops, the unseen and the seen, and the share above 0.
- **The flow** (`results/flow.csv`): taker quote volume in the scalp's direction, per second in 11 ranges from T − 60 s
  to T + 900 s, in units of the hop's mean quote volume a second over [T − 600 s, T − 60 s).
- **Read against** `registry.program_trials()`: 9,479,093 on this branch before this lane and 9,479,100 after it
  (9,479,117 counting #56's R338-R346; R357-R361 are engineering rounds on #56).

## Outputs
`experiments/settleticks_v1/results/`:
- `summary.json`: the verdict, the checks, the family counts, the counts and the input hashes;
- `scalps.csv`: every scalp's statistics;
- `hops.csv.gz`: every traded hop's scalp: gross, entry and exit times after T, flag;
- `path.csv` and `flow.csv`.

FINDINGS.md is written after the run, with 1x/2x/3x costs.

## Evidence lineage and admission
- **Method:** M267. **Parents:** R354 (the hops), R356 (the minute path), R353, R355 (forward, unchanged), R348 (the
  speed limit on Lighter).
- **Decision group:** this lane decides M267's seconds scalp on Binance.
- **Samples:** seen: R354's hops at the hour and R356's 87 at the minute (gate 0). Fresh: the forward tape of any
  later lane.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa…a926`.

## Known limits (written before the result)
- **A trade print is not a fill.** The next trade on the entry's side approximates the touch; a real order also pays
  the depth it walks. Books in the minutes after a settlement were not recorded, and may be thin.
- **The funding deviation:** Binance states 15 seconds. Whether a later position ever pays the lump is not checked.
- **Venue:** these are Binance prices. MEXC and Lighter follow Binance within about a second (R348), but their own
  books and settlements are not measured here.
- **In-sample:** R354's hops at gate 0; check 5 asks the 134 unseen hops to agree.
- **Concentration:** 216 of the 221 hops are short scalps before deeply negative settlements, on 34 coins.
- **Margin and liquidation:** not modelled. A scalp lasts at most 5 minutes.
