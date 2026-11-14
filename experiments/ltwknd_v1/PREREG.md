# PREREG: ltwknd_v1 (R465). Does R462's weekend fade hold on Lighter, at zero fee?

- **Registry id:** R465
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

Method M515 (trade.xyz US-stock perps weekend overshoot), on a second venue. Parents: R462 (gate-0 PASS on xyz), R463
(xyz forward), R464 (NULL on xyz's non-stock markets) and idea wave 6 (`research/intake/idea_wave6_20261111.md`).
This file is frozen by `lab.prereg.freeze()` before any Lighter price of these markets is fetched for this question.
After the freeze it is never edited; a changed idea is a new lane.

## Question
Lighter lists 50 of the 76 US stocks and funds in R462's universe as perps, at 0 maker and 0 taker fee on a Standard
account, reachable from France (R457 and R459 already trade there on paper). They trade every weekend hour.

Run R462's frozen rule unchanged on Lighter's own candles and funding. Does fading the weekend move from Sunday 19:00
to 22:00 New York pay there too, and by more than its cost?

## Why this lane
- **Cost is the binding constraint.** R462's cost unit is 5.8 bp (two 0.9 bp growth-mode taker fees plus 4 bp of
  slippage). Lighter charges 0 fees (`orderBookDetails`: taker_fee and maker_fee 0.0000 for all 50 markets on
  2026-11-11), so the unit falls to the 4 bp of slippage.
- **Lighter's closed-market rule is the same kind as xyz's** (docs.lighter.xyz `llms-full.txt`, fetched 2026-11-11,
  sha256 `6f19423588574410…`, read by the author [A]):
  - "Outside the underlying's trading hours, external prices can become stale and pricing switches to the price
    derived from the order book."
  - "The internal price is derived from order book impact prices, smoothed using a time-weighted Exponential Moving
    Average"; for the index, "τ = 30 minutes".
  - "The current mainnet stale threshold is typically 1 minute … As soon as a fresh external price is available,
    pricing switches back to it."
  - Since 2026-07-10 the internal price of the largest names (SPY, QQQ, NVDA, TSLA, AAPL, AMZN, MSFT, GOOGL, META, MU,
    INTC, AMD, MSTR and others) is no longer capped against the last oracle price. Before that it was capped at
    ±1/L of it.
  - **Not documented:** when on Sunday the external stock price returns on Lighter. If its feeds carry the Sunday
    20:00 overnight session, X1 (22:00) is after it, as on xyz. If they return only on Monday, X1 is too early and
    only X2 (Monday 10:00) would show a give-back.
- **R462's result** (xyz, sample A): +42.4 bp per market-weekend before costs at |W| ≥ 50 bp, exit Sunday 22:00,
  Holm p 0.004; B +36.2 bp.

## What the author has seen
- **Lighter market list, ids, listing times and fees** (`orderBookDetails`, 2026-11-11), and Lighter's docs.
- **A feasibility check, counts only, no price:**
  - For NVDA, AAPL, TSLA, SPY, QQQ and COIN over 2026-11-06 .. 11-09, every hour had a candle with volume.
  - For NVDA, TSLA and COIN on five weekends (Fridays 2025-12-05, 2026-01-16, 02-27, 04-10, 05-08), the count of
    weekend hours with volume (out of 51) was:
    - 14-29 in December and January;
    - 45-51 from 2026-02-27.
  - Sample C starts at 2026-02-27 for this reason.
- **R462's results on the same markets and weekends (samples A and B)**, from xyz's prices. A and B here are
  therefore a venue replication, not new weekends. Sample C's weekends were never read on any venue, though R432 read
  SPY's and QQQ's on Binance.
- **The Lighter book recorder** (`lighter/books` on `claude/xyz-books-data`) was never read.
- **No Lighter price, weekend move or return of these markets has been computed for this question.**
- The runner was run only on synthetic worlds (`tests/test_ltwknd.py`).

## Universe (`experiments/ltwknd_v1/universe.csv`, frozen)
- **Built by** `python scripts/fetch_lighter_wknd.py universe` on 2026-11-11.
- **Members:** the rows of R462's frozen `experiments/xyzwknd_v1/universe.csv` whose coin is a Lighter perp symbol.
  That gives 50 markets, 5 of them funds.
- **Columns:** Lighter's market id, `created_at`, status and fees. NOK and MAGS were inactive on 2026-11-11.
- **IPO dates:** R462's `ipo_424b4` column is kept. A weekend counts only after the IPO, as in R462.
- **Survivorship:** Lighter markets delisted before 2026-11-11 (for example after corporate actions) are absent.

## Samples
- **A, decides.** Fridays 2026-05-01 .. 2026-09-25: R462's 18 weekends.
- **B, confirms.** Fridays 2026-10-02 .. 2026-11-06: 6 weekends.
- **C, confirms when large enough.** Fridays 2026-02-27 .. 2026-04-24: 8 weekends (Good Friday dropped).
- **Skipped weekends:** R462's rule (`xyzwknd_rule.weekend`): non-trading or early-close Fridays, Monday holidays.
- **Bars:**
  - Lighter 1 h candles and hourly funding over 2026-02-13 .. 2026-11-10 00:00 UTC.
  - Fetched **after this freeze** by the frozen `scripts/fetch_lighter_wknd.py bars` into `data/lighter_wknd`, with
    a per-file sha256 manifest and a provenance record.
- **Eligibility:**
  - the market's first candle is at least 7 days before R;
  - the IPO rule passes;
  - both P(R) and P(E) exist.

## The rule
- **R462's frozen module, unchanged:** `scripts/xyzwknd_rule.py`. It sets:
  - R = Friday 20:00, E = Sunday 19:00, X1 = Sunday 22:00, X2 = Monday 10:00 New York;
  - P(T), W, the fade side s, c_k, f_k and g_k = c_k + f_k.
- **The one difference: a price is a trade.** Lighter returns a candle for every hour, with or without trades. Only
  candles with volume > 0 are passed to P(T), so P(T) is the last trade before T, at most 3 hours old.
  - xyz's `candleSnapshot` serves traded hours only, so this matches R462's meaning.
  - Funding is Lighter's hourly rate, signed + when longs pay (`lab/carrylane.lighter_funding`).
- **Groups, thresholds and exits:** R462's: `all`, `single`, `etf`, `rel`; θ in {0, 50, 100, 200} bp; X1, X2.
- **Test:** R462's two-sided weekend-cluster sign-flip test, 200,000 draws, seed 465.
- **Decision cell:** R462's D2 only: `all`, θ = 50 bp, X1. The fade side is fixed by R462, so a pass needs a positive
  mean.

## Trials
- Cells: 4 groups × 4 thresholds × 2 exits = **32**, each read in A, B and C. B and C add no hypothesis.
- Registry trials: 32.
- Program trials: 9,785,142 before this lane, 9,785,174 after.

## Decision
- **PASS:** all of these.
  - **A:** at least 100 events over at least 10 weekends; p ≤ 0.05; mean > 2 cost units.
  - **B:** at least 30 events over at least 4 weekends; mean > 1 unit.
  - **C:** a positive mean when it has at least 30 events over at least 4 weekends. When it is smaller, C is
    reported only.
- **PARTIAL:** A has its sizes, p ≤ 0.05 and mean > 1 unit; B has its sizes and a positive mean.
- **INCONCLUSIVE:** A is below its sizes.
- **NULL:** otherwise.
- Read against 9.8 million program trials, any hit is weak. A PASS or PARTIAL earns a forward paper lane on Lighter
  at recorded book costs, under a new id, never a trade.

## Costs (1x, 2x, 3x)
- **One cost unit is a round trip:** 0 fee + 4 bp of slippage for both fills = **4 bp** (R462's slippage assumption).
- Lighter's weekend books for these markets were not measured. Their real cost may be higher.
- Funding is charged inside g.
- The 1x, 2x and 3x nets subtract 1, 2 and 3 units from the mean.

## Power (stated before the run)
- MDE80 = 2.8 sd / sqrt(n), reported for every cell; the cluster test is wider.
- R462's A had 556 events at θ 50 over 72 markets with an sd of 140 bp. With about 50 markets here, many listed in
  2026, expect roughly 250-400 events over 18 weekends.
- Assumed weekend-level sd of 30 bp: the lane detects about 20 bp, against a 2x cost of 8 bp.
- R462's +42 bp would be seen. An effect a third of that size would likely be missed.

## Code
```inputs
a4d7d0f4dcca6a857c69ca620ce374f118fa70423f236de5b6fedff9bb42bc28  experiments/ltwknd_v1/universe.csv
14b88ff65e496d36c43955cd686290c970b3922afeedec35617c8cfc0f25e205  scripts/run_ltwknd.py
2e7acf52916be76fb94debae872c134581cfa413d12b0ffaa7bf14f2776f3a52  scripts/fetch_lighter_wknd.py
7821882c6dcf31d1e7bc18b90b61ea1376e68e3bcb238f4a5172909835672a8a  tests/test_ltwknd.py
746d69923e55a68a5fefad555afba4647eac8b41d355b460edaaa73c1f611373  experiments/xyzwknd_v1/universe.csv
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a  scripts/xyzwknd_rule.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
6a9c4286ac1a12a391c0ebaca022510fb40d59affff9eb56ce71d44246a64ca1  scripts/earnperp_rule.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
```
The runner also re-hashes every bar and funding file against `data/lighter_wknd/manifest.json`.

## Feature lineage and point-in-time availability
- **W and s.** Source: Lighter trades before R and E (traded candle closes). Available at E. Missing data: the event
  is dropped and counted.
- **Fees.** Source: `orderBookDetails` on 2026-11-11. Not point-in-time for earlier weekends.
- **c_k and f_k.** Source: traded candle closes before X_k, and funding settled in (E, X_k]. Outcome only.

## Evidence lineage and admission
- **Method:** M515 on a second venue. **Parents:** R462, R463, R464.
- **Decision group:** one pre-named cell, so no multiplicity correction within the lane.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: pre-named cell; 32 cells counted; costs at 1x/2x/3x; power stated; two confirmation samples.
  - Not met: gate 1 (forward, on-time, measured costs) and gate 3 (account risk). Exploratory.

## Stop rules
- The lane ends with its first complete run. Nothing is retuned afterwards. A changed idea is a new lane.
- **A PASS or PARTIAL earns** a forward paper lane on Lighter under a new id, with tickets at E and recorded Lighter
  book costs. R463's pinned files are not edited for it.
- **A NULL** says R462's effect does not survive the move to Lighter's prices at these instants. M515 and R463 are
  unaffected.
- No orders, no money, no credentials. The run reads files and writes `experiments/ltwknd_v1/results/`.
