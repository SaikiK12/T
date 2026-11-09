# PREREG: rawlead_v1, the sub-second lead of Binance USDT perps over USDC perps on the raw tape (BTC, ETH), gate 0

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R431
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); no runtime file of another lane is written
- **Date registered (UTC):** 2026-11-09
- **Methods:** M430 (sub-second touch transition) and M431 (latency frontier), on the raw tape recorded for them.

The owner asked on 2026-11-09 for deeper work on market microstructure and HFT problems. The raw tape exists only in
this container (162 files / 809 MB unarchived, docs/LEADS.md), so it is measured now or never.

## Question
When Binance's USDT perp book moves away from its USDC perp book by at least 2 bp, does a taker who buys or sells
the USDC book from this container, after its own measured delay, earn more than the 4 bp a fill taker fee?

The lane also maps the frontier behind that answer. It records how many ms the USDC book takes to catch up, and how
the gross edge decays with delay. And it measures what the same moments cost a resting USDC maker.

## Universe
- **Instruments:** BTCUSDT, BTCUSDC, ETHUSDT, ETHUSDC Binance USD-M perpetuals. USDT is the source, USDC the target.
- **Days:** 2026-10-29 (13:00-17:00 UTC, 4.0 h), 2026-10-30 (13:00-15:46, 2.76 h), 2026-11-05 (15:08-16:16, 1.13 h).
  - These are every merged raw-tape day.
  - The recorder kept market rows only between 13:00 and 17:00 UTC, and only while the chat container was awake.
- **Not used:** Bybit (M430's confirmation feature), Kraken, RPI depth, liquidations, M434's quote-FX residual and
  M438's intra-second phase. They stay untested.

## Data
`scripts/record_raw.py` wrote one row per websocket message, in arrival order, into gitignored `data/rawtape/`.
- **Books:** `bbo/<sym>/<day>.parquet` from Binance `bookTicker` on one connection
  (`wss://fstream.binance.com/public/stream`, connection 0).
  - `t`: local wall-clock receive time, µs. `off`: wall minus monotonic.
  - `T`: Binance matching-engine time, ms. `dE` = E − T, where E is the publication time.
  - `bid` and `sp`: price and spread in hundredths. `bq` and `aq`: sizes in thousandths of a coin.
- **Trades:** `trade/<sym>/<day>.parquet` from `aggTrade` (connection 1). Only the USDC books' trades are read.
  - `T` (ms), price `p` (hundredths), size `q` (thousandths) and `m` (1 = buyer is the maker).
- **Pings:** `rtt/all/<day>.parquet`, an application ping every 30 s per connection.
- **Provenance:** `docs/provenance/rawtape.json`. Every input below is checked by sha256 before the run, including the
  runner itself.

```inputs
1862a8c2790ce236122c1613523bc39ec9236ebe6ea6af7b2c77ad5f1a39cc12 data/rawtape/bbo/BTCUSDT/2026-10-29.parquet
688771a34b99d260cbecf5e5dbbff2cecd7bb9c4b705fe236122980dc37f2bf7 data/rawtape/bbo/BTCUSDT/2026-10-30.parquet
cf184cca323e5d2fba3b5768900b10884394226416a5ee6936ff6bfb2178ae26 data/rawtape/bbo/BTCUSDT/2026-11-05.parquet
b2b0217ac5273728d838565454e39528c5778433e52c01d0b45d23172f333a72 data/rawtape/bbo/BTCUSDC/2026-10-29.parquet
e0a974f57cb7c860439b9a52441f7b203f07e7fb43682369887b2238c26ba82c data/rawtape/bbo/BTCUSDC/2026-10-30.parquet
fdd933315113c9927752aa09b77536f7dffa0972f8a4b1cb90853d4e07991773 data/rawtape/bbo/BTCUSDC/2026-11-05.parquet
53a17bae28d0ade4a49d6c6bdfce16aded6d5d9356c70a94fec2c830c5a8c120 data/rawtape/bbo/ETHUSDT/2026-10-29.parquet
c831ecec2316a6b2c5281491ab901f1bbd7dad6e03fceb090614104ec30c6a96 data/rawtape/bbo/ETHUSDT/2026-10-30.parquet
736f716928750a3be7db87cd15dfc13c97c6af630235fd26f49eb1edbbc6948c data/rawtape/bbo/ETHUSDT/2026-11-05.parquet
e27afdd2cea29335ee588762d37f3e307a72e5c88c5839f58404af7cd0c77ee6 data/rawtape/bbo/ETHUSDC/2026-10-29.parquet
3151087bec98fc8937abc525aebb1313e27c364a9982c8cb0b4144c842e2ca21 data/rawtape/bbo/ETHUSDC/2026-10-30.parquet
c5e3bac8ad9f006555dccab390ad8f51eea968ad19ee364f8d69b48525cf9bbd data/rawtape/bbo/ETHUSDC/2026-11-05.parquet
1dfd4f738e1c5eb8ebafff0df689c4483b204640fd582812edc6826c21397ff0 data/rawtape/trade/BTCUSDC/2026-10-29.parquet
b308b1e23c8607e0de5c254c8fe88b3221d0b66c899ce3f23b30389f348f3988 data/rawtape/trade/BTCUSDC/2026-10-30.parquet
5b4992353e286c1044d0628b522af72e9b82e63845ca36fb4ef9d244ac23e357 data/rawtape/trade/BTCUSDC/2026-11-05.parquet
0082942bdf96cde393be19e0b78db38a36a2ed83ad70efacf03b1d9f05e9fdf3 data/rawtape/trade/ETHUSDC/2026-10-29.parquet
e20daed36c2a6879c974ea43a97d6dd44250ffa6c987f6127b4d381a60381851 data/rawtape/trade/ETHUSDC/2026-10-30.parquet
15dc240615e79650ff4c04b9a64de052df9ea948eb224a6b481ef64bb6f2707f data/rawtape/trade/ETHUSDC/2026-11-05.parquet
c302780e81672879c77b7a380e2ae78b8c7801022013a22f30e81d62ddba39a1 data/rawtape/rtt/all/2026-10-29.parquet
918f19d81b8fbcff8e939718d03e52db1e83bbe09e6c94444f479286eb419a4d data/rawtape/rtt/all/2026-10-30.parquet
8217f6a8351ec261f9dc0cdf157b803176374b5deee56f11c781744f70b8cb30 data/rawtape/rtt/all/2026-11-05.parquet
087618d502bf1a3a51c6c35fd355f4622a0bf28f85f91fb39fbbbf50292ee3c6 scripts/run_rawlead.py
```

## Two clocks
Both books are on Binance, so their stamps share one clock. The local clock is used only for what this machine knew
and when.
- **Local clock.** The receive time `t − off` orders detection: an event is a row this machine read.
- **Binance's clock.** Everything after the decision uses T or E.
  - The order's arrival at the matching engine.
  - The USDC book it meets, as of T ≤ arrival.
  - The exit, and the Part A and Part C paths.
- **Feed lag.** Lag = local wall ms − E. It contains the network path, local processing and the clock offset.
- **Floor.** Per wall-clock minute, the 0.1% quantile of lag over all four books. It stands for a row that did not
  queue. A minute with fewer than 200 rows has no floor, and its events are dropped.
- **Queue.** A row's queue is its lag minus its minute's floor.
- **Arrival.** An order sent when the trigger row was read reaches the engine at X = E + q + RTT.
  - Here q is the decision delay defined under the Rule, and RTT is the day's median ping.
  - This follows from lag = d_in + c, floor = d_in,base + c and RTT = d_in,base + d_out.
  - The order gateway's own extra delay is unknown. The delay grid covers it.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| basis b = trailing median of log(mid USDT / mid USDC) | bid, sp of both books | Binance bookTicker, log units | 60 one-second grid points of local time before the event's second, at least 30 valid | computed at each local second | yes: shifted one second | forward-captured tape | a grid point with a book silent > 1 s (USDT) or > 5 s (USDC) is NaN |
| fair USDC mid f = log mid USDT − b | USDT bid, sp; b | same | the trigger row | received at t | yes | same | NaN basis: no event |
| gap up = (f − log ask USDC)·1e4; gap down = (log bid USDC − f)·1e4 | f; the USDC row used for the decision | same, bp | the trigger row | drained machine: the later of the last USDC row read and the last USDC row with E ≤ trigger E | yes, after the drain wait, which is charged to the delay | same | none |
| decision delay q | lag, floor, USDC arrival times | local and Binance stamps, ms | trigger row | trigger's queue + drain wait | yes | same | a minute without a floor: no event |
| RTT | rtt rows of connection 0 | ping, ms | median of 13:00-17:00 UTC rows of the day (whole day if < 10) | ping rows | a day-level constant | same | none |

Classification: forward-captured raw tape. The universe is the four named instruments; there is no cross-section and
no survivorship question.

## Rule
**Events.**
- **Drained machine (primary).** Before it decides, it reads every message already published. Its USDC state at a
  USDT row is the later of two rows: the last USDC row received by then, and the last USDC row whose E is at or before
  the trigger's E.
  - The time from the trigger's arrival to that row's arrival is the drain wait. It is added to the delay.
- **Naive machine (diagnostic).** It decides on the last USDC row received, and waits for nothing.
- **Event.** A USDT row at which gap up or gap down first reaches θ, after being below it on the previous USDT row.
  - θ ∈ {1, 2, 4, 8} bp. Up means buy USDC.
- **Refractory.** 3 s per asset, both directions.
- **Filters:**
  - No USDT stall (local silence ≥ 1 s) starts within 7 s after the event, or ended within 5 s before it.
  - q ≤ 100 ms, where q = the trigger's queue + the drain wait (the naive machine has no wait).
  - At least 7 s of recording remain on both books.

**Part B (M431): taker frontier, Binance's clock.**
- **Arrival X:**
  - E + D for D ∈ {1, 25, 50, 100, 250, 500, 1000, 1500} ms (the frontier);
  - E + ⌈q⌉ + RTT for this machine (`machine`);
  - the same for the naive machine (`naive_machine`, diagnostic).
- **Entry:** taker at the USDC touch as of T ≤ X (buy at ask, sell at bid).
- **Exit:** taker at the touch as of T ≤ X + H, with H ∈ {300, 1000, 3000} ms.
- **Gross bp** = direction × (log exit − log entry) × 1e4.
- **Cost:** 4 bp per fill, so 8 bp a round trip at 1x, 16 at 2x and 24 at 3x.
  - Source: secondary, a 2025-12-10 Binance notice seen through a search summary, as in R367's PREREG.
  - The break-even fee per fill (gross / 2) is reported in every cell.
- **Thin touch:** reported where the touch at entry or exit holds less than $5,000. Fills are priced at the touch
  regardless, so a thin share makes the result optimistic.

**Part A (M430): competing outcomes, Binance's clock, drained events only.**
- The predicted move is g = direction × (f − log mid USDC at the decision). Start: the trigger's T.
- **Catch:** the first later USDC row with direction × (log mid − log mid₀) ≥ g/2.
- **Reversal:** the first later USDT row with direction × (log mid − log mid₀) ≤ −g/2.
- **Adverse:** the first later USDC row with direction × (log mid − log mid₀) ≤ −g/2.
- The first of these within 3000 ms is the outcome. A tie goes to reversal or adverse.
- **Labels:** P(catch first within h) for h ∈ {300, 500, 750, 1000, 2000, 3000} ms.
- **Reported:** the quantiles of the catch time, and the share of catches within 5, 25, 50, 100 and 250 ms.

**Part C: the maker's side, Binance's clock.**
- **Crossings:** every first crossing at θ = 1 on the drained reading, with no refractory and no filter.
- **Classes of USDC trades:**
  - *with*: within 1000 ms after the latest crossing, in its direction;
  - *against*: in the window, the other way;
  - *out*: everything else.
- **Kept trades:** those with no USDT stall starting within 11 s after.
- **Markout:** aggressor side × (log mid USDC at T + h − log price) × 1e4, for h ∈ {1000, 10000} ms. A resting maker
  earns the negative.
- **Reported:**
  - with − out and against − out, with block-bootstrap intervals;
  - the share of trades and of notional in the *with* class;
  - for kept θ = 1 drained events, the ms from the trigger's T to the first USDC trade in its direction (≤ 1000 ms).

## Decision
**Primary cell:** θ = 2 bp, `machine` delay, H = 1000 ms, drained events, net at 1x.
- **PASS** needs all of:
  - n ≥ 100 events;
  - mean net 1x > 0;
  - the 2.5% bound of a 15-minute block bootstrap of the mean net 1x > 0 (2000 resamples, seed 431; blocks are day ×
    15 minutes of local time, both assets in one block);
  - a mean net 1x > 0 on each asset, with at least 20 events each.
- **INCONCLUSIVE** when n < 100.
- **NULL** otherwise.

**Registry mapping:** PASS → PARTIAL (a gate-0 screen, nothing confirmed), NULL → NULL, INCONCLUSIVE → PENDING with
the word in the notes.

**Reported, never decided:**
- the full grid with 1x/2x/3x;
- the frontier at θ = 2, H = 1000;
- τ_50: the delay at which mean gross falls to half its D = 1 value;
- τ_BE: the delay at which mean gross falls to 8 bp;
- τ_0: the delay at which mean gross falls to 0 (each by linear interpolation; "0" if it starts below, none if never);
- the naive machine against the drained one;
- Parts A and C;
- per-day and per-asset splits.

## Gates
Gate 0 only, one sample, no holdout.
- **What a PASS would earn:** a written case to the owner about fees (VIP tier or maker routes) and hosting, and a
  forward recording on an always-on host. It earns no order.
- **What a NULL with τ_0 well above the RTT would mean:** the edge exists but this machine is too slow or the fee too
  high. That is a statement about infrastructure, not a strategy.

## Null
No shuffled null: the primary is a cash P&L against a fee. Dependence is handled by the block bootstrap.

## Multiplicity
- **Trials: 148.**
  - Part B: 4 θ × (8 frontier delays + machine + naive) × 3 holds = 120 cells.
  - Part A: 4 θ × 6 horizons = 24 labels.
  - Part C: 2 horizons × 2 contrasts = 4.
- One cell decides. The rest are reported so that no cell can be chosen afterwards.
- Program trials so far: 9,784,363. After this lane: 9,784,511. The raw program sum is bookkeeping, not a correction.

## Evidence lineage and admission
- **Canonical methods:** M430, M431.
- **Related rounds:**
  - R367 (M427 selective USDC maker on the 100 ms tape, INCONCLUSIVE: 1 usable day);
  - R347/R348 (Lighter vs Binance lag scalps, NULL);
  - R370 (CME → Binance commodity perps lead).
  - None used the raw tape.
- **Samples already seen:** the plumbing counts and feed statistics listed below. No price after an event has been
  read.
- **Gates:** current `docs/GATES.md` sha256 e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. This lane
  meets gate 0 only and stays exploratory.
- **Selection control:** none across families.

## What was seen before this freeze
- **Plumbing passes.** An uncommitted earlier draft of this runner ran `--plumbing` once in this session: row counts,
  feed lags, spreads and event counts. Two more plumbing passes ran with this runner; the last one is saved as
  `experiments/rawlead_v1/plumbing.json`. A feed-only check counted how much earlier, in E, the unread USDC rows had
  been published, and how much later they arrived.
- **Rows and hours** (USDT / USDC, millions):
  - BTC: 8.35 / 2.85 on 10-29, 9.86 / 2.97 on 10-30, 10.14 / 3.46 on 11-05;
  - ETH: 11.14 / 4.74, 9.79 / 3.93, 9.42 / 4.59.
- **RTT** (connection 0 median): 252.7, 248.8 and 248.6 ms.
- **Clock.** The minute floor of lag wanders from −80 to +160 ms within a day on 10-29 and 10-30. It changes by up to
  30 ms a minute, which is local clock drift. On 11-05 it is steady near 70 ms.
- **Queueing.** The share of USDT rows queued over 100 ms is 12-16% on 10-29 and 10-30. On 11-05 it is 69% (BTC) and
  32% (ETH): the BTCUSDT median queue that day was 1.1 s, the 90th percentile 15 s. This container's consumer fell
  behind in busy minutes.
- **Spreads.** USDC median 0.012 bp (BTC) and 0.04 bp (ETH), 90th percentile 0.09-0.36 bp. USDT spreads are about one
  tick.
- **The naive reading's apparent stale quotes.** On 10-29 and 10-30, most were moments when the USDC book had already
  moved in the same Binance millisecond as the trigger (4-18 USDC rows with the same E). Those rows were read about
  0.1 ms (median) after the trigger. On BTC none had been published a full ms earlier; on ETH about 10% had. This is
  why the drained reading is the primary.
- **Events kept at θ = 2** (drained / naive):
  - 10-29: BTC 14 / 20, ETH 27 / 29;
  - 10-30: BTC 26 / 30, ETH 64 / 69;
  - 11-05: BTC 15 / 16, ETH 179 / 186.
  - Total 325 / 350. At θ = 1: 4,347 / 4,174. At θ = 4: 19 / 30. At θ = 8: 1 / 4.
- **The runner.** It ran end to end on a synthetic tape (USDC following USDT by 120 ms). It recovered a median catch
  time of 120 ms and τ_0 of about 230 ms; the 11 unit tests are in `tests/test_run_rawlead.py`.
- No gross, net, markout, catch time or other outcome of the real tape has been computed.

## Stop rules
- The runner runs once after this freeze, the registry row and a pushed commit.
- No re-run with another θ, delay, hold, fee, day or filter.
- A changed idea is a new lane: Bybit confirmation, a maker form (M433), conditioning features (M434, M438), more days.

## Limits (stated now)
- **Sample.** 7.9 hours on three afternoons, one regime, and 11-05 is dominated by ETH. A gate-0 screen, not evidence
  of persistence.
- **Clock.** The receive clock carries drift and the agent proxy's path. The floor removes the offset only minute by
  minute. A wrong floor moves q by tens of ms, against an RTT of about 250 ms.
- **Arrival model.**
  - The arrival assumes the order path equals the ping path. Binance's order gateway and matching queue add an
    unmeasured delay; the frontier shows what extra delay costs.
  - The two Binance books are assumed to share one clock within a few ms.
- **Fills.**
  - Taker fills at the touch with no queue, no rejection and no market impact.
  - The touch can be thinner than $5,000 (reported).
  - bookTicker may skip intermediate states.
- **Fee.** The 4 bp taker fee comes from a secondary source and is not verified for this account. VIP tiers and BNB
  discounts are not modelled; the break-even fee is reported instead.
- **Trades.** Part C trades come from a second connection, whose queue is not filtered. They are aligned in Binance's
  clock only.
