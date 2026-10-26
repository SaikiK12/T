# Direction (owner-approved 2026-10-20): all the data, all the strategies, tested as families, confirmed on samples nobody has read

**Reading scope (2026-10-22).** This preserves dated owner decisions and later progress notes. Counts, missing-data
lists, worker assignments and Day 1 tasks describe those snapshots, not the current checkout or a fresh instruction
to run them. Latest owner instructions and fresh [room claims](https://github.com/SaikiK12/T/issues/7) govern work;
use [the live queue](../registry/methods.csv), [round registry](../registry/rounds.csv) and timestamped [panel](PANEL.md)
for current recorded scope. Recheck actual inputs and authorization before any acquisition or execution.

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
| M295 funding response to up days, as a gate | **R297 NULL**: neither measure leads the top-50 basket or BTC at 7/30 days (validation \|t\| ≤ 0.88); up-day funding is the funding level |
| M290 scheduled US releases (CPI, NFP, FOMC, EIA) | 1-minute klines held; FOMC dates held; CPI and payroll dates not reachable from this container (BLS 403, FRED bot check) |

**Recorders where history cannot be bought:**
- the Deribit option chain, hourly from 2026-10-21 (M175, M289, M300: expiry pinning and dealer gamma);
- Lighter order books, hourly from 2026-10-21 (M292: the cost of a zero-fee API venue);
- DEX pool prices next to the MEXC perp, every 5 minutes from 2026-10-21 (M288: on-chain AMMs against exchange
  futures, the prop trader's third edge);
- wallet status on Bithumb, Gate, KuCoin, HTX and Bitget, hourly from 2026-10-21 21:21 UTC (M294,
  `scripts/record_wallets.py`). Upbit's status needs an API key, so it is not recorded.

**Venue structure (the prop trader's lead, `docs/VENUE_STRUCTURE.md`).** Lighter charges no fee through the API. On
one snapshot, a $1k order costs a median 2.0 bp per side there against about 8.7 bp on MEXC's API, for the same 27
coins. API-mode rules that died on costs between 2 and 8 bp per side get a second look:
- once the Lighter recorder has two weeks of books;
- on Lighter's own price history;
- as one frozen family at gate 0.

Lighter also joined the cross-venue carry family as a venue. **R288 `xfund_lt_v1` is done: CONFIRMED as a venue
replication (gate 0).** R275's best book replicates on 5 of the 6 Lighter sets.
- **The result is small:** +3.5 to +6.2%/yr at 1x, against +20-24%/yr for the KuCoin sets over the same years.
- **The zero fee** is worth only about 0.3-0.4%/yr there.
- **R294 `xfund_lt_fwd` runs the mexc+lighter book forward on paper** from 2026-10-23 (PREREG frozen 2026-10-22, 1
  trial).
  - `lab/carrylane.py` now reads Lighter: hourly candles and funding, the contract list, and book mids. Every request
    goes under the machine-wide Lighter lock.
  - The Python twin reproduces R288's book exactly: 305 of 305 trades.
  - The first look is at 90 scored days (2027-01-21). The in-sample power is 96%, but the book earns only about
    5%/yr, so it ranks below the KuCoin lane (R279).
- Trading on Lighter needs an on-chain wallet: that is the owner's call.

## What proven traders let slip (owner, 2026-10-21)
The owner asked for the talks of people who made money trading, starting with Tarek Elmarhri, and for what they say
by accident about how the money is made. The write-up is `docs/TRADER_TALKS.md`. It has cards per person with a
credibility tier, seven sources of trading money with who pays each, and a checklist for finding opportunities
ourselves.

**The common thread:** each of them names who is on the other side and why that side keeps paying. The other side
is forced, impatient, constrained or wants leverage. The flows that pay best run on a clock or a rule. Small
accounts can reach three of the seven sources: risk-transfer premia (carry), barrier gaps (venues) and forced or
rule-bound flow.

**New queue rows:**

| Method | Clock or rule | Data |
|---|---|---|
| M301 | US cash-open flush and reverse (Elmarhri: "on le prend tout le temps") | 1-minute klines for BTC/ETH/SOL; **R289 NULL** |
| M303 | Deribit settlement TWAP, 07:30-08:00 UTC (SEBI's Jane Street order is the template) | 1-minute klines; **R289 NULL** |
| M304 | ETF fixing hour (BRRNY, 15:00-16:00 New York) | hourly klines; daily ETF flows to fetch |
| M302 | 25-day MA deviation buy (BNF) | held; overlaps NULL lanes, so last |

The 1-minute data also unblocks M290 (scheduled releases) and M206 (opening-range breakout).

**R289 (clockflow_v1) tested M301 and M303 together: NULL** (40 trials; OPEN rc_p 0.31, SETTLE rc_p 0.87).
- The US-open fade won in 2022 and lost in 2024-26.
- The Friday settlement-window fade has about +20 bp gross per trade in both windows, but it is +0.38 bp a day at
  2x and t 1.37.
- Seeds seen only after the run, for a later lane on reserved 2020 bars or forward data: the 09:30 New York fade
  on days the US market is shut (validation t 2.67), and continuation after 10:30 New York (t about −2 in both
  windows).

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

## Auction, order flow and options positioning (owner, 2026-10-21)
The owner listed 21 terms (TPO, VWAP bands, POC and value area, initial balance, HVN/LVN, volume profile, delta,
CVD, absorption, exhaustion, dark pool, gamma, delta, charm and vanna exposure) and asked for data, our own method,
a critical eye, our own Bloomberg and an AI council. The write-up is `docs/AUCTION_AND_FLOW.md`.

**The common thread:** the terms are three families by information:
- **Auction levels** are transforms of bars the lab has already searched hard (R263, R246 NULL). They get one
  family, R290 `auction_v1`, with real session anchors against random placebo anchors, to settle whether sessions
  mean anything in crypto.
- **Order flow** carries trade sides that bars do not. It has partial life here (R185, flow books).
- **Dealer options exposure** is the only family that forces someone to trade. The size is real: BTC gamma notional
  per 1% move is about one hour of Binance perp volume. Its sign was a guess until now, because every Deribit
  option trade since late 2016 carries the taker's side (`data/deribit_trades`, M308).

**Built:** `lab/auction.py`, `lab/orderflow.py` and `lab/exposure.py` (tested), plus two downloads:
- the Binance option history: hourly greeks 2023, which our Black-76 reproduces to 0.06%, and BVOL per minute
  2023-26;
- the Deribit option trade history.

**R290 `auction_v1` is NULL:**
- real session anchors are no more structured than random clocks (p 0.36);
- no auction rule trades: the discovery pick's validation t is −0.96.

**R291 `vpin_v1` is NULL** (the owner's reel on toxic order flow, `docs/QUANTDATA.md`): VPIN from true trade
sides adds no volatility forecast beyond volume, and plain volume flags crash hours better.

**R293 `er_v1` is NULL** (the owner's reel on forecasting tomorrow's efficiency ratio):
- the next UTC day's efficiency is only weakly predictable (AUC 0.537), and today's efficiency alone does as well;
- gating a first-hour trend rule on that forecast makes each trade worse.

Post hoc, the first UTC hour reverses in both windows. That is M315, for unseen data only (2020 in batch 2, or a
forward lane).

**R292 `dealerflow_v1` is done: NULL.** It tested dealer gamma from 41M Deribit option trades, with the taker's side
on each trade.
- It does not improve a HAR forecast of next-day BTC or ETH volatility (DM t −1.23), and it does not sign next-day
  hourly autocorrelation out of sample.
- **Why:** dealers are short gamma on 76-92% of days, and the hedge they need is a fraction of a percent of a day's
  perp volume per 1% move. Open-interest GEX dashboards overstate it, because most open interest nets out.
- **Next on this data was** `charm_expiry_v1`, now run as R296 (below). M316 (post
  hoc) is for unseen data only.

**R295 `optflow_v1` is done: NULL** (15 trials). It covered block prints (M311) and net drift (M313).
- Signed Deribit option flow does not lead the BTC or ETH perp over 1, 4 or 24 hours out of sample, in any of 5
  forms.
- Its gross edges are a few bp per trade, against 17 bp of API round trip.
- R292 and R295 agree. Deribit's taker flow, by gamma or by direction, does not move the perp at hourly or daily
  scale.

**R296 `charm_expiry_v1` is done: NULL** (5 trials). It tested Deribit's Friday 08:00 UTC expiry (M303's dose,
M309, M317).
- R289's settlement reversal does not grow with the position expiring near the money. High- and low-dose Fridays
  swap between the windows.
- The dealers' delta in expiring options moves the perp neither inside the 07:30-08:00 window nor in the two hours
  after it. The sign of the after-08:00 test flips between windows (+1.55, then −1.55).
- That delta is 0.13-0.47% of a day's perp volume at the median.
- With R292 and R295, three Deribit nulls agree: Deribit positions are too small next to Binance perp volume to move
  it at these scales.
- **Still open on options:** M310 (vanna after FOMC, low power), and M289/M175 (pinning, max pain) on the chain
  recorder's true open interest, which needs forward Fridays.

The AI council can only be a forward lane with frozen prompts and a key the owner sets up (M312).

## Factor leads from R282 (2026-10-22)
**R298 `lotcap_v1` is done: NULL** (16 trials, M276). It tested R282's lottery-cluster quintile books with a close-based
cover on each short.
- The best discovery book (age, 24 h, 35% cover; t +1.70) has a validation t of +1.03, against a 2.0 bar.
- Wide covers clip the squeezes without cutting the median, but they added money only in 2024-26.
- The cluster books flip sign between 2021-23 and 2024-26, as R282's vol_mcap did.
- **The age factor ties about 80 pre-2021 coins at its maximum** (`scripts/pitfac_factors.py` counts them from the
  panel start). So the age books' long leg in 2021-24, here and in R282, was an alphabetical slice.
  - Any further age lane needs an uncensored listing date first.
  - Factor plumbing runs should print the tie at each leg's edge.

**Next family: R299, ML cross-sectional rankers on the daily panel (M042).** The panel's 66 columns (funding on six
venues, OI, positioning, basis, Korean premium, caps, on-chain) have never been combined. The old session's ridge and
GBM composite used 13 price features (rank IC 0.01-0.04, NULL).
- Purged walk-forward fits.
- The books are costed at API rates with funding.
- The family is decided by SPA.

## Cross-sections on the daily panel (2026-10-22)
**R300 `intrars_v1` is done: NULL** (24 trials, M318). Ranked from 00:00 UTC, the top 50 perps' first-hour movers
reverse and the late-day leaders keep leading, but no book pays the 34 bp/day round trip reliably.
- The pick (10:00 New York, 3 names, follow) grossed about +70 bp/day in both windows and every year. Its validation
  t is 1.28, and it is negative without its 10 best days.
- Post hoc lead for unseen data only: relative strength into the US morning (M319).

**R301 `qbasis_v1` is done: NULL** (16 trials, M170). Sorting the 5-10 coins with Binance quarterlies on their
annualized basis, or its weekly change, does not rank the perps that follow.
- The pick (long the 2 lowest basis, short the 2 highest, weekly) earned +14.6 bp/day net in 2021-23 and +1.2 in
  2024-26 (t 0.16).
- The sides flip between windows. The basis is about half funding (rank correlation +0.41 to +0.50).

**R302 `fundxs_v1` is done: NULL** (8 trials, M263). The pick (fund3, daily, top 150) earned +25.3 bp/day net in
2021-23 (t 3.32) and −7.2 in 2024-26. It reproduces R276's +10.43 (here +11.2 at 7 bp), and that number is 2021's
price effect. The funding part is steady; in 2025-26 squeezed perps paid their longs about 30 bp/day and fell by as
much. R276 and R190 do not conflict: funding is worth collecting only hedged.

It was frozen as follows (8 trials, M263). R276's reference factor as a book: long the fifth of the universe
paying the least funding, short the fifth paying the most, net of the funding each leg pays.
- The family: fund3 or fund30 × a 1 d or 7 d hold × the top 150 or top 50.
- It splits each book into its price and funding parts. That is the reconciliation with R190's carry that M263
  asked for.
- **Gate 0 on seen data:** R276 read this book over 2021-26 in one piece. A pass earns reserved batch 2 and a
  forward paper lane, not a confirmation.

**R299 `mlrank_v1` passed its frozen rule, and its audit invalidated it** (12 trials, M042).
- The GBM weekly book earned +55.4 bp/day net in 2024-26 (t 4.02), with a rank IC of 0.19. That is too strong for a
  market-neutral book.
- **The cause is coverage survivorship.**
  - KuCoin, Kraken, MEXC, Hyperliquid, Upbit and Bithumb were fetched only for markets live at download time.
  - `n_venues`, `fund_gap7` and `kimchi7` therefore tell the model which coins will later be delisted.
  - KuCoin covers 53-95% of survivors' rows and 0-5% of later-delisted perps'.
- The rule for every lane is in `docs/FEATURE_VINTAGE_INTEGRITY.md`.
- Registry rows R299-R302 are appended. Program trials: 9,478,673.

**R303 `capit_v1` is NULL** (10 trials, M302 and M286). Frozen in 811283d before the run.
- The pick, dip40 h5, earned +670 bp per event in 2021-23 (t 2.08) and −450 in 2024-26 (t −4.58).
- Every hedged dip book lost in 2024-26, and so did the long leg alone. Deep dips kept falling.
- breadth h5 (buy the top 50 after a breadth day) beat the drift in all six years, on too few days (t 1.55). It is
  queued as M322, to be read on unseen data only.
- Program trials: 9,478,683.

**R304 `mlrank_v2` is PARTIAL, and R305 `mlaudit_v1` could not explain it** (7 + 7 trials, M042, gate 0).
- Without the three leaking columns the weekly GBM still earns +58.9 bp/day net in 2024-26 (t 4.21). A GBM on the
  leaking columns alone loses. R299's leak was real but carried nothing.
- **R305 rejected the three obvious stories.** Age, the six risk features and beta did not carry the pick.
  - Without age it still earns +56.1 bp/day.
  - The risk features alone lose, and without them the book earns +62.4.
  - A fixed low-risk score loses.
  - The alpha over the equal-weight universe is +58.4 bp/day (t 4.22).
  - What is left: the GBM's interactions among flow, funding, OI and positioning.
- **It is not tradable as run.** Both windows were read before (R299). The short leg had a name up >100% in a week
  in 15.5% of 2024-26 weeks (COAI +1,850%, 2025-10). Missing OI and positioning (about half the rows) are untested as
  a driver.
- Program trials: 9,478,697.

**R306 `msnr_v1` (M323, the owner's reel on Malaysian support and resistance): NULL, 24 trials.**
- Every book loses in both windows: fade and break, levels 5 or 30 days old, three exits, top 50 perps.
  - Validation: −6.7 to −62.1 bp/day at 1x.
  - The 17 FX, metal and index perps lose too (t −1.3 to −9.6).
- Fading a fresh level is about 0 gross at 24 hours and −13 to −50 bp at 72 hours. Levels break more than they
  bounce.
- With R243, R246 and R263, chart levels on liquid perps are closed. No more level-drawing variants without a new
  reason.
- Program trials: 9,478,721.

**R307 `rrskew_v1` (M174) and R308 `nagel_v1` (M325): both NULL, 24 and 8 trials.**
- **R307:** the Deribit 25-delta risk reversal does not time BTC or ETH by the week.
  - It follows the week before (correlation +0.2 to +0.5) more than it leads the week after (+0.03 to +0.15).
  - With R209, R292, R295 and R296, the Deribit tape has now been read four ways for direction, with no edge.
- **R308:** the reversal after stress days earned in 2021-23 and lost in 2024-26. After stress days the losers kept
  falling, including in the 2025-10-10 cascade.
- Program trials: 9,478,753.

**Next, in order:**
1. **R304's pick goes forward:** three frozen paper lanes on MEXC prices:
   - the pick;
   - the long leg against an equal-weight hedge;
   - the pick with a cover on each short.
   They need a live feature pipeline from the daily Binance metrics archive. The pick also goes into reserved
   batch 2, whose PREREG must fix how rows without metrics (all of 2020) are scored.
2. **The open audit:** a missing-flag refit, and a refit on rows with metrics only, as one frozen lane.
3. **The reels' three lanes are done** (R306-R308, all NULL). `lab/stress.py` (M324) stays as a report for every
   FINDINGS.
4. **The source fix, first half done:** `lab/coverage.py` labels the survivor-only columns and measures any column's
   coverage for survivors against later-delisted perps. `lab/daily.py` stays as is, because it is a frozen input of four
   lanes. Still to do: refetch the survivor-only venues with delisted markets where their APIs allow it.
5. **M322** goes into reserved batch 2's candidate list and gets a forward paper ticket design.
6. **M320 / M321 (owner's reels, 2026-10-22):**
   - MEXC lists NAS100, SPX500 and US30 perps at a 0 / 2 bp fee, and the LSE vault has their index ticks from 2023.
   - First, validate LSE's index bars against an independent close.
   - Then fetch the MEXC index-perp klines.

## Claude leads again; the forward clock (owner, 2026-10-26)

**The owner:** Claude takes the lead. Codex was asked for 100 enhancements because the project felt too narrow; start
from them, and look at how fresh the files are.

**Codex's 100 items** (`experiments/owner_acceptance_v1`, R320), merged into this branch with the rest of PR #49:
- 46 verified, 36 partial, 15 blocked and 3 not selected. None is validated on the market: they are infrastructure,
  checks and accounting.
- Kept: the `python -m lab` commands, the orchestrator with run IDs, the Decimal paper account, strict admission of
  journal rows, and the Control Room's paper datasets.
- Before merging: `registry/rounds.csv` was only appended, 143 frozen PREREGs and 160 input pins verify, and `python -m
  lab integrity` reports 0 errors.

**The forward clock was broken.**
- `forward_loop.sh` ticked at minute 6, but R200 computes an hour 12 minutes after its bar closes. Every hour waited
  for the next tick (66 minutes), so `forward_lag` counted it late by construction. That is one reason strict
  on-time days stayed at 0. The other is the four-day outage from 10-22 to 10-26, when the container was down; the
  hourly routine has been switched off since 10-23 20:07.
- Now: the full tick runs at minute 15, R200 alone at minute 45, and R200 starts first. Each orchestrator task records
  its own code snapshot, so a commit during a tick blocks nothing.
- The 15:00 hour of 10-26 was journaled at 16:19, 20 minutes after its close. 10-27 can be the first strict day, if
  the loop runs all day.

**Freshness (owner item 86).** `lab/freshness.py` gives one row per recorder, loop and forward lane: its last write
against its cadence (FRESH, LATE, STALE, MISSING). For R200 it also gives the newest hour and how long after the close
that hour was computed. It is the Control Room's Freshness card and `python -m lab.freshness`.

**Forward record so far (R200, on-time days by date, 10-19..10-25):** book A -5.9%, book B -3.6% net over 7 days. The 18
backfilled days before the freeze (+22% for A) are not evidence.

**Next, in order:**
1. **Keep the clock running.** The loop must run day and night for strict days to count. The owner decides how:
   switch the hourly routine back on, or run the loop on the owner's own computer.
2. **R332 `mlrank_v3`:**
   - R304's PARTIAL may come from the metrics look-ahead. `data/metrics_1h` was fetched only for days a coin was in
     the old top 100 within the next 35 days.
   - The complete refetch is running. Then the v2 panel, the plumbing run, the claim on #7, the freeze and the run.
   - R304's forward lanes wait for R332's answer.
3. **Reserved batch 1 on 2026-11-03,** as frozen (R286).
4. **Unblock Codex's blocked items with data already recorded:**
   - 17: the funding forecast error, from the funding board snapshots;
   - 21 and 23: executable carry and spot-perp costs, from R224's depth;
   - 36: the reserved samples and batch 1;
   - 38: the survivorship-free panel;
   - 91 and 93: forward candidates in the common paper account, once admission evidence exists.
5. **Roles.** Codex audits, tests and builds tools on its own branch through PRs. Claude is the single writer of the
   journals, the registry rows and the forward loop. R-ids are claimed on #7 before a freeze.

## Measure first (owner, 2026-10-26 evening)
The owner: the methods so far do not make money. Try other ways, but measure them before launching anything.

**What that means here**
- **A new idea starts as a gate-0 measurement on seen data,** frozen like any lane. It reports three things:
  - the gross per trade;
  - the one-way cost at which it breaks even;
  - the book at each reachable route's cost: MEXC web, Lighter API and MEXC API.
- **Nothing goes forward or real from that step.**
- **Only a lead that can move on gets new days** (forward paper or a reserved batch), and only with the owner's go.
  That means a lead whose break-even clears a route the owner can actually use.

**Measured today**
- **R333** (the owner's break-or-rebound model, M412) is frozen at `ac077d2` and running. It reports those three lines.
- **Cost map:** `docs/EDGE_SCOREBOARD.md`, "Where cost alone decides".
  - Seven families failed only on cost; most others failed on gross.
  - The strongest lead is R300's US-open leaders book: 12 orders a day, and a break-even of 17-18 bp a side against
    about 3-5 bp on MEXC web.
- **The web fee itself moves.** The default group was 0/2 bp (maker/taker) on three of five snapshot days and 1/4 bp
  on two. 57 crypto contracts were 0/0 on all five.
- **The forward clock broke again today.** A container restart stopped the loops for hours; 10-26 has 14 of 17 hours
  late. 10-27 can still be the first strict day.

**Proposed, not started (the owner decides)**
1. **A frozen manual-web forward lane for R300's pick.** It is paper only, and needs about 2 years to an expected t of 2.
2. **Lighter-API paper versions of the cost-limited hourly families:** R186 M2, R249, R246 and R287.
3. **R332, then reserved batch 1 on 2026-11-03,** as planned. Neither launches anything.
