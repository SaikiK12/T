# PREREG: fixed inventory, event-bound settlement cash and separate venue capital

- **Registry id:** R357
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-28
- Canonical dependency: existing M409 account/fee/latency alias; M267 and
  Claude's R355 forward / R356 exit-time work remain read-only.
- Claims: issue7 comments6463497621 and6463538593; existing consolidation draft56.

## Known evidence and scope

R310/R311 are unchanged: 1318 actual missing funding events repaired, all twelve
calibration models exercised, only224/273 common validation days, preselected
2x/3x losses. No rescore, gap/tradability relaxation, winner switch or leverage-up.
R350's completed-subset accounts are negative and lack original executable fills.
R353 is NULL. R354 passes its gate0 rule with proxy prices/rates, not verified
fills or comparable account risk. Its reported primary costs fail3x. R355's
separately frozen prospective rule is owned by Claude and is never rewritten.

Source inspection found that R355 walks a NEW1000quote exit order instead of
retaining entry base quantity; it extends thin exit depth at the last shown
price; its score sums funding-rate fractions and constant entry fee fractions.
Those mechanisms are visible in code, not measured results of live tickets.
R355's observations/outcomes/journal are not read. No new predictive candidate
is selected here. All controls below are INVENTED and chosen after source
inspection. They are accounting counterexamples, not blinded market tests.

One bounded source-code transfer is CLOSED: max12GETs/512KiBbody/3MiBnormalized
text/120saccumulated tool time, commitf7935da10cac2c4969310bc93ad0705d8a5c8d2c.
Used10GETs/169748normalizedUTF8bytes/4200mstooltime;2unused slots closed.
Five producer code hashes match R353/R354/R355 preregistrations. Remaining
source texts are pinned received documents; downloaded scope is distinct from
semantic read scope. Original files, old provenance and every prior scope stay
intact. No market/history/private acquisition, login, credential value, or live
forward process is used. Historical spend stays7757/8000requests and reported
229.85/250MiB; that allowance is not reset or extended.

## Data contract and implementation

New SettlementAccount delegates cash, positions, fees, funding, reservations,
pending amounts and durable hash journals to unchanged PaperAccount. It owns no
second financial ledger. EntryLeg supplies venue/asset/symbol, signed fixed
base quantity, conditional price/mid/fee and separate receive UTC/monotonic
clocks. Both legs are validated against each account's free capital BEFORE
posting either. A crash can retain a partial pair in the native journal; no
transactional fill/atomic venue execution is claimed. Idempotent entry events
reuse native identities. Revision/reconciliation faults remain unknown.

Exit uses the CURRENT native fixed position quantity, not a new quote budget.
Unchanged liquidation_quote validates its exact displayed depth and first-seen
receive/source freshness. Missing/thin/future/stale/wrong-identity depth and
unknown exit fee keep inventory open. There is no last-level extrapolation or
invented forced fill. The inherited sweep returns descriptive float notional;
the new adapter sums the SAME validated levels using decimal strings for cash.
Original quote output is retained diagnostically; no frozen kernel is edited.

Funding delegates to unchanged position_spans and assess_settlement. MEXC
preserves its entire15s inclusion ambiguity and fair-value event binding;
Lighter needs event-bound index plus the explicit pre-update basis declaration.
Rates, estimated stages, missing effective values and changed exposure cannot
be treated as cash. Unknown assessments post pending native amounts; a later
verified-within-the-supplied-model amount resolves once, including provider
aliases of the same economic venue/symbol/time. Caller declarations never
establish an authenticated account/deployment/index bridge.

1x/2x/3x are FIXED cost stresses with unchanged quantities. A conditional fill
price is mid+k*(base fill-mid); fee is k*fee_bp*abs(q)*that fill price/10000,
on EACH entry and exit's actual model notional. Spread is embedded in prices
once. No additive spread cash debit, resizing, top-up, filtering or leverage-up.
Stress prices are scenarios and can exceed displayed prices; they are not
additional observed executable depth. Every financial event is simulation-only.

Initial capital is10000 total,5000USDT on MEXC and5000USDC on Lighter. The one
capital-shortfall control uses1000/9000 without changing total capital. One
venue's gains/capital cannot fund the other. An explicit1:1USDT/USDC FX scenario
reports combined PnL over ALL10000 initial capital; missing FX or account NAV
withholds the return. This is no stablecoin-parity or margin assurance. Native
per-venue NAV/locks/pending exposures remain visible even with missing totals.
PaperRisk's ORIGINAL limits/stops apply and persist across reopening. Financial
completion, input/session/fee entitlement, actual margin and strategy efficacy
are separate; actual_expected_net remains null and activation stays false.

## Finite constructed controls

Exact cases and decimal values are in config.json. Twelve cases, BOTH directions
(shortMEXC/longLighter and the reverse), ALL three fixed cost tiers =72cells.
Each cell has a separate alternative10000account; they are not combined into
a portfolio. Entry is one1000quote order per leg on an INVENTED99.9/100.1book;
q is derived once from the original source's1x entry fill and retained at all
cost tiers. Entry occurs at constructed second1; funding at10; exit at30;
coverage/scoring at40. These are COMPRESSED SYNTHETIC clocks, not hour-long
observations or genuine source receive timestamps. Full synthetic event lists
are declared; a no-event control is never evidence that real missing funding=0.

Cases: flat; both prices double; both halve; MEXC-only42.6percent rise;
one-base-unit MEXC exit depth; missing exit; future receipt; stale receipt;
event-bound funding values; missing funding values; exit at nominal+5s inside
MEXC's15s inclusion window; and separate-venue capital shortfall. Effective
invented fair/index values are120/80, rates.01/.001fractions. They are stress
examples, not calibrated forecasts or observed probabilities.

Run the UNCHANGED pinned R355 pure rule on each constructed entry/exit where
available, retaining original net1/net2/net3, its1000quote normalization, thin
flag and nominal-close residual inventory/reversal. The new native adapter
separately closes fixed q only when depth/clocks permit and posts event-bound
funding only when inputs permit. No old source outcome is overwritten.
Native account and risk journals reopen and reproduce state; incomplete exits
or cash retain exposures/unknown NAV and stop new model entries. Keep ALL72
cells, including blocked entries, failures, negative/zero and unknown results.

## Verification and interpretation

Run the full unittest suite before the lab-code commit, including twelve new
account/cash/clock/capital/alias/restart controls. Freeze and COMMIT this finite
spec, code and exact input identities BEFORE running the result script. Verify
all identities before/after; no fresh output path may overwrite another run.

The separate stdlib/Fraction checker imports NONE of the production financial,
quote, risk, rule or reporter code. It reconstructs every cell's quantity,
fee, price and funding cash, pending amount, capital denominator, whole return,
legacy score and leftover inventory, every native journal hash/sequence/cash
flow, preserved risk stop and input identity. Financial absolute tolerance is
1e-65 for80-digit Decimal rounding; original float score tolerance is2e-12
fraction /2e-9normalized quote units. These distinct declared tolerances never
turn unknown/absent data into a number. Run/check twice in fresh directories
and require byte-identical results/journal pack/audit. A deliberately corrupted
money result must fail independent checking without modifying original output.

No return inference, p-value, calibrated market uncertainty, multiple-testing
win, historical profit or prospective strategy day is available from invented
fixtures. New predictive trials=0; all72engineering cells are explicitly counted.
The local program count remains9479022. Known disjoint upstream throughR355
adds6R337+6R348+57R349+1R351+12R353+6R354+1R355 =89, conservative9479111.
Claude quotes9479105; the six-trial discrepancy remains unresolved and immutable
R331's14reservation is never silently deleted. R356's5claimed trials are not
counted as executed without results. No new inference uses this snapshot.

A future corrected strategy needs its OWN frozen finite protocol, raw and
separate first-seen quotes/depth, session and identity checks, actual fee/input
contracts, fair/index notionals, segregated account risk and ON-TIME future
observations. Do not replace R355's frozen scoring or retroactively convert its
old tickets into new prospective evidence. No orders, money, secret inspection,
merge/closure, automatic activation or promise of permanent execution.

## Frozen identity manifests

f3b607727b3b3bf6a14ec849ae884f0e53565609767103844ce634f7f27450e8  code_inputs.json
6137d906574955e0b77b1c172ee482268a6497778e43cfe8b69a96675e6bd15f  inputs.json
95a2a9484d5730faef6365b6a41b0dc7d71113cc5f7b9e05419c2e4ef8e331ec  config.json
3de78cd09aecda499b48fb2d6a0431c341948bd0cb36dc613c550cbd5e9764aa  sources.json
