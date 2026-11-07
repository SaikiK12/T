# M090 and M322: prospective implementation review (not a PREREG)

This is an implementation handoff, not a forecast PREREG or authority to score
an outcome. The original rule modules below remain pure prototypes with
caller-supplied hashes/clock bounds. Subsequent
[R374 content engineering](../experiments/m090_content_v2/PREREG.md) implements
a bounded public adapter and signed local archive, without UTC/forecast
qualification. R373's uncommitted implementation was lost at restart; its
[original frozen text and interruption](../experiments/m090_publication_v1/FINDINGS.md)
are preserved exactly. The original prototype work read no market outcomes.

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

R374 now supplies a bounded public-response adapter, exclusive fsynced archive,
signed content checkpoint, exact reported event ids, restart/tamper guards and
head-pinned replay. It deliberately supplies no UTC interval, candidate
admission, later-label pairing or forecast score. A signed hash does not prove
exchange truth, public dissemination or independently verified clock accuracy.

Still required: qualified source/clock evidence and authenticated previous-event
completeness; fixed
scheduled collector and append-only ticket/label journal; single-look paired
forecast scorer and dependent-day inference; no-change baseline availability;
power/selection disclosure; exact runner/input hashes, registry id and frozen
forecast PREREG. Until those exist, do not score the primitive on market records
or count an engineering packet as an eligible prospective forecast.

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

## Intraday continuation: cost and independence constraints (2026-11-02)

Re-read the [official June API fee announcement](https://www.mexc.com/announcements/article/updates-to-api-futures-trading-fees-jun-1-2026-17827791535742)
on Nov 2, bounded article table and API-precedence/applicability paragraphs.
The effective table gives maker 0.06% and taker 0.08% per executed notional;
the page's example still uses the earlier 0.04%/0.06% and must not replace the
effective table. No exhaustive later-notice/account-entitlement audit is claimed.

At equal entry/exit notionals, fees alone are 12/14/16 bp round trip for
maker-maker/maker-taker/taker-taker; at 2x they are 24/28/32 and at 3x
36/42/48. These are arithmetic hurdles, not measured costs or expected profit.
Actual account models must charge exit notional, spread, impact, latency,
adverse selection and funding separately. Web promotions are no API-fee proof;
maker fills require evidence of executions/queue assumptions. Region/account
eligibility and any current discounts must be established before a live lane.

More trades do not automatically provide more independent evidence. Overlapping
positions, same-event coin baskets and persistent order flow can leave the
effective independent sample close to the number of days or event clusters.
A new intraday lane must freeze its dependence units, loss/PnL account, family
correction and stopping/power rules before data outcomes. Do not accelerate it
by counting correlated fills as independent trials or reading the reserved
batch early. Existing hourly automation stays stopped; dated Nov 3/5 reads
stay with their current owner. This note starts no new alpha trial or scheduler.
