# PREREG: stock_tugofwar_v1, the overnight-versus-intraday tug of war on MEXC's US-stock perps

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R435
- **Owner (single writer):** Claude (a forked worker of the session's orchestrator), 2026-11-10
- **Date registered (UTC):** 2026-11-10

Method: M492 (new, 2026-11-09). Source: Lou, Polk and Skouras (2019), "A tug of war: Overnight versus intraday expected
returns", JFE 134(1). The paper was not re-read for this lane; its claim is the prior, not evidence.

## Question
Across the most traded MEXC US-stock perpetuals, does a stock's mean overnight return over the last 20 sessions predict
its next overnight return? If so, does a long-short book that holds only the overnight leg earn a positive net return
after the measured fee, spread and funding? Falsified if the primary book's 1x net mean is ≤ 0 or its block-bootstrap
95% interval includes 0.

## Why this could pay, and why fast firms might leave it
- **Who pays:** in the paper's story, the intraday traders who reverse the overnight moves (institutions trade
  intraday, individuals at the open).
- **Why it might be left here:** these perps trade 24/7 on a crypto venue, with thin size. Median daily quote volume
  per contract is about $108k, and the top 30 trade about $0.2-50M a day.
- **Priors against:**
  - M195 (R235) found no overnight drift on QQQ alone.
  - A long-short daily book pays two round trips across two legs, about 11 bp a day at 1x on the liquid names
    (plumbing below).
  - The paper's effect is a few bp a day.
- **Not a repeat:** no lab lane has scored a cross-section of these stock perps. R306 read only MEXC index,
  commodity and QQQ perps, on 4-hour candles, for another question. MEXC TradFi contracts are not reserved
  (`docs/GATES.md`).

## Universe
- **Candidates:** every type-2, state-0 contract in MEXC's contract snapshot of 2026-10-22 (`contracts.json` below):
  - bases ending in `STOCK`, without the funds `QQQSTOCK` and `DIASTOCK`;
  - plus the US single stocks listed without the suffix: `NVIDIA`, `TESLA`, `ROBINHOOD` and `COINBASE`.
  - That gives 403 candidates.
- **US class, point-in-time.** On the contract's MEXC index-price hourly bars from its first bar to 30 days after
  it, compare two shares of the total absolute hourly index move:
  - the share in NYSE regular hours (bars opening 09:00-15:00 New York, NYSE trading days);
  - the share in Tokyo cash hours (bars opening 09:00-14:00 Tokyo, weekdays).

  US if the first share is larger. The class uses only data from before the contract can first enter the universe.
  320 of the 403 are US; the rest are Japanese, Korean, Taiwanese, Hong Kong and mainland Chinese names.
- **Daily universe** at decision session d. A US-class name enters if all of these hold:
  - it has been listed at least 30 days (first hourly bar ≤ close of d − 30 days);
  - its signal exists (at least 15 valid overnight returns among the last 20 sessions; 45 of 60 for L = 60);
  - its close price at d exists;
  - its trailing quote volume exists: the mean daily USDT `amount` over the 20 UTC days strictly before the UTC day
    of d's close.

  The top N = 30 by that trailing volume are kept. No trade if fewer than 15 names are eligible.
- **Survivorship:** the candidates are the contracts listed on 2026-10-22. Stock perps delisted before then are
  missing; 8 stock contracts dropped between the 10-19 and 10-22 snapshots, e.g. CAVA, CELH, DTE and GPN. This is a
  current-survivor, venue-own universe:
  - ranking by trailing volume limits the effect but does not remove it;
  - the verdict is therefore a gate-0 screen. A PASS earns only a forward paper lane under a new id; it admits no
    holdout or real-money claim.

## Data
All inputs are held locally. No fetch is made. Every file is listed with its sha256 in `inputs_manifest.json`
(1,316 files), and the runner checks all of them, and the exact file set, before reading anything:
- **Prices:** `data/mexc_tradfi/klines_1h/<symbol>.parquet`, MEXC contract hourly bars (`t` = bar open, ms). The
  history runs from 2025-04-01 or listing to the fetch end, 2026-10-22 12:00 UTC (`scripts/fetch_mexc_tradfi.py`,
  run manifest `runs/1792671203016652636`). The price at instant T is the close of the bar opening at T − 1 h, and
  an observation is missing if that bar is missing.
- **US class only:** `data/mexc_tradfi/index_price_1h/<symbol>.parquet`.
- **Funding:** `data/mexc_tradfi/funding/<symbol>.parquet`, the settled rates (`t`, `rate`).
- **Fee:** the per-contract `taker` field of `contracts.json`. It is 2 bp on 316 of the 320 US names and 0 on 4.
- **Spread:** `data/recorders/mexc_ticker/<day>/<hour>.parquet`, 2026-10-20 to 2026-11-06 (105 files), the best bid
  and ask of every contract at each snapshot.
  - The half-spread is the per-contract median over snapshots: (ask − bid) / mid / 2.
  - All 320 US names were recorded. A name without a record would get the 90th percentile of the recorded medians,
    58.8 bp.
  - These are current costs applied to the history, not historical quotes.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| close C_d | klines_1h close | MEXC contract, USDT price | close of the bar opening 15:00 New York | instant 16:00 NY | yes, at the decision | current-survivor list of 2026-10-22 | missing bar: missing value |
| open proxy O_d (o+30 / o-30) | klines_1h close | same | close of the bar opening 09:00 / 08:00 NY, i.e. the price at 10:00 / 09:00 NY | that instant | used only as an exit, or inside the signal for earlier sessions | same | missing: missing value |
| overnight ON_d = ln O_d − ln C_{d−1} | O, C | same | previous NYSE full session only; missing across an early close | at O_d | yes for every d' ≤ d at the close of d | same | missing if either price is missing |
| intraday ID_d = ln C_d − ln O_d | O, C | same | same session | at C_d | target only | same | same |
| signal S_d (L = 20 or 60) | ON | same | mean of the available ON over sessions d−L+1..d, needing 15 of 20 or 45 of 60 | at C_d (ON_d was known at O_d) | yes | same | too few: no signal |
| trailing volume A_d | klines_1h amount | MEXC, USDT | mean daily sum over the 20 UTC days strictly before the UTC day of C_d | before C_d | yes | same | fewer than 20 days: missing |
| listing age | first klines_1h bar | MEXC | first bar ≤ C_d − 30 days | before C_d | yes | same | — |
| US class | index_price_1h close | MEXC index, USDT | first 30 days after the first contract bar | before eligibility | yes | same | no move in window: not US |
| funding F | funding rate | MEXC settled rate | settlements in (entry, exit] | known after settlement; charged as cash | cost, not a feature | same | none settled: 0 |
| half-spread hs, fee | ticker bid/ask; contracts taker | MEXC | 2026-10-20 to 11-06 / 2026-10-22 snapshot | after the sample | cost only, never a feature | current | see Data |

## Rule
- **Sessions:** NYSE trading days by `lab.sessions.NYSEHolidays`, from 2025-07-01 to 2026-10-22.
  - Days with a 13:00 close are not sessions: 2025-07-03, 2025-11-28 and 2025-12-24.
  - The next overnight return across such a day is missing.
  - 328 sessions, 324 of them following a full session.
  - The close is 16:00 New York and the open proxy is 10:00 (o+30) or 09:00 (o−30) New York, all on the hour, with
    daylight saving.
- **Legs:** rank the day-d universe by S_d. With k = max(3, ⌊n/5⌋), the top k form `top` and the bottom k form `bot`.
  - **B1, overnight momentum (PRIMARY with L = 20, o+30):** at C_d, long `top` and short `bot`; exit at
    O_{d+1}. Return ON_{d+1}.
  - **B2, intraday reversal:** at O_{d+1}, long `bot` and short `top` (the legs formed at C_d); exit at C_{d+1}.
    Return ID_{d+1}.
  - **B3, both:** B1 + B2, no netting of trades.
- **Book return:** the sum of the two equal-weighted legs, i.e. per $1 long plus $1 short:
  - mean over long names of (r − c − F) plus mean over short names of (−r − c + F);
  - c = 2 × m × (fee + hs) per name;
  - F = settled funding in (entry, exit]: a long pays a positive rate, a short receives it.
  - Funding is not scaled by m.
  - A name whose exit price is missing drops from its leg that day; a leg with no valid names voids the day.
- **Costs:** m = 1, 2, 3 at the contract's listed (web) fee.
  - An API line uses 8 bp instead: the API taker fee since 2026-06-01 (`docs/MEXC_EDGES.md`).
  - The owner places orders by hand (AGENTS rule 6), so the web fee is the execution mode for 1x.
- **IC:** each session's Spearman correlation between S_d and the next ON (persistence) and the next ID (reversal),
  over the day's universe, with at least 5 valid pairs. Mean IC with a Newey-West t at lag 5.

## Search space and trials
- **IC:** 2 targets × 2 lookbacks (20, 60) × 2 open proxies (o+30, o−30) = 8.
- **Books:** 3 books × 2 lookbacks × 2 proxies = 12.
- **Total: 20 trials.** Costs (1x/2x/3x, API) are sensitivities, not trials.
- N = 30, the quintile, the 30-day listing age, 20 volume days and the minimum of 15 names are fixed, not searched.

## Inference and verdict (primary only)
- **Days counted:** traded days are decision sessions where B1 has both legs (the 1x frame); every cell is scored
  on those days.
- **Bootstrap:** blocks of 5 consecutive traded sessions, 10,000 replicas, seed 435, a 95% percentile interval and
  p = share of resampled means ≤ 0.
- **PASS needs all of:**
  - at least 120 traded sessions;
  - a 1x net mean > 0, with the interval's lower bound > 0;
  - a 2x net mean > 0;
  - a positive 1x mean in each half of the traded sessions.
- **INCONCLUSIVE:** fewer than 120 sessions. **NULL:** anything else.
- **Also reported:** the primary's p against Bonferroni 0.05 / 20 = 0.0025, every cell's gross, net and interval,
  the API line, the median leg size, and the leg names' trailing volume. A non-primary cell cannot change the verdict.
- **Capacity:** at $10k ($5k a side, about 6 names a leg) each position is about $800, against a median daily quote
  volume per name that the run reports. No depth was recorded, only the touch.

## Power
- **Sample:** plumbing counts 252 decision sessions with at least 15 eligible names for L = 20, from 2025-10-17 (229
  for L = 60, from 2025-11-19), with a median of 65 eligible names. N = 30 caps the universe at 30.
- **Detectable effect:** with a long-short daily SD of about 1.2% (an assumption: single-stock overnight SD of 1.5-2%,
  6 names a leg), the standard error over ~250 sessions is about 7.6 bp. A mean of about 21 bp a day is detectable at
  80% power and two-sided 5%.
- **What it means:** the paper's few bp a day is undetectable here. This lane is a futility screen for effects below
  ~20 bp a day; a NULL does not exclude a small effect.

## Pre-freeze reads (disclosed)
- **What was read on real data before the freeze:**
  - contract metadata, fees and listing dates;
  - each candidate's index-price bars, as absolute hourly moves for the US class;
  - hourly quote volumes and their distribution;
  - the ticker recorder's bid/ask spreads;
  - counts of eligible names per session (`plumbing.json`, sha below).
- **What was not:** no overnight or intraday return was computed, summarised or printed. The plumbing computed
  signal availability (finite or not), never its value. No book, IC or outcome was looked at.
- **Tests and dry run:** both ran on synthetic data, with `pandas.read_parquet` and `read_csv` refusing any path
  outside the test's temporary folder.
- **One classifier change:** the class first used each contract's whole index history (321 US). Before the freeze it
  was changed to the point-in-time window above (320 US). It is a class rule, not an outcome.

## Multiplicity
- **Program trials before this lane:** 9,784,937. Read the result against `registry.program_trials()`.
- **This lane:** 20 trials, all counted whether they pass, fail or are void.
- **No across-family selection control:** a PASS is exploratory and leads only to a forward paper lane.

## Evidence lineage and admission
- Canonical method id: M492. No parent round; the nearest are M195/R235 (QQQ overnight drift, NULL) and M321
  (index-perp weekend gap).
- Samples already seen: none of these stock-perp returns. The `docs/GATES.md` sha256 is
  `ed486814256194323dc2ee7d3375d16f8971a6f7b1775ddb2d6c9e476bf30070`.
- Gate requirements not met: a survivor-only universe; spread costs measured after the sample; no strict on-time
  forward clock; no leave-two-coins-out; no dependent-null calibration. So the lane-native verdict is gate 0 and
  admits nothing beyond a forward paper proposal.

## Stop rules
- **One run.** A crash after the freeze abandons the lane: no edit and no rerun under this id.
- **After the result:** no new lookback, proxy, universe size, filter or cost assumption. A changed idea is a new lane.

```inputs
5ae2f585c3e7fa1f3da39238e6344aedbdf1565799a15bed768d42b564ac9f22 experiments/stock_tugofwar_v1/inputs_manifest.json
97ab0003ffefae8547818234cad0297ba212dbcd5c4de3d86ef946b4c4a0c78d experiments/stock_tugofwar_v1/plumbing.json
4efee79393d7f06db6e8065e707c297e5059fc3dc8705ec480ee07cbcdbf2f3c scripts/run_stock_tugofwar.py
30cf483d6aa994dc2e69b0b6599211b8818e700f88cb400ccbf4b8b9d405898f tests/test_run_stock_tugofwar.py
ed486814256194323dc2ee7d3375d16f8971a6f7b1775ddb2d6c9e476bf30070 docs/GATES.md
```
