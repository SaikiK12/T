# R357 — PARTIAL: retain the actual inventory, settlement notional and venue capital

Financial code/spec/input freeze **924a57e** preceded all72constructed outcomes.
PREREG SHA256 `10dbb5d40132549d57a51810fe89f980a5d1bbb6a1c1999bff08e932bd4294b3`.
The original independent checker failed on a boundary-capital expectation.
**R358**, separately frozen8104c28, corrects only that checker's expectation
in memory; every R357 financial file/input/result remains unchanged. Its
6371checks PASS and both output directories byte-reproduce. See
[the correction and original failure](../settlement_check_v1/FINDINGS.md).

This is implemented native-paper-account arithmetic and a source-code review,
not a new trading strategy, historical PnL or prospective paper observation.
R355's frozen forward/code/journal and Claude's R356 exit work were not edited,
read for outcomes, stopped, restarted or adopted as our own process.

## Concrete source defects and completed implementation

At pinned public-repository sourcef7935da, R355's `exit_hops` walks another
1000quote order on each leg. That does not generally close the base quantity
opened by the first1000quote order. Its `side_fill(...,complete=False)` also
extends a thin exit at the last shown price. Its score sums funding-rate
fractions and entry-notional fee fractions; event fair/index notionals and
changed exit-notional fees are absent. Original proxy calculations stay intact.
These are source mechanics, not a claim about any actual R355 live outcome.

New `lab/settlement_account.py` uses unchanged PaperAccount as its ONLY cash,
position, reservation, pending-amount and durable-journal authority. Both
entry legs are checked against their separate venue/asset capital before
posting either. Entry quantity remains fixed across1x/2x/3x. The close order
uses the quantity currently held, and needs the full shown depth plus valid
receive/source clocks. Missing/thin/future/stale depth or an unknown fee
retains the position and withholds its liquidation NAV; no last-level fill.
The old quote kernel's descriptive float notional is retained, while money is
summed from those SAME validated levels with decimal strings in the new adapter.

Funding reuses native position_spans and assess_settlement, including MEXC's
entire15s inclusion window and Lighter's explicit pre-update index basis.
Effective values must bind the economic event. Unknown amounts remain native
pending events; a later supplied-model resolution posts once, including
provider aliases. An event-bound caller declaration is not real cash proof.
Twelve unit controls cover fixed closes, fees, missing values, the15s boundary,
alias/resolution deduplication, capital, clocks, restart and unknowns.

## Executed finite economic controls

All **72cells** remain:12invented cases x2directions x3cost tiers. Each cell is
a SEPARATE alternative10000capital account:5000USDT MEXC +5000USDC Lighter;
the shortfall control uses1000/9000 at the SAME10000total. No leverage increase,
capital borrowing, filtering or top-up. Entries use an invented99.9/100.1book
and1000quote per leg. Quantities are fixed from the source's1x entry sweeps.
Fees are supplied SCENARIOS,3bp MEXC and0Lighter, not owner entitlement evidence.
Spread is embedded once. Each exit fee uses its model quantity*exit price.

The table is for **shortMEXC/longLighter only**, with an explicit1:1USDT/USDC
conversion scenario. Amounts are normalized model quote units, not observed
USDC receipts. All other direction/cost cells remain in results.json.gz.

| Invented case | Native1x | Native2x | Native3x |
|---|---:|---:|---:|
| Flat midprices, full depth | -4.600605 | -9.201209 | -13.801814 |
| Both midprices double | -6.900907 | -11.801812 | -16.702717 |
| Both midprices halve | -3.450453 | -7.900908 | -12.351362 |
| MEXC price +42.6%, hedge price fixed | -431.154959 | -435.883491 | -440.612024 |
| Invented event-bound fair/index funding values | +6.612207 | +2.011602 | -2.589003 |
| Same rates, effective values missing | unknown | unknown | unknown |
| Exit at nominal funding+5s, inside MEXC's15s ambiguity | unknown | unknown | unknown |
| MEXC exit depth only1base unit | unknown | unknown | unknown |

The funding example uses invented fair120/index80 and settled rate fractions
.01/.001; it is deliberately NOT a market forecast. Its legacy proxy gives
+4.40/-0.20/-4.80 from rate sums. Correct notionals can change a numeric sign
in EITHER direction; missing event evidence must still withhold cash. The
example's positive1x/2x values do not validate an edge or calibrated expectancy.

**36cells** have a complete conditional combined NAV;36remain unknown. Of the
numeric cells,5are positive,27negative and4zero blocked-entry controls. The
four zeros are inactivity, never profitable strategies. No cell establishes
actual_expected_net: that field stays null in ALL72. Capital shortfall blocks
four of its six cells. Two short-side stressed prices lower the required
reserved notional enough to fit; the SAME fixed q is retained. That boundary
is why the original case-label-based checker expectation was wrong.

### Closing a quote amount does not close an inventory

All66complete legacy synthetic ticket pairs leave nonzero inventory under the
original repeated-dollar order mechanics; six missing-MEXC-exit pairs remain
incomplete. In the flat example, residuals are about-0.02000002base on EACH
venue. When both prices double, the short retains-5.012509base and the long
retains+4.987509. When they halve, the source dollar-close quantities reverse
BOTH positions. These source-side inventories are diagnostic hypothetical
orders, including cells whose native capital check would have blocked entry.
They are not recorded real fills. The new full-depth model closes to zero;
an unsupported close retains its real native inventory instead.

### A small combined loss can hide a large loss on one venue

In the both-prices-double1x example, the combined conditional PnL is-6.90on
ALL10000capital, while MEXC loses1003.90on its own5000and Lighter gains997.00.
The other venue's gain cannot recapitalize MEXC. Original PaperRisk stops
subsequent entries and preserves that stop after reopening. **51/72cells**
halt from a venue loss or unknown cash/liquidation value. This runner observes
risk at the final model state; it does NOT simulate an intrahold liquidation,
execution of a stop, transfer, margin offset or immunity from a large loss.
Actual initial/maintenance tiers, account eligibility and matching remain open.

## Verification, provenance and next dependency

- Full suite before financial freeze:1609tests,0failures,3existing skips,
  202.696s. Final full suite with the separate checker tests: **1612tests,
  0failures,3existing skips,198.912s**. Actualpandas3 is not newly tested.
- Separate stdlib/Fraction reconstruction under R358: **6371checks PASS**,
  including all cells, event cash, fees, funding, unknowns, whole capital,
  every hash/sequence in144account/risk journals and persistent restart stops.
  Financial absolute tolerance1e-65 is distinct from the inherited float score's
  2e-12fraction/2e-9normalized quote comparison. No production financial/risk/
  quote/reporter or original source-score functions are imported by the checker.
- Two fresh native runs have identical results, journal pack, audit and R358
  review receipt. A fresh COPY with one cash field changed by0.01is rejected
  at `native cash conservation`; original artifacts are unchanged.
- Closed reuse scope:10GETs/169748connector-normalizedUTF8bytes/4.2stooltime,
  two unused slots closed; five producer code hashes verified. No source-ticket,
  market/history/private acquisition; earlier allowances never reopened.
- Zero predictive variants/paper days. Local reported trials9479022remain;
  conservative known upstream snapshot throughR355=9479111, versus Claude's
  9479105claim. Immutable R331reservation and all old rows are retained; that
  unresolved six-trial discrepancy is not silently deducted. No market inference.
- R310/R311, every old source/protocol/result and the historical7757/8000requests,
  reported229.85/250MiB accumulated spend stay intact. Only M409's existing
  accounting note/intake dependency is extended; no new queue or panel.

To adopt this in prospective scoring requires a NEW frozen protocol, fixed
inventory tickets with distinct first-seen book/depth clocks and source identities,
actual session/fee/asset contracts, fair/index notionals at each event, and
segregated account risk. Original R355 tickets must not be relabelled as corrected
prospective evidence. No orders, money, secret values, merge/closure or permanent
process. Expected executable net remains unknown; strategy activation is false.

```sh
python scripts/run_settlement_account.py --out /fresh/R357-output
python scripts/check_settlement_account.py --out /fresh/R357-output  # original expected failure
python scripts/check_settlement_account_v2.py --out /fresh/R357-output
```
