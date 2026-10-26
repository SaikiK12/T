# R312 — PARTIAL: paired REST inputs and cost arithmetic work; executable evidence remains blocked

R310/R311 are unchanged and INCONCLUSIVE. This measurement adds **zero predictive
trials**, no new strategy, no historical rerun and **zero prospective paper days**.
It supplies a reusable quote/lot/cost contract for their unresolved M409 execution
inputs, using the existing MEXC decoder, depth-level type and Lighter API lock.

## Frozen before measurement

- Specification/code/universe frozen and pushed in `3ea8440`, before collection.
  PREREG SHA-256: `5e7942da7b22d482e3e754a9f0c7d4be5c4a16cb81a2be1f00b834279410ea30`.
- Raw inputs and per-request receipts sealed and pushed in `c2ba810`, before costs.
  Evidence-manifest SHA-256: `fa76ba23ef1ff9dc49cd939ed17cd04259cd9262c464bdd5b81df92bc420add6`.
- Public current-data collection: **43 GETs, 643,091 response bytes (0.613 MiB),
  21.624 seconds**, no request failure or retry. Caps were 48/8 MiB/180 seconds;
  43 compressed bodies plus receipts occupy about 90 KiB. All are committed.
- Separate primary-schema inspection used four public documentation GETs,
  20,605 bytes. The official Lighter SDK revision is
  `a7a9ba88514d38a863a33642acd41f8adf442e5c`; URLs/hashes/scope are in `sources.json`.
- R310/R311 historical acquisition is still **7,757/8,000 requests and
  229.85/250 MiB**. That allowance was neither reset nor extended.

## What the code and live probe establish

All **12/12** fixed observations have a valid uncrossed displayed book on each
venue, sufficient shown depth for the exact common base quantity, fresh local
metadata and venue-reported active/API flags. Maximum inter-venue receipt skew
was **272.233 ms**. This is local first-seen availability, not source age or an
order's execution latency. Every observation retains `execution_ready=false`.

MEXC quantity is contracts times `contractSize`, and its market-order level limit
is respected. Lighter uses remaining base quantity, with repeated order prices
aggregated. Exact Decimal common-lot sizing rounds down rather than rounding two
legs separately. Thin/failed books stay explicit; they never acquire a zero cost
or partial-fill profit. Current q*fair (MEXC) and q*index (Lighter) notionals have
separate observation ages, without assuming they are settlement-time cash flows.

## Conditional unit economics, all observations retained

The following are **same-snapshot displayed round-trip costs**, not profits or
verified executable quotes. Each range covers the pair's two registered
observations. Quantities fit a $250 maximum midpoint notional on either leg;
capital remains $10,000 split $5,000 per venue. BP below uses **one leg's**
q*mean(venue midpoints), not gross two-leg exposure or capital return.

| Pair | Matched base q | 1x break-even bp | 2x bp | 3x bp |
|---|---:|---:|---:|---:|
| BTC | 0.0031 | 28.14–28.40 | 56.29–56.81 | 84.43–85.21 |
| WIF | 1,390 | 49.21–49.21 | 98.42–98.43 | 147.63–147.64 |
| SKR | 17,400 | 37.30–42.46 | 74.59–84.93 | 111.89–127.39 |
| ROBO | 44,830 | 56.83–56.83 | 113.67–113.67 | 170.50–170.50 |
| MEGA | 5,618 | 33.35–34.80 | 66.70–69.60 | 100.04–104.40 |
| XPD (metals control) | 0.239 | 50.77–50.77 | 101.54–101.54 | 152.30–152.30 |

**Cost interpretation matters:** R310's 10/4 bp MEXC/Lighter values were declared
all-in scenario costs, not known account fees. R312 conservatively retains those
values as an explicit charge reserve **and adds observed crossing**. This is not
an exact replay of R310's old costs and is not a measured exchange-fee schedule.
`results.json` keeps the components separate: crossing is $0.00356–$0.72029,
reserve $0.68917–$0.69990, giving $0.69273–$1.42003 round trip at 1x for these
sizes. All fixed 1x/2x/3x scenarios retain the same quantities. No zero-fee switch,
validation-winner substitution, leverage increase or funding prediction is used.

## Validation and limits

The complete offline suite passed **1,074 tests, two skipped**. The fourteen new
tests cover contract-versus-order-count units, depth limits, exact common lots,
cash arithmetic, thin/crossed books, individual clocks and skew, cap/failure
retention, immutable evidence and the complete twelve-row offline report.

The report reproduces byte for byte. The independent post-outcome
`check_costs.py` walks raw individual orders with Decimal arithmetic, without
importing the production cost kernel: **36 cost scenarios** agree within
**$7.97e-14**, and **24 fair/index notional observations** agree within $1e-9.
It also checks input/body hashes, paired quantities and local receive skew.
This audit verifies accounting, not economic out-of-sample performance.

No official matching-engine age is established by these REST responses, and no
market-session calendar, book persistence through the standard taker delay,
partial/failed-leg recovery, settlement-time notional or historical liquidation
path is certified. XPD's active metadata and visible book cannot establish that
its underlying/session is open. Two nearby snapshots cannot establish daily,
weekend or historical availability, capacity persistence or uncertainty bounds.

The next input work is source-clock/sequence-aware public depth and fair/index
observations with explicit market sessions and measured missing intervals,
followed by a separately frozen prospective scoring protocol. These observations
cannot repair R311's 49 unscored common days, rescue its negative 2x/3x policy,
or authorize paper/live activation.

## Reproduce offline

```sh
.venv/bin/python scripts/probe_pair_quotes.py report
.venv/bin/python experiments/pair_quotes_v1/check_costs.py
```

Do not rerun `capture`: the frozen lane refuses an existing evidence directory,
including failed ones. Another current-data acquisition needs a new finite scope.
