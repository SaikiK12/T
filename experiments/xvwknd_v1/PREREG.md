# PREREG: xvwknd_v1 (R466). Does the Sunday gap between trade.xyz and Lighter on the same stock close?

- **Registry id:** R466
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

New method M524 (cross-venue weekend gap between two 24/7 US-stock perp venues), next to M515 (R462, R463, R465) and
M443 (the same question for WTI). This file is frozen by `lab.prereg.freeze()` before any Lighter price of these
markets is read, before R465 runs, and before any gap between the two venues is computed. After the freeze it is
never edited; a changed idea is a new lane.

## Question
- trade.xyz and Lighter both list 50 of R462's US stocks and funds as perps.
- Over the weekend each venue prices them from its own order book:
  - trade.xyz: a 30-minute EMA starting from the last external print;
  - Lighter: an order-book EMA once its external price is stale for about a minute.
- So on Sunday evening the two prices of one stock can differ.
- Both venues return to an external price:
  - trade.xyz from Sunday 20:05 New York (Blue Ocean overnight session);
  - Lighter at an undocumented time, probably the same session through Pyth (wave 7, lens 6).
- Once both are back on an external price, the gap should close.

Selling the dearer venue and buying the cheaper one at Sunday 19:00 New York, closing at Monday 10:00: does the gap's
closure pay more than both venues' costs?

This is a hedged pair. Its result does not depend on which way the stock moves over the weekend, only on how the
two venues' weekend prices differ. R462 and R465 trade the weekend move itself.

## Why this lane
- **R462 and R465 trade the weekend move outright,** so they carry the stock's risk (R462: sd 140 bp per event).
  The pair removes it.
- **Costs are low:**
  - Lighter charges 0 fee;
  - trade.xyz's growth mode charges 0.9 bp a side;
  - wave 7, lens 4 found no cheaper venue reachable from France.
- **Lighter's corporate-action rule** (docs.lighter.xyz `corporate-actions.md`, read by a helper [V]): splits are
  not adjusted; the market is delisted and settled. Such markets are absent from the universe (survivorship).

## What the author has seen
- **R462's results** on the xyz side of these weekends: its weekend moves W and fade returns, per event, from
  `data/xyz_wknd`.
- **R464's results.**
- **Lighter's market list, fees and listing times,** and the R465 feasibility counts (weekend hours with volume, no
  price).
- **R465's fetch log** (one line per market: candle and funding counts). The Lighter files were being written while
  this file was drafted. No price in them was read.
- **No Lighter price, no R465 result** and no gap between the two venues has been computed.
- The runner was run only on synthetic worlds (`tests/test_xvwknd.py`).

## Universe (`experiments/xvwknd_v1/universe.csv`, frozen)
- **Built by** `python scripts/run_xvwknd.py universe` from two frozen files:
  - R465's `experiments/ltwknd_v1/universe.csv`: 50 markets with Lighter ids;
  - R462's `experiments/xyzwknd_v1/universe.csv`: the xyz growth flag and the IPO date.
- **Growth flag:** 47 markets are in xyz growth mode. MSTR, STRC and BMNR are not, and carry the standard 9 bp xyz
  fee as in R462.

## Samples and data
- **A, decides.** Fridays 2026-05-01 .. 2026-09-25: 18 weekends.
- **B, confirms.** Fridays 2026-10-02 .. 2026-11-06: 6 weekends.
- **Not covered:** the xyz candles start on 2026-04-17, so R465's sample C is not covered.
- **Weekends:** R462's rule (`xyzwknd_rule.weekend`). Holiday and early-close weekends are dropped.
- **xyz data:** `data/xyz_wknd`, R462's frozen fetch (candles t, c, v; funding time, rate), re-hashed against its
  manifest.
- **Lighter data:** `data/lighter_wknd`, R465's fetch after its freeze (candles t, close, volume; funding t, rate),
  re-hashed against its manifest.
- **Eligibility:**
  - both venues' first candle is at least 7 days before Friday 20:00;
  - the IPO rule passes;
  - both venues have a fresh trade at E.

## The rule (`scripts/xvwknd_rule.py`)
- **Instants:** R462's E = Sunday 19:00, X1 = Sunday 22:00, X2 = Monday 10:00 New York.
- **Fresh trade Q(T):** the close of the hourly candle that opens at T - 1 h, if it traded (volume > 0).
  - This is stricter than R462's 3-hour window: the two prices are at most an hour old.
  - Both are last trades, up to 59 minutes apart.
- **Gap and side:**
  - G(T) = 1e4 ln(Q_xyz(T) / Q_lighter(T));
  - d = sign(G(E)): +1 sells xyz and buys Lighter.
- **Returns:**
  - c_k = d (G(E) - G(X_k)), the gap's closure;
  - f_k = d · 1e4 (F_xyz - F_lighter), funding settled in (E, X_k], signed + when longs pay;
  - g_k = c_k + f_k, in bp of one leg's notional.
- **Thresholds and exits:**
  - θ on |G(E)|: {0, 10, 25, 50, 100} bp;
  - exits: X1, X2.
- **Test:** two-sided weekend-cluster sign-flip test (`earnperp_rule.cluster_flip_p`), 200,000 draws, seed 466.
- **Decision cell:** θ = 25 bp, exit X2.
  - **Why X2:** it is the first instant at which both venues are surely on an external price (the Monday cash open).
    Lighter's Sunday resumption is undocumented.
  - **Why θ 25:** it is 2.5 cost units.
  - A pass needs a positive mean.

## Trials
- 5 thresholds × 2 exits = **10 cells**, read in A and B. B adds no hypothesis.
- Registry trials: 10.
- Program trials: 9,785,174 after R465, 9,785,184 after this lane.

## Decision
- **PASS:**
  - **A:** at least 100 events over at least 10 weekends; p ≤ 0.05; mean > 2 cost units;
  - **B:** at least 30 events over at least 4 weekends; mean > 1 unit.
- **PARTIAL:**
  - **A:** its sizes, p ≤ 0.05 and mean > 1 unit;
  - **B:** its sizes and a positive mean.
- **INCONCLUSIVE:** A is below its sizes.
- **NULL:** otherwise.
- **Program trials:** read against 9.8 million, any hit is weak. A PASS or PARTIAL earns a forward paper lane under a
  new id, with both books walked at E and X2; never a trade.

## Costs (1x, 2x, 3x)
- **One cost unit:** the pair's round trip.
  - Fees: two xyz taker fees (0.9 bp each in growth mode, 9 bp otherwise) plus two Lighter taker fees (0).
  - Slippage: 4 bp on each venue, R462's assumption.
  - Total: **9.8 bp** in growth mode, 26 bp otherwise.
- **Funding** is inside g.
- **Nets:** the 1x, 2x and 3x nets subtract 1, 2 and 3 units.
- **Known bias, before the run:** both prices are last trades.
  - Bid-ask bounce on either venue makes a gap that "closes" without a tradable price.
  - Up to 59 minutes between the two trades does the same.
  - So gate 0 overstates the executable result, and only book walks at E settle it.
- **Diagnostic, reported and not decided on:**
  - `persistence` in `results/summary.json`: over A's decision-cell events with a fresh gap at E - 1 h, the
    correlation of G(E - 1 h) with G(E);
  - the mean return when the earlier gap had the same sign and |G(E - 1 h)| ≥ θ, against the other events.
  - A gap made of bounce would not persist.

## Power (stated before the run)
- **MDE80** = 2.8 sd / sqrt(n), reported for every cell.
- **Expected count in A:**
  - roughly 50 markets × 18 weekends, minus unlisted and untraded hours: about 500-700 priced events;
  - perhaps a third of them with |G(E)| ≥ 25 bp.
- **Assumption:** an sd of 30 bp per event. The lane then detects about 6-10 bp, or about 15 bp with the cluster test.
- **Bar:** a pass needs more than 19.6 bp in growth mode.

## Code
```inputs
455f982fbc5baff5169a2ff356fbade0f7e64770fdcee4d5660264368a25f161  experiments/xvwknd_v1/universe.csv
e1f1d4ab5a932d8a06aca7a643c88cdf7bf4fc5a938a2e472c809e80d08ca75b  scripts/xvwknd_rule.py
ca6ff744df28f363e7c880117cef60ac9431c9bc310056a4338dfcb8c9bb9cb8  scripts/run_xvwknd.py
2e0dca5f2aa535754fae41daf8570b6e60546c099547356ffa3180d86fac9799  tests/test_xvwknd.py
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a  scripts/xyzwknd_rule.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
6a9c4286ac1a12a391c0ebaca022510fb40d59affff9eb56ce71d44246a64ca1  scripts/earnperp_rule.py
746d69923e55a68a5fefad555afba4647eac8b41d355b460edaaa73c1f611373  experiments/xyzwknd_v1/universe.csv
a4d7d0f4dcca6a857c69ca620ce374f118fa70423f236de5b6fedff9bb42bc28  experiments/ltwknd_v1/universe.csv
2e7acf52916be76fb94debae872c134581cfa413d12b0ffaa7bf14f2776f3a52  scripts/fetch_lighter_wknd.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
e43362092fec877dd735739236cfaccfb91b829c4239aff48fb639a12ef827a4  docs/provenance/xyz_wknd.json
```
The runner also re-hashes every bar and funding file of both venues against their manifests.

## Feature lineage and point-in-time availability
- **G(E) and d:**
  - Source: last trades in the hour before E on both venues.
  - Available at E.
  - Missing data: the event is dropped and counted.
- **Fees:**
  - Source: R462's growth flags and Lighter's fees on 2026-11-11.
  - Not point-in-time for earlier weekends.
- **G(X_k) and f_k:**
  - Source: last trades in the hour before X_k; funding in (E, X_k].
  - Outcome only.

## Evidence lineage and admission
- **Method:** new M524. **Neighbours:** M515 (R462, R463, R465) and M443.
- **Decision group:** one pre-named cell, so no multiplicity correction within the lane.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: pre-named cell; 10 cells counted; costs at 1x/2x/3x; power stated; a confirmation sample.
  - Not met: gate 1 (forward, measured costs) and gate 3 (account risk). Exploratory.

## Stop rules
- The lane ends with its first complete run. Nothing is retuned afterwards.
- **A PASS or PARTIAL earns** a forward lane under a new id.
- **A NULL closes** M524 in this form.
- No orders, no money, no credentials. The run reads files and writes `experiments/xvwknd_v1/results/`.
