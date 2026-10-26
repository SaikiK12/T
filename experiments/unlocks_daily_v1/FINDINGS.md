# R258 unlocks_daily_v1 — PARTIAL, historical price screen only

The fixed R265 event selection has a positive price-only effect in this independent
daily-archive check. All four preregistered gates pass. This is not R265's exact
replication, a self-financing account return, a MEXC result or prospective evidence.

## What actually ran

Code/spec/request inventory frozen and pushed **bffb3d9** before any price read.
All 3,125 official daily USD-M ZIPs and publisher checksums validated, 98 contracts
including BTC, 2021-01..2026-09. Catalogs + responses total **8,027,496 bytes**;
ZIPs alone 5,720,020 bytes. No acquisition errors/retry pass. The complete source
manifest was locked and pushed **0b7e5d2** before outcomes. No reserved 2020/MEXC
prices, calendar refresh, original Claude disk or large hourly archive was accessed.

Fixed cohort: 530 events, 97 symbols. Exact positive-volume daily entry/exit closes
price **421 events on 69 symbols**, excluding109 with every row retained. No
post-outcome coin, horizon, sign or threshold selection. All421 have seven complete
positive-volume holding bars, allowing the high-excursion diagnostic.

## Price-only result, costs and controls

| Round-trip fixed cost | Primary mean/event | ISO-week t | Hit rate | Worst event |
|---|---:|---:|---:|---:|
| 20bp (1x) | +3.2610% | 3.2023 | 63.66% | -132.4925% |
| 40bp (2x) | +3.0610% | 3.0059 | 63.18% | -132.6925% |
| 60bp (3x) | +2.8610% | 2.8095 | 62.23% | -132.8925% |

These are event means after a fixed price-cost deduction, not compounded portfolio
returns and not complete net perpetual PnL: funding, exit-notional fee differences,
margin, liquidation, concurrent positions, spread/impact and capital constraints
are not modeled. The same seven-day event can overlap other events.

- Matched same-symbol random-date null:2000 replications, p **0.00049975**
  (0 exceedances); null mean **-0.23077%**. Event dates exclude +/-14 days around
  all kept dates of that symbol. All scored symbols have nonempty pools.
- Chronological halves: **+2.14256%, +4.37418%** at1x.
- Remove the top3 summed-net symbols (H, EIGEN, ZORA): **+2.40293%**.
- BTC hedge (421 matching dates), with separate fees for BOTH legs: mean
  **+3.15274/+2.75274/+2.35274%**, week-t **3.56164/3.10975/2.65786** at1x/2x/3x.
  It remains a price-return diagnostic, not an executed hedge/account.
- Verified-only:407 events,1x mean **+3.2424%**, t **3.1553**.
- 2021 is negative (-4.3312%,11 events); the other five years have positive means.
  Every year/cost is retained in summary.csv; no year becomes a new selection rule.

The owner-pasted Claude report was +3.24% on422 events. This independently checks
the direction and rough magnitude, not exact equality. His uncommitted event-level
artifacts are still unavailable. Our exclusions consist of96 events missing both
endpoints,12 missing entry only, and1 with entry but no exact exit daily bar
(HBAR,2022-04-01). Do not impute zero, silently substitute an hourly bar or claim
that this identifies Claude's one-event difference without his files.

## The material risk hidden by close-to-close PnL

Six events lose over40% at1x, one over100%. **21 events** have a holding-period
daily high more than40% above entry. The extreme is STO's2026-04-03 unlock:
entry close2026-03-27 **0.10835**, high2026-04-02 **1.86666**, exit close2026-04-03
**0.14245**. The close-only gross loss is31.47%, while the high is
**1,622.8057% above entry**. A close-only event report conceals that excursion.

Verified directly in the publisher-checksummed CSVs:
- STOUSDT-1d-2026-03.zip SHA256
  `05df7c4d4ff43a1416de9f286f7062db14380d8bc8b9a3e120198ceddbeb46c5`;
- STOUSDT-1d-2026-04.zip SHA256
  `b5ac3151b0246d46f6a082b0a1f22dc00bb408e991c47221ebeca8506be41596`.

This is the traded-contract candle high, not the mark price used by a venue for
liquidation. It proves the archived price excursion, not the exact liquidation or
fill of a real account. Validate mark price, timestamp/unit/corporate-action issues
and higher-resolution prints before selecting a stop or margin model. No result
here demonstrates that an ordinary collateralized short survives these paths.

## Limits, provenance and next concrete question

This is a retrospective revised calendar and hindsight symbol selection on spent
years. Weekly t/matched-date p do not correct the full program's roughly9.47M raw
trials, price regimes or calendar revision bias. No gate1 pass is claimed. Neither
2020 nor MEXC-only reserved outcomes were consumed. R265's original frozen files
remain intact and its empirical result stays unverified. M057 is PARTIAL only
for this exact daily-price scope; actual funding/account/risk mechanics and new
point-in-time MEXC paper remain open.

The next study must test a finite protective-exit and collateral rule in an actual
account model, with funding and both-leg costs; it must not retrofit a profitable
stop to these already-seen paths. Any stop fills from daily OHLC remain hypotheses
until checked with finer data and prospective paper.

Validation:355 tests pass, including8 new synthetic checks. All5 result artifacts
reproduce byte-for-byte in a fresh output directory; no required primary statistic
is undefined. Source hashes and all priced/excluded records are retained.

```sh
python scripts/unlocks_daily_check.py run \
  --raw /workspace/quant-small-data/unlocks_daily_v1 --out /new/r258-path
```

Use the frozen source manifest/DATA.sha256; no re-fetch or silent source revision.
