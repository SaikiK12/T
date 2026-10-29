# M090 and M322: prospective implementation review (not a PREREG)

This is an implementation handoff, not a frozen specification, registered lane,
or authority to compute an outcome. The local modules listed below are pure
synthetic-testable primitives: they have no data adapter, journal, scheduler,
network client, scoring command, or order endpoint. Their SHA strings and clock
bounds are caller-provided inputs, not proof of authenticated files or a reliable
clock. No market data, reserved rows or outcomes were read for this work.

## M090: displayed funding versus last settled rate

The proposed primary comparison is BTC_USDT only. For a target settlement T,
decide at T−1 h; use the most recent displayed rate received and durably
available in [T−3 h, T−1 h], and compare it with the exact previous settlement
already available by that decision. Do not assume an eight-hour cycle. Use the
exact target settlement as the eventual label, not a rounded hour. One final
look requires at least 90 unique eligible settlements across 30 UTC dates;
other contracts are descriptive. Missing, late, conflicting and clock-uncertain
events remain missing. A forecast improvement alone is not a carry PnL result.

`scripts/m090_event_rule.py` builds tickets, checks byte-identical publication
under a caller-supplied clock bound, and checks label identity/coverage;
`scripts/m090_history_rule.py` parses a bounded page-one response without
flooring `settleTime`. A missing event on that page is missing even when other
pages exist. Before a real run, an adapter must prove raw-body hashes, on-time
durable publication (including the ticket publication time), exact prior-event
identity and complete labels, and must
connect verified clock evidence to each observation. New `mexc_ticker` fields
are response bounds, not evidence of durable publication; legacy `recv_ms`
is only a request-start time. The old clock journal lacks per-source round-trip
times and cannot alone establish the 1,000 ms bound used by the primitive.

Still required: authenticated source adapter and publication receipts; fixed
scheduled collector and append-only ticket/label journal; single-look paired
forecast scorer and dependent-day inference; no-change baseline availability;
power/selection disclosure; exact runner/input hashes, registry id and frozen
PREREG. Until those exist, do not run the primitive on actual market records.

The [deep source batch](intake/deep_leads_batch_20261029.json) identifies Inan's final
funding-predictability paper (SRC26-032), but does not supply its full costed
implementation or validate MEXC transfer. Keep this first lane to the displayed
and previous-settled forecasts. Proposed primary paired loss is
`(display - target_settled)^2 - (previous_settled - target_settled)^2` on the same
eligible events. Record rate units explicitly; direction accuracy is secondary.
The 90/30 count establishes coverage, not significance or a calibrated pass bar.
Dependence-aware inference and power remain pre-freeze work, especially given
the inference-control limitations already recorded in R320/R321. A later fitted
DAR predictor is a new declared challenger, not a retrospective rescue of this test.

## M322: prospective panic basket

The candidate preserves R303's breadth calculation: rank <=150, 25 consecutive
daily closes, gap <=−20%, 95th percentile of up to 365 preceding days with at
least 180 valid shares, and breadth >=10%. The basket is rank <=50 with at least
30 current names; tied ranks may yield more than 50. A signal is constructed by
00:02 UTC using inputs available then, with proposed entry at 00:03 UTC and a
five-day hold. The selected basket is fixed before execution; unmapped/missing
names stay in cash. Five slots each reserve 20% of initial capital. The eventual
paper comparison must include an always-on basket and cash on the same calendar,
including no-trade days, and one final look after at least 30 eligible events.

At a five-day rollover, release a slot only after its exit and funding
reconciliation have actually completed with the required evidence. Do not free
it merely because its nominal exit timestamp has passed. Process the exit before
reusing the slot; if it cannot be completed before the new entry deadline, skip
that entry while retaining the old exposure and its missing-exit status. This is
a draft policy that the future runner and frozen specification must enforce.

`scripts/m322_signal_rule.py` constructs synthetic tickets and rejects late,
duplicated or incomplete inputs; it does not authenticate them. The provisional
`scripts/m322_account_rule.py` tracks a fully funded inventory proxy, top-level
contract depth and volume steps, partial entries, cash, fixed 1x/2x/3x spread
and API-fee tiers, settlement reconciliation, and missing exit refusal. It is
not an exchange fill, margin, liquidation, or deployable perpetual account model.
`scripts/m322_calendar_rule.py` checks one complete ordered calendar, durable
pre-entry ticket times and account continuity before the 30-trigger look. Its
current conservative rule blocks that look on any missing day rather than
zero-filling it; this policy is a draft choice, not a frozen live rule.
MEXC's published API taker fee was 0.08% per side from 2026-06-01; any live lane
must verify applicable current fee/eligibility and contract metadata rather than
assume they remain unchanged ([fee announcement](https://www.mexc.com/announcements/article/updates-to-api-futures-trading-fees-jun-1-2026-17827791535742)).
The [contract API documentation](https://mexcdevelop.github.io/apidocs/contract_v1_en/) describes
depth volume in contracts and supplies `contractSize`, `volUnit`, `minVol` and
`maxVol`; capture time, current schema and unit provenance still need verification.

Still required: a point-in-time universe and previous-breadth builder with
verified publication; live contract/fee/clock and book adapters; durable
append-only tickets, portfolio state and restart-safe deduplication; per-event
funding schedule and fair-price proof; missing exits, margin and liquidation
handling; always-on and cash control accounts; a calendar-day scorer with
dependent inference and a single-look guard; program-trial and prior-selection
disclosure; exact runner/input hashes, registry id and frozen PREREG. Without
these, the account primitive must not be run on real records or treated as PnL.

R303's own 2020 March signal cannot meet 180 valid prior days without a 2019
warm-up, and the recorded 24 contracts are below its 30-name basket minimum.
Later 2020 eligibility has not been read. Any reserved read belongs only in the
scheduled frozen batch; do not adapt thresholds after looking at the sample.

## Clock evidence and existing work

`scripts/prospective_clock_rule.py` tests conditional bounds from two independent
request intervals. Its output assumes each server timestamp is generated during
the request and within the supplied UTC error, and that the supplied drift bound
is independently justified. It rejects backwards or inconsistent wall/monotonic
durations. It does not measure, synchronize or adjust a clock, and it cannot
turn the existing incomplete clock journal into a verified certificate.

R367 remains frozen and scheduled under its existing owner and rules. R285 and
all active forward lanes, their journals, and the reserved batches are unchanged.
An M090 forecast is one research question and M322 one previously selected
candidate; each needs its own registered trial accounting and a disclosure that
the candidates were chosen after prior searches. Neither result is proven alpha.
