# R315: source-typed funding values and matched publication availability

- **Registry id:** R315
- **Owner (single writer):** Codex, `codex/lab-consolidation`, draft PR #49
- **Date registered (UTC):** 2026-10-25
- **Canonical methods:** M409 execution inputs; M267 funding accounting mechanics

Code/input manifest SHA-256: e8b4b79007da20462e486854714b7fa68a7f330624307e272b27a5d8abad0bba

## Binding question and limits

R311 repaired 1,318 missing funding events and calibrated all twelve models, but
remains INCONCLUSIVE on 224/273 common scored validation days. Its preselected
F0+B_h14 loses at registered 2x/3x costs. R314 supplied five delayed altcoin
displayed-cost observations, none with both fresh fair/index publications. Do
not rerun that historical sample, change the validation policy, relax clocks or
increase leverage. Existing R310–R314 specifications/evidence stay frozen.

Can dedicated MEXC REST fair snapshots supply more jointly fresh **source
publications** than its change-only fair stream, against the same Lighter index,
books, causal quantity, deadlines and costs? This is a fixed input-availability
and cost diagnostic, not expected return or cash settlement. REST's documented
`data.timestamp` is **System timestamp**; a fresh publication is not a certified
effective-value age or the price used by a funding engine. The trade-time-labelled,
trade-conditioned single/all-ticker alternatives are received but not collected
or treated as idle heartbeats. Source versions and exact read/unread scope are in
`sources.json`; this pass does not rederive Lighter's premium/clamp model.

Four descriptive profiles (WS_change/REST_system crossed with immediate/300 ms),
six pairs and six grids give **144 retained rows, zero predictive variants**.
Program trials remain 9,478,782. No calibrated uncertainty, independent sampling,
dependent-null significance or multiple-testing-adjusted alpha inference is
claimed from these dependent observations. No paper protocol or activation.

## New accounting component, before data

Implement source-typed values with separate publication, first-seen UTC/monotonic,
optional effective-value and funding-event identities. Do not relabel clocks.
Contracts explicitly name venue, symbol, linear-base versus inverse-contract
quantity, base/quote/settlement assets, source version, rate unit and settled
versus estimated stage. Lighter inverse contracts are unsupported. A settlement
value must be bound explicitly to the actual event and known as of the decision;
an arbitrary fresh index/fair packet cannot satisfy that condition.

Model cash for linear quantity q is -q*settlement_value*settled_rate_fraction.
For inverse contracts n with quote face value F it is -n*F/value*rate_fraction,
in the explicit base settlement asset. Official MEXC arithmetic fixtures are
-3 USDT (10,000 contracts *0.0001 BTC *30,000 USDT *0.01%) and -0.0001 BTC
(100 contracts *100 USD /10,000 USD *0.01%). These fixtures validate dimensions,
sign and percentage conversion; they are not observed payments or strategies.

MEXC's public guide allows up to 15 seconds of batch-inclusion ambiguity, including
an entry at nominal settlement +5 s. Require an observed, contract-bound, constant
signed position spanning the whole possible closed inclusion interval; planned
future holdings, gaps, partial intervals, quantity-unit mismatches and changes
remain unscored. Lighter uses its declared hourly event with explicit API rate
units/asset evidence, which the received pages do not establish. Current estimate,
last-paid rate, nominal event, value publication and account credit stay separate.

Deduplicate posted model cash by venue/market/event time; bind a known settled
event ID to its first observed economic time, reject conflicting revisions and
keep append-only assessment attempts. Totals remain segregated by venue and
settlement asset without inferred FX conversion. Verified flat exposure is an
inactive zero; missing inputs are unknown, not zero. Even a complete model-cash
calculation does not assert a real credited account payment. The collection below
has no position or actual settlement-value binding and cannot produce model cash.

## Finite acquisition and input order

Commit/push this frozen specification, code, tests, source identities and runtime
before market collection. One new evidence directory, one attempt only, no reset.
Exactly BTC, WIF, SKR, ROBO, MEGA and XPD from the pinned R288 symbol table; XPD
is the metals/session control and BTC a reference, not altcoin substitution.

Reuse R314's owned-worker metadata requests, common machine-wide Lighter lock
(wait <=10 s), metadata identity mapping, bounded WS reader, full-depth assembler
and immutable raw sealing. At most **7 metadata GETs**, 2 MiB total body-read
upper bound, <=1 MiB/body and a 20-s metadata request-start window. Dedicated fair
snapshots add at most **36 GETs**, <=4,096 body bytes each (144 KiB upper bound),
therefore **<=43 public GET attempts total**. No redirects, retries, accounts,
history, signing, orders or transactions. A failed attempt still consumes its
slot. Known HTTP401/403/429/451/503 stops further metadata/future fair batches;
already-dispatched fair requests may finish. No inferred backoff expiry or retry.

At fixed anchor +9,19,29,39,49,59 s, schedule exactly six fair GET slots, one per
pair, with <=6 concurrent owned spawned workers. The parent deadline is **3 s
including startup**. Record actual dispatch separately from the planned time;
late dispatch after the 65-s request-start window is skipped. Full-body receipt
time is recorded before child cleanup. Partial/error bodies and their first
known failure remain evidence. Reserve a full 4,096-byte unknown tail for an
incomplete read; no cap+1 read. Terminate only owned workers, with at most two
0.2-s cleanup joins. The final slot inventory, response bytes, conservative
read upper bounds and cleanup clocks are retained. Transport overhead is not
claimed as measured application bodies.

At most **2 public WS handshakes**, one per venue, five-second open timeout,
no redirect/retry/reconnect/replacement subscriptions. MEXC: six full5 depth and
six fair-change subscriptions; Lighter: six order_book and six market_stats.
Common UTC/monotonic anchor after metadata; **65-s application read-start window,
120 s total** including lock/network/cleanup. Each venue: <=8 MiB decoded payload,
20,000 messages, 256 KiB/message, compression disabled, receive queue one. Reserve
one maximum message before every read; retain malformed/error/control frames.
Keep inherited proxy/CA/TLS validation. Stop makes a stream unusable immediately,
separately from its cleanup completion; whole async phase <=75 s or remaining
total time. No idle-market refresh or full snapshot-size SLA is inferred.

The prior R310/R311 allowance stays **7,757/8,000 requests, 229.85/250 MiB**.
This separate small current-data diagnostic neither resets nor extends it. Static
primary reading used 8/8 requests, 1,447,969 bytes, 5.237 s against its separately
declared 8-request/6-MiB/120-s limit; raw copyrighted pages remain ignored cache.

Capture computes no economics. Seal/hash all exact raw inputs to this code
identity, then commit/push that seal **before reporting any market outcomes**.
Retain failed/partial capture and every row. Differing output overwrite is refused;
reproduction writes elsewhere. No adaptive second sample to obtain a better result.

## Causal controls and economic reporting

Reuse R314's sequence-consistent full Lighter state, MEXC full5 contract conversion,
market-order depth limits, poisoned-state handling and source timestamp units,
unchanged. For grids **10,20,30,40,50,60 s**, derive an immediate common-lot q
from the $250 leg target divided by the larger midpoint, rounded down only when
the decision books/metadata are valid. Both value profiles and the +300-ms access
control use that exact q; no future quantity backfill or delayed resizing.

For WS_change use the latest valid source-ordered MEXC fair and Lighter index
packets actually received by the deadline. REST_system changes only the MEXC
reference to the latest full-body reply/failure actually known by the deadline.
The latest failed or malformed REST reply poisons that profile; no fallback to
an older good response, other feed or future reply. Preserve REST system versus
WS publication roles and require each exact instrument/kind to match its book.

Strict inherited guards: receive age 0..1 s, reported source age -100 ms..2 s,
cross-venue book source and receive skew <=1 s, local UTC/monotonic movement
<=50 ms. Apply the same age/clock guards to reference publications, plus paired
reference source/receive skew <=1 s. Trade-time packets are not value-publication
evidence. Failed/closed/capped books are unusable; old unchanged prices/orders do
not get fresh timestamps. REST responses ahead of receipt UTC by >100 ms fail.

At valid q/books and jointly fresh publication packets report sampled q*price,
one-bp notional sensitivity q*price/10,000 and reference-minus-book-mid bp. MEXC
units are USDT; Lighter USD quote units retain unverified settlement asset. These
are not a funding forecast, settlement cash or inter-asset nettable PnL.

Reuse pair_costs: **$10,000 capital segregated $5,000/venue**, equal base quantity,
fixed **10/4-bp charge reserve per side PLUS displayed crossing**. These are
conditional charges, not measured account fees or exact R311 all-in-cost replay.
Fixed **1x/2x/3x** multiplies crossing+reserve together. Report displayed-cost and
joint-publication counts by all 24 symbol/delay/profile cells, retaining absent
costs and flags; report USD and per-leg-bp break-even hurdles at all three tiers.
Entry+unwind uses the same current book, not a guaranteed future exit or fill.

All rows remain execution_ready=false and funding cash unscored. Active flags and
raw trading_hours (including empty text) do not certify session/account permission.
Funding-engine effective value, actual inclusion, API rate units/assets, account
fees, fills, two-leg recovery, margin/financing/liquidation, impact and adequate
prospective evidence remain required before a return/activation claim. The
independent frozen Decimal checker audits raw receipts, causal references, all
matched quantities/cost controls, 1x/2x/3x arithmetic and sensitivity products.
