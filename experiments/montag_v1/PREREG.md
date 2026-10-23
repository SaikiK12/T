# PREREG: montag_v1 (R269). Short the perps of coins Binance adds to its Monitoring Tag

Freeze with `lab.prereg.freeze()` before any price is read. Never edited afterwards; a change is a new lane.

- **Registry id:** R269 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 0. This is the archive, 2023-10..2026-09, which the lab has used for other questions. To the author's
  knowledge, no one in either session has read this event family.
- **Execution mode:** API. The entry follows the notice within the hour, at any time of day.
- **Code:**
  - `scripts/montag_events.py` builds the legs from titles only;
  - `scripts/run_montag.py` is the runner. It reuses `scripts/run_delist.py`'s pricing (`Book`) and statistics. It
    calls `prereg.verify()` first, then rebuilds `legs.csv` byte for byte and checks the input hashes below.
- **Paper only.** Nothing here places an order.

## Hypothesis
- Binance's Monitoring Tag (introduced 2023-07) marks tokens at risk of delisting.
- R267 found that spot delisting notices are followed by a further fall in the hour after the first hourly open:
  +4.15% at 1x, t 3.07, n 25. That was a logged variant.
- The tag is the earlier, softer version of the same news. If holders sell on it, the perp keeps falling after the
  first hourly open.

## What the author has seen
- R267 in full.
- The titles of all 27 tag notices and the leg list below.
- No price, volume, funding or return has been read for any leg at or after its notice.

## Inputs (frozen)
- **Catalogs:**
  - `data/recorders/notices/binance_news.csv` and `binance_delisting.csv`, deduplicated by id;
  - rows released before 2026-10-20T17:00:00Z (4,900 rows).
  - sha256 of those rows' `id,code,title,release_ms` as CSV:
    00630318fed1b32268ba4212bbe22a707f2d6506a483d9015208200c8c43a8d9.
- **Legs:** `experiments/montag_v1/legs.csv`, sha256
  771a8a3a4d06e0e13c77d97a35bd506aed6caacb7499415b8b6740ce1a9d9057.
  - 27 notices and 149 legs in all.
  - **The sample:** `kind == tag`, `window == archive` and `in_archive`. That is 24 notices and 97 legs before the
    traded check.
- **Prices:** `lab.panel.load_panel` on the legs' perps plus BTCUSDT, 2021-01-01..2026-09-30. No row before 2021 is
  read.

## Events and legs (as built by `scripts/montag_events.py`)
- **Tag:** the names in "Extend the Monitoring Tag to (Include) A, B and C", up to ", (and) Remove ..." or
  " on <date>".
- **Untag:** "Remove the Monitoring Tag for ...". Reported only, never counted: there are 5 notices.
- **Perp:** `delist_events.perp_for`, that is `<T>USDT` or a 1000- or 1000000-prefixed archive contract.
- **t0:** the notice's `release_ms`.

## Trade (per leg): R267's rules, unchanged
- **r0** is the hourly bar that contains t0. The entry price is its close, which is the first hourly open after the
  notice. The leg needs volume > 0 on r0; otherwise it is `no_market`.
- **Exits:** the close of r0 + h, for h = 1 (primary), 24 and 72 hours.
  - If the exit bar has no volume, use the last traded close, flagged `stale_exit`.
  - If the perp stopped trading before the exit, flag it `delisted_in_hold`.
- **Gross (short):** `-(exit / entry - 1)`.
- **Funding:** the settlements in (entry, exit] (fund_event rows r0+2 .. exit + 1). The short receives `+rate`.
- **Cost:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x.
- **Net:** `gross + funding - cost`.
- **Hedged line:** the same short plus a long BTCUSDT over the same rows. It pays BTC funding and costs 10 bp round
  trip x the cost multiple.
- **One observation per notice cluster:**
  - notices whose t0 fall in the same hourly bar form one cluster;
  - a perp counts once per cluster;
  - the observation is the equal-weight mean net of the cluster's priced legs.
- **t:** mean / (sd / sqrt(n)), with ddof 1.
- **Halves:** in time order. The first floor(n/2) clusters form the first half; the rest form the second.

## Gates (primary: tag, +1 h, unhedged, 1x)
| Gate | Rule |
|---|---|
| G1 | cluster t >= 2.0 |
| G2 | both halves have a mean net > 0 |
| G3 | clusters from 2025-01-01 have a mean net > 0 |
| G4 | matched null p < 0.05 |

- **The G4 null is R267's:**
  - same hour of day, on a random day in [t0 - 60 d, t0 - 7 d];
  - the day is admissible if every priced leg traded on that r0. With fewer than 10 admissible days, the window
    widens to 180 d; a cluster still short is left out;
  - 2,000 draws, seed 269;
  - p = (1 + #(null mean >= observed)) / 2,001.
- **Verdict:**
  - **PASS (gate 0)** if G1-G4 all pass at 1x. The registry row reads PARTIAL, as gate 0 cannot confirm.
  - Otherwise **NULL**.
  - 2x and 3x are reported next to it.

## Logged variants (6 trials, with the primary)
| # | Exit | Hedge |
|---|---|---|
| 1 | +1 h (primary) | none |
| 2 | +24 h | none |
| 3 | +72 h | none |
| 4 | +1 h | BTC |
| 5 | +24 h | BTC |
| 6 | +72 h | BTC |

- Each variant reports n, mean, median, hit, t, halves and 2025+ at 1x/2x/3x, with G1-G3 shown.
- The verdict is on the primary only. A variant that clears G1-G3 is a reason for a new frozen lane, not a pass.

## Robustness (reported, not counted)
- Without the top 3 legs.
- Per year.
- **The move the entry cannot catch:** the close of r0 - 1 to the close of r0, short sign.
- Counts of `no_market`, `stale_exit` and `delisted_in_hold`.
- Gross and funding apart.
- **Untag notices, long:** mean and n at each horizon. These are descriptive.

## Program reading
- Read the result against `registry.program_trials()` after this row (6 trials).
- **Forward option, if PASS:** the notice recorder already journals this catalog hourly. A new PREREG would trade it
  on MEXC like R268.
