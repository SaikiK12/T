# R313: source-stamped paired quotes and fixed quote-access delay

- **Registry id:** R313
- **Owner (single writer):** Codex, `codex/lab-consolidation`, existing draft PR #49
- **Date registered (UTC):** 2026-10-24
- **Canonical method:** M409; input/execution measurement, not a new predictive policy

Code/input manifest SHA-256: 1c47b790de854c63cd2ebd6c85ee166444259105412a7340bec7b5954d19a86a
Current gates SHA-256: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926

## Question and fixed scope

Can the existing public tape endpoints supply source-stamped, first-seen paired
quotes with enough displayed base quantity on a fixed clock grid, and how do the
displayed costs change after a fixed 300-ms access delay? This closes part of
R312's absent source-clock contract; it does not test a trading signal.

Prior R310/R311/R312 evidence is already seen and remains frozen. R311 selected
F0+B_h14 loses at its registered 2x/3x costs and is INCONCLUSIVE on 224/273 common
days. R312's twelve REST observations established local availability and conditional
costs, not source age, sessions or fills. None is rescued or rerun here. Total
predictive trials before R313: 9,478,782. **This measurement adds zero**: two
predeclared access profiles, twelve grids and six pairs are descriptive input
measurements, not strategy candidates. No PnL, inference, forecast selection,
uncertainty bound, alpha significance or strategy success verdict is computed.

Exactly the same BTC, WIF, SKR, ROBO, MEGA and XPD as R312; no substitutions or
post-result crypto-only filter. Pin R288's symbol table, require its MEXC and
Binance identities, and retain XPD as a metals/session control. This diagnostic
set is not a representative sample of the 117-parent universe.

## Finite collection and input identity

Commit/push frozen specification, code, tests, runtime/source versions and symbol
identity before any market collection. `capture` refuses an existing evidence
directory, even if the old attempt failed. No reattempts, daemon or reconnects.
Hold the existing machine-wide Lighter public-API lock, waiting at most 10 seconds.
Use at most **seven metadata GETs**: one current public Lighter perp listing and
one current MEXC detail request per pair. Metadata responses: **2 MiB total**,
1 MiB per body, 20-second request-start budget, per-request timeout at most 3 s.
Preserve failed/truncated bodies and every attempt. Do not read byte cap+1.

Use the existing `record_tape.py` public endpoints: MEXC full-depth snapshots
(`sub.depth.full`, limit 5) and fair-price changes; Lighter read-only BBO `ticker`
and `market_stats`. At most **two WebSocket handshakes**, one per venue, with
5-second connection timeouts and no automatic redirects/reconnects. These are
24 public subscription messages, not orders. Application pings every 15 s; no
account channels, signing, credentials or transaction methods.

One common anchor after metadata, then at most **65 seconds** of stream capture;
the whole operation including lock/metadata is capped at **120 seconds**. Each
venue is limited to **4 MiB decoded application payload, 20,000 messages and
64 KiB per frame**. Reserve a whole maximum-sized frame before the next read;
stop on capacity/duration, preserving why. Compression is disabled, receive
queue is one frame, TLS verification and the managed runtime proxy/CA trust stay
enabled. Limits concern received application bodies; transport overhead and
socket buffering are not interpreted as market observations. Report refuses a
completed collection outside the declared request/body/duration caps.

Record exact raw text frames with venue, ordinal, individual UTC and monotonic
application-receive clocks, including controls and errors. No batch timestamp
stands in for arrival. Retain connection open/close times and failure reasons.
Capture itself computes no economic statistics. `seal` pins the exact evidence
inventory and hashes to frozen code. Commit/push that input identity **before
reporting costs**, as in R312. Failed inputs still produce inactive output rows.

This is a small separately bounded current-data probe. R310/R311 history remains
at **7,757/8,000 requests and 229.85/250 MiB**; no historical allowance is renewed
or used. No reserved 2020 or MEXC-only sample is opened.

## Source contract, clocks and continuity

Reuse MEXC's strict contract-quantity decoder and the validated `DepthSnapshot`
and `DepthLevel` types. Only `push.depth.full` is accepted as a full five-level
snapshot; `push.depth` deltas are never misread as snapshots. The existing full
mode is unversioned and absent from the current depth page inspected here; this
remains an explicit protocol-completeness limitation, not certified execution.
Respect `marketOrderMaxLevel` even for the limited full-depth feed.

MEXC book source time is mandatory `data.cts`, milliseconds as in the existing
tape adapter, separate from envelope `ts`. Lighter's complete one-level BBO uses
mandatory `ticker.last_updated_at`, microseconds consistent with the official
examples and existing tape adapter, plus its reported nonce. Explicit units must
normalize into 2020..2100; never auto-guess another unit or fall back to receipt
or publication time. These are reported source clocks, not certified alignment
to UTC or evidence that an unchanged resting order is still fillable.

Full snapshots/BBO may skip version numbers: this is not event-complete OFI or
an incremental book. Regressing source clocks/versions, conflicting same-version
books and malformed recognized messages invalidate that stream. Recovery needs
a new valid full quote. Identical repeated books, including later production
timestamps at the same version, do not refresh first-seen/source age or erase an
intervening fault. Unattributed corrupt frames invalidate all fields on that venue.

MEXC fair-price WS uses `data.price` and envelope `ts`, unlike REST's `fairPrice`.
Lighter index price uses `market_stats.index_price` and its envelope `timestamp`.
Keep these publication clocks and first-seen ages separate from book-event clocks.
Do not confuse estimated funding with a settled rate or assert a settlement-time
cash flow from these sampled q*fair/index notional observations.

## Fixed causal grid and economic controls

Grid: 5,10,...,60 seconds after the common monotonic anchor. For each of six
pairs, evaluate latest observations actually received by each grid deadline,
then by deadline+300 ms: **144 rows**, retained whether valid, missing, inactive,
stale, thin or disconnected. No resampling after a failed clock or connection.

Fixed quote guards: receipt age 0..1 s, reported source age -100 ms..2 s,
inter-venue source and receive skew each <=1 s, and UTC-versus-monotonic movement
from the anchor <=50 ms. A disconnected channel is unusable immediately, even
if its last quote is recent. These conservative source/availability guards are
not proof that an old unchanged book cannot trade; missing intervals are reported
under this contract without loosening it after collection.

At the immediate deadline only, compute exact common-lot q by R312's frozen
`common_quantity`: round down $250 / max(venue midpoint) to the common base
lattice, using current static contract metadata. Current active/API and known
not-reduce-only flags are required for cost calculation; quote/base minima and
maximum size still apply. If the immediate clock/metadata fails, no future quote
may backfill a decision quantity. The delayed row uses **that exact same q**,
even if prices or displayed size change. A thin immediate quote may retain its
fixed target quantity, but has no available immediate fill or cash-drift control.

MEXC uses at most the shown five full levels; Lighter **only its displayed BBO
level**. Insufficient BBO quantity cannot borrow unobserved deeper liquidity.
Reuse R312's `pair_costs` without modification: displayed same-snapshot crossing
plus a fixed **10/4 bp MEXC/Lighter charge reserve**, at identical 1x/2x/3x
quantities, $10,000 capital segregated $5,000 per venue. Those inherited values
were total-cost assumptions; adding crossing makes this a deliberately
conservative profile, not measured account fees or an exact parent cost replay.
Stablecoin parity is an explicit inherited assumption, not traded FX profit.

Retain every per-observation tier; summarize only fixed per-pair/profile counts,
failure reasons, fresh reference-price counts and cost ranges. Cost BP uses
current one-leg midpoint notional, capital BP uses $10,000. Current prices can
change notional risk during the delay; no budget/leverage multiplier is increased.

For controls with both clocks/depths valid, also report the change in quoted
entry cash at the same q for **both orientations**: long-MEXC is
(M_buy_delay-M_buy_now)-(L_sell_delay-L_sell_now), and long-Lighter is the reverse
buy/sell counterpart. This is quote-cash drift, not realized slippage, arbitrage
profit or a selection of the winning direction. 300 ms is a fixed diagnostic
informed by the public Standard taker delay, not our measured order latency.

## Sessions, inference and stop rules

Retain the literal current `market_config.trading_hours` and status/reduce-only
flags. Empty/uninterpreted trading hours are unknown. `lab.sessions` reference
NYSE/CME clocks are not venue trading permissions and are not used to classify
these perps. Metadata stays static during this short probe; changes are not
certified. Fresh quotes or active metadata do not prove an underlying/session
is open; stale quotes do not prove it is closed.

Every row remains **execution_ready=false**: market sessions, externally aligned
source clocks, the unversioned full-feed guarantee, actual fills/latency and
settlement notionals remain unverified. No strategy is activated; prospective
scoring needs its own frozen protocol and on-time evidence. R311's old 49 common
unscored days and negative stressed policy remain unchanged.

Verify frozen code/PREREG, exact evidence inventory, body hashes and budgets before
reporting. Reproduction may only write byte-identical outcomes; no different
result replacement or edited frozen code. No significance claim or dependent-null
test applies to these dependent descriptive snapshots. No predictive trial count
is reset or suppressed, and no profitability/strategy verdict is permitted.
