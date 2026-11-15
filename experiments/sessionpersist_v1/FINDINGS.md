# FINDINGS: sessionpersist_v1 (R493, M541)

Run 2026-11-15T11:33:09.063035+00:00 by `scripts/run_sessionpersist.py run`; PREREG `7bb80998fbe0` verified before and after; raw manifest `4dabc93e6d5c`. Gate 0, latest-vintage public archive, exploratory. The holdout (2025-07-01 onward) was not read.

**Verdict: NULL.** Three pre-registered factors, no search. Program trials before: 9,785,316; this lane adds 3.

## Universe and coverage
- Candidates: USDT perps present in both frozen provenance manifests with a first bar before 2024-01-01, minus R216's frozen TradFi list (frozen in universe.json before any price was read). Universe: top 50 by trailing 30-day quote volume at 2026-09-30 (latest-vintage selection, declared); daily eligibility re-ranks point-in-time on trailing volume through d-1.
- Mean eligible names per day: 39.1. Book-leg mentions: 150 survivor / 0 later-delisted symbols.
- Survivorship: the archive includes delisted contracts, and eligibility uses only data through d-1, so a name that later dies is tradable while it lived. The first-bar-before-2024 filter excludes later listings by design (they have no discovery-window history); the result is bounded to seasoned perps, not the full listing universe. Latest-vintage volume ranking is the remaining selection caveat.

## Results (bp/day; NW t lag 10; cost 9.36 bp/side at 1x = R224 median $10k API all-in)

| factor | window | gross | net 1x | net 2x | net 3x | NW t (1x) | rank IC | IC t |
|---|---|---|---|---|---|---|---|---|
| S_A | disc | -6.54 | -12.19 | -17.84 | -23.49 | -1.67 | -0.0290 | -4.54 |
| S_A | val | +1.18 | -4.56 | -10.29 | -16.02 | -0.47 | -0.0280 | -3.84 |
| S_B | disc | +4.91 | -0.62 | -6.14 | -11.66 | -0.07 | -0.0230 | -4.10 |
| S_B | val | +6.20 | +0.75 | -4.70 | -10.16 | +0.07 | -0.0239 | -2.47 |
| MOM24 | disc | +5.36 | -0.48 | -6.32 | -12.16 | -0.05 | -0.0397 | -6.27 |
| MOM24 | val | +4.10 | -1.49 | -7.07 | -12.66 | -0.12 | -0.0372 | -4.02 |

Discovery gate: net 1x mean > 0 and NW t >= 2.0. Validation gate (read for every factor, no selection): mean > 0 and t >= 1.5. Passes: none (discovery), none (validation).

## Null (moving-block bootstrap, centered discovery gross)
- 200 replicas, block 20 days, seed 20261115.
- Per-factor 95th-pct t: S_A 1.44, S_B 1.37, MOM24 1.34.
- Family-max 95th-pct t (3 trials): 1.79.
- Family-wise p (share of null family maxima >= real discovery 1x t): S_A 1.000, S_B 0.790, MOM24 0.780.

## Funding diagnostic (not charged to the books)
Mean settled funding over the read window, bp per settlement: 1000BONKUSDT +0.73, 1000PEPEUSDT +1.21, 1000SHIBUSDT +0.42, AAVEUSDT +1.56, ACEUSDT +0.67, ADAUSDT +1.33, APTUSDT +0.44, ARBUSDT +1.07, ARKUSDT -2.35, ARUSDT +0.97 (first 10 symbols; full table in results/report.json).

## What the null says
The pre-registered direction was continuation (long the top quintile). It fails in
every window at every cost multiple, and the family-wise p values are 0.78-1.00, so
nothing here is near the null's upper tail. The rank ICs are small but consistently
**negative** (t -2.5 to -6.3): the cross-section shows mild next-day *reversal*, not
same-session persistence. That is the opposite sign to the equity mechanism, and it
is reported, not traded on: reversing the direction after seeing the result would be
a new lane with a new id, and a |IC| near 0.03 does not clear 9.36 bp/side anyway.
The unsplit control MOM24 behaves the same way, so the imposed UTC boundary adds
nothing over ordinary short-horizon reversal. Consistent with the mechanism being an
artifact of the equity close/open clock, which a 24/7 perp does not have.

## Deviations from the frozen spec (plumbing, not rule changes)
The frozen PREREG is unchanged (`7bb80998fbe0`). Three implementation details in its
feature table were wrong about the archive and were corrected before any result was
recorded; none changes a factor, a threshold that decides, a split or the direction.
1. **Boundary price.** The spec said the 00:00 UTC close is the hour-0 bar's `open`.
   On this archive `open` is the first trade of the hour and differs from the prior
   23:00 close on 1335 of 2464 BTC hour-0 bars (max $21.66), even with contiguous bars.
   The runner uses the **close of the bar opening at 00:00 UTC**, which is the price
   the session sums start from, so the decomposition is internally exact.
2. **Session hour counts.** A bar opening at hour h earns close(h+1)/close(h). Session
   A (open hours 0..13) therefore holds **14** returns and B (14..23) **10**. Verified:
   S_A + S_B equals the boundary-to-boundary daily log return to 9.2e-16 over 8746
   day-symbol cells.
3. **Completeness threshold.** The spec's flat '150 of 168 hours' is unreachable for a
   10-hour session (max 70 over 7 days). The runner requires **90% of each session's
   own lookback hours** (A 98, B 70), the same intent applied per session.
A first run produced an all-NaN panel (`np.add.at` on NaN-initialised accumulators) and
would have printed a spurious NULL; it was discarded, not recorded. A second run showed
+270 bp/day at t=17 from a target-alignment leak (the factor was scored on its own day's
return); that was fixed and is now locked by a regression test. Both are why the numbers
below come from the third run.

## Limits
- Gate 0 on seen history; no reserved sample, no forward day, no gate-1 claim.
- Costs are R224's measured median $10k MEXC API all-in per side (8 bp taker + 0.6765 bp half-spread + 1.3635 bp impact); 2x/3x bracket a worse book. R224 reports every one of its 37 coins above the assumed 8 bp at $10k, so 1x is not conservative.
- Books are gross of funding; the diagnostic above bounds the carry overlay.
- Session cut 00-14/14-24 UTC is fixed, not tuned; the 24h control MOM24 is the no-split comparison. A different cut is a new lane.
- Rank IC and quantile reports come from lab/factor_report.py (unit-tested).

## Reproduce
```sh
python scripts/run_sessionpersist.py run   # verifies the freeze, re-fetches, re-runs
```
