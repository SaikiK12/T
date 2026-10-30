# PREREG: settlehop_exit_v1 (R356). R354's settlement hops closed minutes after the settlement

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R356
- **Method:** M267 (settlement-window cross-venue carry), its exit-time form.
  - R353 tested the hop on the last settled rate (NULL). R354 tested it on a predicted rate (PASS at gate 0,
    recorded PARTIAL). R355 runs R354's hop forward on paper, unchanged by this lane.
- **Owner (single writer):** the Claude session that froze it. R356 was claimed on issue #7 (comment 6457871518)
  before the freeze.
- **Date registered (UTC):** 2026-10-28
- **Code:** `scripts/run_settlehop_exit.py`, tested by `tests/test_settlehop_exit.py` (14 tests on invented minute bars
  and files).
  - It imports R353's frozen runner `scripts/run_settlehop.py` unchanged for the book, the net, the description and
    R354's four checks. R353's 17 tests cover that code.
  - It imports R355's frozen rule `scripts/settlehop_rule.py` unchanged for the cluster-robust t, the trimmed mean and
    the leave-two-coins-out mean.
  - The runner calls `verify()` on this file first and checks every input below. Before and after the run, it checks
    that `data/settlehop_1m` holds exactly the 164 files listed in `docs/provenance/settlehop_1m.json`, each with its
    listed sha256.
- **Gate:** 0. R354's hops, its hourly price path and its "closed at T" bound have been read. No lane has read these
  minute bars.
- **Execution mode:** API on both venues, as R354: two orders an hour before T and two at T + k. At k = 5 the two exits
  can also be placed by hand; at k = 1 and 2 only an API can place them in time.

## Why this lane
- **The owner's format:** a short-hold perp trade, not a long hold.
- **R354's hourly path** (primary book, in the hop's favour, from the entry close):
  - The hedged price was +25.0 bp at T and −19.8 bp at T + 1 h, so the hour after T gave back 43.5 bp a hop on
    average.
  - Lighter's two hourly settlements cost 42.4 bp a hop. The one at T + 1 h is about half of that.
- **The bound:** closed at T, the primary would net +89.6 bp a hop, against +30.9 held to T + 1 h. No exit can get
  both the price before the payment and the payment.
- **The question:** how fast does the giveback come after T? If the crowd that bought the paying perp for the lump
  sells it over several minutes, an exit a few minutes after T keeps part of the pre-payment price and the whole lump.
  If it sells in the first minute, a quick exit only saves Lighter's second hour. Only the minute path can say.

## What the author has seen
- **R354 in full,** including its after-run tables. Of its 87 primary hops, 86 are long Binance and short Lighter
  before a deeply negative settlement, and 7 settled at Binance's −2% floor and then received a second lump at T + 1 h
  after Binance switched those coins to hourly settlements.
- **R354's published per-hop columns,** for the power statement below:
  - **The funding part of every early exit's gain is already known:** +15.2 bp a hop on average. That is Lighter's
    T + 1 h settlement no longer paid, net of the 7 floor hops' second Binance lumps no longer received.
  - **The price part at T** (R354's price0 − price) is +43.5 bp a hop.
  - **The gain at T** (the bound) has a standard deviation of 66.4 bp a hop and a CR1 standard error of 8.4 bp over
    80 settlement times.
- **The minute data,** fetched by `scripts/fetch_settlehop_1m.py`, which prints counts only:
  - 77 Binance coin-days, each zip checked against its published sha256;
  - 87 Lighter windows of 181 bars each.
- **Plumbing** (`--plumbing`; counts only):
  - **Hops:** 87 hops on 26 coins at 80 settlement times. Both legs' entry minute was found in all 87.
  - **Exits on an untraded minute** (count of hops, by leg):

    | Exit | T | T + 1 | T + 2 | T + 5 | T + 15 | T + 30 | T + 60 |
    |---|---|---|---|---|---|---|---|
    | Binance | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
    | Lighter | 5 | 1 | 2 | 6 | 11 | 7 | 9 |

  - **Parity:** rebuilt from the minute bars, the exit at T + 60 equals R354's price in 87 of 87 hops, and the exit at
    T equals R354's price0 in 87 of 87, within 1e-6.
- **Not computed:** any price at T + 1 to T + 59 minutes, and any return of a hop closed there.

## Inputs (frozen)

```inputs
f81769a74f97074ea32d44ee927bd342272672157cebe81be9d39f8c8cd47e44  scripts/run_settlehop_exit.py
009145b050e50f4394499e318737fe4ef86a00ef21136fb327658d4072c86829  scripts/run_settlehop.py
bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c  scripts/settlehop_rule.py
2827686d38b2e90cd9d24bbfca05d15a666771a7ad476b6db0d582dae44c2730  scripts/fetch_settlehop_1m.py
85f95bbbb9c8bfbaee010e2187b9280032b9819db97e217ca3c8a271b4761c71  tests/test_settlehop_exit.py
c1a56b86965711c6dd8316582392267a5a7a664bcf0241564005b8935f77cc43  tests/test_settlehop.py
d1e6d7f0c515b451986b2567c3bef5929f8289413a1ea0738a9054780bf8f71e  experiments/settlehop_pred_v1/results/hops.csv.gz
f0bcff9a2cca809f8d62a4df74b4fbb6bc5cfadb75fa549fa646cb87d559f1a9  experiments/settlehop_pred_v1/results/daily.csv.gz
aa34e5e4586bdc5f2adf4bb744cf1a6c78f6e72627565e950763465a2e4c94b3  experiments/settlehop_v1/symbols.csv
968b3a1b805bf72729282c21623179651d7e99c842303d30ae8cfb4b931631f2  docs/provenance/settlehop_1m.json
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926  docs/GATES.md
```

## Data
- **Binance:** `data/settlehop_1m/binance/<Binance perp>/<YYYY-MM-DD>.parquet`.
  - The source is data.binance.vision's USD-M daily 1-minute klines, each zip checked against its published `.CHECKSUM`
    sha256.
  - Columns: t (open time, ms), open, high, low, close, volume, quote_volume, count.
  - 77 coin-days: every UTC day that a window [T − 2 h, T + 1 h + 1 min) touches.
- **Lighter:** `data/settlehop_1m/lighter/<Lighter symbol>/<T ms>.parquet`.
  - Lighter's public 1-minute candles for [T − 2 h, T + 1 h + 1 min), keeping only bars that had closed when fetched
    (2026-10-28).
  - The columns are mapped as for the lab's hourly Lighter archive: o, h, l, c, v and V become open, high, low, close,
    volume and quote_volume.
- **Data identity:** `docs/provenance/settlehop_1m.json` lists the sha256 of all 164 files (6.6 MB) and the 77 zips.
  The run stops if the folder holds any other file, or if a file is missing or changed.
- **R354's frozen outputs:**
  - `hops.csv.gz`: the 87 primary hops with their coin, T, direction d, e, costs, price, funding, price0 and fund0;
  - `daily.csv.gz`: the primary book's calendar, 622 days from 2025-01-17 to 2026-09-30.
- **R353's `symbols.csv`** maps each Binance perp to its Lighter symbol.
- **Nothing reserved is read:** no 2020 row, no MEXC-only coin and no `reserved/` row.

## The rule
For each of R354's 87 primary hops (coin, T, d; d = +1 means short Binance and long Lighter):
- **Entry: R354's, unchanged.** Each leg is entered at the close of its last traded 1-minute bar opening in
  [T − 2 h, T − 61 min]. That is the close of the hourly bar ending at T − 1 h.
- **Exit at T + k,** for k in {1, 2, 5, 15, 30} minutes:
  - each leg at the close of its last traded minute bar opening at or before T + k − 1 min, and not before its entry
    bar;
  - so the exit price is the leg's last trade before T + k;
  - a bar is traded when its close is above 0 and its volume is above 0.
- **Funding at T + k:** the hop keeps the settlements in (T − 1 h, T], which is R354's fund0: Binance's lump at T and
  Lighter's settlement at T. It receives and pays nothing at T + 1 h.
- **Control (k = 60):** R354's own hop, with its price and its funding over (T − 1 h, T + 1 h].
- **Net:** d·(ret_Lighter − ret_Binance) + funding − 2·(c_Binance + c_Lighter), with R354's costs for each hop.
- **Parity:** the run stops unless, in all 87 hops and within 1e-6, the minute rebuild of the exit at T + 60 gives
  R354's price and the exit at T gives R354's price0.

## Costs (a side, 1x): R354's, per hop
- **Binance API:** 8.5 bp.
- **Lighter (fee 0):** the hop's trailing 24 h volume band. In these hops that averaged 1.73 bp a side.
- **Round trip:** four sides, 20.45 bp on average.
- **2x and 3x:** every cost doubled and tripled.
- **The paired gain is cost-free:** the cost is the same at every exit, so it cancels.

## Books and trials
- **Exits:** k = 1, 2, 5, 15 and 30 minutes, so **5 trials**. The control is R354's own result, not a trial.
- **Each exit's book is R354's:**
  - 5 equal slots, with a hop's net counted on the UTC day of T;
  - R354's calendar of 622 days, with idle days at 0;
  - halves are two equal runs of days.
- **The primary is k = 5,** fixed here before any return: an exit that two orders can make by hand.

## Decision (k = 5 only)
**PASS** if all five hold:
1. the Newey-West t (lag 5) of the 1x daily net is ≥ 2.0;
2. the 2x daily mean is > 0;
3. the 1x daily mean is > 0 in both halves;
4. without the coin with the largest summed 1x net (all its hops removed), the 1x daily mean is > 0;
5. the paired gain over the control, per hop, has a CR1 t of at least 2.0, with errors clustered by settlement time.
   The gain is (price at T + 5 + fund0) − (price + fund).

Checks 1-4 are R354's four checks, on the k = 5 book. **NULL** otherwise. A PASS is recorded as PARTIAL (gate 0).

**What each verdict earns:**
- **PASS:**
  - A forward paper lane with the quick exit, under a new id, frozen before its first day. It runs on MEXC + Lighter
    as R355 does, and its PREREG says how its decision relates to R355's.
  - R355 is frozen and keeps running unchanged.
  - No money moves. That needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **NULL:** the hop's exit stays at T + 1 h, and R355 is unchanged.

**Power** (from R354's published columns, before any minute return):
- **The gain has two parts:**
  - the funding part, +15.2 bp a hop, which is already known;
  - the price part, which is the question. It is 0 if the whole giveback is over by T + 5, and up to +43.5 bp if none
    of it has come.
- **Its noise:** the gain at T has a CR1 standard error of 8.4 bp. Taking that as the k = 5 gain's (the minutes after T
  add some noise):
  - the t ≥ 2 bar needs a mean gain of about +17 bp;
  - power is 47 / 67 / 84 / 94% at +15 / +20 / +25 / +30 bp (a cluster bootstrap of R354's gain at T, 4,000 draws).
- **So 80% power needs a true gain of about +24 bp:** about 9 bp of price kept at T + 5, on top of the funding part.
  Below that the test is a screen.

## Reported (not decided on)
- **Every exit** (k = 1, 2, 5, 15, 30 and 60):
  - all of R354's statistics: hops, funding and price parts, gross, cost, net 1x/2x/3x, hit, trimmed net, daily means
    and t, halves, best coin, stale exits;
  - GATES' trimmed mean (without the 10 best and 10 worst hops), the leave-two-coins-out mean, and the per-hop CR1 t;
  - the funding kept, and the paired gain: mean, CR1 t, hit, and its price and funding parts.
- **Family:**
  - how many of the 5 exits reach a gain t of 2.33 (Bonferroni, one-sided 5% over 5) and of 2.0;
  - how many pass R354's four checks.
- **The minute path** (`results/path.csv`): from T − 60 to T + 60 minutes,
  - the mean and median hedged price;
  - Binance's and Lighter's parts;
  - the stale count of each leg at each minute.
- **After the run, from the outputs:** the gain at each exit for the 7 floor hops and the other 80, by year, and
  without the 10 best days.
- **Read against** `registry.program_trials()`: 9,479,088 on this branch before this lane and 9,479,093 after it. That
  is 9,479,110 after it counting #56's R338-R346.

## Outputs
`experiments/settlehop_exit_v1/results/`:
- `summary.json`: the verdict, the checks, the family counts, parity, the costs and the input hashes;
- `books.csv`: every exit's statistics;
- `hops.csv.gz`: every hop's price, stale flag and 1x net at every exit, next to R354's columns;
- `daily.csv.gz`: each exit's daily net at 1x/2x/3x;
- `path.csv`: the minute path.

FINDINGS.md is written after the run, with 1x/2x/3x costs.

## Evidence lineage and admission
- **Method:** M267.
- **Parents:**
  - R354, which supplies the hops and their hourly result;
  - R353, the same hop on the last settled rate;
  - R355, the forward lane on MEXC + Lighter, which this lane leaves unchanged.
- **Decision group:** this lane decides M267's exit time on R354's hops.
- **Samples:**
  - seen: R354's hops and their hourly path (gate 0);
  - fresh: R355's forward hops, and the hops of any future quick-exit forward lane.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa…a926`.

## Known limits (written before the result)
- **Fills right after a settlement:**
  - Each leg exits at its last trade before T + k, with both legs on the same minute, at R354's flat costs.
  - The books in the first minutes after a settlement may be thinner and wider than the October 2026 snapshots
    behind Lighter's bands. That is not measured. The 2x and 3x costs are reported.
- **A trade price is not a fill:** a minute's close can sit on either side of the spread.
- **Sources:** Lighter's candles come from its API today, and Binance's from its archive. Both legs exit on the same
  minute.
- **In-sample:** these are R354's 87 hops at gate 0. A pass is in-sample on prices R354 read at the hour level.
- **Forking paths:** picking the best of 5 exits after seeing them would be one. The primary is fixed at k = 5 here,
  and the others are reported.
- **Funding timing:**
  - A hop closed at T + k keeps the lump at T only if it is open at the settlement.
  - Binance stamps its settlements within milliseconds of T, and Lighter charges positions open at its hourly
    settlement.
  - Neither venue's settlement is checked to the second.
- **Margin and liquidation:** as R354, not modelled.
- **Venue:** the hops are Binance + Lighter, R354's primary. A pass reaches MEXC only through a new forward lane.
