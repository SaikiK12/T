# FINDINGS: unlockrisk_v1 (R494, M542)

Run 2026-11-15T13:30:11.385576+00:00 by `scripts/run_unlockrisk.py`. PREREG `f8b3bf3e7d98` verified before and after; events sha `0aeb33d4cce2`, 422 events. No download, no new signal, no filter, no grid search.

**Verdict: SURVIVABLE.** One frozen rule, c=2% per event (the owner's Gate-4 proposal) with a 10% portfolio gross cap, no stop, no funding veto, no ADV filter.

## Portfolio path (concurrent positions marked together)

| marking | terminal | annualised | max DD | worst day | peak gross | cap binds |
|---|---|---|---|---|---|---|
| LUMP (primary, conservative) | 1.257x | 4.22% | -4.62% | -3.55% | 10.0% | 98 d |
| SPREAD (7-day accrual) | 1.262x | 4.31% | -3.78% | -0.51% | 10.0% | 98 d |

- **S1** max DD better than -10%: PASS (-4.62%).
- **S2** worst day better than -5%: PASS (-3.55%).

The two markings bracket an assumption, not a measurement: the committed file has one return per event and no intrabar path. LUMP puts the whole move on the unlock day and is the binding number for a daily-loss limit; SPREAD smooths it over the hold and understates spikes.

## What the cap costs

| costs | uncapped mean net/event | after the cap |
|---|---|---|
| net1x | +3.24% | +0.061% |
| net2x | +3.04% | +0.057% |
| net3x | +2.84% | +0.053% |

The cap scales each event by the concurrency on its entry day, so busy days are sized down. The drag is the price of surviving the cluster.

## Cluster risk (unsized)
Worst concurrent cluster: -179.5% of notional on 2026-01-17. A per-event cap alone does not bound this; the 10% gross cap does.

## The owner decision this surfaces
Gate 4 proposes a hard stop at 25% of the stake = -0.50% of equity at c=2%, while the worst archived event is -3.55%. The stop is breached by the observed tail at every cap in {1%, 2%, 3%} and cannot be tested without intrabar bars. Either accept a no-stop book sized small, or authorise hourly-bar collection and freeze a stop in its own lane. **This lane does not choose.**

## Sensitivity (reported, decides nothing)

| c | G | terminal | max DD | worst day | cap binds |
|---|---|---|---|---|---|
| 1% | 10% | 1.127x | -2.33% | -1.78% | 0 d |
| 3% | 10% | 1.357x | -6.75% | -4.44% | 265 d |
| 2% | 20% | 1.268x | -4.62% | -3.55% | 0 d |
| 2% | 30% | 1.268x | -4.62% | -3.55% | 0 d |

G=20% and G=30% never bind at c=2% (peak gross 18%), so they are identical to no gross cap. That was verified before the freeze and is why G=10% is the primary.

## Limits
- gate 0 description of R265's already-seen events; no confirmation, no new signal
- no intrabar path: LUMP and SPREAD bracket the marking assumption, neither is a path
- no stop, no funding veto, no ADV filter (see PREREG for why each is excluded)
- sizing uses concurrency at each day; the sequential number is not the portfolio path
- This is not evidence that the edge is real out of sample. Only R266's forward tickets can give that, and this lane does not touch them.

## Reproduce
```sh
python scripts/run_unlockrisk.py
```
