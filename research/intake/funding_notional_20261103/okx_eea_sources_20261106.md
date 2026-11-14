# M484: OKX Europe X-Perps public-data qualification

Source review and counts-only plumbing, accessed **2026-11-06**. This extends the
existing carry intake and the M484 queue note; the queue remains authoritative.
No account, credential, order, new market recorder, paid data or bulk history.

## What is documented, and what was actually reached

| Need | Official evidence | Qualification here |
|---|---|---|
| EEA API host | [EEA API guide](https://my.okx.com/docs-v5/en/#overview-production-trading-services), live/undated: `https://eea.okx.com`. | One ordinary unauthenticated `GET /api/v5/public/instruments?instType=FUTURES` returned **HTTP 403**. No alternate host, browser User-Agent, login or retry. The command did not retain the error body or exact request timestamp; it was reported to #7 before 16:19 UTC. Do not invent a response-body checksum. |
| Instrument metadata | Same guide, Public Data / Get instruments: `instType`, `instFamily`, `instId`, expiry/listing, contract value/currency/type, lot/minimum, price tick, settlement currency. | Documented; no native EEA inventory received. Display names in the contract table do not establish API ids. Global SWAP data is not a substitute. |
| Settled funding history | Same guide, Public Data / Get funding rate history: `GET /api/v5/public/funding-rate-history`, `instId`; **up to three months**, **400** rows/request. X-Perps `FUTURES` are explicitly supported. Quote: “realizedRate … Actual funding rate”. | Documented, not live-verified. `fundingRate` is predicted; a future cash test must use `realizedRate` and retain missing values. No rate, APR or return was measured. |
| Current funding/premium | Same guide, Get funding rate: next and last settlement, interval inferred from funding times, cap/floor and `premium`. | Documented current premium. A distinct **EEA premium-history endpoint was not found** in the reviewed guide. Do not invent `/public/premium-history`. |
| Books/prices | Same guide, Market Data / Get order book and Get candlesticks history. | Documented public paths; neither native EEA books nor historical price coverage was reached after the first block. Candles do not supply historical L2. |
| Risk tiers | Same guide, Public Data / Get position tiers; instrument type/family and margin mode matter. | Documented; no EEA tier response or collateral haircut received. Current tiers cannot be asserted to hold historically. |
| Personalized fees | The guide's account trade-fee route requires authentication. | Not requested. Published regular rates below are scenario inputs, not an authenticated entitlement. |

The guide was read only in the listed sections. No complete API/schema audit is
claimed. Its live publisher date is unstated. The single 403 establishes a local
access block; it establishes neither absence of history nor France eligibility.

## Published EEA fees and materially different product terms

- [X-Perps fees overview](https://www.okx.com/en-eu/help/okx-x-perps-eea-fees-overview),
  OKX, published **2026-04-09**, updated **2026-09-01**, relevant fee/funding sections:
  regular maker **0.02%**, taker **0.05%**; the overview describes funding every
  **8 hours**. The instrument-specific schedule prevails over that summary.
- [EEA spot fee comparison](https://www.okx.com/en-eu/help/eea-xperp-spot-trading-fees-comparison),
  OKX, published **2026-05-18**, both regular-user rows and regional caveat:
  with an X-Perps account, spot maker/taker **0.08%/0.10%**; without one,
  **0.20%/0.35%**. A future regular-taker hedge on this CASP therefore starts
  from the disclosed **0.30%** two-leg round-trip fee scenario
  `2 × (0.10% spot + 0.05% derivative)`, before spread, impact, conversion or
  funding. This is fee arithmetic, not a measured return.
- [X-Perps contract specifications](https://www.okx.com/en-eu/help/x-perps-contract-specifications),
  OKX Europe Markets, published **2026-04-13**, crypto section updated
  **2026-11-04**: BTC/ETH term **five years**, expiry **2031-04-04 at 16:00 Hong
  Kong time**. Funding is instrument-specific; the table includes **2/4/8-hour**
  entries while the prose says 4/8 hours. PnL settlement, collateral discounts,
  margin-call and early-termination clauses differ from generic perpetuals.
  The stated margin-call collateral threshold is **30%** of contract value;
  the negative-balance-protection clause forfeits a contract's negative balance
  after collateral liquidation. These are published terms, not a verified
  implementation of OEM's margin engine. R417's generic segregated-perp toys
  do **not** implement or certify X-Perps liquidation or that protection.

The public fee landing page returned navigation without a usable live grid.
The explicit EEA help articles supply the rates above. Account tier, symbol,
conversion/settlement assets, collateral haircuts, funding intervals and the
exact OEM contract must be reconciled before a history or paper result.

## Engineering delivered and decision

`lab/okx_eea_public.py` and `scripts/probe_okx_eea_public.py` are an **inactive**
capability handoff, tested with synthetic responses. They use only the documented
regional host, refuse redirects/private endpoints and preserve immutable request
receipts. Any 403/451/429, HTML challenge, timeout, failed schema or finite budget
stops dispatch without retry. They are absent from the forward task graph and
were **not run** here. The older one-request plumbing failure is the only live
API probe in this review.

The provisional BTC/ETH selector requires five-year linear USD_UM metadata and
refuses a SWAP, ordinary short-expiry future, missing identity or duplicate. Its
binding is deliberately unqualified until an authentic public EEA response can
be compared with the official contract. The handoff reports only schema, counts
and time bounds, with `paper_lane_ready=false`.

**M484 remains BLOCKED on native public data, not rejected economically.** The
documentation indicates funding history exists; creating a recorder as though
history were absent would misstate this result. Normal permitted public access
must first work. Then freeze a separate, single BTC/ETH gate-0 protocol before
measuring: exact X-Perp plus EU-CASP spot, fixed quantity, 1x per leg with both
cash pools counted, published regular EEA fees and 1x/2x/3x all-in costs, actual
settled funding, mark/basis, quote conversion, minimums and each venue's margin
path. Only a qualified history result should lead to a newly frozen forward
paper lane. No legal eligibility or individualized legal advice is inferred
from a public API response; any account/legal decision remains with the owner.

## M485 data boundary

R404 `record_book_costs.py` stores summary costs at $1k/$5k/$10k and aggregate
shown depth; `record_lighter_book.py` stores costs at $1k/$10k. Their parquet
rows do not retain the levels necessary to compute $25k/$50k/$100k sweeps.
Raw tape has BBO, RPI/selected depth and different venue subsets, not a full
matched dYdX/KuCoin/MEXC/Lighter depth archive. No gitignored data folder is
present in this worktree. This does not establish that Claude's container lacks
raw data; #7 requests an existing immutable nonreserved depth/tier manifest.

R417 uses only the two already archived **BTC** MEXC/Lighter snapshots from
R312 as a bounded displayed-depth diagnostic at the requested new sizes.
Other coins, R404's unfinished window, reserved rows and all forward journals
remain outside its measurement. Real synchronized capacity, source clocks,
arrival delay, fees, effective venue risk tiers, conversion and historical
2025-10-10 L2 remain unqualified. No cost-summary extrapolation is allowed.
