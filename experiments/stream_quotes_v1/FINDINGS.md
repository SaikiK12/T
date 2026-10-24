# R313 — PARTIAL: source-stamped replay works; the available BBO is usually insufficient under the frozen contract

Both public streams ran successfully, and all 144 registered observations are
retained. Only **7/144** have a fresh paired book and sufficient shown quantity
under this contract. **No altcoin has an available 300-ms cost observation.**
This supplies concrete M409 input evidence, not a return estimate or a trading
result. R310/R311/R312 remain unchanged; predictive trials and prospective paper
days added are both **zero**. Program trials remain 9,478,782.

## Freeze and bounded acquisition

- Specification, code and source/runtime identity pushed in `cebbea2` before
  collection; PREREG SHA-256:
  `f84048042335ce203c7b89f855760fa4051877b37733a1187a95c70ed5c4b8d2`.
- Raw input identity sealed and pushed in `3c04b0a` before costs; manifest SHA-256:
  `3df24af0bacc538ea83ee9724f28790e161179562e3a52cd76b50395b58adddd`.
- Seven metadata GETs: **404,204 bytes**. One handshake per venue, no retry,
  redirect or reconnect. Stream anchor: **2026-10-24 18:15:18.936603 UTC**.
- **568 MEXC + 2,629 Lighter messages**, respectively 152,144 and 775,618 decoded
  payload bytes. Both ended at the declared stream duration; total operation
  **69.930 s**. All caps held: seven GETs/two handshakes, 2 MiB REST + 8 MiB
  stream application bodies, 65-s stream and 120-s total.
- Raw compressed evidence/receipts occupy **210,323 bytes**; summary and compressed
  144-row output together are 18,867 bytes. Source inspection separately fetched
  four official documentation pages, 476,830 bytes, with body hashes retained.
- Historical R310/R311 acquisition remains **7,757/8,000 requests and
  229.85/250 MiB**. No historical or reserved sample was downloaded/read.

## What was actually observed

MEXC full five-level snapshots carry `cts`; Lighter's complete one-level BBO
carries `last_updated_at` and nonce. All received market messages parsed without
a recorded parser error. Fair-price changes use MEXC WS `data.price`/envelope
`ts`; Lighter index observations retain their own market-stats publication clock.

At 5,10,...,60 s, the immediate profile fixes a common base quantity from a $250
leg target. The delayed profile uses that same target, with no future quantity
backfill or resizing. The table counts **cost availability**, never fills:

| Pair | Immediate available / 12 | After 300 ms available / 12 |
|---|---:|---:|
| BTC control | 3 | 3 |
| WIF | 1 | 0 |
| SKR | 0 | 0 |
| ROBO | 0 | 0 |
| MEGA | 0 | 0 |
| XPD metals/session control | 0 | 0 |

BTC has insufficient shown quantity at nine immediate grids and nine delayed
grids. Other pairs frequently fail the frozen 1-s receive-age, 2-s reported
source-age or 1-s cross-venue-skew guards. Lighter XPD fails receive/source age at
every grid. Failure counts overlap; the full reasons remain in `results.json`
and every row remains in `observations.jsonl.gz`.

**This does not show that $250 cannot trade in the full market.** Lighter exposes
only its top level in this probe; deeper liquidity is intentionally unknown.
Unchanged resting quotes also age under these conservative guards. R312 used
REST depth at another time, so its 12/12 locally usable rows are not a matched
control. Do not attribute the difference solely to delay, or infer a closed
session from infrequent quote updates.

## Conditional unit economics, without selecting a direction or winner

Costs below include displayed crossing plus the explicit **10/4-bp charge
reserve** on MEXC/Lighter, per side. The inherited numbers were total-cost
assumptions; adding crossing is deliberately conservative, **not measured
account fees or an exact R310 replay**. Both legs have the same fixed base q;
capital remains $10,000 segregated $5,000 per venue.

| Pair/profile | Available grids | 1x round-trip USD | 2x USD | 3x USD |
|---|---:|---:|---:|---:|
| BTC immediate | 3 | 0.7015–0.7068 | 1.4030–1.4135 | 2.1045–2.1203 |
| BTC +300 ms | 3 | 0.7023–0.7112 | 1.4047–1.4225 | 2.1070–2.1337 |
| WIF immediate | 1 | 1.3098 | 2.6195 | 3.9293 |
| Other nine pair/profile combinations | 0 | unavailable | unavailable | unavailable |

Only **one BTC grid** has both controls available; its quoted entry-cash drift
is $0 in both orientations. The other available grids do not form matched
controls. This single dependent observation cannot estimate slippage, execution
latency, quote-survival probability, uncertainty or expected net return. No
zero-cost substitution is made for the 137 unavailable cost rows.

## Verification and remaining blocker

The complete offline suite passed **1,095 tests, two skipped**, including 21 new
tests for causal receive-time selection, unit-specific source clocks, malformed
and duplicate/regressing updates, disconnections, fixed quantities, BBO capacity,
bounded acquisition and the complete retained 144-row report.

The summary and compressed observations reproduce byte for byte. Independent
`check_stream.py`, importing no production replay/cost kernel, verifies all
**288 selected book receipts precede their deadlines**, common lot quantities,
reported clock guards on cost-eligible rows, and **21 cost scenarios** from raw
frames with Decimal arithmetic: maximum discrepancy **$5.2e-14**. It also checks
14 recorded notional products; these are not verified settlement cash flows.

Every row remains `execution_ready=false`. External source-clock alignment,
market-session permissions, the unversioned MEXC full-feed guarantee, actual
fills/leg recovery, standard-API execution latency, stablecoin parity and
settlement-time notionals remain uncertified. Empty `trading_hours` is retained
as unknown; NYSE/CME reference clocks are not used as venue permissions.

The binding next input is **sequence-consistent deeper paired depth with explicit
fresh-snapshot/heartbeat semantics**, plus contemporaneous funding-notional and
session evidence. A top-only public stream cannot silently borrow deeper resting
liquidity, and an event timestamp alone cannot certify a current executable book.
Do not rerun this capture, enlarge size/leverage, relax age/depth guards, use BTC
as a replacement altcoin strategy, or infer funding-policy returns from this
sample. Prospective scoring still needs its own frozen protocol and on-time data;
R311's negative 2x/3x policy and 49 common unscored days remain unresolved.

```sh
.venv/bin/python scripts/probe_stream_quotes.py report
.venv/bin/python experiments/stream_quotes_v1/check_stream.py
```
