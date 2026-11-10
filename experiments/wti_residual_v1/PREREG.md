# PREREG: wti_residual_v1

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R434
- **Owner (single writer):** Claude (a lane fork of the 2026-11-09 orchestrator session; lane files only, no git)
- **Date registered (UTC):** 2026-11-10

## Question
On the 24/7 commodity perps recorded from 2026-10-28 to 2026-11-06 (WTI, Brent, natural gas and gold on Lighter,
Hyperliquid xyz, Kraken Futures and Binance), when one venue's mid departs from the median of the other venues by at
least twice that venue's own round-trip cost (measured against the residual's trailing 30-minute median), does a taker
on that venue earn more than its cost? The taker enters 1.0 s later (1.3 s on Lighter), at the displayed touch, and
exits 60 s after entry at the displayed touch.

**Primary cell:** WTI, all venues pooled, k = 2, H = 60 s, while CME is open.

## Why this lane (ex ante)
- **M443's story.** The venues have different oracles, books and participants, so a venue's price can sit away from
  the others for a while. It was reported, not verified, that Hyperliquid xyz switches to internal pricing while the
  benchmark is closed, and that Kraken follows Pyth.
- **Lighter is the venue the lab can reach at the lowest cost:** a Standard account pays 0 fee, with a 300 ms taker
  delay (`docs/VENUE_STRUCTURE.md`).
- **A NULL is the likely result.**
  - R348: on crypto majors, Lighter's makers close a Binance-led gap within a second (taker form NULL).
  - R370: Binance's CL and NG perps move with CME's first threshold trade.
  - R369 (frozen, pending) covers only the EIA-release windows.
  - What stays open is ordinary-time disagreement among the commodity venues, and whether it lasts longer than R348's
    one second.
- **Why CME-closed time is not the primary**, although it is the stratum M443's story points to: the recordings hold
  no weekend at all. The recorder was down from 2026-10-30 15:50 to 2026-11-02 17:32 UTC. The only CME-closed seconds
  are three daily maintenance breaks, 8,868 s (2.46 h) in all. That stratum is reported as a futility screen and cannot
  decide anything.

## What the author has seen (before freezing)
- **Recordings, quality control only:**
  - session coverage and gaps per venue (`sessions.csv`), file counts, and the first three rows of one file per WTI
    venue;
  - those rows showed WTI levels that differ across venues: Lighter about 102.68 (10-29), Hyperliquid 101.85, Kraken
    101.76, Binance 101.93 (10-28 23:56). This is why the residual is measured against its own trailing median: the
    venues reference different contract months and indexes.
- **`plumbing.json`** (run by `--plumbing`; it reads no price after a decision):
  - valid seconds and median spread per venue;
  - trigger-second counts per venue and k, for example WTI k = 2: Lighter 8,196, Binance 4, Hyperliquid 0, Kraken 0;
  - 184,541 grid seconds per energy instrument, of which 8,868 are CME-closed.
- **No outcome has been computed on real data:** no residual after a decision, no return, no fill, no convergence.
- **Synthetic tests only.** They run on a planted world in a temporary folder. After the orchestrator's warning about
  R432's dry-run reading real data, they guard `pandas.read_parquet` and `read_csv` and fail on any file outside the
  temporary root. The module's data, lane and manifest paths point at a missing folder during the tests. All 9 tests
  pass.
- **Overlap with earlier lanes:**
  - **R426** read a 225-second fragment of 10-29 Lighter commodity data.
  - **R427** read 134 Lighter trades.
  - **R369's frozen forward lane** scores EIA releases from these recordings with its own rule (its first read is
    about 2026-12-23). Two releases fall inside the covered time here: gas on 10-29 at 14:30 UTC and gas on 11-05 at
    15:30 UTC. Crude on 11-04 is not covered. This lane neither reads nor changes R369's decision; its triggers may
    include those windows.

## Universe and data
| Instrument | Lighter | Hyperliquid xyz | Kraken Futures | Binance USD-M |
|---|---|---|---|---|
| WTI | WTI | CL | PF_WTIOILUSD | CLUSDT |
| BRENT | BRENTOIL | BRENTOIL | PF_BRENTOILUSD | BZUSDT |
| NATGAS | NATGAS | NATGAS | PF_NATGASUSD | NATGASUSDT |
| GOLD | (none) | GOLD | PF_XAUUSD | XAUUSDT |

- **Sources:** best quotes from `data/lighter_trades/quote/<sym>/` (written by `scripts/record_lighter_trades.py`) and
  `data/commodity_perps/{hlbbo,krtick,bnbook}/<sym>/` (`scripts/record_commodity_perps.py`), plus the two recorders'
  `sessions.csv`. All are public websockets, written on change and stamped with this container's receive time `t`, in
  µs.
- **Binance rows** keep the first change in each 100 ms bucket.
- **Kraken rows** with `suspended != 0` count as no quote.
- **Manifest:** `experiments/wti_residual_v1/data_manifest.json` lists all 9,268 files (path, bytes, sha256) and is
  hashed below. The run refuses any difference in the file set, a size or a hash.
- **Coverage:** about 52 h per venue between 2026-10-28 22:28 and 2026-11-06 14:38 UTC. The record is continuous from
  10-28 23:56 to 10-30 15:50; after that it falls into 15 fragments, with gaps of up to 14 h.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Window and close rule | Received / computed time | Available by decision? | Coverage vintage | Missing-value rule |
|---|---|---|---|---|---|---|---|
| Venue touch (bid, ask, sizes) | feed bid/ask/bq/aq | each venue's public feed, price units | last row received at or before s | local receive `t` | yes (as-of) | forward-captured | none before the feed's first row since (re)connection; none in the first 60 s after it; NaN if bid ≥ ask or non-finite |
| log mid m_v(s), spread_v(s) = 1e4 ln(ask/bid) | touch | bp | as-of s | computed at s | yes | forward-captured | NaN with the touch |
| Residual e_v(s) = 1e4 (m_v − median of the other venues' m) | m of all venues | bp | as-of s; at least 2 other valid venues | at s | yes | forward-captured | NaN otherwise |
| Baseline b_v(s) = median of e_v over valid seconds in [s − 1800, s) | e_v | bp | left-closed window, at least 900 valid seconds | at s | yes | forward-captured | NaN otherwise |
| Deviation d_v(s) = e_v(s) − b_v(s) | e_v, b_v | bp | at s | at s | yes | forward-captured | NaN otherwise |
| Threshold θ_v(s) = max(k (spread_v(s) + 2 fee_v), 4 bp) | spread, fee | bp | at s | at s | yes | fee: assumption below | NaN with spread |
| CME-closed flag | clock only | America/Chicago | Mon-Thu 16:00-17:00; Fri 16:00 to Sun 17:00 | at s | yes | calendar | no holiday in range |

## Rule
- **Grid:** every whole UTC second s at which at least 3 venues of the instrument have a valid touch.
- **Trigger** for venue v: |d_v(s)| ≥ θ_v(s), with k ∈ {2, 3}. Side = −sign(d): sell a rich venue, buy a cheap one.
- **Entry and exit:**
  - Entry fills at the touch as-of te = s + L_v: ask to buy, bid to sell. L = 1.3 s on Lighter (1.0 s decision plus
    300 ms Standard taker delay) and 1.0 s elsewhere.
  - The exit is a taker at the touch as-of tx = te + H, with H ∈ {10, 60, 300} s.
  - Both instants must fall inside the same connected feed session as s, or the decision is skipped. A skipped decision
    consumes no time.
- **One position per (instrument, venue):** the next decision is no earlier than the previous exit, tx. Strata are
  assigned by s, from the same continuous stream.
- **Pooled scope:** the union of the instrument's per-venue streams. Each venue keeps its own non-overlap.
- **Gross** = side × 1e4 ln(mid_x / mid_e), in bp.
- **Cost** = half-spread paid at entry + half-spread paid at exit (log bp, so at 1x the touch-to-touch return is exact)
  + 2 × fee.
- **Net at k×** = gross − k × cost, for k = 1, 2, 3.
- **Diagnostics** (primary events only; not decision cells, no trials):
  - the share of the deviation closed by tx, with the baseline held at s;
  - the venue's move toward the consensus, and the others' median move toward the venue, from s to tx;
  - the age of the venue's last quote row at s (Lighter's feed is bursty);
  - the share of fills against a touch under $5,000 (size × price).

## Costs (taker fee per side)
| Venue | Fee | Source / status |
|---|---|---|
| Lighter (Standard account) | 0 bp | `docs/VENUE_STRUCTURE.md` (docs read on 2026-10-21). Per-account fees seen on public trades (0.28-2.66 bp) belong to other account tiers |
| Hyperliquid xyz | 9 bp | R369's assumption: twice the 4.5 bp base taker for HIP-3. The "growth mode pays 90% less" note is unverified for xyz, so 9 bp is the conservative choice |
| Kraken Futures | 5 bp | base schedule, as in M443's note |
| Binance USD-M | 5 bp | regular taker; the TradFi schedule was not read (as in R368) |

The spread is inside the fills. The 2x and 3x cells multiply the whole cost (both half-spreads and the fees), so that
the zero-fee Lighter cells are stressed too.

## Cells and multiplicity
- **Scopes:**
  - WTI, BRENT and NATGAS: 4 venues + pooled each.
  - GOLD: 3 venues + pooled.
  - That is 19 scopes.
- **Cells:** 19 scopes × k {2, 3} × H {10, 60, 300} × stratum {open, closed} = **228 trials**. Every one is reported.
- **Program trials** at freezing: 9,784,709, after the rows of R432 and R433. The raw sum is bookkeeping, not an effective number of
  independent tests.
- **No cross-family selection control.** The lane is exploratory at gate 0. A pass only earns a frozen forward
  recording lane under a new id.

## Inference and decision
- **Bootstrap:** UTC-hour blocks of the decision time, 10,000 draws, seed 434. It gives the 95% interval and
  P(mean ≤ 0) of the mean net at 1x. MDE80 ≈ 2.8 × the bootstrap sd.
- **Primary verdict:**
  - **INCONCLUSIVE** if it has fewer than 30 trades or fewer than 4 hour blocks.
  - **PASS** if the lower 95% bound of the mean net at 1x is above 0 and the mean net at 2x is above 0.
  - **NULL** otherwise.
- **Every other cell is descriptive.** A secondary cell that looks good is not a finding.
- **Power, ex ante:**
  - At k = 2, WTI pooled is in practice Lighter. The other venues' thresholds sit far higher: Binance about 22 bp,
    Kraken about 28 bp, Hyperliquid about 38 bp.
  - Lighter WTI has 8,196 trigger seconds in about 47 h of CME-open coverage. After the 61.3 s non-overlap, expect tens
    to about 150 trades.
  - With a per-trade sd of about 5 bp at 60 s (assumed from WTI's ~2% daily volatility) and 30-45 hour blocks, MDE80
    is about 1.5-3 bp.
  - The CME-closed stratum (2.46 h) is underpowered: a futility screen.

## Gates
- `docs/GATES.md` sha256 `ed486814256194323dc2ee7d3375d16f8971a6f7b1775ddb2d6c9e476bf30070`.
- **Gate 0** on forward-captured, mostly unread recordings.
- **Unmet:** no strict on-time clock (local receive time, feed gaps); no 80% power proof; about 5 recorded days, so no
  10-day trimming; no leave-two-instruments-out (results are reported per instrument instead).
- **Not certified:**
  - fills against real books, queue and rejects;
  - the order path from this container to any of these venues;
  - Lighter's jurisdiction status for the owner: R428's stream was refused for the native runner's jurisdiction.

## Evidence lineage and admission
- **Method:** M443 (decision group: the cross-venue residual). Related: M447 (reopen re-anchoring, untouched), M442
  (downgraded).
- **Parents:** R348, R369, R370, R426, R427 (scopes above).
- **The sample:** the commodity recordings above. They are the first read of the residual question on them.
- **The verdict:** reported as the lane's own. It is not a gate-1 admission.

## Stop rules
- Run once, by `python scripts/run_wti_residual.py`. It verifies this file, every input below and the data manifest
  first.
- After results, add no venue, threshold, horizon, baseline, delay, fee or stratum. Any change is a new lane.
- A crash after the freeze abandons the lane (as R347 and R408). No frozen file is edited.

```inputs
541703d0aee51a530d86d0c0cffcc614faf127db4536154ba1981867e2a34122 scripts/run_wti_residual.py
cad828976e2e2ba1af0337c7bdc04c3908481cd250bab4818a95fb49af859b49 tests/test_run_wti_residual.py
52521b1d0ecd6d382b54e246979008708c84acde310e920c568aba63014f8e11 experiments/wti_residual_v1/data_manifest.json
226573a00a7a09d6d41502d305a3177e88267dedd2e84651409426328a7d0db2 experiments/wti_residual_v1/plumbing.json
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba scripts/run_clockflow.py
ed486814256194323dc2ee7d3375d16f8971a6f7b1775ddb2d6c9e476bf30070 docs/GATES.md
```
