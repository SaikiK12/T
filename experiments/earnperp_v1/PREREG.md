# PREREG: earnperp_v1 (R461). After an out-of-hours earnings release, does a 24/7 stock perp keep its first move?

- **Registry id:** R461
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

Method M513, from idea wave 4 (2026-11-11). Frozen by `lab.prereg.freeze()` before any price, reaction or return of a
stock perp around an earnings release is computed, and before sample B's bars exist on disk. After the freeze this
file is never edited; a changed idea is a new lane.

## Question
When a US company files its earnings release (SEC 8-K, Item 2.02) after the cash close or before the open, its
single-stock perpetual trades while the cash market is shut. Does the move the perp makes in the first hour or
two **continue, or reverse,** by the next cash open and the next cash close? Is it by more than a Hyperliquid xyz
round trip?

## Why this lane
- Stock perps on Hyperliquid's xyz markets and on Lighter can be traded from France. MEXC lists over 400 of them,
  with hourly history from 2025-07 (`data/mexc_tradfi`). MEXC itself cannot be reached from France, so it serves here
  as the price record only.
- The perp is thinner than the stock's own after-hours market. Its first reaction to a report could under-shoot or
  over-shoot where the cash market opens. The research lens found no measured effect: its earnings searches failed.
  Weekend studies (Allium, Binance Research; see `research/intake/idea_wave4_20261111.md`) report that perps sit
  13-50 bp from the cash open. Those are context, not evidence for earnings nights.
- EDGAR gives each filing's acceptance time to the second, free (checked on Apple: 16:30 New York in summer and
  winter).
- Distinct from M222 (post-earnings drift over days, skipped for paid data) and from R432 (weekend reopen).

## What the author has seen
- **Filings.** `scripts/fetch_edgar_earnings.py` wrote 1,735 8-K Item 2.02 filings, from 2025-06-01 to the fetch
  (2026-11-11), for 288 of the 405 tickers with a MEXC single-stock perp:
  - 81 tickers are unmapped, mostly foreign issuers and ETFs;
  - 36 have no such filing.

  The author looked at counts only, by quarter and by New York session (amc, bmo, other), and at the plumbing counts
  below.
- **Bars.**
  - Hourly bar times only, to count perps listed before each filing: median first bar 2026-07-22; 35 perps listed
    before 2026-01-01.
  - The median traded amount by New York hour, for four perps (AAPL, MSFT, NVDA, TSLA). Off-hours amount is 5-20% of
    the 09:00 hour's, and the perps trade every day of the week.
  - While checking the MEXC kline format: five AAPL hourly bars of 2026-10-18 (a Sunday, no filing near it), and 24
    SPX500 bars of 2026-10-01, compared with the archive (identical).
  - **No price, reaction or return around any filing has been computed or looked at.**
- **Code.** The rule and runner were exercised only on synthetic worlds (`tests/test_earnperp.py`, including an
  end-to-end run with a planted continuation).

## Samples
- **A, decides.** Filings accepted before 2026-10-21 00:00 UTC, priced on `data/mexc_tradfi/klines_1h` (held before
  this freeze; every file matches `docs/provenance/mexc_tradfi.json`).
- **B, confirms.** Filings accepted from 2026-10-21 to 2026-11-09 23:59 UTC: the bulk of the third-quarter season.
  - B is priced on `data/mexc_stock_post/klines_1h`, fetched **after this freeze** by the frozen
    `scripts/fetch_mexc_stock_1h.py`. The symbols are those in `experiments/earnperp_v1/sample_b_symbols.txt`; the
    window runs from 2026-10-14 to 2026-11-11 00:00 UTC.
  - B's manifest is written by the fetch and quoted in the FINDINGS.
- **Plumbing counts** (`--plumbing`, bar times only):
  - usable after-close (amc) filings: A 227, B 100 (B may grow once bars of perps listed after 2026-10-22 exist);
  - usable before-open (bmo) filings: A 130, B 85.
- A filing is usable when its perp has bars from at least two days before the filing. A repeated ticker, session and
  next-session day is dropped.

## The rule (scripts/earnperp_rule.py)
All times New York; "trading day" is the NYSE calendar of `lab/sessions.py`. Early closes at 13:00 are
2025-07-03, 2025-11-28, 2025-12-24, 2026-11-27 and 2026-12-24.
- **Sessions:**
  - amc: acceptance from the cash close (16:00, or 13:00 on an early close) to 21:00 on a trading day D;
  - bmo: acceptance from 04:00 to 09:30 on a trading day D;
  - any other acceptance time is skipped and counted.
- **Reference R:** the cash close of D (amc), or of the trading day before D (bmo).
- **Entry E:** the acceptance time rounded up to the hour, plus one hour (at least 60 minutes after the filing).
- **Next session N:** the trading day after D (amc), or D itself (bmo).
- **Exits:** X1 = N 10:00 (half an hour after the cash open); X2 = N's cash close.
- **Price P(T):** the open of the first hourly bar that starts in [T, T + 2 h). On MEXC that open is the previous
  bar's close.
- **Reaction:** r0 = 1e4 ln(P(E) / P(R)) and s = sign(r0). r0 = 0 is dropped.
- **Continuation:** c_k = s * 1e4 ln(P(X_k) / P(E)), in bp before costs. A positive value means the first move
  continued; a negative value means it turned back.
- A horizon whose exit is not after E, or whose price is missing, is missing for that event.
- **Hedged continuation (diagnostic):** c_k - s * 1e4 ln(SPX500(X_k) / SPX500(E)), using MEXC's SPX500_USDT perp.
- **Subsets:**
  - `all`;
  - `pos` (s > 0) and `neg` (s < 0);
  - `big`: |r0| at or above the 2/3 quantile of sample A's |r0| for that session. The cut is computed from A only and
    applied to A and B.
- **Test:** a two-sided sign-flip randomization test of mean continuation = 0.
  - Signs are flipped together within each next-session day N, so the filings of one busy day count as one unit.
  - 200,000 draws, seed 461; p = (1 + hits) / (1 + draws).
- **Decision cells:**
  - D1: amc, X2 (next cash close), `all`, unhedged, sample A.
  - D2: amc, X1 (next cash open + 30 min), `all`, unhedged, sample A.
  - Holm adjustment over their two p values.

## Trials
- Cells: 2 sessions x 4 subsets x 2 horizons x 2 (raw, hedged) = **32**, each read in A and in B. Sample B replicates
  the same 32 cells and adds no hypothesis.
- Registry trials: 32.
- Program trials: 9,785,037 before this lane, 9,785,069 after.

## Decision
The trade direction is the sign of the cell's sample-A mean: follow the first move if positive, fade it if negative.
- **PASS:** a decision cell meets all of these:
  - at least 100 events in A;
  - a Holm-adjusted p of at most 0.05;
  - |mean| above 2 cost units (60 bp), so the 2x net is positive;
  - in sample B: at least 30 events, the same sign, and |mean| above 1 cost unit.
- **PARTIAL:** the same cell has at least 100 events in A, a Holm p of at most 0.05, |mean| above 1 unit, and the same
  sign in B with at least 30 events.
- **INCONCLUSIVE:** neither decision cell has 100 events in A.
- **NULL:** otherwise.
- The best state of the two cells is the lane's verdict. Nothing else is decided on.
- A p of 0.05 is weak against 9.8 million program trials. The FINDINGS read any hit against `program_trials`. A PASS
  earns a forward paper lane on xyz, never a trade.

## Costs (1x, 2x, 3x)
- One cost unit is a **30 bp** round trip of price:
  - xyz's standard HIP-3 taker fee, 9 bp each way (R451's assumption; growth-mode cuts not counted);
  - 10 bp for the spread and slippage of two off-hours fills on a thin stock perp (an assumption, not measured);
  - 2 bp of funding for a hold of under a day.
- 1x, 2x and 3x subtract 30, 60 and 90 bp from |mean|. The mean is also the break-even cost.

## Power (stated before the run)
- MDE80 = 2.8 sd / sqrt(n), reported for every cell.
- If the sd of an overnight continuation after earnings is about 400 bp (an assumption): with about 227 amc events,
  D1 detects about 75 bp, slightly above the 60 bp 2x cost. Clustering by day widens the test.
- The lane screens for a large continuation or reversal, not a small one.

## Code
```inputs
4b235017a007d9f263b2e7402e49b8463c0c7f0b02ba76610b72bbcd79b8fbcd  experiments/earnperp_v1/events.csv
4b9d29f36345fd7e1524b3d9e2ee8b776cce8583a85f1b87b3a5994a19346a03  experiments/earnperp_v1/sample_b_symbols.txt
6a9c4286ac1a12a391c0ebaca022510fb40d59affff9eb56ce71d44246a64ca1  scripts/earnperp_rule.py
dbe45744b41bcfbc590e04f4ae03f04946e1c863c6d7fac3c2a76128fdfc30a8  scripts/run_earnperp.py
9ebf32aae758939a9d584b9c1825b9b21e0df5f7f4d9dbed372593dafab85b1f  scripts/fetch_edgar_earnings.py
300f05acf378e7723c913787f2786c7701f25110f2d126255190f2206efa5bde  scripts/fetch_mexc_stock_1h.py
5267b60a05fd06c12c673034229d7d3f18d27901c6ca37720bbe476fd9b59ab8  tests/test_earnperp.py
8249fd5b0cd7bd445e0968232864ea29a817e4725c52e77d2c2cd2e364827db3  docs/provenance/edgar_earnings.json
8d977757a5c6eb0bcac296fa9e51f0f1c1639e4189313c7271e7dd4ca8d68705  data/edgar_earnings/manifest.json
3ed2c254769463b0ae6849f8352ab1de58b7c1fd3eb04be0804eb0dcce5c18e1  docs/provenance/mexc_tradfi.json
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
```
The runner also re-hashes each bar file it reads: sample A files against `docs/provenance/mexc_tradfi.json`, and
sample B files against `data/mexc_stock_post/manifest.json`.

## Feature lineage and point-in-time availability
- **Filing time and session.**
  - Source: EDGAR `acceptanceDateTime` (UTC) of an 8-K with Item 2.02.
  - Available at acceptance; entry is at least 60 minutes later. Point-in-time.
  - Missing data: none; a filing exists or it does not. 8-K/A and 6-K are not used.
- **r0 and s.**
  - Source: MEXC perp hourly opens at R and E.
  - Available at E. Point-in-time.
  - Missing data: the event is dropped and counted.
- **`big` cut.**
  - Source: sample A's |r0| distribution.
  - Not available at decision time (look-ahead), so it is a diagnostic only.
- **c_k and the hedge.**
  - Source: MEXC perp and SPX500 opens at X_k.
  - Outcome only.
  - Missing data: the horizon is missing for that event.

The universe is the stocks with a MEXC perp listed today (survivor-only: perps delisted before 2026-10-22 are absent).
A filing counts only while its perp existed. This is a per-event time-series test, not a cross-section, and the
survivor limit is stated.

## Evidence lineage and admission
- **Method:** M513. **Parents:** none; no lane has read stock perps around filings.
- **Decision group:** M513 on MEXC prices; one verdict from the two pre-named cells.
- **Samples:** A (before 2026-10-21) has never been read for this question. B is fetched after the freeze and is
  fresh.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: pre-named cells; Holm over 2; 32 cells counted; costs at 1x/2x/3x; power stated; a fresh confirmation sample.
  - Not met: gate 1 (a forward, strict on-time sample on the trade venue) and gate 3 (account risk). The result stays
    exploratory.

## Stop rules
- The lane ends with its first complete run on A and B. Nothing is retuned afterwards (no other session window, lag,
  exit, subset, cost or sample); a changed idea is a new lane.
- **A PASS or PARTIAL earns** a forward paper lane on Hyperliquid xyz (or Lighter) stock perps, under a new id: live
  EDGAR polling, measured xyz book costs, its own PREREG and at least 60 new events before any verdict.
- **A NULL earns** M513 closing NULL for this form. The `big`, `pos`/`neg`, hedged and bmo cells are diagnostics and
  do not reopen it.
- No orders, no money, no credentials. The run reads files and writes `experiments/earnperp_v1/results/`.
