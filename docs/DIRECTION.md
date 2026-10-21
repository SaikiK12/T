# Direction (owner-approved 2026-10-20): all the data, all the strategies, tested as families, confirmed on samples nobody has read

## Context

**What we want:** the best net PnL the owner can actually trade (MEXC perps first), proven on days nobody had seen,
and handed over through the gates.

**Where we are (2026-10-20, checked today against the repo and PR #25's notes)**

*The search so far*
- 80 rounds and 9.47M trials: 56 NULL, and nothing has passed gate 1.

*What survives*
- **Carry (R191):** the only frozen holdout pass, at 1x cost only. That is about 1.2-1.45%/yr, below a T-bill, and
  t 1.14 at 2x.
- **Top-vs-crowd book B:** holdout t 2.72, but it was picked after the fact, it falls to t 1.6 without its 10 best
  days, and its MEXC replay is about 0.
- **Flow book A:** holdout t 1.22. Its 10 best days are 113% of its sum.
- PR #25's integrity audit says none of these can carry a decision yet. Gaps are zero-filled, coins that leave the
  universe exit for free, and the replay days are TradFi-driven.

*Forward lanes*
- All 8 paper lanes bet on one signal family (the flow cells).
- There are 0 strict on-time days. The first decision is 2027-01-18.

**Why progress is slow**

1. **Daily books cannot reach the bar in useful time.**

   | Edge size (annual Sharpe) | Days for an expected t of 2 |
   |---|---|
   | 1 | 1,460 |
   | 1.5 | 650 |
   | 2 | 365 |
   | 3 | 160 |

   Realistic edges sit at Sharpe 0.5-1.5. Each new forward lane on a daily book is a 2-4 year wait.
2. **Breadth runs one method per tick.**
   - Each method costs a full tick, and each null leaves nothing to confirm on.
   - There is no unread sample to send a survivor to, so a screen pass just waits for forward days.
3. **Missing data, some of which cannot be backfilled.**
   - Missing: the unlock calendar, delisting and listing notices, MEXC history for MEXC-only coins, spot legs, market
     cap and supply, and dated-futures basis.
   - Point-in-time data (calendar revisions, notices, next funding rate, MEXC open interest) exists only if recorded
     live.

**What we hold that nobody has read**
- **2020 crypto:** 81 perps on Binance from 2020-01-01. The research panel starts in 2021 (`lab/panel.py` START), and
  no crypto lane PREREG reads 2020. It covers price, funding, premium and taker volume only; top-trader ratios start
  in 2021.
- **MEXC-only coins, 2025-04..2026-10:** available once the approved download runs.
- Both samples turn a screen pass into a gate-1 answer in days instead of years. They must be protected and spent in
  scheduled batches.

**Where a $10k trader has an edge over funds**
- **Small size:** thin coins and events funds cannot size into. The literature puts crypto anomalies in small,
  illiquid coins. Tokenomist finds the unlock drop is in thin-float tokens.
- **Zero-fee web execution:** 1,106 MEXC contracts have a 0 maker fee.
- **Patience on events:** for example the old unlock short. It had 414 events, +2.5% per event, matched-date null
  p 0.002, and a dose-response.
- **Caveat:** a live Binance study (arXiv 2502.18625, 232k maker orders) found maker fills adversely selected. Zero
  fees help only a signal that already has gross edge.

**Owner's answers (2026-10-20)**
- **Downloads:** every one approved: "we need all data possible". The binding limit is disk (about 14 GB free in this
  container), not permission.
- **Execution:** both. Each lane is labelled manual-web or API, with that mode's costs:
  - manual web: 0 / 2-4 bp fee plus measured spread, at most about 15 orders a day, daily;
  - API: 6 / 8 bp fee plus spread, any frequency.
- **Calibration orders:** not yet. Costs come from public order books and paper markouts only.
- **R263:** run it offline to see whether it produces edges. Do not exclude it.
- **Strategies:** ingest every strategy from quant docs and research.
- **Subagents:** none. I do all of it myself.

## Direction

1. **Breadth through families, not ticks.**
   - Every strategy from the queue and the quant literature becomes a mechanical rule.
   - Rules are grouped into families. Each family is one frozen PREREG with all its variants, run offline in the
     background.
   - Each family is decided with multiplicity built in: White's reality check or SPA (`lab/inference`), plus a
     random-selection null. That is the R263 pattern.
   - Hundreds of strategies per run, with one registry row carrying the full trial count.
2. **Confirm on unread samples.**
   - Family survivors go to a scheduled batch read of 2020 and of the MEXC-only coins, at gate 1, with Bonferroni over
     the batch.
   - Each sample has a fixed number of batch reads, counted on the panel.
3. **Start every forward clock now.** Recorders for all point-in-time data, and forward paper tickets for each
   gate-1 survivor and each event lane.
4. **Fix the accounting before trusting anything.** Re-check the survivors with gaps raising and exits charged.

## Steps

**Day 1: start the long jobs and protect the samples**
- Commit `docs/PANEL.md` and the forward journals. Forward loop pid 344 is untouched.
- **R263:**
  - Run `scripts/run_brute5k.py` in the background at low priority (nice), as frozen.
  - Its result is read only by its own frozen rules.
  - Registry row via `lab.registry.append` when done, with 5,475 trials.
  - Its single best strategy and its walk-forward stream join the next 2020 batch whatever they score. This is a
    rule written before the result.
- **2020 guard:**
  - Check `docs/OLD_SESSION_EDGES.md` and the registry notes for any old-session read of 2020 crypto; say so if found.
  - Add the reserved window to `docs/GATES.md`.
  - Add a guard in `lab/research.py` that refuses pre-2021 rows unless a frozen PREREG path is passed. This is the
    same pattern as the holdout guard at `lab/research.py:60-62`.
  - Build `data/research_2020/` with the `scripts/build_views.py` code path. `load_universe(root=...)` already takes a
    root.
- **Downloads in the background, smallest and most valuable first.** Each goes into its own `data/<source>/`, with a
  provenance note (source URL, date, file hashes, expected shards, per `docs/DATA_PROVENANCE_AUDIT.md`). Disk is
  checked before each one.
  1. DefiLlama unlock calendar (emissions).
  2. MEXC history (`scripts/fetch_mexc_history.py`).
  3. Binance, Upbit and MEXC notice catalogs.
  4. Binance COIN-M dated-futures klines (M170 basis).
  5. Market cap and supply history, from CoinGecko or CoinPaprika's free API (M093 size factor).
  6. Binance spot hourly klines for the top-100.
  7. Hyperliquid public history.
- **Excluded for disk:** full tick history (aggTrades, bookTicker). Only one month for about 5 coins, for markout
  research.

**Days 1-3: recorders and the accounting re-check**
- **Recorders,** run from `scripts/forward_loop.sh`. Each is idempotent per hour and has a fixture test.
  - MEXC current and next funding (M172)
  - MEXC `ticker.holdVol` (open interest)
  - unlock calendar snapshot, daily
  - listing and delisting notices, hourly
  - the R224 depth snapshots extended to the owner's stake
- **Survivor re-check** (gate 0, 0 trials):
  - Rebuild A, B and X2 with `scripts/run_regime.py` `build`, and carry with its runner.
  - Run `slices.run(missing="raise")` plus an exit charge when a coin leaves the universe.
  - Report the change against R217 at 1x/2x/3x.
  - If a book loses more than half its net, say so on the panel. Frozen lanes keep running.

**Days 2-10: strategy ingestion and family runs**
- **Harvest** (by me, WebSearch and WebFetch). Each strategy becomes a methods.csv row with source, rule, data needed
  and execution mode. Sources:
  - the 30 UNTESTED and 31 PARTIAL queue items;
  - Quantpedia's crypto and futures lists;
  - SSRN and arXiv crypto anomaly papers: Liu-Tsyvinski-Wu factors, Fieberg trend factor and momentum,
    Cakici illiquidity, Dobrynskaya, Chi basis-momentum, Borri carry, Zaremba reversal;
  - books: Chan, Carver, Clenow, López de Prado.
- **Families,** each one frozen PREREG, background run, registry row and FINDINGS at 1x/2x/3x of its mode's cost:
  - cross-sectional factors: size, value proxies, illiquidity, momentum and reversal by tier, MAX and IVOL;
  - basis and carry: perp premium, dated-futures basis, spot-leg carry, next-funding revision;
  - time-series trend and volatility targeting;
  - event rules: unlocks, listings, delistings;
  - remaining chart and TA rules not in R263;
  - ML rankers (M042-M044) as one family with purged walk-forward.
- **Unlock short (E01):**
  - Archive replication per spec S1 in `docs/OLD_SESSION_EDGES.md`, on 2021-26. This is gate 0, because the old
    session read those years.
  - 2020 events go into the batch.
  - Forward MEXC paper tickets per event.
- **Ids:** claimed on #7 before each freeze.

**Day 14: first gate-1 batch and checkpoint**
- **The batch:** one frozen PREREG lists every family survivor plus R263's best and stream, carry R191 and the unlock
  short.
  - Read once on 2020 and on the MEXC-only coins.
  - Bonferroni over the batch, 1x/2x/3x, trimmed mean, leave-two-coins-out.
- **What passing earns:** a frozen forward paper lane (gate 1 continues on on-time days), labelled manual-web or API.
- **Checkpoint report for the owner:**
  - families run and trial counts;
  - batch results;
  - recorders live, data ingested, disk used;
  - what to stop.
- **Later batches:** every 2 weeks, from a read budget fixed in GATES (proposed: 4 reads per sample, then the sample
  is spent).

**Loop and room**
- Update the hourly trigger's prompt (`trig_016TEUgXKYYAQzELorwi9buf`) and the :43 cron to these steps:
  - start or continue one family run in the background;
  - check the downloads and recorders;
  - forward ticks;
  - room;
  - commit and push;
  - no subagents.
- Post the direction on #7, and propose that Codex re-runs fixes and audits while Claude does data, families and
  batches.

**Kept as is:** the 8 forward lanes and their dates, the hard rules, and the append-only, one-writer journals.

## Optional axis: faster profits (owner, 2026-10-21)
The owner asked for profits made faster:
- close to scalping, on MEXC and other venues;
- futures order books;
- leverage and confidence sizing per position.

It is an option beside the main direction, not a replacement. It enters the queue as four methods:

| Method | What | First step |
|---|---|---|
| M264 | Order-flow imbalance scalp (1-10 s imbalance, microprice) on MEXC and Binance | **Recorder running since 2026-10-21 06:35 UTC** (`scripts/record_tape.py`, `data/tape`): per-second best bid/ask, order-flow imbalance and trades for 12 liquid coins on both venues, capped at 3 GB (about five weeks). Next: a PREREG frozen before the tape is read against any price change, with its first weeks as discovery and the weeks recorded after the freeze as a sample nobody has seen. Only QA counts (rows, spreads, lags) have been looked at. API execution only. |
| M265 | Leverage and liquidation check for R275's carry legs at 1x / 2x / 3x / 5x | Gate 0 and descriptive, on R275's own trades. It gives the safe leverage per book and the return on capital at that leverage. |
| M266 | Confidence-sized carry: weight by spread width and persistence, capped at 3x | A qx spread variant, so a new lane with its own engine version. |
| M267 | Settlement-window carry: hold the pair only around the short venue's settlements | Screen the size of settlement gaps against 4 legs of cost first. |

**What the lab already knows here:**
- R193 (maker entries) and R223 (settlement capture) were NULL.
- arXiv 2502.18625 found maker fills on Binance adversely selected.
- Short-horizon order-flow edges are real but decay within seconds to minutes. Fees and the spread take most of them
  at retail latency.
- Leverage multiplies the edge and the error alike.

So each item goes through the same gates: a frozen family, then forward paper.

## Ideas from comment sections and transcripts (owner, 2026-10-21)
The owner asked for quant and trading comment sections and transcripts to be mined for ideas. The sources, what was
reachable and the ideas are in `docs/COMMENT_DIG.md`. Eleven rows were added to the queue (M288-M298).

**What they say:** practitioners keep saying that only fee and rebate structure, speed and venue-structure arbitrage
paid them, and that "nothing based on OHLC worked". That matches the lab's record, so event, carry and venue lanes
come before chart rules.

**Order of testing** (cheap held-data rows first, each a frozen family):

| Method | Status |
|---|---|
| M298 PCA residual reversion, hourly | **R287 NULL**: gross about +9.5 bp/day in the steadiest variants; costs 18-76 |
| M295 funding response to up days, as a gate | next |
| M290 scheduled US releases (CPI, NFP, FOMC, EIA) | needs release calendars and 1-5 min klines |

**Recorders to start where history cannot be bought:**
- Deribit open interest by strike (M289);
- Upbit and Bithumb wallet status (M294).

## Critical files
- **New:**
  - `scripts/record_mexc_funding.py`, `scripts/record_notices.py`, `scripts/record_unlocks.py`
  - `scripts/fetch_unlocks.py`, `scripts/fetch_spot.py`, `scripts/fetch_coinm.py`, `scripts/fetch_mcap.py`
  - `experiments/<family>/PREREG.md` (one per family), `experiments/batch2020_v1/PREREG.md`
  - `tests/test_recorders.py`
- **Changed:**
  - `lab/research.py` (2020 guard)
  - `docs/GATES.md` (reserved samples and read budget)
  - `scripts/forward_loop.sh` (recorders)
  - `registry/methods.csv` (harvested strategies, via code)
  - `docs/PANEL.md` via `scripts/panel.py`
- **Reused:**
  - `lab/inference` (SPA/MCS, DSR)
  - `lab/slices.py` `run(missing=)`
  - `scripts/run_regime.py` `build`
  - `scripts/run_brute5k.py` (reality-check pattern)
  - `lab/screen.py`
  - `lab/prereg.py`, `lab/registry.py`, `lab/mexc.py`
  - `scripts/record_mexc_depth.py`, `scripts/fetch_mexc_history.py`
  - `lab/gate.py`

## Verification
- `.venv/bin/python -m unittest discover -s tests -t .` passes before every `lab/` commit. This includes a test that
  the 2020 guard raises without a frozen PREREG.
- Every family and batch is frozen with `prereg.freeze()` before its first statistic, and its runner calls `verify()`
  first. Rebuilt books keep parity with R217.
- Each recorder runs twice in a row with no duplicate rows. Each download has a provenance note and a shard count.
- Every FINDINGS reports 1x/2x/3x of its execution mode's cost, its full trial count, and a reading against
  `registry.program_trials()`.
- Nothing places orders or uses keys. Downloads stay within the disk allowance, checked before each one.
