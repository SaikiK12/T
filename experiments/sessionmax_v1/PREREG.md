# PREREG: sessionmax_v1 (R490), session-decomposed MAX on 24/7 crypto perps (M539)

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R490
- **Owner (single writer):** the session that froze it; it writes only `experiments/sessionmax_v1/`
- **Date registered (UTC):** 2026-11-14
- **Code:** `scripts/run_sessionmax.py`, `lab/slices.py`, `lab/research.py`, `lab/engine.py`, `lab/stats.py`
- **Method:** M539 (registered 2026-11-14, `research/intake/new_edge_scan_20261114.md`)
- **Source:** Haichen Yang, "Max Effect in Crypto Market: Evidence from Intraday and Overnight Trading", PhD
  dissertation, University of Hawai'i at Manoa, May 2026 (not peer-reviewed; CoinMarketCap VWAP, not perp data).
  Distinct from M144 (plain 24 h MAX; R222 NULL) and M492 (MEXC stock-perp session split; R435 NULL): it combines the
  MAX factor with the intraday/overnight session split and its distinctive claim is a **positive same-session
  (momentum) sign** with a **falsifiable zero cross-period** effect.

## Question
On 24/7 crypto perpetual futures, does the past-week maximum return measured **within one session** (intraday
14:00-20:59 UTC, or overnight 21:00-13:59 UTC) positively predict the coin's **forward 7-day net return** on the
same session, more than the matched plain 24 h MAX book (M144) does? One sentence: the top-minus-bottom quintile
session-MAX spread is positive, net of executable cost, and exceeds the 24 h MAX book by >= 1 bp/day on discovery.

## What the author had seen
- R222 (`xsalt_v1`) tested a plain 168 h MAX (M144) and found it NULL (MAX_POS +3.0 bp/day, t 0.27).
- R435 (`stock_tugofwar_v1`) tested an overnight/intraday split on MEXC **stock** perps and found it NULL.
- No session-decomposed MAX has been computed on crypto perps. The split is untested here.

## Universe
- **Manifest:** `data/klines_1h/manifest.json`, sha256
  `16e6434c8fcdbc2ff96c2062de47a05f720853cea4e6d71dabb84717f1472077`. 50 USDT-margined perpetuals, the
  long-lived major set: BTC, ETH, BNB, XRP, ADA, SOL, DOGE, DOT, LINK, LTC, BCH, ETC, XLM, TRX, EOS, ATOM, NEO, DASH,
  ZEC, FIL, UNI, AAVE, SUSHI, CRV, COMP, MKR, SNX, YFI, RUNE, ALGO, VET, ICP, THETA, AXS, SAND, MANA, CHZ, ENJ, ONE,
  ZIL, IOTA, ONT, QTUM, BAT, ZRX, KNC, LRC, STORJ, CVC, ANKR (USDT perps).
- **Eligibility:** `lab.research.make_universe(p, elig_top=50, col_top=50)` — tradable when in the top 50 by trailing
  30-day quote volume (all 50 columns here), point-in-time. Delisted symbols keep their archive rows.
- **Window:** 2021-01-01 .. 2026-09-30 (the archive end). Binance USD-M quarterly contracts are excluded.

## Data
- **Backtest:** `data/klines_1h/<SYMBOL>.parquet` (Binance USD-M public monthly klines, `data.binance.vision`,
  keyless), fetched 2026-11-14 with `python -m lab.data build klines 1h`. Manifest sha256 above.
- **Trade venue:** Binance USD-M (paper only; no order, no key).
- **As-of:** 2026-11-14. Delisted symbols included where the archive holds their rows.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| intraday session return `r_intra[d]` | 1 h close | Binance USD-M perp, log return | `log(C[d 20:00 bar close] / C[d 13:00 bar close])` (bars 14:00-20:59 UTC) | at the 21:00 UTC bar close | yes | archive as fetched 2026-11-14 | missing bar = NaN session, never zero-filled |
| overnight session return `r_over[d]` | 1 h close | same | `log(C[d+1 13:00 close] / C[d 20:00 close])` (21:00-13:59 UTC) | at the next day 14:00 UTC close | yes | same | same |
| 24 h return `r_24[d]` | 1 h close | same | `log(C[d+1 00:00 close] / C[d 00:00 close])` | at 00:00 UTC | yes | same | same |
| `MAX_intra[i]` | `r_intra` | same | max of `r_intra[i-6..i]`, needs >= 5 finite | at day i's 21:00 close | yes (uses past only) | same | < 5 finite -> NaN |
| `MAX_over[i]` | `r_over` | same | max of `r_over[i-6..i]`, needs >= 5 finite | at day i+1's 14:00 close | yes | same | same |
| `MAX_24[i]` (control) | `r_24` | same | max of `r_24[i-6..i]`, needs >= 5 finite | at day i+1's 00:00 close | yes | same | same |
| forward return `ret[t]` | close, funding | same | `engine.forward_returns` (next-bar return less funding a long pays) | next bar | yes | same | archive rule |

All inputs are point-in-time archive rows, keyless and reproducible. Cross-sectional eligibility is trailing-volume
based (point in time). Survivor-only concern: the 50-symbol universe is a fixed major set, so **survivorship is
explicit** — it is a large-cap set chosen in 2026, not the 2021 universe; this is a stated limit, not a hidden one.

## Rule or search space (closed)
Three books, no search. At each UTC day close:
- **S-INTRA:** score = `MAX_intra`; long the top quintile, short the bottom quintile, dollar-neutral, hold 7 d (168 h).
- **S-OVER:** score = `MAX_over`; long the top quintile, short the bottom quintile, dollar-neutral, hold 7 d (168 h).
- **CONTROL (M144):** score = `MAX_24`; same book, so S-INTRA/S-OVER can be compared to the plain 24 h MAX.
Signal computed once a day on the 00:00 UTC close from data up to that close; slices open at that close and are held
168 h (`lab.slices.positions` / `lab.slices.run`, hedge on, `missing="legacy"`). Needs >= 15 scored coins per day.

**Deviation from the paper (stated):** the paper holds only within the session (intraday book earns intraday returns).
This lane holds the coin **continuously** for 7 days and measures the total net return, because the lab's slice engine
prices a continuous hold; a session-restricted hold is left for a successor. So this tests "does session-MAX predict
the forward 7-day return?", the same target M144's control uses, which makes the comparison clean.

## Splits and cost
Splits from `lab/config.py` (PROGRAM_VERSION 1): discovery day < 2024-01-01, validation 2024-01-01..2025-06-30,
holdout >= 2025-07-01 (untouched unless a book reaches it through the stages). Cost from `engine.cost_matrix`
(liquidity tiers, fee plus slippage), sensitivity at 1x / 2x / 3x.

## Gates (numbers)
- Discovery: mean 1x net > 0 **and** alpha t (vs BTC, NW lag 10) >= 2.0.
- Validation (only if discovery passes): mean 1x net > 0 **and** alpha t >= 1.5.
- The M539-specific claim: S-INTRA (and/or S-OVER) 1x net mean exceeds the CONTROL 1x net mean by >= 1 bp/day on
  discovery. A session book that does not beat its own 24 h control is reported as NOISE even if positive.

## Null
Block bootstrap of the book's own 1x daily net with the mean removed: block 10 days, 2,000 replicas, seed 20261114.
The NW-t threshold is the 95th percentile of the null. Verdict SIGNAL only if the realised alpha t exceeds it and the
gate is met. A within-day **session-label permutation** (swap which window is intraday vs overnight per day,
seed 20261114, 200 replicas) is reported as the paper's distinctive cross-period check: if the edge survives label
shuffling it is not a session effect.

## Multiplicity
Variants in this decision family: 3 books (S-INTRA, S-OVER, CONTROL) x 3 cost multipliers x 2 windows = 18 scored
cells; 1 decision (does session-MAX beat its 24 h control net). Registry count for the MAX family: R222 (7 variants)
+ this (3) = 10. Program trials from `registry.program_trials('registry/rounds.csv')` at freeze — bookkeeping, not an
effective independent-test count.

## Evidence lineage and admission (future lanes only)
- Canonical method ids: **M539** (this), M144 (parent MAX), M492 (session split, other venue).
- Parent rounds / previous outputs: R222 (M144 NULL), R435 (M492 NULL).
- One decision group this signal feeds: the MAX/session-momentum family (one decision).
- Samples already seen by parents: 2021-2026 Binance alt cross-sections (R222), MEXC stock perps (R435).
- Proposed fresh sample: the session **decomposition** on this 50-symbol crypto set — new to the lab, overlapping the
  R222 symbol pool (same venue). Overlap is acknowledged.
- `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`; met requirements: batch
  read, 1x/2x/3x, frozen PREREG; unmet: a full coverage-survival comparison (fixed major universe). Dependent-null
  calibration: block bootstrap as above. 10-day trimming and leave-two-coins-out: reported in FINDINGS. 80%-power:
  an archive diagnostic, not a gate.
- Across-family selection control: none beyond this family's gates; the result stays exploratory.
- A PASS authorizes only a gate-1 confirmation and a candidate forward paper lane (new id, API) — no money, no order,
  no key, not gate 2.

## Stop rules
The lane ends after one run. After seeing results: no new features, no new splits, no re-run with other parameters.
A second read of this sample needs a new frozen PREREG.
