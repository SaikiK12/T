# PREREG: carrycost_hist_v2 (R500). What C14's real entries and exits cost on the recorded books, 2021-07..2026-09

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R500
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_carrycost_hist_v2.py` is the only writer of `experiments/carrycost_hist_v2/results/` and of the
    git-ignored `data/carrycost_hist_v2/`.
- **Date registered (UTC):** 2026-11-17

**Methods:** M547 (historical execution cost of a frozen carry book from public order-book archives). It feeds M546 and
the C14 decision. No new signal.
- **Paper only:** it reads public files; nothing in the code can place an order.

## Why a second lane
R499 (`experiments/carrycost_hist_v1`) asks the same question. Its fetcher kept every raw Gate hour file, and the
session's disk allowance ran out: about 1 GB was free for about 3 GB of raw hours. Its fetch was stopped after 137 Gate
hours and 91 Binance first hours, and **no cost was computed from them**. R499's frozen script cannot be changed, so
this lane takes over with two changes in plumbing and one in the Binance proxy:
1. **Each Gate hour is reduced at fetch time** to its per-side event costs (the same rules 2-3 below) and the raw file is
   dropped. R499's 137 raw hours are reduced the same way and then deleted (they are this session's own cache).
2. **Binance proxy: the first 15 minutes** of the month's first day, not 60. Streaming each first hour would have cost
   about 3 GB more of transfer and hours of time. Minimum 8 fillable samples of 15. R499's 91 Binance files (60 samples
   each, never costed) are truncated to their first 15.
3. Gate files are fetched before Binance files, so the exact-hour leg is complete first.

The cost rules, the book, the window, the sizes, the fees and the verdict thresholds are R499's.

## Question
R390's C14 book (binance + gate, 14-day lookback, 10%/yr entry, 20 slots, R275's v1 engine) charged a flat 7 bp a leg a
side. Each of its real entries and exits from 2021-07-01 to 2026-09-30 can instead be charged what the venues' books
asked at that hour, as recorded in public archives. After that, does the book still beat R275's 4.13%/yr T-bill hurdle
at $1,000 a leg?

The owner asked on 2026-11-17 for evidence in days, not months. This uses years of recorded books instead of waiting
for live fills.

## What the author has seen
- Everything listed in R499's PREREG ("What the author has seen"): one non-event Gate hour replayed (MTL 2023-06-01
  12:00), the format rows of MTL 2023-06-01 00:00, a 401-byte Tardis header of BTCUSDT, file sizes by range request.
- R499's interrupted fetch wrote 137 raw Gate hours and 91 Binance sample files to disk. Their names, counts and byte
  sizes were seen (about 254 MB). **No walk, spread or cost was computed from any of them.**
- **Other costs already known.**
  - R495 (PR #100) measured one live snapshot on 2026-11-15: a median walk of 7.17 bp at $1k on Binance and 17.12 bp
    on Gate, before fees.
  - The fee map (`research/intake/fee_map_20261116.md`) derived 18.4 bp a leg a side at $1k all-in from it.
- **The book's own archive results** are known: 1x +10.05%/yr over 2021-01-22..2026-09-30 (R275, R437); 9.79%/yr over
  this window at the flat 7 bp; the year split in R390's PREREG.
- **No historical execution cost for any C14 event was computed before this freeze.**

## Data
| Input | Source | What is used |
|---|---|---|
| Events | R275's v1 trade list, strategy `binance+gate L14d th10% K20` | entry and exit days, coin, long and short venue |
| Gate books | Gate public bulk archive (S3 `gateio-public-data`, no key): `futures_usdt/orderbooks/YYYYMM/<CONTRACT>-YYYYMMDD00.csv.gz` | the hour 00:00-01:00 UTC of each event day, reduced on arrival |
| Binance books | Tardis.dev free first-day-of-month files: `binance-futures/book_snapshot_25/YYYY/MM/01/<SYMBOL>.csv.gz` | the first 15 minutes (00:00-00:15 UTC) of the event month's first day only; the stream is closed after it |
| Gate multipliers | R499's file, fetched 2026-11-17 from Gate's public contract endpoint for all 432 contracts | coins per contract |
| Book daily nets | R437's v1 replay of the same book | gross per day and legs traded per day, recovered as gross = 2·net_1x − net_2x and legs = (net_1x − net_2x)·2K / 7 bp |

- **Licensing.** Raw Tardis files are never stored or committed; their terms bar redistribution. Only per-event costs,
  each an aggregate over 15 or 60 minutes, are written to the lane.
- **Transfer cap.** The fetcher stops at 4.5 GB transferred, under the owner's 5 GB threshold. Expected: about 3 GB.
- **Expected volume.** 2,544 events, 2,525 Gate hour files and 1,896 Binance coin-month first-day streams.

### Frozen inputs
| File | sha256 | After the freeze |
|---|---|---|
| `scripts/run_carrycost_hist_v2.py` | 51ea8d91012ae28dec9f2cd1feceec99215ef2f818dc93d5d3d07f6e038e6596 | fixed; `run` refuses to start if any row here changed |
| `experiments/xfund_v1/results/trades.csv` | c490bdbc062ce7ec930ed090e63c1d80a3b058091f28d6d7d5a7fe67cf9add94 | fixed |
| `experiments/xfund_v1/symbols.csv` | 78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0 | fixed |
| `experiments/carry_v2_audit_v1/results/daily.csv` | 3de6b7f29a3a3d786474b3e48444b004357c6cf2e78715e1d963f9ffe6f5fa08 | fixed |
| `experiments/carrycost_hist_v1/gate_multipliers.csv` | 651bbc885b37e3d50fa62b9c101e77e0645647adeebcc91ec117a8aabfcd2581 | fixed |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d | fixed (the engine behind the trade list) |

## Feature lineage and point-in-time availability
| Feature | Parent fields | Provider, units | Window | Available at the decision? | Coverage | Missing-value rule |
|---|---|---|---|---|---|---|
| Gate book at minute m | `set`/`make`/`take` rows (contracts) × multiplier | Gate archive, coins and USDT | 00:00 + m min, m = 0..59, of the event day | yes: the book the order would meet | contracts in the archive from 2021-07 | no file, or fewer than 30 fillable minutes: unmeasured |
| Binance book at minute m | top-25 snapshot rows | Tardis, coins and USDT | 00:00 + m min, m = 0..14, of the event **month's first day** | proxy: same coin and hour, another day of the month | from 2019-11 | no file, or fewer than 8 fillable minutes: unmeasured |
| Multiplier | `quanto_multiplier` | Gate, coins per contract | value on 2026-11-17 | latest-vintage: a past change would scale Gate depth, not its spread | 432 of 432 | none missing |

The book's decisions use only R275's frozen engine. This lane adds no decision feature, only a cost per executed leg.

## Rule
1. **Events.** Every entry and exit of the book with a day in 2021-07-01..2026-09-30.
   - At an entry, the long venue buys and the short venue sells; at an exit, the reverse.
   - The order is placed in the hour after 00:00 UTC of that day: the engine's daily close.
2. **Cost of an order of N dollars at one minute.**
   - Walk the book from the mid: (VWAP / mid − 1) × 1e4 for a buy, (1 − VWAP / mid) × 1e4 for a sell.
   - A minute is unfillable if its book is empty or crossed, or too thin for N.
3. **Event cost, primary (`median`).** The median over the fillable minutes, when at least 30 of the 60 (Gate) or 8 of
   the 15 (Binance) are fillable; otherwise the leg is unmeasured.
   - Reported, not deciding:
     - `snap0`: the 00:00 sample alone;
     - `best`: the lowest fillable minute, a patient taker's bound.
4. **All-in per leg.** Walk plus taker fee: Gate 7.5 bp, Binance 5 bp (base tier, as in the fee map).
5. **Imputation.** A leg that is unmeasured takes the median measured all-in cost of the same venue, size and
   aggregation in the same calendar year.
   - The count of imputed legs is reported, by venue.
   - The archive's final day closes 20 open pairs. Those closes are imputed the same way.
6. **Book net at measured cost.** For each day of R437's v1 replay in the window:
   - net = gross/(2K) − Σ over the day's events of (Gate all-in + Binance all-in)/1e4/(2K), with K = 20;
   - %/yr = mean daily net × 365 × 100.
7. **Sizes.** $250, $1,000 (primary) and $5,000 a leg.

## Verdict (primary cell: `median`, $1,000)
- **COST_OK:** the measured-cost net is at least 4.13%/yr, the R275 hurdle R437 used.
- **COST_BINDS:** it is above 0 but under 4.13%/yr.
- **COST_KILLS:** it is 0 or below.
- **INCOMPLETE** is appended when more than 20% of events miss a measured Gate leg, or more than 50% miss a measured
  Binance leg (the Binance leg is a proxy and the deeper venue). The number is still reported.

**Cost sensitivity.**
- The same net at 2x and 3x the measured walk, with the fee unchanged, is reported beside the verdict.
- So are the flat 1x / 2x / 3x nets of the same window.

**Also reported:**
- the mean and median all-in per leg per side, as a multiple of 7 bp;
- every year, and 2024-01..2026-09 alone;
- $250 and $5,000;
- the `snap0` and `best` variants.

**What the verdict means.**
- COST_OK says the book's archive return survives the recorded books at $1k taker execution.
- It says nothing on fills of resting orders (R498), funding actually credited, transfers or outages.
- The Binance leg is a proxy day and a 15-minute window.

## Null and multiplicity
- **No null.** This is a measurement of one frozen book under fixed cost rules. Registry trials: 0, as for the cost
  reads R456 and R497 and for R499, which this lane supersedes before any cost was read. The variants above are
  reported, never chosen among.
- Program trials so far: 9,785,313.
- The book's own selection (C14 among R275's books) is unchanged by this lane. Its return stays read against that
  selection, and its forward verdict stays R390's.

## Evidence lineage
- **Parents:**
  - R499 (same question; superseded for disk before any cost);
  - R275 (book and trades);
  - R437 (daily nets);
  - R390 (the forward book);
  - R495 and the fee map (one live cost snapshot);
  - R497 and R498 (Gate maker route).
- **One decision this feeds:** whether C14 is executable at $1k with taker orders. That sets the order type and the size
  in the small-stake plan.
- **Fresh data:** historical order books never read by the lab. The returns are the archive's, already seen.
- **docs/GATES.md** sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - This is a gate 2 (execution) input on history.
  - It does not replace gate 1.

## Not checked before the freeze
- **Gate multiplier history.** Whether any C14 contract's multiplier changed between 2021 and 2026. A change would
  scale Gate depth, not its spread.
- **Fee tiers.** Whether Gate's or Binance's base taker fee differed in past years.
- **Delayed fills.** Whether the 00:00-01:00 hour is representative of a real order a few minutes late.
- **Binance window.** Whether 00:00-00:15 on the 1st is representative of the event day's 00:00-01:00.
