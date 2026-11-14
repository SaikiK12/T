# PREREG: unlocks_v1 (R265). Does the old session's unlock short replicate here?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R265 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Owner (single writer):** the Claude session that froze it
- **Origin:** E01 in `docs/OLD_SESSION_EDGES.md`, spec S1 (old R179 EDGE-SURVIVES, R181 volume split); step "unlock
  short (E01)" of `docs/DIRECTION.md`.
- **Gate:** 0. The old session read all of 2021-26 for this family, so nothing here confirms out of sample. Clean
  evidence can only come from the reserved samples and forward tickets listed at the end.
- **Execution mode:** manual-web. Two orders per event, about five events a week, daily timing.
- **Code:** `scripts/unlock_events.py` (events and symbol map; already run, outputs frozen below) and
  `scripts/run_unlocks.py` (written after this freeze; it calls `prereg.verify()` first).

## What the author has seen
- The old session's numbers in `docs/OLD_SESSION_EDGES.md`:
  - R179: 414 events on 68 coins, mean net +2.50% per event, week-cluster t 2.43, null p 0.002.
  - R181: unlock/ADV of at least 0.82 days gave +5.84%.
- In this snapshot: the event counts by window, year and dose band; the symbol map; and each mapped perp's first and
  last traded bar and last traded close (used for the ticker check).
- **No event return, funding sum or volume ratio has been computed here.**

## Data (frozen inputs)
- **Calendar:** DefiLlama emissions snapshot `data/unlocks/2026-10-20/` from `scripts/fetch_unlocks.py`, 370
  protocols. Its manifest holds the sha256 of each decompressed file; emissionsIndex is `5600e62e…`.
  - **Caveat:** this is today's calendar, not point-in-time. Later corrections can flatter old events. The daily
    recorder (`scripts/record_unlocks.py`, from 2026-10-20) fixes this for forward events only.
- **Event list:** `experiments/unlocks_v1/events.csv`, sha256
  `24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e`.
- **Symbol map:** `experiments/unlocks_v1/symbol_map.csv`, sha256
  `0f924ae96cf137e8a09305aff0c07ec041f3a07cd5417643741e3366aace472b`.
- The runner rebuilds both from the snapshot and must reproduce them byte for byte before reading any price.
- **Prices:** Binance USD-M hourly klines and funding through `lab.panel.load_panel` (start 2021-01-01; no 2020 row is
  read). Delisted perps are included.
  - After a delisting, the archive keeps flat zero-volume bars. A bar counts as traded only if volume > 0.

## Event rule (as built by `scripts/unlock_events.py`; see its docstring)
- **Unlocks counted:** cliff allocations in the categories insiders and privateSale, summed per token and UTC day D.
- **Qualifying day:** the sum is at least 1% of max supply.
- **Spacing:** per perp, a qualifying day is kept only if it is at least 14 days after the last kept one.
- **Map exclusions:** GRAM, ETH, BNB, POL and FTM; ticker mismatches (price ratio outside [1/3, 3]); collisions; and
  perps that traded before the token's first calendar event.

## Primary sample
- **Included:** events with venue binance, window archive (D from 2021-02-07 to 2026-09-30), and check verified or
  unverified. That is 530 events on 97 perps.
- **Excluded (counted, not traded):**
  - **no_market:** no traded bar in the 24 hours up to the entry time, or none before the exit time.
  - **Not in this run:** windows reserved_2020 (30 events), reserved_mexc (41), post_archive (15), forward and
    no_prices.

## Trade
- **Entry:** short at the close of day D-7, the close of the bar opening 23:00 UTC on D-7. The price used is the last
  traded close at or before that bar, which must be within 24 hours.
- **Exit:** at the close of day D, the bar opening 23:00 UTC on D. The price used is the last traded close at or before
  that bar.
  - If the perp never trades again after its last traded bar inside the hold, the event is flagged delisted_in_hold
    and still exits at that close.
- **Gross:** `-(exit / entry - 1)`.
- **Net:** gross minus the round-trip cost: 20 bp at 1x, 40 bp at 2x, 60 bp at 3x.
- **Funding:** a separate line, as in the old primary. The short receives `+sum(fund_event)` over the bars after the
  entry bar through the exit bar, following the engine's convention. A missing value counts as 0.

## Primary statistics and gates (1x, funding excluded)
- **Clustering:** by ISO week of D. Cluster-robust t = mean / se, with se = sqrt(G/(G-1) x sum over clusters of
  (sum of (x - mean))²) / n.
- **G1:** week-cluster t >= 2.
- **G2: matched random-date null.**
  - 2,000 replications, numpy default_rng(265).
  - Each event keeps its perp and gets a random day D' drawn with replacement from that perp's admissible days.
  - Admissible days: D' from 2021-02-07 to 2026-09-30; the trade above is priceable at D'; and D' is more than 14 days
    from every kept event day of that perp in events.csv (any window).
  - Each replication is priced with the same rule and cost.
  - p = (1 + #{replication mean >= observed mean}) / 2001. Pass if p < 0.05.
- **G3:** both halves positive. Events are sorted by D and split into the first and second half by count. Each half's
  mean net must be > 0.
- **G4:** positive without the top 3. Drop the 3 perps with the largest summed net; the mean of the rest must be > 0.
- **Verdict:**
  - **REPLICATES (gate 0)** if G1-G4 all pass at 1x;
  - **NULL** otherwise.
  - G1 at 2x and 3x is reported, not gated.

## Logged, not gated (counted as trials)
1. Net including funding.
2-4. Dose bands by fraction of max supply: [1%, 2%), [2%, 5%), >= 5%.
5-6. **R181 volume split.** V = tokens x (close at the end of D-8 / multiplier) / mean daily quote volume over days
   D-37..D-8, with at least 20 days required. Split at V >= 0.82 versus V < 0.82 (the old in-sample cut, used as a
   hypothesis only).
7. **BTC-hedged:** the short's gross plus BTCUSDT's return over the same hold.
8. **Horizon D-30 to D:** entry at the close of D-30.
9. **Horizon D to D+7:** entry at the close of D, exit at the close of D+7.
- **Robustness breakdowns, not counted:** verified-only, per year, hit rate, worst event, and delisted_in_hold count.

**Trials:** 10 (the primary and 9 logged variants). FINDINGS reads the result against `registry.program_trials()`.

## What a result earns
- **REPLICATES:**
  1. a forward MEXC paper lane (new PREREG, new id), with events taken only from the daily recorder snapshots so the
     calendar is point-in-time. The old go-real gate is at least 20 scored events, mean net > 0, hit >= 55%, and no
     event losing more than 40% unlevered. The owner places any stake.
  2. The same frozen rule on reserved_2020, reserved_mexc and post_archive events in the first reserved batch
     (`docs/GATES.md`).
- **NULL:** recorded as a null. No forward lane and no batch slot. A changed rule would be a new lane.
