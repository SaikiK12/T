# R359 — PARTIAL: new first-seen controls run, but exits are late and altcoin books fail freshness

Protocol/code/input-contract freeze **4ae8101** preceded EVERY new market call.
PREREG SHA256 `e35ffd5419b3b602b507ebf1111cdbb6046d6a4ecabd2d6713ec43a6c8e787bb`.
Raw frames, actual online receipts, native journals and their exact identity
were sealed in **8516653** before independent/offline analysis. This is one
new prospective INPUT capture with fixed no-signal shadow controls; it is not
a profitable strategy, complete net-PnL observation or qualified strategy day.

## What is now implemented and actually exercised

The new collector wraps the UNCHANGED R314 transport. Its mirror records the
actual receive start and earliest full-body UTC/monotonic first seen of the
SAME frames, before parent transport recording. No additional socket, GET,
reconnect or inferred timestamp is created by the mirror.

At fixed anchor+20/+50sappointments, the controller reconstructs only the
then-received prefix, writes the full snapshot and fixed q, fsyncs its hash
into the native evidence journal, and records actual issue completion.
Only then does it wait at least300msbefore using later quotes for the model
entry/exit. q is never recalculated from later prices. The new online model
action time is separate from original quote receipt; no quote clock is refreshed
to make it appear current. A late/missed event cannot be backfilled as on-time.

All old depth/nonce/epoch/source/receive/lot/activity guards remain. Both entry
and exit need the full shown base quantity. The native PaperAccount owns all
price/fee/position/lock state. Exits close the held q, without another fixed-
dollar target or thin-book extrapolation. Missing exits retain exposure.
The source/view, online decision, later execution, actual fee/fill/session and
funding-value qualifications are different facts; none authorizes real orders.

## Exact completed live scope

- **7public metadata GETs**,405878response-body bytes; conservative read upper
  bound also405878. One Lighter list and the six fixed MEXC detail endpoints.
- **2WS handshakes**, one per venue, no reconnect. Lighter1752messages/
  1206807decoded payload bytes; MEXC600messages/161337payload bytes.
- **2352new first-seen frames** total, with exact parent/mirror byte identity.
  Combined network response-body/decoded-payload measure1774022bytes, below
  the declared2MiBmetadata +16MiBstream cap. Physical wire bytes are not measured.
- **72.877021606swhole capture**, within120s. Both streams ended at the fixed
  receive window;0frames were received after it. No capture error/denial,
  request retry, historical/private request, order or recurring process.
- Scope CLOSED. All7metadata and2handshake slots were used; no allowance is
  reset. The historical7757/8000requests and reported229.85/250MiB stay unchanged.
  This was the separately declared small live scope, not historical approval.

## Actual issue timing: preserve two late exit stages

Times below are ACTUAL application receipt timestamps, not a replay schedule.
The250msissue deadline was fixed before collection and is unchanged.
Execution's planned time is the preceding actual issued decision+300ms.

| Stage | Start lateness ms | Processing/IO ms | Issue lateness ms | On time |
|---|---:|---:|---:|---|
| Entry decision | 1.198 | 176.667 | 177.865 | yes |
| Entry model execution | 0.911 | 222.326 | 223.237 | yes |
| Exit decision | 0.999 | 300.983 | 301.982 | **no** |
| Exit model execution | 0.891 | 348.115 | 349.006 | **no** |

All FOURissued stages remain, but only TWOare on time. The six closed BTCcells
therefore do not have a fully on-time lifecycle even before financial/source
qualification. Their late source receipts and model closes are preserved
separately; no deadline is widened and no qualified strategy day is added.

The controller currently rebuilds the growing received prefix at each stage.
Measured processing/serialization/native-journal IO is part of this application
lateness, not isolated exchange or real-order latency. The next concrete
implementation target is incremental/precomputed book state with preserved
source identity and unchanged deadlines. No speedup is measured or claimed here.

## Economic result at unchanged capital and costs

All12fixed diagnostic variants/36cost cells remain: six symbols x2directions,
each at1x/2x/3x. Each alternative has10000initial capital,5000per venue, and a
250quote leg budget. They are not summed into a larger-capital portfolio. The
same base q is used on both legs and all tiers; no leverage-up/top-up/resizing.

Only BTCpasses the entry book/lot guards, giving6conditional model accounts
and24native simulated fill events. Its fixed quantity is **0.0030BTC** per leg.
The other30cost cells remain blocked. WIF/SKR/ROBO/MEGA have stale receive/
source books or source skew at the required instants, not fabricated exits or
zero-profit trades. XPD also retains its predeclared metals/session-negative
control. Missing original decision quantities are not created from later books.

The table reports ONLY a known closed **price-minus-scenario-fee component**,
using explicit1:1USDT/USDC conversion. Fees remain the original10/4bpMEXC/
Lighter reserve scenarios; they are not owner-account entitlement evidence.
Full funding cash is UNKNOWN and not zero-filled; all full_net_pnl,
full_account_nav and actual_expected_net fields remain null in every cell.

| BTC fixed direction | Price/fee component1x | 2x | 3x |
|---|---:|---:|---:|
| ShortMEXC / longLighter | -0.653486 | -1.338171 | -2.022857 |
| LongMEXC / shortLighter | -0.729927 | -1.428643 | -2.127347 |

These are modeled quote-equivalent amounts on ALL10000capital, not actual
account cash or complete net returns. No positive control/winner is selected.
For the1xshortMEXCcontrol, realized price component is +0.030600, fees0.68408562,
giving-0.65348562. Its funding-needed-to-break-even component is +0.65348562;
that is a hurdle, not a forecast or verified payment. The opposite fixed
direction is also negative before the unverified funding amount. The no-action
10000cash reference has explicit zero modeled interest over this short scope.

The native snapshot is deliberately named price_fee_only_native_snapshot:
its zero funding-event subtotal means no funding cash was supplied to that
COMPONENTaccount, not that a real missing payment was zero. Consumers must use
the outer null full-net/full-NAV fields and funding_coverage_verified=false.
Unpriced residual inventory also withholds even a closed component subtotal.
Missing FX withholds asset aggregation; individual asset accounts remain intact.

This single dependent65swindow has no calibrated strategy uncertainty, market
p-value or average-return inference. Even a positive component would not
establish an executable edge. Actual matching, total order latency, owner fees,
session/access, event-effective fair/index cash, collateral/margin/liquidation
and stablecoin conversion remain unqualified. Paper strategy activation is false.

## Verification and reproducibility

- **1622tests,0failures,3existing skips,200.526s** before the code/spec commit.
  Ten new tests exercise minimum decision delay, immutable q, actual action
  versus quote time, late/missed/thin guards, FX, denial/no-reset and an
  independent cash-corruption rejection, using invented fixtures only.
- **13117independent financial/timing/raw-identity checks PASS**. No production
  account/quote/risk/controller functions are imported by that checker. Fraction
  reconstructs each native price/fee/q/cash/FX/break-even identity at1e-65absolute
  tolerance for80digit Decimal. Source full-book reconstruction is additionally
  compared using the frozen assembler, not claimed as an independent parser.
- Fresh offline reproduction is BYTE-IDENTICAL to the original online result,
  all37native account/reference journals and the receipt file (38files). Two
  runs of the independent audit also byte-match. The reproduction notice explicitly says
  offline-only and0newprospectivetickets. It cannot increase on-time counts.
- Exact input/result/audit hashes are in evidence_inputs.json and reproduction.json.
  All101frozen code/source identities, older specifications/results and original
  failure receipts stay intact; R310/R311 are not rerun. Actualpandas3 is not
  newly tested. Runtime is Python3.12.14/websockets16.0/NumPy2.3.5/pandas2.2.3.
- All12diagnostic variants are counted conservatively, including inactivity and
  blocked inputs: local reported trials9479022→**9479034**. These are not twelve
  newly discovered alpha models or independent samples. The pre-existing
  six-trial cross-branch discrepancy/reservations are retained, with no new
  multiplicity/efficacy claim. Prospective STRATEGY days added=0.

The remaining concrete blockers are on-time local processing, publisher-
certified current validity of idle altcoin books without relaxing old guards,
and actual fee/session/funding-value/account-risk contracts. No new collection
is authorized by reusing this lane's closed allowance. Any future strategy
needs its own frozen protocol and qualified new observations. R355/R356/M267,
PANEL and all original collectors remain unchanged. No orders, money, secret
inspection, merge/closure, daemon or guarantee of permanent execution.

```sh
python scripts/capture_live_pair_controls.py reproduce --out /fresh/R359-replay
python scripts/check_live_pair_controls.py --out /fresh/R359-audit
```

The capture command is intentionally not a reproduction instruction: its one
evidence directory already exists and refuses another network attempt.
