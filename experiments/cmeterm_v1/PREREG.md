# PREREG: cmeterm_v1 (R503). Commodity term-structure carry on 13 CME futures roots, 2010-09..2026-10

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R503
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_cmeterm.py` is the only writer of `experiments/cmeterm_v1/results/` and of the git-ignored
    `data/databento/cmeterm/`.
- **Date registered (UTC):** 2026-11-17

**Methods:** M549 (commodity term-structure carry on CME futures). Carry family; commodity futures curves are new to
the lab.
- **Paper only:** it reads metered historical data; nothing in the code can place an order.

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
- **Quote:** $2.9455 for the 65 requests (13 definitions, 52 statistics chunks), seen before the freeze.

## Data
| Input | Source | Used |
|---|---|---|
| Settlements | Databento GLBX.MDP3 `statistics`, {root}.n.0/n.1/n.2 (continuous, ranked by the previous day's open interest), 2010-06-06..2026-11-01, one root and four years per request | stat_type 3, update_action 1; the last publication for each contract and trading day |
| Contracts | Databento `definition`, same symbols, one request per root | daily rank → contract, expiry, tick, unit of measure |

- **Spend caps:** $0.40 per statistics request, $0.05 per definitions request, $3.50 in total. The Databento spend
  before this lane was about $0.92.
- **Disk.** Statistics files are reduced on arrival to their settlement rows (`settle_<ROOT>.csv`), and the raw file is
  deleted. The manifest keeps each raw file's quote, size and sha256; `reduced.csv` keeps the rows kept.
- **Calendar.** Settlement days on which at least 7 roots have a settlement for a ranked contract. A day without a
  definition record carries the last rank map forward, for up to 31 days.

### Frozen inputs
| File | sha256 | After the freeze |
|---|---|---|
| `scripts/run_cmeterm.py` | 0d035322383ebac8df92922ed2edd214b17988e81cb5d1edb4aacfb0ae48e08a | fixed; `fetch` and `run` refuse to start if any row here changed |
| `scripts/fetch_databento.py` | b2a03bdcbcd64412c83eec66751ccbbecc3ab3b3bd34a273f1847a0aebea95b2 | fixed |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 | fixed (Newey-West t) |

The data are pulled after this freeze by the frozen `fetch`.

## CME specifics in the rule
| Specific | How it enters |
|---|---|
| Roots | CL, HO, RB, NG (energy); GC, SI, HG, PL (metals); ZC, ZS, ZW (grains); LE, HE (livestock) |
| Which contracts | the two with the most open interest (n.0, n.1). These are the liquid ones, not the serial months |
| Expiries | from the definitions, never from a calendar rule |
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
  - Registry trials: 1.
- **Program trials so far: 9,785,314.** A PASS is read against them as a single pre-specified rule. It earns no money:
  - at most a minimum-capital and micro-contract feasibility study;
  - then a forward paper lane, only if a book is possible at the owner's stake.
- **Power, stated before the read.**
  - Over 16.2 years, a true Sharpe of 0.6 gives t ≈ 2.4. A Sharpe of 0.4 (the published level less the usual
    post-publication decay) gives t ≈ 1.6.
  - So the chance of a PASS is roughly 65% if the published Sharpe held, and roughly 35% after decay.
  - A NULL at 1x is informative against a Sharpe of 0.5 or more. A WEAK is weak evidence either way.

## Evidence lineage
- **Parents:**
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
- **Data.**
  - Whether every root has definition records on every day.
  - Instrument id reuse across years. Settlements are keyed by id and day, and a held contract is followed for at most
    about a month.
- **Model.**
  - Constant weights within the month (an implicit daily rebalance at no cost).
  - Seasonality in NG, grains and livestock curves, which the primary signal does not remove.
