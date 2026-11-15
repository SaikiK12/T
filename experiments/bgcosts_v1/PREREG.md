# PREREG: bgcosts_v1 (R495). What a taker order actually costs on Binance and Gate, for the carry book that passed

Freeze with `lab.prereg.freeze()` before any order book is read. After that this file is never edited.

- **Registry id:** R495
- **Owner (single writer):** OpenHands agent, branch `openhands/session-persistence-factor-report`
- **Date registered (UTC):** 2026-11-15

Method M543. **Measurement only, 0 trials.** No strategy test, no signal, no reserved read, no orders.

## Why this lane exists
Three reserved-sample batches have run. The strongest PASS is **C14, binance+gate funding carry**
(`experiments/reserved_batch1`): +2.86%/yr at 1x on 2020, NW t 4.03, p 2.8e-5, trimmed +0.68 bp,
leave-two-coins-out +0.59 bp, 2x +1.86%/yr. Its earned forward lane **R390 `xfund_bg_fwd`** is running.

Every reserved PASS is blocked on the same sentence in its own FINDINGS: *measure the book costs
before the lane is written*. `R404 book_costs_v1` measures dYdX, KuCoin and MEXC — **not Binance and
not Gate**. So C14, the best-confirmed book in the lab, is the one whose cost is unknown.
`research/RESERVED_COST_CHECK_20261115.md` shows why this matters: R391's long-tail PASS assumed
7 bp/leg/side but KuCoin's measured median is 196-337 bp/side in three of four ADV bands, 28-48x.

**R404's recorder is not extended.** Its frozen PREREG says the recorder is not changed and that
Binance futures answer 451 and are "not worked around". This is a separate lane with its own script,
its own outputs and its own freeze, so R404's inputs and evidence stay untouched.

## Question
For the contracts C14 can trade, what is the measured taker cost per side at $1k / $5k / $10k on
Binance and on Gate, and how does it compare with C14's frozen 7 / 14 / 21 bp per leg per side?

## Endpoints and why they are legitimate
- **Binance:** `https://www.binance.com/fapi/v1/depth`. `fapi.binance.com` is geo-blocked here (451);
  `lab/live.py` already documents that the *same public endpoints* answer on `www.binance.com`, and
  R278's Binance carry book reads funding through it. This is the repo's established public path,
  not a circumvention: no key, no login, no bot check, no private endpoint.
- **Gate:** `https://api.gateio.ws/api/v4/futures/usdt/order_book`. Public, keyless, HTTP 200.
Both were probed for reachability before this freeze; no book was read.

## Universe (bounded before any read)
`experiments/xfund_v1/symbols.csv` rows with **both** a `binance` and a `gate` symbol: **860 contracts**,
the C14 universe. Two reads per contract per snapshot, **1,720 book reads**. Nothing else is fetched.
Current listings only, so delisted contracts cannot be measured; that survivorship limit is stated,
not corrected.

## What is measured, per contract per venue
Best bid/ask, mid, half-spread in bp; the cost per side of a market order of **$1k, $5k, $10k** walked
through the shown book (bp from mid to average fill; NaN when the shown book is too thin); USD shown
and USD within 1% of mid per side; the venue's listed taker fee where the endpoint publishes it.
Depth limit 100 levels on Binance, 100 on Gate (both endpoints' caps are respected).

## Pacing and failure handling
Binance 0.2 s and Gate 0.2 s between requests, the two venues in parallel, at most 2 workers each.
On HTTP 429/418: stop that venue for the snapshot and record the failure, never retry-storm.
A contract that errors or is unlisted is recorded as missing, never as zero cost.

## Decision (this is a measurement, so there is no significance gate)
Report, per venue and per 24h-volume band where volume is available, the median over contracts of the
per-contract median side cost at each size, and the **multiple of C14's frozen 7 bp unit**.
- **PRICEABLE** if at least 60 contracts on **both** venues return a finite $10k side cost.
- **NOT PRICEABLE** otherwise; the lane then reports what it got and stops.
The comparison is reported as a multiple, **not** as a new verdict on C14. C14's frozen PASS and
R390's frozen forward rule are unchanged by anything here.

## Multiplicity
**Trials: 0.** This measures costs; it tests no return. Program trials before: **9,785,317**, unchanged
after. No reserved sample is read, so no read budget is spent (2020 2/4, Gate 2/4, MEXC-only 1/4,
KuCoin/dYdX/Lighter 1/4 all stay as they are).

## Evidence lineage and admission
- Canonical method id M543. Parents: R286 C14 (the PASS and its cost unit), R275 (the rule and the
  7/14/21 bp unit), R390 (the forward lane, untouched), R404 (the sibling cost lane, untouched),
  R224 (MEXC cost precedent and the method this follows).
- `docs/GATES.md` SHA-256 at registration:
  `45933022474f272cfe299e6defbfc4e95ec1f34e579ecda9c53a26a7903df9cf`.
- Admits nothing to real money. Paper measurement on public endpoints; places no order.
- One snapshot is a thin cost sample, as R224 needed 102. This lane reports its own snapshot count
  and does not claim a stable cost surface from one pass.

## Stop rules
One run of `scripts/record_bg_costs.py`. No new sizes, venues, contracts or thresholds after seeing
any output. A crash fixed after the freeze is documented in FINDINGS with the changed sha.

```inputs
78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0 experiments/xfund_v1/symbols.csv
5ba96808e1c71f3c0b45d6b0e7db6dbde7aa10c532d396ddf63b99ebf2c07d8d scripts/record_bg_costs.py
a7f67cdb1fd9dec7e7bce4d09dee9d2061462b9a6dc68f414cba56fd46d1c699 tests/test_record_bg_costs.py
d049ac04e97f9e65da74549ce4abaab569afbc9fc92f69b4854c125323019afb experiments/reserved_batch1/carry.toml
```
