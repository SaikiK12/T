# FINDINGS: R372 ORB index pilot — NULL within the frozen cost model

The implemented four-account family fails its frozen economic screen: every
account loses at 1x, 2x and 3x costs. This is a complete retrospective conditional
bar-account result, not a finding about every ORB, an exact TradeX replication,
actual exchange fills, executable profit or prospective performance.

## Result on common capital and calendar

MEXC NAS100_USDT, October 1–28, 2026: 20 NYSE sessions, all 28 calendar dates
retained, including cash/no-signal days. Every account has 28 known outcomes;
no missing day was dropped or filled with zero. Each starts with USDT 2,000,
with a USDT 1,000 entry-notional cap and funded inventory-proxy accounting.

| Account | Trades | PnL 1x, USDT | PnL 2x, USDT | PnL 3x, USDT | 1x break-even total cost, bp/side |
|---|---:|---:|---:|---:|---:|
| parent | 14 | -24.06 | -52.03 | -79.98 | +1.54 |
| vwap | 14 | -24.06 | -52.03 | -79.98 | +1.54 |
| volume | 5 | -21.22 | -31.17 | -41.13 | -11.07 |
| joint | 5 | -21.22 | -31.17 | -41.13 | -11.07 |

At primary 2x, VWAP-parent is exactly zero, joint-volume is exactly zero, and
volume-parent (therefore joint-parent) is +20.8543 USDT. This reduces losses;
it does not produce a positive account. VWAP passes every one of the fourteen
parent tickets, so it adds no selection here. Volume retains five tickets.
The filtered book's negative break-even cost means price change plus modeled
reported funding is already negative before trading costs. No fitted threshold,
new exit, lower fee or alternate interval is introduced to rescue this result.

Costs are scenarios, not measured historical execution: 1x is the announced
8 bp API taker fee plus 2 bp adverse price cost per side, with adverse tick
rounding. Both scale at 2x/3x. The lower fee displayed in current contract
metadata was not used to bypass the API fee notice. Cash funds the position,
lot rounding and applicable modeled fees; no daily capital reset or leverage.
Funding is base quantity times the exact-event fair-minute open times the
reported rate. The fair open is a mark approximation, not verified payout.

The break-even column is (raw model price PnL minus reported-funding debit)
divided by raw two-sided traded notional. It is the total proportional one-way
cost budget under that model, not a broker quote. Cash comparator is zero on
the same dates. No p-value, statistical winner or program-wide correction is
claimed for twenty exploratory trading sessions.

## Implementation and independent checks

- [Frozen PREREG](PREREG.md) and all direct code/policy/data hashes were committed
  and pushed at `d742de18cc03967d96ec6f31e86be0a2e45da997` before the first run.
- The independent engine creates one close-derived parent ticket and enters one
  full minute later. Rejected filters remain cash; they cannot await a later
  qualifying entry. Stops, gap conventions, 16:01 scheduled exit and funding
  boundaries follow the frozen specification.
- All 24 original synthetic tests passed before freeze. The full local suite
  ran 1,964 tests, OK with three skips. Fifty-four separate rational-arithmetic
  synthetic cash/lot/fee/funding cases passed.
- The complete second run is byte-identical to the [first result](runs/first_read/result.json).
  SHA-256: `fde4f43a553940583734dcf73496f229d47085d2ea7fd3a8b38809e96899da7f`.
- A separately added [Fraction/array checker](../../scripts/check_orb_pilot.py)
  independently reconstructs all 14 parent tickets and 114 trade/account cells
  from the sealed raw responses. Its [audit](runs/first_read/independent_audit.json)
  passes, including quantities, adverse prices, funding and terminal capital.
  Two tamper tests reject changed PnL and a deleted calendar day; the final
  focused suite has 26 passing tests. The checker was added after freeze and
  does not change the registered strategy or its inputs.

Exact raw request URLs and all 43 file hashes are in the
[provenance manifest](../../docs/provenance/orb_index_pilot.json); the acquisition
was 1,472,028 bytes, below its 8 MB budget. Bodies remain outside Git. Re-fetching
latest-vintage history is not guaranteed to reproduce these exact bytes.

## Native verdict, registration and limits

Native verdict: **NULL under the declared economic screen**, because all four
2x accounts are nonpositive. Process result: COMPLETE_DIAGNOSTIC; these describe
different facts. No live forward lane was started and no actual order exists.

Twelve account/cost cells are counted as twelve trials; program bookkeeping
moves 9,479,227 to 9,479,239. This sum is not an independent-test denominator or
selection guarantee. The append-only R372 registry row remains the immutable
REGISTERED/PENDING registration snapshot, explicitly pointing here for actual
completion/native verdict. [outcome.json](outcome.json) is the terminal receipt;
no previous registry row, frozen file or forward journal was rewritten.

Historical contract parameters and publication timing, true book liquidity,
partial fills, latency, fair settlement marks, complete funding reporting,
margin/liquidation and account-specific fees remain unverified. Sample dates
are not a new holdout; earlier project work may have seen them. The parent
R290 crypto OR15 null is unchanged, and M213's QQQ first-candle-direction rule
is not tested by this independent NAS100 OR30 adaptation. Gate eligibility,
power, independent selection control and prospective days are not established.

## Decision

Park this exact OR30/VWAP/volume account family at these costs. Do not move it
into forward paper or brute-force more thresholds on this exposed interval.
Reuse the tested data/guard/accounting machinery for a separately justified,
newly registered rule. The next research priorities remain M090 input fidelity
and the already chosen R305 variants, whose own data/execution constraints must
be resolved independently. There is no newly profitable strategy from R372.
