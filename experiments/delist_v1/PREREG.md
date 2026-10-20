# PREREG: delist_v1 (R267). The Binance delisting-notice short, archive version (old E03, spec S2)

Freeze with `lab.prereg.freeze()` before any price is read. Never edited afterwards; a change is a new lane.

- **Registry id:** R267 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 0. The old session read this family on 2022-26 (R167, `experiments/delistshock`), so this is a
  replication on the lab's archive, not a confirmation. A pass earns a forward lane, not money.
- **Execution mode:** API. The entry has to follow a notice within the hour, at any time of day.
- **Code:**
  - `scripts/delist_events.py` builds the legs (titles and article text only, no price);
  - `scripts/fetch_notice_bodies.py` fetched the article text;
  - `scripts/run_delist.py` is the runner. It calls `prereg.verify()` first, then rebuilds `legs.csv` byte for byte
    and checks the input hashes below.
- **Paper only.** Nothing here places an order.

## What the author has seen
- **Old session (docs/OLD_SESSION_EDGES.md E03):** 161-notice catalog, 46 legs from 22 announcements.
  - Per leg, 1 h: +642 bp, t 2.69.
  - Clustered by announcement: 1 h +518 bp, t 1.42 (fails); 24 h +1,039 bp, t 2.01.
  - 2025 1 h net negative. The old entry decayed within seconds of the notice.
- **This lane's inputs:** every title and article text in the catalog, and the leg list below. No price, volume,
  funding or return has been read for any leg at or after its notice.
- The lab's hourly archive has been used by many other lanes, but never at these notice times.

## Inputs (frozen)
- **Notice catalog:** `data/recorders/notices/binance_delisting.csv`, rows released before 2026-10-20T17:00:00Z
  (442 rows).
  - sha256 of those rows' `id,code,title,release_ms` as CSV:
    4711c4f6b6df02db045d0f53c5712bbd5a02edd31d06a0acf18d386251463d29.
- **Article text:** `data/recorders/notices/articles/<id>.txt`.
  - sha256 over the lines `<id>\t<sha256 of file>` in id order:
    f155ba8da5eacbf837ac763beb902494d8536cd5159779b6de1e6882bc1501a6.
- **Legs:** `experiments/delist_v1/legs.csv`, sha256
  fbdfe6efc9a7bedebb66f1d465d6294b3764bc42ee6f3200f5ab4f537e51771e.
  - 83 notices and 259 legs in all.
  - 72 notices and 170 legs fall in the archive and have an archive perp.
- **Prices:** `lab.panel.load_panel` on the legs' perps plus BTCUSDT, 2021-01-01..2026-09-30 (`data.END`). No row
  before 2021 is read.

## Events and legs (as built by `scripts/delist_events.py`)
- **Spot notices:** "Binance Will Delist A, B and C on <date>", plus the vote-to-delist variant. Tickers come from
  the title.
- **Futures notices:**
  - "Binance Futures Will Delist ..." and other titles announcing a USD-M futures delisting.
  - Tickers are the title's names plus every `<X>USDT` symbol in the article text. This covers "Multiple Perpetual
    Contracts" titles.
  - Postponements and COIN-M-only notices are excluded.
- **Other titles are excluded:** margin, loans, staking, options, leveraged tokens and trading-pair removals.
- **Perp:** `<T>USDT`, or a 1000- or 1000000-prefixed contract in the archive. BUSD-, USDC- and USD-quoted names are
  dropped.
- **t0:** the notice's `release_ms`.
- **Sample:** legs with `window == archive` and `in_archive`.

## Trade (per leg)
- **Rows:** r0 is the panel row of the hourly bar that contains t0 (it opens at the hour of t0).
- **Entry price:** the close of r0. That is the open of the first hourly bar after t0, 0-60 min after the notice.
  - The leg needs a traded perp at t0: volume > 0 on r0. Otherwise the leg is `no_market` and dropped.
- **Exits:**
  - +1 h (primary): the close of r0 + 1.
  - +24 h: the close of r0 + 24.
  - If the exit bar has no volume, use the last traded close at or before it, and flag it `stale_exit`.
  - If the perp has stopped trading by then, flag it `delisted_in_hold`.
- **Gross (short):** `-(exit / entry - 1)`.
- **Funding:** the sum of `fund_event` on rows r0+2 .. exit row + 1. These are the settlements in (entry time, exit
  time], as in R266. The short receives `+rate`.
- **Cost:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x.
- **Net:** `gross + funding - cost`.
- **Hedged line:** the same short plus a long BTCUSDT over the same rows. It pays BTC funding and costs an extra 10 bp
  round trip times the cost multiple.

## Observation and statistics
- **One observation per notice cluster:** the equal-weight mean net of its priced legs.
  - Notices whose t0 fall in the same hourly bar form one cluster.
  - A perp counts once per cluster.
  - A cluster with no priced leg is dropped.
- **t:** mean / (sd / sqrt(n)) over the cluster observations, sd with ddof 1.
- **Halves:** clusters in time order. The first floor(n/2) form the first half; the rest form the second.

## Gates (primary: all legs, +1 h, unhedged, 1x)
| Gate | Rule |
|---|---|
| G1 | cluster t >= 2.40 (the old S2 gate) |
| G2 | both halves have a mean net > 0 |
| G3 | clusters released from 2025-01-01 have a mean net > 0 |
| G4 | matched null p < 0.05 |

- **The G4 null:**
  - Each cluster gets a random day d, with the same hour of day as t0, in [t0 - 60 d, t0 - 7 d].
  - The day is admissible only if every priced leg of the cluster has volume > 0 on the random r0. With fewer than
    10 admissible days, the window widens to [t0 - 180 d, t0 - 7 d]. A cluster still short of 10 is left out of the
    null, and the observed mean is then taken over the clusters that remain.
  - The null observation is the same net (1x, +1 h, unhedged) at that time.
  - 2,000 draws, seed 267. p = (1 + #(null mean >= observed mean)) / 2,001.
- **Verdict:**
  - **REPLICATES (gate 0)** if G1-G4 all pass at 1x. The registry row reads PARTIAL, because the registry has no
    REPLICATES verdict.
  - Otherwise **NULL**.
  - 2x and 3x are reported next to it.

## Logged variants (8 trials, with the primary)
| # | Legs | Exit | Hedge |
|---|---|---|---|
| 1 | all (primary) | +1 h | none |
| 2 | all | +24 h | none |
| 3 | all | +1 h | BTC |
| 4 | all | +24 h | BTC |
| 5 | spot notices | +1 h | none |
| 6 | futures notices | +1 h | none |
| 7 | spot notices | +24 h | none |
| 8 | futures notices | +24 h | none |

- Each variant reports n, mean, median, hit, cluster t, halves and 2025+ at 1x/2x/3x, with G1-G3 shown.
- The verdict is on the primary only. A variant that clears G1-G3 is a reason for a new frozen lane, not a pass.

## Robustness (reported, not counted)
- Without the top 3 legs by net.
- Per year.
- Without the two crash notices of 2022: LUNA (91745, 91819) and FTT (141460).
- **The move the entry cannot catch:** the close of r0 - 1 to the close of r0, short sign.
- Counts of `no_market`, `stale_exit` and `delisted_in_hold`.
- Gross and funding apart.

## Program reading
- Read the result against `registry.program_trials()` after this row (8 trials).
- The registry row is appended with `lab.registry.append`.
- **Forward option, if REPLICATES:** a notice listener faster than the hourly recorder, and a new PREREG.
- **Old caveats kept:**
  - Binance may restrict new shorts after a futures notice.
  - Borrow and open-interest caps are not modelled.
