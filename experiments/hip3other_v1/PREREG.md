# PREREG: hip3other_v1 (R476). Does R475's stock-perp funding carry hold on the other HIP-3 deployers?

- **Registry id:** R476
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M530, a replication of R475 (`experiments/hip3stock_v1/PREREG.md`, sha256 `14434bf9`) on new venues. This file
is frozen by `lab.prereg.freeze()` before the data are fetched and before R475's result exists. After the freeze it is
never edited.

## Question
- R475 shorts trade.xyz's US-stock perps with high trailing funding and holds the same stocks. Its rule was set on
  xyz alone.
- Here the same frozen code, parameters and samples run on the US-stock perps of every other HIP-3 deployer.
- Does sample A (2026-01-16 .. 2026-07-22) earn at least 2 points a year over the 13-week T-bill, with Newey-West
  t ≥ 2.0 and a positive excess at 2x cost?

## Why run it
- **New funding data, never ranked:** these deployers' funding in A has not been read by any lane or scan.
- **Different funding rules:** the deployers set their own funding (xyz halved Hyperliquid's default on 2025-12-19).
  The default, 0.01% per 8 h with no premium, is about 10.95%/yr. R475's entry bar (12%/yr) is applied
  unchanged, not re-tuned to any venue.
- **Deployer exits:** three of the five A-period deployers closed in June 2026 (below). The book meets each
  shutdown through R475's rule: a held name with no mark left is closed at its last mark. FINDINGS reports what the
  exits cost.

## What the author has seen
- **Hyperliquid perpDexs and meta (2026-11-12):** xyz, flx, vntl, hyna, km, abcd, cash, para, mkts and io.
  - Every market on flx, vntl, hyna, km, abcd and cash is delisted; mkts has one live market, para 33, io 15.
  - US-stock names:
    - flx: TSLA, NVDA, CRCL, COIN.
    - km and mkts: BABA, TSLA, AAPL, GOOGL, NVDA, MU, PLTR, BMNR, RTX.
    - cash: TSLA, NVDA, HOOD, GOOGL, INTC, AMZN, MSFT, META and CAR.
    - para: 19 names (AVGO, COHR, GLW, CRDO, LRCX, NET, STX, IREN, VST, TER, AAOI, CIEN, RDDT, CRWD, MELI, SMCI,
      SOFI, TTWO, CIFR).
    - io: SNDK, IONQ, NBIS, GPRO, NVDA, AAPL, CRCL, GOOGL, MU, META, INTC.
  - Live open interest: para:TTWO about $3.2M; the rest of para under $1.1M each; io:NVDA $6.3M, io:SNDK $4.4M.
- **Spans of five probes** (first and last 4-hour candle, first funding print; no rate or price printed):
  - flx:TSLA: 2025-11-13 .. 2026-06-20.
  - km:NVDA: 2026-02-11 .. 06-16.
  - cash:HOOD: 2026-01-28 .. 07-02.
  - io:SNDK: from 2026-08-19.
  - para:TTWO: from 2026-09-03.
  - A is therefore mostly Felix, Kinetiq and Dreamcash, and B mostly Paragon and io.
- **Paragon's funding in B (2026-09-17 .. 11-12)** was in R475's 8-week scan. Annualized means on the stock names:
  - TTWO 59%; CIFR 22%; IREN 19%; COHR 19%; VST 16%; STX 15%; GLW 14%; SMCI 13%; CRDO 11%.
  - Most medians were 6.57%/yr.
  - io's funding was never read.
- **Web (2026-11-12):**
  - Felix's HIP-3 dex shut down on 2026-06-19/20.
  - Ventuals wound down in June 2026.
  - HyENA was delisted.
  - Paragon launched on 2026-04-02 with crypto index perps.
  - EntropyIO (io) lists pre-IPO and stock perps.
  - Trade.xyz holds over 90% of HIP-3 open interest.
  - Sources: kucoin.com and htx.com news, cryptobriefing.com, defillama.com.
- **Code:** run only on synthetic data (`tests/test_hip3other.py`).

## Data (`scripts/fetch_hip3other.py`, run once after this freeze)
- **Universe:** every HIP-3 dex in perpDexs except xyz, with delisted markets. R475's filter applies: Yahoo calls
  the ticker an EQUITY in USD on a US exchange.
- **Names:** each listing is named <DEX>_<TICKER>, so the same stock on two deployers is two markets. R475's
  identity check then drops ticker collisions.
- **Fetched:** hourly funding and 4-hour candles from 2025-10-01 to 2026-11-12, Yahoo closes, and ^IRX.
- **Manifest:** sha256 of every file; provenance goes in `docs/provenance/hip3other.json`.

## The book, samples and verdict
- **R475's frozen code** (`run_hip3stock.load`, `book`, `weekly`, `stats`, `verdict`), with its `decide` variant:
  5 slots, enter at ≥ 12%/yr, exit below 6%/yr, M = 1/3.
  - Marks: 20:00 UTC 4-hour candle open against the stock close.
  - Costs: 5 bp stock, 2.9 or 11 bp perp by today's growth-mode flag, 10 bp transfer.
  - Liquidation on 4-hour highs, the split guard, and the bill.
  - Book from 2026-01-16 to 2026-11-06.
- **Samples:** A = weeks ending by 2026-07-22 (decides); B = later weeks (reported).
- **PASS:** A's excess ≥ 2.0 points, NW t ≥ 2.0, 2x excess > 0. **PARTIAL:** excess > 0. **NULL:** excess ≤ 0.
- **INCONCLUSIVE:** fewer than 20 weeks with a slot held in A. This is a likely outcome: the A deployers traded
  for 18-24 weeks inside A, and a name enters only above 12%/yr.
- **Reported:**
  - `slots10` and `enter20`, as in R475.
  - B, with io's trades apart from Paragon's.
  - Trades and exit reasons per deployer.
- **What it earns:**
  - The A venues no longer exist, so a PASS cannot become a forward lane on them.
  - It supports M530 across deployers. Paragon and io could join a forward lane that R475 earns, under a new id.
  - A NULL or INCONCLUSIVE is recorded as such and does not change R475's verdict.

## Power
- No funding level for these venues in A has been read, so no effect size is assumed.
- The noise model is R475's. Assumed weekly book sd 0.15-0.3%; se of the annualized mean over about 22 active
  weeks: 1.7-3.3 points.
- Only a large carry (about +5 points or more) passes with good probability.

## Trials
- 3 configurations computed (decide, slots10, enter20); one decides. Registry trials 3.
- Program trials: 9,785,253 before this lane, 9,785,256 after.

## Risks (as R475, plus)
- **Deployer exit:** a HIP-3 deployer can delist every market at short notice. A position is then settled at the
  venue's price, not at the paper's last 20:00 UTC mark.
- **Thin books:** the live stock markets on para and io hold under $7M of open interest each. The paper book has
  no size; FINDINGS reports the median daily traded notional of the names held.
- **Fee schedules:** each deployer sets its own fee share. The paper charges R475's 2.9 bp (growth mode) or 11 bp.

## Code
```inputs
7d16aa61bad9d3176b434d9ca40baf1f601344d0cc2c0e37af9d6318bea26dfc  scripts/run_hip3other.py
303fbe81dd5822daebc425d417e6e1b470f7c1cb8b21e65609f1036afbeb1580  scripts/fetch_hip3other.py
35bcf8826194a05645bc2a157a381f9dc6dd25924faafc4283d1f80368a0b6e0  tests/test_hip3other.py
a3f7e3e9b90f6371fe2577617a692068c73fdaa8081a3b5fa84cf68b6110fe77  scripts/run_hip3stock.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
53ccaeb382362178a06abb3f88c53e009d0670c28b7b77bd3ef67151215a48e6  tests/test_hip3stock.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```

## Evidence lineage and admission
- **Method:** M530. **Related:** R475 (same rule on xyz), R474, R470.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one pre-named decision, trials counted, costs at 1x, 2x and 3x, unread decision data, hashed public fetch.
  - Not met: measured costs, forward evidence, live venues in A.

## Stop rules
- One run after the fetch. Nothing is retuned; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/hip3other_v1/results/`.
