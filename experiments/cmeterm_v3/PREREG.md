# PREREG: cmeterm_v3 (R505). Commodity term-structure carry on 13 CME futures roots, 2010-09..2026-10

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R505
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_cmeterm_v3.py` is the only writer of `experiments/cmeterm_v3/results/` and of the git-ignored
    `data/databento/cmeterm_v3/`. It imports R503's frozen rule from `scripts/run_cmeterm.py` unchanged and reads
    R504's pulls in `data/databento/cmeterm_v2/` without writing there.
- **Date registered (UTC):** 2026-11-17

**Methods:** M549 (commodity term-structure carry on CME futures). Carry family; commodity futures curves are new to
the lab.
- **Paper only:** it reads metered historical data; nothing in the code can place an order.

## Why a second lane
R503 froze this rule and its data requests, then its `fetch` could not finish (2026-11-17).
- Its first request asked for 16 years of continuous-symbol definitions for CL in one stream. Databento generates such
  a stream day by day. After about 15 minutes, at 2020-05, the response was cut (`ChunkedEncodingError`).
- Out-of-window timing (2026-11-02..16) showed definitions take seconds per day while settlements are fast. So none of
  R503's 16-year definition requests can finish.
- R503's script is frozen, so its requests cannot change. This lane keeps **R503's rule, cells and verdict
  unchanged**: they are imported from R503's frozen script, whose hash is pinned below. Only the data plumbing is new.
- No statistic of R503 was computed. R503 counted the trial, so this lane counts 0.

## Why a third lane
R504 froze the same rule with new plumbing. Its `fetch` then stopped (2026-11-17) after the rank map and the 67
quarterly snapshots, before any settlement was pulled.
- 2010 definition rows of the NYMEX and COMEX roots carry no unit of measure (250 rows), and `float(None)` stopped
  the run.
- A second check, made before this freeze, found 145 grains and livestock rows with a unit of **zero**. Under R503's
  rule that would divide by zero.
- A settlement row without a price would also stop R503's parser.
- This lane adds only guards (see the Data section). R503's rule, cells and verdict are unchanged.
  - It reuses R504's rank map and snapshots, pinned below and checked file by file against R504's manifest.
  - R503 counted the trial; R504 and this lane count 0.

## Question
The owner asked on 2026-11-17 for lanes on bigger markets with long recorded histories, "with all their specifics".
Room 2 ranked commodity roll carry first among CME lanes.

Does a textbook commodity carry book earn a positive excess return at executable CME costs, 2010-09..2026-10? The book
is long the most backwardated and short the most contangoed of 13 roots, rebalanced monthly. And what capital does it
need?

## What the author has seen
- **No CME commodity settlement, curve or definition inside the window was read before this freeze.**
- **A format sample outside the window** (2026-11-03, after the window's end; $0.0003) was read for columns, units and
  flags. It covered CL, GC and ZC n.0/n.1, definitions and statistics. It showed:
  - settlements are stat_type 3, preliminary (flag 2) during the day, final (flag 3) after midnight UTC;
  - the n ranks put CLZ6/CLF7, GCZ6/GCG7 and ZCZ6/ZCH7 first;
  - definitions carry `expiration`, `min_price_increment` and `unit_of_measure_qty`.
  - Their `min_price_increment_amount` is not the tick value: it was 1.0 for ZC, whose tick is worth $12.50. So
    notional is price × unit of measure, divided by 100 for the roots quoted in cents.
  - That day CL was backwardated (about +16%/yr), ZC and GC contangoed.
  - The sample's files were lost with a container replacement. Nothing from them enters the run.
- **Earlier lanes with commodity futures data, none ranking roots by curve slope:**
  - R370: CL/NG ticks around 60 EIA releases, 2025-2026;
  - R478, R480, R481, R482: front-month roll-ups of NG, CL, Brent and copper through US funds, xyz and Lighter
    oracles, and NYMEX futures recorded forward from 2026-11;
  - R432, R459: Lighter WTI/Brent weekends;
  - R464: xyz commodity perps.
  - Some of those prices overlap 2025-2026 of this window for CL, NG and copper.
- **Literature, from the author's memory, not re-read:**
  - Erb and Harvey (2006); Gorton and Rouwenhorst (2006);
  - Gorton, Hayashi and Rouwenhorst (2013): backwardation and low inventories predict returns;
  - Koijen, Moskowitz, Pedersen and Vrugt (2018): commodity carry Sharpe about 0.6-0.7 over 1980-2012;
  - Szymanowska et al. (2014); Bakshi, Gao and Rossi (2019).
  - The author does not know how the strategy did after 2013.
- **R503's quote:** $2.9455 for its 65 requests (13 definitions, 52 statistics chunks).
- **Since R503's freeze** (all disclosed; no statistic computed):
  - **R503's cut CL definitions file** (2010-06..2020-05, in window). Only its first and last line's timestamps were
    printed, to see how far it reached. It holds contract identities, no prices. It is deleted.
  - **Out-of-window speed tests, 2026-11-02..16:**
    - continuous definitions for all 39 symbols: 81 s and 13 s for 14 days;
    - CL statistics: 7 s;
    - a one-day parent definitions snapshot: 11 s;
    - symbology.resolve: 1.4 s.
  - **An out-of-window smoke test of this lane's plumbing, 2026-11-02..16, for CL, GC, ZC and LE.** On 2026-11-03 it
    printed the ranks, the far contract, notional, tick and carry: CL +16.3%/yr, ZC −12.7%, GC −5.2%, LE −9.5%.
  - **A first smoke test with a bug** (the chunk dates were bound before the test's patch).
    - It pulled CL statistics for 2010-06-06..2012-01-01 and part of 2012, in window, about $0.04.
    - It was stopped by the author, and the files were deleted unread. Nothing from them was printed except the
      quotes and kept-row counts. Its output file holds only the exit code.
  - **R504's frozen fetch** pulled the rank map (9,809 intervals) and the 67 quarterly snapshots, then stopped on the
    first missing unit.
    - Definitions only were read after that, to design the guards:
      - counts of rows with a missing field, by root and year;
      - the zero units;
      - the units and ticks per root after the fallback;
      - the 22 contracts still without details.
    - With the guards, 1,771 of 233,688 mapped contract-days still lacked details before the follow-up requests.
    - **No settlement or price inside the window has been read.**

## Data
| Input | Source | Used |
|---|---|---|
| Daily ranks | R504's `symbology.resolve` map (free), {root}.n.0/n.1/n.2 continuous → instrument id, 2010-06-06..2026-11-01 | the contract at each rank on each UTC date (ranked by the previous day's open interest) |
| Contract details | R504's 67 quarterly snapshots (`definition`, stype_in=instrument_id, a 4-day window from each quarter's start), then one request per first-mapped day for any contract still missing (22 contracts on 22 days at the freeze). A unit of measure that is missing, zero or below takes the root's CME contract unit: CL 1,000 bbl; HO and RB 42,000 gal; NG 10,000 MMBtu; GC 100 oz; SI 5,000 oz; HG 25,000 lb; PL 50 oz; ZC, ZS and ZW 5,000 bu; LE and HE 40,000 lb. A positive unit that differs is reported and used | expiry, tick, unit of measure, raw symbol. Details come from the latest snapshot on or before the date where the contract is listed and live, else the earliest later one. A definition whose raw symbol is not the root's (a reused id) is dropped |
| Settlements | Databento GLBX.MDP3 `statistics`, {root}.n.0/n.1/n.2, one root and one calendar year per request, four roots at a time | stat_type 3, update_action 1; the last publication for each contract and trading day |

- **Retries.** A cut stream or a server error is retried up to four times, with waits of 30, 90 and 240 seconds.
  Every attempt counts against the caps.
- **Spend caps:** $0.15 per statistics request, $0.05 per definitions request, $4.00 in total.
- **Spend before this lane.** The Databento spend before this lane was about $1.00:
  - about $0.92 earlier;
  - R503's cut request ($0.0127 quoted);
  - the pulls described under "What the author has seen" (about $0.07).
- **Settlements.** Rows without a price, contract id, statistic type or update action are dropped and counted.
- **Restarts.** A raw statistics file already on disk is reduced rather than fetched again.
- **Report.** The report adds:
  - the count of mapped contract-days without details;
  - the unit fallbacks and mismatches;
  - the dropped settlement rows.
- **R504's pulls**, reused here, cost $0.0123.
- **Disk.** Statistics files are reduced on arrival to their settlement rows (`settle_<ROOT>.csv`), and the raw file is
  deleted. The manifest keeps each raw file's quote, size and sha256; `reduced.csv` keeps the rows kept.
- **Calendar.** Settlement days on which at least 7 roots have a settlement for a ranked contract. A day without a
  definition record carries the last rank map forward, for up to 31 days.

### Frozen inputs
| File | sha256 | After the freeze |
|---|---|---|
| `scripts/run_cmeterm_v3.py` | 98064ca0ee4ad11dfe610b9efcf4eddab64193c9c3a078385761bf38cd53c068 | fixed; `fetch` and `run` refuse to start if any row here changed |
| `data/databento/cmeterm_v2/resolve.json` | 8580ec72a4ecff16dd94ad0981fe26afc00c0f12f6b6d8b02288fe0417cc0a7e | fixed: R504's rank map (git-ignored) |
| `data/databento/cmeterm_v2/manifest_defs.csv` | af3855623279bcdba24dfc06969300e4c9670416ba0c803539ab3cae9c96e456 | fixed: R504's 67 snapshots' quotes and sha256; each file is checked against it before use |
| `scripts/run_cmeterm.py` | 0d035322383ebac8df92922ed2edd214b17988e81cb5d1edb4aacfb0ae48e08a | fixed: R503's frozen rule, imported unchanged |
| `scripts/fetch_databento.py` | b2a03bdcbcd64412c83eec66751ccbbecc3ab3b3bd34a273f1847a0aebea95b2 | fixed |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 | fixed (Newey-West t) |

The rest of the data is pulled after this freeze by the frozen `fetch` into `data/databento/cmeterm_v3/`. Their manifests keep
each request's quote, size and sha256.

## CME specifics in the rule
| Specific | How it enters |
|---|---|
| Roots | CL, HO, RB, NG (energy); GC, SI, HG, PL (metals); ZC, ZS, ZW (grains); LE, HE (livestock) |
| Which contracts | the two with the most open interest (n.0, n.1). These are the liquid ones, not the serial months |
| Expiries | from the definition snapshots, never from a calendar rule |
| Delivery | hold the farther of the two; skip a root whose held contract expires within 40 days of the decision. Holdings within 60 days of expiry are counted and reported, because first notice can come about two weeks before expiry |
| Price units | cents for ZC, ZS, ZW, LE, HE; dollars for the rest |
| Costs | per contract per side: $3.00 all-in (exchange, clearing, NFA and a retail commission) plus 1 tick of slippage against the settlement, in bp of that contract's notional |
| Entry | at the next settlement day's settlement (E), never at the signal's own settlement |
| Holidays, limit days | no settlement means no mark: returns are taken between the held contract's available settlements. Limit-locked days are not modeled |
| Margin and cash | not modeled. Futures returns are excess returns: the collateral's interest is not counted, so the bar is zero (cash) |
| Integer contracts | not modeled. The capital at which every position is at least one standard contract is reported |

## Rule
1. **Decision day D.** The first calendar day of each month, 2010-09..2026-10, that is a settlement day.
2. **Per root, on D:**
   - carry = ln(F_near / F_far) × 365.25 / (expiry_far − expiry_near, in days), where near and far are n.0 and n.1
     ordered by expiry;
   - both settlements must exist on D.
3. **Valid root:**
   - it has a carry;
   - the far contract expires 40 or more days after D;
   - the far contract settles on E;
   - it has at least 40 of the last 63 same-contract daily returns of its n.1 contract.
4. **Book.** No book when fewer than 9 roots are valid. Otherwise k = floor(valid / 3):
   - long the k highest-carry roots, short the k lowest;
   - each leg 0.5 of capital, weighted by inverse volatility (the standard deviation from step 3); gross 1.
5. **Holding.** Each root holds its far contract from E's settlement to the next month's E, at constant weight. At E:
   - a root that keeps its contract pays the change in weight;
   - a root that changes contract pays both sides.
   - Everything is closed at the window's end.
6. **Statistics.**
   - %/yr = Σ daily net / years × 100, with years = calendar span / 365.25.
   - Newey-West t on the daily nets, lag 20.
   - Volatility and Sharpe are on daily nets.

## Verdict (primary: inverse-volatility, k = floor(valid / 3), entry at E, 1x costs, 2010-09..2026-10)
- **CARRY_PASS:** net > 0 with Newey-West t ≥ 2.0 at 1x, and net > 0 at 2x costs.
- **CARRY_WEAK:** net > 0 at 1x, not PASS.
- **CARRY_NULL:** net 0 or below at 1x.

**Cost sensitivity.** 1x, 2x and 3x every cost.

**Also reported, never chosen among:**
- every year; 2010-09..2018-06 and 2018-07..2026-10 apart; 2024-01..2026-10 alone;
- gross by root and by sector;
- months with a book, mean valid roots, the skip counts, mean carry spread between the legs, and how often each root
  is long or short;
- holdings within 60 days of expiry;
- minimum capital (median over months, and at the last month);
- variants:
  - equal weights;
  - k = 3;
  - entry at D's own settlement (no lag);
  - the 12-month mean of each root's carry as the signal (seasonality).

## Null and multiplicity
- **No placebo.** This is one textbook rule with a published prior, read against zero with a Newey-West t.
  - The variants are reported, never chosen.
  - Registry trials: 0. R503 counted this rule's 1 trial; neither R503 nor R504 computed anything.
- **Program trials so far: 9,785,315** (R503's trial included). A PASS is read against them as a single pre-specified rule. It earns no money:
  - at most a minimum-capital and micro-contract feasibility study;
  - then a forward paper lane, only if a book is possible at the owner's stake.
- **Power, stated before the read.**
  - Over 16.2 years, a true Sharpe of 0.6 gives t ≈ 2.4. A Sharpe of 0.4 (the published level less the usual
    post-publication decay) gives t ≈ 1.6.
  - So the chance of a PASS is roughly 65% if the published Sharpe held, and roughly 35% after decay.
  - A NULL at 1x is informative against a Sharpe of 0.5 or more. A WEAK is weak evidence either way.

## Evidence lineage
- **Parents:**
  - R504 (same rule; its fetch stopped on a missing unit of measure);
  - R503 (same rule; its fetch could not finish);
  - room 2 (2026-11-17, the owner's request; M549);
  - R501 and R502 (CME plumbing: settlements and continuous symbols);
  - R478-R482 (commodity roll-up lanes);
  - R370.
- **One decision this feeds:** whether commodity carry is worth a capital and broker study for the owner. The micros
  that exist today are MCL, MGC and 1-ounce gold, SIL, MHG, and micro grains (since 2025). There is none for HO, RB,
  PL, LE or HE.
- **Fresh data:** CME commodity curves never read by the lab.
- **docs/GATES.md** sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. This is gate 1
  on history.

## Not checked before the freeze
- **Fees.** The owner's actual fees from France: broker, exchange tier, non-member fees.
- **Contract mechanics.**
  - First notice dates per root: only the 40-day expiry rule and the 60-day count are applied.
  - Limit-locked settlements.
  - Whether Databento's open-interest ranks match what a trader saw that morning.
  - Whether a contract in the top three by open interest is always listed at its quarter's first snapshot. The
    follow-up request covers the others, and the count still missing is reported.
- **Data.**
  - Whether every root has definition records on every day.
  - Instrument id reuse across years. Settlements are keyed by id and day, and a held contract is followed for at most
    about a month.
- **Model.**
  - Constant weights within the month (an implicit daily rebalance at no cost).
  - Seasonality in NG, grains and livestock curves, which the primary signal does not remove.
