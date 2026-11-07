# PREREG: common-parent ORB/VWAP/volume index implementation pilot

- **Registry id:** R372
- **Owner (single writer):** Codex, owner-authorized implementation while Claude is absent
- **Date registered (UTC):** 2026-10-29
- **Inputs manifest SHA-256:** 9b4c5e085edfa008ae1cb88766e35b069c71010912a196a587086fc0fef869dc

## Question

On the fixed NAS100_USDT historical bar-account scenario below, do VWAP and
relative-volume filters improve the same first OR30 parent ticket at 2x costs?
This is a retrospective implementation/economic pilot, not a calibrated
confirmatory test, a TradeX/Fractal replication or prospective paper evidence.

## Universe and data

One currently listed MEXC USDT-settled TradFi perpetual, NAS100_USDT, selected
from the owner's index-ORB request before reading its pilot outcomes. No
cross-sectional universe or delisted-symbol inference. Current metadata is
not historical membership, contract-unit or account-fee verification.

Fixed interval: 2026-10-01 through 2026-10-28 inclusive; 20 explicit NYSE sessions,
all 28 calendar dates retained. NYSE's official calendar lists no holiday/early
close in this interval. The exact UTC sessions and weekends are sealed in
calendar.json. No reserved 2020 or reserved coin sample is accessed: GATES
explicitly excludes TradFi index perps from that coin reserve. Dates may already
have been inspected by other project work and are not a new holdout.

Public MEXC last-trade and fair-price minute-bar raw bodies for 09:30–16:02 New
York and exact reported funding events were acquired without outcome analysis.
The 43-file, 1,472,028-byte folder has an exclusive raw receipt and file-level
hash manifest at docs/provenance/orb_index_pilot.json; its own digest and all
direct code/policy inputs are bound by inputs.json and this frozen document.
Receipts/hashes establish these local bytes, not independent source truth,
historical publication times, quote freshness or complete settlement reporting.

## Feature lineage and availability

| Feature | Parents and units | Window and assumed availability | Vintage and missing rule |
|---|---|---|---|
| OR high/low | Venue last-trade minute highs/lows, USDT per base unit | Complete [09:30,10:00) bars; known only at 10:00 in this historical proxy | Latest-vintage REST, not first-seen captures; any missing opening bar is unknown |
| First parent close | Minute close above OR high | First eligible completed bar after 10:00, close strictly before 11:30 | First parent ticket is irrevocable; no later qualifying-ticket substitution |
| Session VWAP | Typical price (H+L+C)/3 weighted by venue vol | Accumulate from 09:30 through the signal bar only | Volume-unit constancy is assumed; zero total/prior-range volume is unknown |
| Relative volume | Signal minute vol / mean per-minute opening-range vol | Signal bar must be complete; threshold 1.5 | Latest-vintage volume; zero opening-range denominator is unknown |
| Entry/exit prices | Venue minute opens and stop-touch minute low | Outcomes only; entry one full minute after decision; scheduled exit one minute after cash close | No quote/fill authentication; missing/untraded active or exit bar is unknown |
| Contract size/steps | Current contractSize, volUnit, minVol, maxVol, priceUnit | Applied as scenario constants, not a historical feature | As-of 2026-10-29; historical changes unverified |
| Funding | Returned exact settleTime/rate and same-time fair-bar open | Accounting label only while position held | No floor/nearest-event substitution; missing mark or event at entry/exit boundary is unknown |

No forward-captured feature, strict on-time clock certificate, portfolio
membership claim or historical release-time proof is supplied by this lane.

## Closed rule family

Four long-only accounts share the same first parent ticket each NYSE session:
parent, parent+VWAP, parent+volume and parent+both. VWAP passes when signal close
is strictly above session VWAP; volume passes at >=1.5 times the opening-range
per-minute mean. The joint needs both. A rejected ticket stays cash for the
whole session; no retest, short book or later replacement. The community
indicator's upper-half-close filter is excluded. OR30 is fixed, no range grid.

Decision at the completed signal bar's close; entry is at the minute open one
full minute later, plus adverse cost and tick rounding. Thus a 10:00–10:01
signal bar enters at 10:02. This deliberate latency is not a claim to obtain
the signal close or the immediately simultaneous next-bar open.

Stop remains the fixed opening-range low. A raw entry open at/below it skips
the shared ticket. Once a held minute touches the stop, exit the next minute
at the worse of stop and next minute open, then apply adverse costs. Otherwise
exit at the 16:01 venue-minute open, one minute after the NY cash close. For a
separately provided half-day calendar the same policy is 13:01; none occur in
this sample. This timing reduces routine coincidence with 16:00 funding; an
actual entry/exit funding boundary is still refused. No target/trailing/ATR
search. Stop-touch ordering and executable prices within a minute are unknown;
the adverse convention is a model, not a certified fill bound.

## Capital, costs and settlements

Each of twelve accounts starts with USDT 2,000 and a USDT 1,000 maximum entry
notional. There is no daily equity reset and no leverage. Lot quantities are
rounded down at the actual adverse entry price under the current unit/step
scenario, capped by current maxVol and available cash with a fee reserve.
Below minVol stays cash. This is a fully funded inventory/cash proxy for
comparison, not exchange margin, an actual spot purchase or liquidation logic.

API taker fee: 8 bp per side, from MEXC's effective June 1, 2026 announcement;
it overrides the current metadata's lower advertised rate. Add a fixed 2 bp
adverse price scenario per side; this is assumed spread/slippage, not a measured
historical book. Scale both fee and price cost by 1x, 2x and 3x. Entry prices
round up and exit prices down to the current price tick. No maker fill model,
web discount or after-the-fact fee reduction is allowed.

Long funding debit = base quantity * exact-event fair-minute open * rate;
negative funding is a credit. This follows the public position-value formula
with a minute-open fair-mark approximation, not an actual settlement mark or
verified cash payout. Events exactly at entry/exit are ambiguous and invalidate
that account. Missing fair marks cannot be replaced by entry notional. Provider
pagination brackets the requested dates but does not independently prove all
settlements exist. Funding cash or worst held-bar equity below zero is retained
as insolvency/unknown, never loss-capped to zero. Real margin/maintenance tiers,
funding corrections, live depth and partial-fill execution remain unverified.

## Splits, summaries and native verdict

There is one fixed descriptive pilot interval and no fit, training selection,
validation split or unseen efficacy look. No p-values or Sharpe-based selection.
Report every account at all three cost tiers, calendar-day mean, trades and
break-even total one-way cost under the model. The five planned 2x differences
are VWAP-parent, volume-parent, joint-parent, joint-VWAP and joint-volume.
Their calendar includes no-trade and weekend cash days.

Never replace an unknown outcome with cash or restart that account's capital
on the next day. All later outcomes of that account remain unknown. An arm that
rejects the ticket can have a known cash result, but no partial-calendar paired
comparison is published if any account is incomplete. A missing bar after a
fully resolved earlier stop does not invalidate an already closed trade.

Native verdict: DATA_BLOCKED/INCONCLUSIVE if any account is incomplete. If all
accounts complete and all four have <=0 total PnL at 2x, the economic screen is
NULL **within this model**. Otherwise PARTIAL descriptive evidence only; no
CONFIRMED verdict, optimum arm selection or automatic forward activation.
The append-only registry row records registration (REGISTERED/PENDING); this
lane's FINDINGS and immutable run receipts record the eventual native outcome.

## Null, multiplicity and evidence admission

The cash account is zero on the same dates; parent and single-filter controls
are explicit. There is no calibrated dependent random null in this pilot and
therefore no statistical SIGNAL decision. The tiny sample and unknown execution
prevent an economic pass from being statistical or executable confirmation.

Four rule variants times three cost tiers = twelve account cells, all counted
conservatively as twelve new program trials. Five descriptive paired contrasts
are disclosed, not extra independent attempts to claim significance. No
alternative dates, exits, symbols, filters or thresholds may be searched after
outcomes. Prior program trials: 9,479,227; raw sum is bookkeeping, not an
independence assumption or program-wide selection correction.

Canonical method: M206; M213 is related but its QQQ first-candle-direction rule
is not tested. Source parents are SRC26-042/044/045, and R290 already tested
different crypto OR15 rules and returned NULL. This does not reopen that result.
One decision group: whether this specific index parent/filter implementation
earns later independent data/execution investigation. No private strategy,
strict prospective day, reserved-read authorization or real-order authority.

Current GATES SHA-256:
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926.
Dependent-null calibration, selection control across the prior program,
strict clocks, calibrated 80% power, 10-best-day trimming, independent universe
evidence and executable margin/funding proofs are not met. Leave-two-coins-out
cannot be satisfied on a one-index pilot. All gate eligibility remains blocked.

## Stop and reproducibility rules

Verify PREREG first, then exact code/policy hashes, registered identity/trial
count and the entire data-folder file set before reading inputs; verify again
before writing results. One exclusive run lock and a fresh run directory. An
identical second run may verify bytes but creates no new variant or prospective
day. No modification of any frozen input, overwritten outcome or repaired
historical raw record. A defect requires a separate new lane; preserve this
lane's original failure. No order endpoint or scheduler exists in this runner.
