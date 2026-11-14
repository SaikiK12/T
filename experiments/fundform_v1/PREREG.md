# PREREG: fundform_v1 (R492)

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R492
- **Owner (single writer):** openhands (2026-11-14)
- **Date registered (UTC):** 2026-11-14
- **Method:** M172 (funding revision), second and final round on this data.

## Question
Using the actual Binance funding formula on the point-in-time partial-cycle premium average, does the predicted next
settled rate beat the no-change forecast? R491 showed the *naive* premium mean is ~3.1 bp worse than no-change; the
diagnostic showed why — the settled rate is `F = P + clip(I - P, -0.05%, +0.05%)` with `I = 0.01%`, so it is clamped.
This lane tests the formula, not the mean.

## Universe
Same 50 USDT Binance perps as R491 (`data/klines_1h` manifest `16e6434c8fcd`), restricted to symbols with a
`data/premiumIndexKlines_1h/<sym>.parquet` (manifest `54acb813841b`) and a `data/fundingRate/<sym>.parquet`
(manifest `601d3d955c34`). Fixed major universe; the estimand is within-coin.

## Feature lineage and point-in-time availability

| Feature | Parent fields | Provider / units | Window and close rule | Available by decision time? | Revision / missing |
|---|---|---|---|---|---|
| `r_next` (target) | `fundingRate.rate` at `t_j` | Binance UM, fraction/interval | settlement at `t_j` | target only | final, no revision |
| `r_prev` | `fundingRate.rate` at `t_{j-1}` | same | prior settlement | yes | none |
| `F_k` | `premiumIndexKlines_1h.close` | Binance UM premium index | `F_k = P_k + clip(I - P_k, -0.05%, +0.05%)`, `I = 0.01%`, `P_k` = mean of bar closes in the cycle with `h <= T-1-k` | yes, by construction | drop settlement if any required bar missing |

`I = 0.01%` and the `±0.05%` clamp are Binance's documented USDT-perp parameters and are constants, not fitted. The
decision time is `T - k` hours; `F_k` uses only bars closed at or before it. No look-ahead.

## Rule or search space
Offsets `k in {0,1,2,3,4,6,8,12,16,24}`; **primary `k = 1`**. Paired absolute-error difference
`d = |r_prev - r_next| - |F_k - r_next|`, aggregated to calendar days, Newey-West (lag 7). One primary number.

## Splits and cost
No split (forecast test, not a strategy); no cost (no trades).

## Gates
- **Discovery:** SIGNAL only if the `k=1` mean reduction > 0 **and** NW t >= 3.0 **and** t exceeds the null 95th pct.
- A SIGNAL would make the funding forecast predictable and feed the carry family (M172 -> R220). The return use is a
  separate future lane.

## Null
Block bootstrap on the daily `d` series (mean removed, block 7 d, 2,000 replicas, seed 20261114); SIGNAL requires the
observed `k=1` t to exceed the null 95th percentile.

## Multiplicity
Cells: 10 offsets x 1 feature = 10, one primary. Lane count 1 (R492). Program trials 9,785,407. Raw program sum is
bookkeeping, not an effective independent-test count.

## Evidence lineage and admission (future lanes only)
Canonical method id M172. Parent: R491 (naive premium mean, NOISE, with the level-bias/clamp mechanism this lane
tests). Samples already seen: R491 saw this data; this is the second and last round on it and uses the mechanism the
first round isolated. Feeds the carry family (M172 -> R220). `docs/GATES.md` inherited; meets one-mechanism/one-
feature/one-horizon/one-baseline/one-estimand; no trade-venue/fill claim (no trades).

## Anytime-valid monitor (M479, optional)
Not used: a single fixed-look test, not a forward daily series.

## Stop rules
One run. After the result, no new offset/feature/split. Either verdict closes M172 on this data. A SIGNAL authorizes
only a separate frozen return lane, never an order, key, or money.
