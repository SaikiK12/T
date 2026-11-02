# Leads: where the project stands and what could still pay (2026-11-02)

A dated digest for the owner, written at their request ("make a summary of the leads when everything is finished").
It is not a queue: `registry/methods.csv` is the live queue, `registry/rounds.csv` the record of rounds, and each lane's
PREREG and FINDINGS say exactly what was tested. Every number below is copied from those files or from a lane journal.

## The honest state
- **No lane has shown a net profit that survives 2x costs.** 171 registered rounds: NULL 93, PARTIAL 34, PENDING 30,
  CONFIRMED 8, DATA_PASS 6. Program trials 9,479,239 (`registry.program_trials()`), so a lone t of 2 to 3 means little.
- **The only frozen holdout pass is funding carry** (R191): +1.45% over 457 days, t 2.07 at 1x, t 1.14 at 2x. That is
  below a T-bill and is not the goal. The flow books' holdout was chosen after the fact (book B t 2.72, MEXC replay about
  zero) and the holdout is spent (`docs/CRITIQUE.md`).
- **Evidence now accrues only on live days, and slowly.** A daily book with a true annual Sharpe of 1.5 needs about 650
  to 1,000 days to reach t 2 (`docs/PAPER_REFINEMENT.md`). The event lanes below are faster, but each is a few events
  a week at most.
- **Operational risk is the largest cost we measured.** This container was off from about 2026-10-30 16:00 to
  2026-11-02 17:29 UTC. Every recorder and forward lane has a gap for those 2.5 days: R371 missed its 11-02 ticket, R367
  lost 10-31 and 11-01, and any settlement or release inside the gap is gone. Nothing in the repository restarts a dead
  machine; `scripts/restart_all.sh` brings everything back once someone runs it.

## Tier A: running forward on paper (the only road to money)
| Lane | What it bets | Evidence so far | Needs | Earliest read |
|---|---|---|---|---|
| **R364 / R355** settlement scalp (Lighter vs a deep Binance settlement; MEXC+Lighter hop) | Short Lighter at T-10 s, cover at T+60 s, when Binance's predicted rate is at least 0.3% negative | Gate 0 (R363): +23.4 / +19.6 / +15.8 bp a hop at 1x / 2x / 3x, t 4.34 / 3.58 / 2.83, on 134 hops. They were **not blind**: R362 had read their Binance seconds. Forward: R364 has logged 11 decisions and R355 93, with 0 scored hops in both | 40 scored hops for an interim look, 80 for the final one. About one qualifying hop every two days | Months |
| **R371** US-open leaders (R300 "us10 n3 follow") | 10:00 New York: long the 3 strongest, short the 3 weakest top-50 perps since 00:00 UTC, flat at 24:00 | Parent R300 was NULL (+38.7 bp/day, t 1.28; 2x +4.7). Forward, MEXC book: day 1 -14.6% (2.2 daily SDs), day 2 +0.5%, 1x. 2 of 500 scored days; 11-02 ticket missed (outage) | Futility read at 125 scored days, PASS or NULL at 500 | About 6 months for futility |
| **R369** EIA release lag (Lighter lags Binance/Hyperliquid after a release) | Follow the lead after crude and gas storage releases | 1 valid event (gas, 10-29), no trade yet. R370 (CME tick leader) was INCONCLUSIVE | 8 valid events and 6 lag-filtered trades per type | Crude 11-04 15:30, gas 11-05 15:30 are the next two events; at one release a week per type, the 8-event bar is about two months away |
| **Carry books** (R220, R278, R279, R294, R285 mix) | Funding carry on MEXC, KuCoin, Lighter | About 0% on 2 to 10 on-time days at 1x | 90 / 180 scored days | Months |
| **Flow books** (R215, R218, R200, R214) | Order-flow shorts, universe-hedged | R215 +0.4%, R218 +0.7% over 10 on-time days at 1x; R200 -4.8%, R214 -5.0% | Day-90 futility, efficacy at 182 / 365 | Months |
| **Event shorts** (R266 unlocks, R268 delist, R270 Monitoring Tag, R272 announcements) | Short after unlock or notice | 0 to 1 scored | 12 to 120 scored events | Months |

## Tier B: dated reads that are already frozen
- **Reserved batch 1 (R286), on or after 2026-11-03.** Ten pre-committed candidates (carry, unlock short, event shorts, an
  R263 strategy) read once on 2020 crypto and the MEXC-only coins, with a weighted Bonferroni. This is the one test in the
  queue that can still confirm something on days nobody has looked at. The sample is read once.
- **R367 `hftlead_v1`, blocked by the outage.** It needs 3 usable recorded days (80% coverage); only 2026-10-29 qualifies
  (10-30 reached 65%). With the recorders back, 11-03 and 11-04 complete the set and the run is due on or after
  **2026-11-05 00:30 UTC**, by 11-08 at the latest, else INCONCLUSIVE. Its 200 ms rules sit below the measured 233-255 ms
  websocket round trip, so only the 500 ms rules are executable from this container. A NULL closes M427 as registered.
- **Reserved batch 2 (C17), on or after 2026-11-17.** The PREREG is not frozen. It must be frozen before that read.

## Tier C: the owner's 2026-11-02 paste, sorted
The paste is a literature scan. None of these is evidence: each is a source's claim that we did not verify.

| Lead | What the record already says | Action |
|---|---|---|
| BTC trend + DXY forecast | The paper reports a spot signal, with fee assumed, gross p-values and no search correction. ICE's DXY needs an account. Our trend lanes are NULL: R229 spot ensemble, R242 VOLTREND (validation t 0.52), R239 dollar trend (t -0.25, 2001-2012 FX) | None. There is no qualified BTC trend parent to blend |
| Time-series momentum + funding carry | The report omits its weighting rule and its component intervals include zero. R309 (fixed 50/50 carry and spot trend) was NULL, failing 3 of 5 gates. R285, a different mix, runs forward | None. Do not touch R285 |
| Negative funding + prior direction | R273 (40 trials, best neg2 long 72 h +7.32%, t 2.39, reality-check p 0.867) and R274 were NULL without the prior-direction split. Only an abstract was available | **M458**, one extra axis, expect a null |
| Portfolio validation (Deprez and Frömmel) | A validation template: multiple-testing control, fees, spread. Their absolute returns were generally not above buy-and-hold, which matches our nulls | None. The lab already does Holm, SPA and DSR |
| Funding x volatility | Funding features may help realized-volatility forecasts. R320 found no validated risk-forecast skill | **M455**, a sizing test, not directional alpha |
| Execution filter (Bybit toxicity) | Adjacent to R367. R291 (VPIN toxicity) was NULL for volatility forecasting. The source shows an illustrative tail-loss filter, not fills | Hold. M436 is the existing row. There is no passing parent strategy to filter |
| Macro and trend (Cheah et al.) | Spot BTC, sample ends 2019, no combined rule tested | None |
| Options signals (DVOL-beta, gamma inventory) | R209 (DVOL minus realized) was NULL. M300 (dealer gamma) is queued. No net perp results in either study | **M456**, held until a parent passes |
| High-volatility reversal (8-10 weeks) | R238 found its rev28, MAX, IVOL and skew books were one high-volatility tilt that paid in 2021; the preprint was not fully accessible and has no clean holdout | **M457**, only as a residual of that tilt |

## What would change the picture, in order
1. **Reserved batch 1 on 2026-11-03.** A pass on unseen days is the first real news in weeks; a null is also a result.
2. **Settlement scalp forward hops (R364, R355).** It has the largest gate-0 net of any lane. It is also a number
   that was not blind, so treat the +23.4 bp as an upper bound until forward hops count.
3. **EIA lag (R369) on 11-04 and 11-05.** A small, event-driven lane; its first two real events decide whether it is
   worth keeping.
4. **Nothing else in the queue is close.** The 105 blocked and 48 untested rows are ideas, and 93 of 171 rounds were
   nulls. More strategy descriptions will not move this faster than the forward clocks do.

## Decisions that are the owner's
- **Where the recordings live.** The `data-archive` branch hit its 900 MB cap on 2026-10-30. On 2026-11-02 it was packed
  again with the cap raised to 1,800 MB: 9,736 files in 15 new chunks, so everything recorded up to then is on the branch
  except one 95 MB+ raw-tape file (`data/rawtape/kbook/PF_XBTUSD/2026-10-29.parquet`, too large for git). It now holds
  1,345 MB of 1,800, which is about one more day at the measured 400 MB a day. After that a bigger home is needed (a
  private repository, a release asset, or a disk), or the raw tape should be stopped.
- **Keep the machine up.** Forward evidence needs a continuous, restartable machine; see "Operational risk" above.
- **Rotate the Databento key** pasted into a chat on 2026-10-29 (`docs/HANDOVER.md` section 6).
- **Whether to keep going after 2026-11-17.** The reads on 11-03, 11-05, 11-17 and the first 40 settlement hops will say
  whether any lane deserves another quarter.
