# PREREG: xyzwknd_v1 (R462). Do trade.xyz US-stock perps overshoot over the weekend?

- **Registry id:** R462
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

Method M515, from idea wave 5 (2026-11-11). Parents: M188 and M321 (weekend perp moves against the reopen), R432 and
R459. This file is frozen by `lab.prereg.freeze()` before any xyz weekend price, move or return is computed, and
before the bars this lane reads exist on disk. After the freeze it is never edited; a changed idea is a new lane.

## Question
Hyperliquid's trade.xyz HIP-3 perps on US stocks and US-listed funds price themselves from Friday 20:00 to Sunday
20:05 New York time. In that window there is no external price: the oracle is a 30-minute EMA of the perp's own book,
started from the last external print.

When external prices return (Blue Ocean's overnight session from Sunday 20:05, then the Monday cash open), does the
perp give back part of its weekend move? Does fading that move from Sunday 19:00 pay more than a round trip at
growth-mode fees?

## Why this lane
- **Cost is the lab's binding constraint, and xyz's is the lowest France-reachable price for these markets.**
  - On 2026-11-11, 72 of the 76 markets below ran in HIP-3 growth mode. The taker fee there is a tenth of the 9 bp
    standard fee: 0.9 bp each way (Hyperliquid info API `meta`; the docs page "Fees" [A]).
  - R453's PREREG already uses this fee formula.
- **The mechanics are documented** (trade.xyz `llms-full.txt`, fetched 2026-11-11, sha256 `7ac7ef34dec6e080…`, read
  by the author [A]):
  - US stocks have external prices "24/5, from Sunday 8:05 PM ET to Friday 8:00 PM ET". The overnight session comes
    from Blue Ocean ATS.
  - While closed, "the internal mechanism initializes from the last available external price" and runs a
    continuous-time EMA with tau = 30 minutes. It "reverts to the externally derived price on the next tick" when
    inputs resume.
  - The time constant was cut from 1 h to 30 min on **2026-04-30** (changelog). Sample A starts after that.
- **A commissioned study exists** (Blockworks for the Hyperliquid Policy Center, 2026-08-03, read by a helper [V];
  vendor-side; numbers not checked by the author). Across 614 market-weekends:
  - the median error against the reopen falls from 113 bp (Friday price) to 53 bp (final weekend price);
  - the reopen move regressed on the weekend move has slope 0.834 (CI 0.73-0.93).
  - A slope below 1 would mean the weekend move overshoots by about a sixth. That is the hypothesis here, not a fact.
- **The lab's own prior:**
  - R432 (Binance TradFi index and commodity perps) found fade slopes of -0.12 / -0.18 / -0.26 to the CME reopen
    + 15 min, + 60 min and the cash open. Its primary cell was NULL at a 12 bp cost unit.
  - Its oil lead is running forward as R459.
  - Single US stocks on xyz have not been read for this question.

## What the author has seen
- **xyz market names** and growth-mode flags (`meta`, dex xyz, 2026-11-11).
- **The trade.xyz Specification Index** (sessions, descriptions).
- **SEC EDGAR** listings and filing indexes (to build `universe.csv`).
- **R451's gate 0** fetched xyz hourly closes for 22 markets, 2026-09-30..2026-11-11, and computed flow-book returns
  from them. That covers sample B's period for those markets. The author never computed or looked at a weekend move,
  a Sunday-evening price or a Monday reopen in those files, or in any other xyz data.
- **Helper reports** of wave 5 (lenses 2, 4, 5, 6), with the Blockworks figures above.
- **No xyz price, weekend move or return for this question has been computed.**
- The rule and runner were run only on synthetic worlds (`tests/test_xyzwknd.py`). The end-to-end test uses a planted
  overshoot.

## Universe (`experiments/xyzwknd_v1/universe.csv`, frozen)
Built by `python scripts/fetch_xyz_wknd.py universe` on 2026-11-11 from names and filings only.

- **Membership:** the 76 rows of trade.xyz's Specification Index whose external session reads "24/5, from Sunday 8:05
  PM ET to Friday 8:00 PM ET". That is 61 companies and 15 funds (`etf` = 1 when the description says ETF or fund).
  Indices (CME-based, 23/5), commodities, FX, and Asian and Indian stocks follow other sessions and are excluded.
- **`growth`:** the market's growthMode on 2026-11-11. "enabled" for 72 markets; blank for MSTR, PURRDAT, STRC and
  BMNR.
- **`ipo_424b4`:** the first 424B4 prospectus filed before any 10-K, 10-Q, 20-F or 40-F. The rule treats it as the
  IPO date of a company that listed recently. A weekend counts only if its Friday is after that date, because before
  the IPO the xyz market was a Pre-IPO perp with other rules. In the window this affects CBRS (2026-05-14), QNT
  (2026-06-05), SPCX (2026-06-12) and SKHY (2026-07-10).
- **Survivorship:** markets delisted before 2026-11-11 are absent.

## Samples
- **A, decides.** Weekends with a Friday from 2026-05-01 to 2026-09-25: 18 weekends.
- **B, confirms.** Fridays from 2026-10-02 to 2026-11-06: 6 weekends.
- **Skipped weekends:**
  - a Friday that is not a trading day, or is an early close (2026-07-03, 2026-06-19);
  - a Monday that is not a trading day (Memorial Day, Labor Day).
- **Bars:**
  - Hyperliquid `candleSnapshot` 1 h and `fundingHistory` for each `xyz:<coin>`, over 2026-04-01 to 2026-11-10
    00:00 UTC.
  - Fetched **after this freeze** by the frozen `scripts/fetch_xyz_wknd.py bars` into `data/xyz_wknd`, with a
    per-file sha256 manifest.
  - The API serves only the most recent 5,000 candles, about 208 days, so the earliest bars are from mid-April 2026.
- **Eligibility:** a market-weekend counts when the market's first candle is at least 7 days before Friday 20:00, the
  IPO rule passes, and both P(R) and P(E) exist.

## The rule (`scripts/xyzwknd_rule.py`)
All times New York.
- **Instants:**
  - R = Friday 20:00 (end of the external session);
  - E = Sunday 19:00 (entry);
  - X1 = Sunday 22:00 (about two hours after external prices resume);
  - X2 = Monday 10:00 (half an hour after the cash open).
- **P(T):** the close of the last hourly candle that opens in [T - 3 h, T - 1 h]. That is the last trade before T, at
  most 3 hours old; otherwise the price is missing.
- **Weekend move:** W = 1e4 ln(P(E)/P(R)). The fade side is s = -sign(W); W = 0 is dropped.
- **Price return:** c_k = s × 1e4 ln(P(X_k)/P(E)).
- **Funding:** f_k = -s × 1e4 × (the sum of hourly funding rates settled in (E, X_k]). It is positive when the fade
  receives funding.
- **Return before trading costs:** g_k = c_k + f_k.
- **Groups:**
  - `all`; `single` (companies); `etf` (funds);
  - `rel`: each market's W and its move from E to X are taken net of that weekend's median over all eligible markets
    (at least 5), then faded. This is a long-short book, gross of funding, charged two cost units.
- **Thresholds:** |W| ≥ θ, with θ in {0, 50, 100, 200} bp.
- **Test:** a two-sided sign-flip randomization test of mean g = 0.
  - Signs are flipped together within each weekend, so one weekend's shared news counts as one unit.
  - 200,000 draws, seed 462. Helpers `cluster_flip_p`, `holm` and `mde80` come from `scripts/earnperp_rule.py`
    (frozen in R461, hashed below).
- **Decision cells** (sample A), Holm over the two p values:
  - D1: `all`, θ = 50 bp, X2 (Monday 10:00);
  - D2: `all`, θ = 50 bp, X1 (Sunday 22:00).

## Trials
- Cells: 4 groups × 4 thresholds × 2 exits = **32**, each read in A and in B. B replicates the same cells and adds no
  hypothesis.
- Registry trials: 32.
- Program trials: 9,785,069 before this lane, 9,785,101 after.

## Decision
The trade direction is the sign of the cell's sample-A mean: fade the weekend move if the mean is positive, follow it
if negative.
- **PASS:** a decision cell meets all of these:
  - at least 100 events over at least 10 weekends in A;
  - a Holm p of at most 0.05;
  - |mean| above 2 cost units, so the 2x net is positive;
  - in B: at least 30 events over at least 4 weekends, the same sign, and |mean| above 1 unit.
- **PARTIAL:** the same cell has the A sample sizes, a Holm p of at most 0.05, |mean| above 1 unit, and the same sign
  in B with B's sample sizes.
- **INCONCLUSIVE:** neither decision cell has the A sample sizes.
- **NULL:** otherwise.
- The best state of the two cells is the lane's verdict.
- Read against 9.8 million program trials, any hit is weak. A PASS or PARTIAL earns a forward paper lane on xyz with
  measured book costs (`record_xyz_books.py`, recording since 2026-11-11), never a trade.

## Costs (1x, 2x, 3x)
- **One cost unit is a round trip:**
  - growth-mode markets: two taker fees at 0.9 bp plus 4 bp of slippage for both fills = **5.8 bp**;
  - the 4 standard markets: 2 × 9 + 4 = **22 bp**.
  - The 4 bp slippage is an assumption: xyz books are recorded only from 2026-11-11. The Blockworks study reports a
    1.43 bp median weekend spread [V, vendor-side].
- Staking discounts and maker fills are not counted.
- Funding is charged inside g from the recorded hourly rates.
- The 1x, 2x and 3x nets subtract 1, 2 and 3 units from |mean|. `rel` cells are charged 2 units per event.

## Power (stated before the run)
- MDE80 = 2.8 sd / sqrt(n), reported for every cell. The cluster test is wider.
- Assumption: a weekend-level mean fade return with an sd of about 30 bp across weekends. With 18 weekends, D1
  detects about 20 bp, against a 2x cost of 11.6 bp.
- If the Blockworks slope holds (a sixth of |W| given back) and the median |W| above 50 bp is about 120 bp, the gross
  effect would be about 20 bp. The lane can see an effect of that size and not much smaller.

## Code
```inputs
746d69923e55a68a5fefad555afba4647eac8b41d355b460edaaa73c1f611373  experiments/xyzwknd_v1/universe.csv
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a  scripts/xyzwknd_rule.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
374365de7ca4b1fe9e527b3a4fab5feef1b3d447ee2905f5a51d2b2341e191d4  scripts/fetch_xyz_wknd.py
8a182260a9481cadb9a26b3563fad03ede183625291161ff61b658818f052d87  tests/test_xyzwknd.py
6a9c4286ac1a12a391c0ebaca022510fb40d59affff9eb56ce71d44246a64ca1  scripts/earnperp_rule.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
```
The runner also re-hashes every bar and funding file against `data/xyz_wknd/manifest.json`.

## Feature lineage and point-in-time availability
- **W and s.**
  - Source: xyz trades before R and E (candle closes).
  - Available at E. Point-in-time.
  - Missing data: the event is dropped and counted.
- **Growth mode (the cost unit).**
  - Source: `meta` on 2026-11-11.
  - Not point-in-time for earlier weekends. Growth-mode history before 2026-11-11 is not held, so a market charged
    5.8 bp may have paid more then.
- **IPO date.**
  - Source: EDGAR 424B4 filing dates.
  - Known before each weekend.
- **c_k and f_k.**
  - Source: candle closes before X_k, and funding settled in (E, X_k].
  - Outcome only.
- **`rel` medians.**
  - Source: the same weekend's markets.
  - Available at E for W; outcome for the move.

## Evidence lineage and admission
- **Method:** M515. **Parents:** M188 and M321 (weekend moves vs the reopen), R432 (Binance TradFi, NULL primary, fade
  slopes) and R459 (oil, forward).
- **Decision group:** M515 on xyz prices; one verdict from the two pre-named cells.
- **Samples:**
  - A: no xyz weekend price was ever read.
  - B: weekend prices never read, though R451 held 22 markets' closes for flow books.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: pre-named cells; Holm over 2; 32 cells counted; costs at 1x/2x/3x; power stated; a later confirmation sample.
  - Not met: gate 1 (a forward, strict on-time sample on the trade venue with measured costs) and gate 3 (account
    risk). The result stays exploratory.

## Stop rules
- The lane ends with its first complete run on A and B. Nothing is retuned afterwards: no other instant, threshold,
  group, cost or sample. A changed idea is a new lane.
- **A PASS or PARTIAL earns** a forward paper lane under a new id. It would cover fresh weekends from 2026-11-13, with
  tickets frozen at Sunday 19:00 ET, xyz book costs from `record_xyz_books.py`, and its own PREREG with at least 15
  weekends before any verdict.
- **A NULL closes M515 in this form.** The `single`, `etf`, `rel` and other-θ cells are diagnostics and do not reopen
  it.
- No orders, no money, no credentials. The run reads files and writes `experiments/xyzwknd_v1/results/`.
