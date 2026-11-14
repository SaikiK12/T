# PREREG: fundrev_v1

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R491
- **Owner (single writer):** openhands (2026-11-14)
- **Date registered (UTC):** 2026-11-14

## Question
Does a Binance USDT-perp's within-cycle **premium index** forecast the **next settled funding rate** better than the
no-change forecast (the previous settled rate), i.e. is the mean paired absolute-error reduction positive and
significant? (M172.)

## Universe
`data/klines_1h/manifest.json` (sha256 `16e6434c8fcdbc2ff96c2062de47a05f720853cea4e6d71dabb84717f1472077`), 50
USDT-margined Binance perpetuals. A symbol enters only if it also has a `data/premiumIndexKlines_1h/<sym>.parquet`
(manifest `54acb813841b`) and a `data/fundingRate/<sym>.parquet` (manifest `601d3d955c34`). Delisted symbols are not
included: the universe is the fixed 50-major set. This is a **fixed-universe, current-survivor** limitation stated
below; the estimand is a within-coin forecast comparison, so cross-sectional survivorship does not enter the primary
number, but it bounds the external validity to majors.

## Data
- **Settled funding:** `data.binance.vision/data/futures/um/monthly/fundingRate/` — columns `t` (settlement ms),
  `interval_h`, `rate` (settled). Public, final, revision-free.
- **Premium index:** `data.binance.vision/data/futures/um/monthly/premiumIndexKlines/1h/` — hourly klines of the
  premium index; `close` is the premium index at the hour close. Public.
- **Prices:** `data/klines_1h` closes, for the return diagnostic only.
- As-of: 2026-11-14. Backtest venue = Binance (the venue the data comes from). No trade venue needed: this lane holds
  no positions, so it makes no fill claim.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| next settled rate `r_next` | `fundingRate.rate` at `t_j` | Binance UM, USDT perp, fraction/interval | the settlement at `t_j` | published at `t_j` | target only, never a feature | fixed 50 | none (final) |
| prev settled rate `r_prev` | `fundingRate.rate` at `t_{j-1}` | same | previous settlement | published at `t_{j-1}` | yes | fixed 50 | none |
| partial premium mean `P_k` | `premiumIndexKlines_1h.close` | Binance UM premium index | mean of closes for bar hours `h` in the cycle with `h <= T-1-k` | bar close at `h+1` h | yes, by construction | fixed 50 | drop settlement if any required bar hour is missing |

Decision time for offset `k` is `T - k` hours (the bar that closes at `T-k`). `P_k` uses only bars closed at or before
that time, so there is no look-ahead. A settlement is dropped for a given `k` when any required bar is missing (never
treated as zero).

## Rule or search space
Closed list of offsets `k in {0,1,2,3,4,6,8,12,16,24}` hours. **Primary estimand: `k = 1`.** For each settlement:
`e_partial = |P_k - r_next|`, `e_nochange = |r_prev - r_next|`, paired difference `d = e_nochange - e_partial`.
Aggregate `d` to calendar days (mean) and test the day series with Newey-West (`lag 7`). One primary number
(`k=1`); the other offsets are a reported sensitivity curve, not a search.

## Splits and cost
No train/test split: this is a forecast-accuracy test, not a strategy, and uses all settlements. Program version 1
(`lab/config.py`). Cost: none in the primary estimand (no trades). The return diagnostic is reported gross, since it
is a signal check, not a book.

## Gates
- **Discovery (primary):** SIGNAL only if the `k=1` mean MAE reduction > 0 **and** Newey-West t >= 3.0.
- Any other offset reaching that bar is reported as exploratory, not a second confirmation.
- The return diagnostic passes if the revision -> next-cycle return rank IC is nonzero with NW t >= 3.0; it is
  diagnostic only and cannot by itself advance the lane.

## Null
Label-preserving block bootstrap over the daily `d` series (mean removed; block 7 days; 2,000 replicas; seed
20261114). Verdict rule: SIGNAL if the observed `k=1` NW t exceeds the 95th percentile of the null; else NOISE.

## Multiplicity
Variants generated: 10 offsets x 1 feature = 10 cells, one primary. Failed/skipped: any settlement with a missing
required bar (counted and reported). Lane registry count: 1 (R491). Program trials so far: 9,785,397. The raw program
sum is bookkeeping, not an effective independent-test count.

## Evidence lineage and admission (future lanes only)
Canonical method id: M172. Parent rounds: R190/R191 (trailing settled funding), R220 (carry forward, ~flat), R223
(rejects simple extreme-negative-settlement capture). One decision group this signal feeds: the carry family — if the
premium index forecasts the next settlement, expected carry becomes predictable (M172 feeds R220). Samples already
seen: R190/R191/R220/R223 used settled funding levels, not the within-cycle premium path; no prior lane computed the
premium-to-next-settlement forecast error, so this estimand is fresh. Current `docs/GATES.md` is inherited; this lane
meets the "one mechanism, one feature, one horizon, one baseline, one estimand" rule and leaves unmet the
trade-venue/fill requirement (no trades here, stated). No reserved read, no order.

## Anytime-valid monitor (M479, optional)
Not used: the lane is a single fixed-look forecast test, not a forward daily series.

## Stop rules
One run. After the result, no new offset, feature, or split is added; a follow-up is a new frozen lane. A NULL closes
M172 as tested.
