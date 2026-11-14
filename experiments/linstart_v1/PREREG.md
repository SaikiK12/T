# PREREG: linstart_v1 (R485). Does shorting around an insider linear-vesting start make money?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R485
- **Owner (single writer):** Kiro coder agent, session on `claude/websearch-organization-and-maintenance` (2026-11-13)
- **Date registered (UTC):** 2026-11-13

Method M538 (queued UNTESTED on 2026-11-13, `research/intake/lit_hype_unlocks_20261113.md`). R265's rule counts cliff
allocations only, so linear-vesting starts were never tested. LIT's team and investor stream (3.194m LIT a week,
0.32% of max supply a week, from 2026-12-29) raised the question; LIT has no past instance, so the historical sample
is other tokens with DefiLlama-documented linear starts. This file is frozen before any OKX candle or funding value
is fetched (`scripts/fetch_linstart.py`) and before any return is computed.

## Question
Does a short of the token's OKX USDT swap from the 1Dutc close of D-7 to the 1Dutc close of D+14, where D is the day
an insiders or privateSale linear stream starts and raises the weekly unlock rate by at least 0.25% of max supply,
earn more than 20 bp a round trip on average?

**The prior expects NULL:** a linear stream is on the calendar for years and sells gradually, unlike a cliff.

## Deviations from M538's kill test (stated before any price)
- **Venue:** M538 names Binance perps (R265's venue). Binance answers HTTP 451 from this sandbox and R265's Binance
  archive is not in this checkout, so prices are OKX USDT-margined swaps.
- **Snapshot:** M538 names R265's 2026-10-20 snapshot, which is not in this checkout. The calendar is a fresh run of
  R265's own fetcher on 2026-11-13 (same public source).
- **Gates:** M538's three (t >= 2, null p < 0.05, 2x mean > 0) plus R265's halves and drop-top-3 checks, all required.

## What the author has seen
- R265 `experiments/unlocks_v1/FINDINGS.md`: the cliff short (D-7 to D) earned +3.24% net per event at 1x over 422
  Binance events, week-cluster t 3.19, all four gates passed (gate 0, in-sample, not point-in-time).
- Prior-art search (WS0023 to WS0026, `research/intake/source_catalog_linstart_20261113.csv`): no source seen reports
  a return number for linear-vesting starts. The Tie (SRC1113-013) sizes 12,350 unlocks against volume only (median
  0.20% of ADV) and reports no return. Keyrock's report was not read (403).
- In this snapshot: event counts by window, label, year and dose band; the symbol map, including OKX's current last
  price per swap (ticker check only) and each swap's OKX listTime (instrument metadata).
- From listTime alone: of the 9 pure archive events, 5 have D-7 before the swap's OKX listing (CVX 2021-05-17, LDO
  2021-12-17, RAY 2022-02-21, KMNO 2025-04-30, YB 2025-09-15), so **at most 4 primary events can be priced**. The
  primary verdict is therefore INSUFFICIENT whatever the prices show (rule below). The lane is run anyway so the round
  is recorded with its numbers and the forward instances are listed.
- **No candle, return, funding value or price change has been fetched or computed for any event or swap.**

## Universe
- Tokens in DefiLlama's emissions snapshot whose index ticker maps to a live OKX USDT linear crypto swap
  (`symbol_map.csv`, check `verified`: OKX last price over index price x multiplier in [1/3, 3]). R265's exclusions
  (GRAM, ETH, BNB, POL, FTM). 127 verified, 4 excluded, 243 unmapped, 0 mismatch.
- **Survivorship bias:** OKX's instrument list holds live swaps only. A token whose OKX swap was delisted is missing,
  and delisted tokens tend to be the ones that fell. This biases the short's return down (against the hypothesis) if
  falls were concentrated in delisted names, and it removes any event on a dead swap. It cannot be repaired with
  OKX's public API.

## Data (frozen inputs)
- **Calendar:** DefiLlama emissions snapshot `data/unlocks/2026-11-13/` (gitignored) from `scripts/fetch_unlocks.py`,
  374/374 protocols, 0 errors, fetched 2026-11-13T10:02:09Z. Its `manifest.json` sha256
  `7163cf7d237dd3f02e7955f43b8e36f18d3965f273d61a2354358ab7415ea50c` holds the sha256 of every decompressed file
  (emissionsIndex `3276bb908c9664bf3313b20732de831322f4ff0921196f4e73efc4425e03450d`; protocols/lighter
  `605f1fb9...`, byte-identical to the frozen R484 body). **Caveat:** today's calendar, not point-in-time; later
  corrections can flatter or hide old events (R265 caveat).
- **OKX swap list:** `experiments/linstart_v1/okx_instruments_swap.json` (GET /api/v5/public/instruments?instType=SWAP,
  2026-11-13 10:03 UTC), sha256 `e0ca70b9b3e62eda2317afecc02325c2959d0a30b5db9f2779a86328698810b7`.
- **OKX last prices (ticker check only):** `experiments/linstart_v1/okx_tickers_swap.json`
  (GET /api/v5/market/tickers?instType=SWAP, same minute), sha256
  `371a8c31e8dbd901809d4ddfc5bb701fdbb0699177f21adc82594da44c39602f`.
- **Event list:** `experiments/linstart_v1/events.csv`, sha256
  `1d671c0467254640cd5163d70e1816ea0c48893cfa8977188e546e5fabd29f9f`.
- **Symbol map:** `experiments/linstart_v1/symbol_map.csv`, sha256
  `bacb9e3ac400a9a9345631d94dd663b01716da1180df28160bb7984445eb5509`.
- **Code:** `scripts/linstart_events.py` sha256 `748ff7e8fab4a75d03baa5ef30b2a98d0eb6d3009ff360e9aa6270821ba9827b`
  (imports `scripts/unlock_events.py`, unchanged, `cec5b380...`); `scripts/run_linstart.py`
  `a2ee4de822ef166cbafb294eaa191033a21c06c9ee71ebe28cf03307fac32f14` (imports R265's `cluster_t` from
  `scripts/run_unlocks.py`, unchanged, `513974db...`); `scripts/fetch_linstart.py`
  `08016eecfb8dece3d2e3b0edefef6dc8dac551cc430eaad991472b6e72049387`.
- The runner verifies this file, the four frozen files, the snapshot manifest and every snapshot file, then rebuilds
  events.csv and symbol_map.csv and requires byte equality before it reads any candle.
- **Prices (fetched once, after this freeze):** OKX GET /api/v5/market/history-candles, bar 1Dutc, limit 100, paged
  with the `after` cursor, every bar opening before 2026-11-07 00:00 UTC back to the swap's first bar, for the 15
  swaps with archive events; OKX GET /api/v5/public/funding-rate-history for the same swaps (OKX serves recent months
  only). Bodies in `experiments/linstart_v1/raw/okx/` with sha256 in `raw/manifest.json`; the runner checks them.
  Only confirmed bars (confirm = 1) are used. A 1Dutc bar's timestamp is its 00:00 UTC open; its close is at 24:00.

## Event rule (as built by `scripts/linstart_events.py`; see its docstring)
- **Streams counted:** linearAllocations with unlockType `linear_start` in categories insiders or privateSale.
- **Rate increase on day D:** the sum of (newRatePerWeek - previousRatePerWeek) over those allocations whose event
  timestamp falls on UTC day D. D qualifies when the sum is at least 0.25% of max supply (max supply from the protocol
  file's supplyMetrics, else the index).
- **Spacing:** per swap, a qualifying day is kept only if it is at least 30 days after the last kept one.
- **Label:** `with_cliff` if the token has an R265-qualifying cliff day (insiders + privateSale cliffAllocations
  summing to >= 1% of max supply on one UTC day) anywhere in D-30..D+21; otherwise `pure`.
- **Windows by D:** pre_window (before 2021-02-07), archive (2021-02-07 to 2026-10-23), post_archive (2026-10-24 to
  2026-11-13) and forward (after 2026-11-13, not traded).
- **Counts:** archive 15 (9 pure on 9 swaps, 6 with_cliff), forward 5 (LIT 2026-12-29 pure 0.319%; CHIP, PROS, AI,
  ARX in 2027), pre_window 1, post_archive 0. Pure archive dose bands: 6 in [0.25%, 0.5%), 2 in [0.5%, 1%), 1 >= 1%.

## Trade
- **Entry:** short at the OKX 1Dutc close of D-7 (the bar opening 00:00 UTC on D-7).
- **Exit:** at the 1Dutc close of D+14.
- **no_market:** no confirmed candle for D-7 (the swap was not yet listed, or a gap). If D+14 has no candle, the exit
  is the last close after the entry and before D+14, and the event is flagged exit_early.
- **Gross:** `-(exit / entry - 1)`.
- **Net:** gross minus the round trip cost: 20 bp at 1x, 40 bp at 2x, 60 bp at 3x.
- **Funding:** reported where OKX's history covers the whole hold, as the sum of fundingRate over settlements in
  (close of D-7, close of D+14] received by the short; excluded from every gate (as in R265).

## Primary sample
Label pure, window archive, priced (not no_market).

## Gates (1x unless stated, funding excluded)
- **Clustering:** by ISO week of D; R265's cluster-robust t (`scripts/run_unlocks.cluster_t`).
- **G1:** week-cluster t >= 2.
- **G2: matched random-date null.** 2,000 replications, numpy default_rng(485). Each primary event keeps its swap and
  draws D' with replacement from that swap's admissible days: D' in 2021-02-07..2026-10-23, confirmed candles at both
  D'-7 and D'+14, and more than 30 days from every event day of that swap in events.csv (any window or label). Each
  replication's mean net 1x; p = (1 + #{replication mean >= observed mean}) / 2001; pass if p < 0.05. If a primary
  swap has no admissible day, G2 fails.
- **G3:** mean net at 2x > 0.
- **G4:** both halves positive: events sorted by D (then instId), split by count (first half has floor(n/2)); each
  half's mean net > 0.
- **G5:** drop the 3 swaps with the largest summed net; the rest's mean net > 0 (fails if nothing is left).
- **Verdict:**
  - **INSUFFICIENT** if the primary sample has fewer than 20 priced events (expected here: at most 4);
  - otherwise **CONFIRMS-ON-HISTORY (gate 0)** if G1-G5 all pass, else **NULL**.
  - The rounds registry has no INSUFFICIENT or CONFIRMS-ON-HISTORY verdict: INSUFFICIENT and NULL are recorded as
    NULL with the native verdict in the notes; CONFIRMS-ON-HISTORY as PARTIAL (gate 0, in-sample, not confirmed).

## Reported, deciding nothing (not counted as trials)
- The `all` (pure + with_cliff) and `with_cliff` archive samples at 1x/2x/3x; pure dose bands; the funding line and
  how many events it covers; counts excluded by reason; LIT's forward instance date and the other forward instances.

## Multiplicity
**Trials: 1** (the primary). Program trials before this round: 9,785,288 (`registry.program_trials()`); 9,785,289
with it. A gate-0 in-sample read on a revised calendar and a survivor-only venue list.

## What a result earns
- **INSUFFICIENT or NULL:** recorded as such; M538 is marked tested with the native verdict. LIT's 2026-12-29 start
  remains one forward instance and decides nothing alone. A changed rule (lower threshold, other venue, other horizon)
  is a new lane with a new id.
- **CONFIRMS-ON-HISTORY:** a forward paper lane (new PREREG, new id) with events from the daily recorder's
  point-in-time snapshots. Not a go-real signal.

## Stop rules
One run of `scripts/run_linstart.py` after the fetch. No new features, thresholds, horizons, samples or venues after
seeing any result. A crash fixed after the freeze is documented in FINDINGS with the changed sha.
