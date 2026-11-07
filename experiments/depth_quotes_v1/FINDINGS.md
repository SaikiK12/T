# R314 — PARTIAL: matched depth capacity improves; delayed altcoin notional evidence is still missing

The full reconstructed Lighter book supports **43/144** conditional paired-cost
rows versus **9/144** for its own top-level-only control. Both controls use the
same raw state, event/receive clocks, immediate common quantity and age guards.
This identifies **34 displayed-capacity rescues** in this sample, not fills or
profitable trades. Of the full rows, **five delayed altcoin observations** pass
the quote-cost contract; **zero of those five** also have both fresh fair/index
references. Every row remains `execution_ready=false`.

## Freeze, input identity and bounded collection

- Code/specification pushed in `9b09a46` before any market collection. PREREG
  SHA-256: `d17ac1e4c21136071d5e276f4c68af481810f55eb65af8743f45d6d0df696eab`.
  The input manifest pins 24 files, Python 3.12.14 and websockets 16.0.
- Raw evidence sealed and pushed in `f1386bc` before costs. Input manifest
  SHA-256: `76ddbf55005308a169b4dab3f8ddc4395c2362b99f4318134a88901498197fa6`.
- Anchor: **2026-10-25 01:01:52.523652 UTC**; one 65-s read-start window,
  **73.435 s** total operation. Seven metadata GETs, **404,120 retained bytes**;
  conservative body-read upper bound also 404,120 bytes. No failed requests,
  retry, redirect, replacement subscription or reconnect.
- One WebSocket handshake per venue: **493 MEXC / 1,636 Lighter messages**,
  **136,062 / 929,116 decoded payload bytes**. Both stopped at duration.
  All declared caps held: 2 MiB metadata, 8 MiB/20,000 messages per venue,
  256 KiB/message, 120 s total. Compressed evidence/receipts: 230,787 bytes.
- Static official-source checking separately used four GETs / 420,000 bytes;
  URLs, hashes, pinned SDK and actual read limitations are in `sources.json`.
  Author/document bodies remain ignored scratch files rather than mirrored.
- R310/R311 history remains **7,757 requests / 229.85MiB** of the one approved
  8,000/250 MiB allowance. No historical, reserved-sample or model download.

## What the matched comparison shows

Each cell is available conditional costs out of twelve registered grids. Missing,
stale, skewed, thin and no-causal-quantity rows all remain in the 288-row artifact.

| Pair | Full immediate | Top immediate | Full +300ms | Top +300ms |
|---|---:|---:|---:|---:|
| BTC control |12|2|12|3|
| WIF |2|2|0|0|
| SKR |7|0|4|0|
| ROBO |1|0|0|0|
| MEGA |2|1|1|1|
| XPD metals/session control |1|0|1|0|
| Total |25|5|18|4|

Altcoins alone have **12/48 immediate and 5/48 delayed** full-depth rows, compared
with 3/48 and 1/48 top-only. The five delayed rows are SKR 4 and MEGA 1. BTC supplies
24 of the 43 full-depth rows and XPD supplies 2; neither is silently substituted
for an altcoin strategy.

By the last grid at 60.3 s, the assembler processed six initial snapshots and 1,355
effective updates with no recorded nonce, offset or parser fault. Sampled BTC
depth contained 1,504–1,532 bid levels and 1,598–1,614 ask levels. This validates
the declared reconstruction on this capture, not every future market/schema,
order-book tail or a source guarantee of 10,000 levels.

The comparison to R313's 7/144 at a different time is **not** a matched causal
effect. Here, the top control deliberately shares the full book's mutation clock;
a deeper-level mutation can renew that selected whole-book clock even if the best
price is unchanged. This was frozen before collection and does not certify each
resting order's survival. Strict 1-s receipt, 2-s source, 1-s skew and 50-ms UTC-step
guards remain unchanged. Remaining altcoin failures mostly concern age/skew and
the absence of an immediate decision quantity, not insufficient deeper capacity.

## Conditional economics, including every fixed cost stress

Equal base quantity targets a $250 leg; $10,000 capital remains segregated
$5,000 per venue. These are quote-based current-book entry+unwind costs, not
realized future round trips. The **10/4-bp reserve PLUS crossing** is conditional,
not measured account fees or an exact replay of R310's old all-in assumptions.
Each stress multiplies crossing and reserve together. USD ranges below include
every cost-eligible **full** row; exact top-control costs stay in the artifacts.

| Pair/profile | n |1x USD|2x USD|3x USD|
|---|---:|---:|---:|---:|
| BTC immediate |12|0.6793–0.6877|1.3585–1.3753|2.0378–2.0630|
| BTC +300ms |12|0.6793–0.6878|1.3585–1.3757|2.0378–2.0635|
| WIF immediate |2|1.2051|2.4101|3.6152|
| WIF +300ms |0|unavailable|unavailable|unavailable|
| SKR immediate |7|0.8471–1.0427|1.6943–2.0854|2.5414–3.1281|
| SKR +300ms |4|0.8364–1.0719|1.6728–2.1437|2.5092–3.2156|
| ROBO immediate |1|1.4060|2.8121|4.2181|
| ROBO +300ms |0|unavailable|unavailable|unavailable|
| MEGA immediate |2|1.1325–1.3362|2.2651–2.6724|3.3976–4.0086|
| MEGA +300ms |1|1.1325|2.2651|3.3976|
| XPD immediate |1|1.2869|2.5738|3.8607|
| XPD +300ms |1|1.2869|2.5738|3.8607|

Across eligible altcoin rows the 1x cost hurdle is **33.67–56.28bp** per mean
one-leg midpoint notional, 2x 67.35–112.56bp and 3x 101.02–168.84bp. Borrowing,
financing, impact, failed-leg recovery and future exit conditions remain outside
this quoted cost model; these are not predicted returns or a viable fee tier.

There are 18 matched full-depth 0→300-ms rows: BTC 12, SKR 4, MEGA 1, XPD 1. Quoted
entry-cash drift ranges are −$0.056197..+$0.006920 in the long-MEXC orientation
and −$0.007800..+$0.085429 long-Lighter. These dependent quote comparisons are
not measured execution slippage, latency calibration or forecast uncertainty.

## Remaining binding inputs and decision

All six metadata snapshots report active/API-enabled/not-frozen/not-reduce-only;
all six `trading_hours` strings are empty. Preserve that as **unknown session
permission**, not proof that markets are closed or continuously executable.

Only **one of 17** full-depth altcoin cost rows also has both fresh reference
prices: one immediate MEGA row. **None of the five delayed altcoin cost rows**
has both fresh fair/index references. MEXC alone is fresh on 1/5 and Lighter on
3/5, with no overlap. Price-change streams do not certify an
unchanged index's current value. Even a fresh sampled q*fair/index product is
not an actual funding settlement, known settled rate, margin availability or
liquidation calculation. Do not manufacture fresh timestamps or settled cash.

Next evidence must address source-certified fair/index value availability and
explicit session semantics, while retaining sequence-consistent paired quotes
and on-time funding events. Merely extending the same short stream, relaxing
its guards, replacing unavailable rows with zeros or switching a validation
winner does not establish net expectancy. R311 remains INCONCLUSIVE and its
preselected policy negative at 2x/3x. R310–R313 old evidence stays intact.

## Verification and limits

- **1,128 tests passed, two skipped**, including 16 new targeted tests. Independent
  pre-freeze review caught and verified fixes for disconnect-before-cleanup,
  post-ping deadlines, absolute metadata-request duration and uncertain-tail
  byte-budget reservation. No old frozen code was edited to apply those fixes.
- Independent standard-library/Decimal `check_depth.py`, frozen before any market
  outcomes and importing no production replay/cost kernel, checks all 288 rows,
  **576 causal book receipts**, **156 cost scenarios**, 18 quoted cash-drift rows
  and 172 sampled reference-notional products. Maximum absolute numeric difference
  **4.57e-12** across audited fields; this is numerical agreement, not a bound on
  trading error, source accuracy, margin risk or expected loss.
- Summary and compressed observations reproduce **byte for byte** in a separate
  folder. Complete source/clock failures and null costs remain reproducible.
- Zero predictive variants or prospective paper days added. Program trials stay
  **9,478,782**. The four descriptive profiles are all retained; no post-result
  symbol/profile selection, dependent-null inference or significance is claimed.
- No order, money movement, secret-value access, merge, permanent collection or
  strategy admission. This short, fixed, nonrepresentative sample is execution
  input evidence; positive expected net return remains unproven.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 .venv/bin/python scripts/probe_depth_quotes.py report --out .cache/r314-fresh-reproduction
.venv/bin/python experiments/depth_quotes_v1/check_depth.py
```

Use a new output folder. Capture itself cannot be restarted under this protocol.
