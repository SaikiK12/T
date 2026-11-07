# Leads: where the project stands and what could still pay (2026-11-02)

A dated digest for the owner, written at their request ("make a summary of the leads when everything is finished").
It is not a queue: `registry/methods.csv` is the live queue, `registry/rounds.csv` the record of rounds, and each lane's
PREREG and FINDINGS say exactly what was tested. Every number below is copied from those files or from a lane journal.

## The honest state
- **No lane has prospective, on-time evidence of a net profit yet, and the best retrospective result is not the one first quoted here.** 172 registered rounds: NULL 94, PARTIAL 34, PENDING 30,
  CONFIRMED 8, DATA_PASS 6. Program trials 9,479,246 (`registry.program_trials()`), of which four early mining rounds (R182, R185, R192, R195) hold
  99.6%; the other 168 rounds total 37,087. `AGENTS.md` says to read a result against that count, but the gates in
  `docs/GATES.md` correct each lane for its own family, so the 9.5M is context, not a threshold.
- **The largest retrospective positive in the project was a data leak (R332, 2026-11-02, NULL).** R304's weekly GBM ranker
  (+58.9 bp/day net in validation, t 4.21) came from a metrics panel in which a coin-day held open-interest and top-trader
  columns only if the coin would be among the 100 most traded within 35 days. Re-run on a complete-metrics panel
  (`data/daily_v2`, 99-100% coverage of top-150 rows from 2022) with the same code, the pick nets -16.5 bp/day (t -1.02;
  2x -18.7, 3x -20.8). A rule with no model, "long a random fifth of the rows that have metrics, short a random fifth that
  do not", earns +50.3 bp/day (t 4.47) on the old panel. `experiments/mlrank_v3/FINDINGS.md`; queue row M459 lists what
  else may share the rule.
- **The best-evidenced lead is cross-venue funding carry (R275, replicated by R277 and R288), not the single-venue carry
  (R191) that an earlier draft of this page quoted.** Long the venue with the lower funding rate, short the one with the
  higher, about 20 pairs, 1x per leg, frozen rule and costs of 7 / 14 / 21 bp a leg. It earns the funding difference
  (funding share 0.94-1.04 of net gross) and was caught by a post-hoc audit of this page on 2026-11-02:
  - R277 on KuCoin sets: gate+kucoin +11.76% / +10.34% / +8.92% a year at 1x / 2x / 3x over 2,078 days, NW t 11.41,
    max drawdown -0.7%, positive every year (2025 +20.0%, 2026 to Sept +23.7% at 1x). binance+kucoin similar.
  - R288 on Lighter sets: mexc+lighter +6.20% / +5.00% / +3.79%, NW t 6.77, max drawdown -0.2%, 507 days; five of six
    sets replicate, but only 3.5-6.2% at 1x, near a T-bill.
  - **Post-hoc split of those saved daily series (not a decision), around the dates the venues started scaling funding by
    interval (Binance 2025-09-18, KuCoin 2026-07-14/24; before that 1h and 4h contracts paid 8x and 2x per settlement):**
    KuCoin sets still net about +10%/yr at 1x over the 69 days from 2026-07-25 (to 06-30: +11%), so the effect is not only
    the old unscaled rates, but half the 2025-26 pace. The Lighter sets fell from 5-7% to 2.2-3.4%/yr over the same 69
    days (mexc+lighter 7.0% to 2.6%), near or below a T-bill. In the KuCoin 4h contracts the median per-settlement rate
    fell from about 2-3e-4 to exactly 5e-5 (the scaled baseline) in July. Whether the engine treats every venue's
    settlement interval correctly is not frozen as an audit yet. **Audited 2026-11-02 (R384 `xfundint_v1`, label
    `robust`):** the replay of `lab/xfund.py` matches R277's trades and net to 5e-11; before the scaling about 65% of
    the KuCoin-leg funding came from 1h/4h contracts, but after it (69 days, 99% of funding in scaled 4h contracts)
    the two KuCoin sets still earn +10.5 and +10.0 %/yr at 1x (+8.4 and +8.2 at 2x, +6.4 and +6.3 at 3x; Newey-West t
    3.7 and 3.1). It is one short regime, and recorded versus paid rates, per-contract interval history and capacity
    are still unchecked (33% of KuCoin position-days imply a different class from that day's settlement count).
  - **Known limits written into the lanes' own PREREGs:** KuCoin's and Lighter's contract lists hold only contracts live
    on 2026-10-20 / 2026-10-21, so coins those venues delisted are missing from their sets (Gate and dYdX include
    delisted markets; the size of the bias for KuCoin is not measured). The engine's delisting accounting is
    conservative, not generous: after a venue stops trading a coin, one leg's close is carried forward for a day while
    the other moves, which produced the family's largest losses (−83% NEIROETH, −140% A2Z, −114% YALA on one leg); R275
    reports all 212 passing books stay positive with every forced exit removed. Capacity is not checked against order
    books ($250 a leg at K = 20 on $10k).
  - It is gate 0 plus venue replications of a rule frozen before the new venues were read; it is not prospective evidence.
    R280: no leverage is safe, so it stays at 1x per leg (about 5-10% a year on capital: $500-1,000 on $10k). It needs two
    funded accounts, transfers, and the spread has shrunk on older venues (Hyperliquid books decayed to 5-8%).
    Forward lanes R278 / R279 / R294 have 2 to 3 on-time days, which cannot show a few percent a year yet.
  The single-venue carry (R191, the only holdout pass of the first program) is +1.45% over 457 days at 1x, t 1.14 at 2x.
  The flow books' holdout was chosen after the fact (book B t 2.72, MEXC replay about zero) and is spent
  (`docs/CRITIQUE.md`).
- **Evidence now accrues only on live days, and slowly.** A daily book with a true annual Sharpe of 1.5 needs about 650
  to 1,000 days to reach t 2 (`docs/PAPER_REFINEMENT.md`). The event lanes below are faster, but each is a few events
  a week at most.
- **Operational risk is the largest cost we measured.** This container was off from about 2026-10-30 15:45 to
  2026-11-02 17:29 UTC, about 3.1 days (a 4-day outage on 10-26..29 is in `docs/DIRECTION.md`). Every recorder and forward lane has a gap for it: R371 missed its 11-02 ticket, R367
  lost 10-31 and 11-01, and any settlement or release inside the gap is gone. Nothing in the repository restarts a dead
  machine; `scripts/restart_all.sh` brings everything back once someone runs it.

## Tier A: running forward on paper (the only road to money)
| Lane | What it bets | Evidence so far | Needs | Earliest read |
|---|---|---|---|---|
| **R364 / R355** settlement scalp (Lighter vs a deep Binance settlement; MEXC+Lighter hop) | Short Lighter at T-10 s, cover at T+60 s, when Binance's predicted rate is at least 0.3% negative | Gate 0 (R363): +23.4 / +19.6 / +15.8 bp a hop at 1x / 2x / 3x, t 4.34 / 3.58 / 2.83, on 134 hops. Not blind (R362 had read their Binance seconds) **and not cost-robust**: R363 charged volume-band costs (3.8 bp a round trip) while R364's PREREG measured $1k round trips of 70 / 61 / 163 / 22 bp for KAITO, RIVER, AVNT, BERA, the four coins that hold 77% of the sum. The other 62 hops net +11.5 bp, which is what R364's cost gate keeps; its own PREREG says power there is low and it is a futility screen. Trigger: the Binance predicted rate at T-1h, either sign, at least 0.3% in size. Forward (2026-11-05 16:00 UTC): R364 has logged 13 decisions and R355 117, with 0 scored hops in both | 40 scored hops for an interim look, 80 for the final one. The ungated archive rate was one hop every 2.4 days; with the cost gate fewer | Months |
| **R371** US-open leaders (R300 "us10 n3 follow") | 10:00 New York: long the 3 strongest, short the 3 weakest top-50 perps since 00:00 UTC, flat at 24:00 | Parent R300 was NULL (+38.7 bp/day, t 1.28; 2x +4.7). Forward, MEXC book: day 1 -14.6% (2.2 daily SDs), day 2 +0.5%, 1x. 2 of 500 scored days (2026-11-05); 4 of 6 tickets missed by host outages | Futility read at 125 scored days, PASS or NULL at 500. Power: the daily SD is about 650 bp, so even a true +52 bp/day reaches t 2 at 500 days only about 41% of the time (17% if +30), and the futility rule rarely fires on a true +50 | About 6 months for futility |
| **R369** EIA release lag (Lighter lags Binance/Hyperliquid after a release) | Follow the lead after crude and gas storage releases | 2 valid events (gas 10-29 and 11-05, no feed gap in [T-10 s, T+65 s]), 0 lag-filtered trades. Crude 11-04 is invalid (no Binance reference: the host was down 09:38-19:10). R370 (CME tick leader) was INCONCLUSIVE | 8 valid events and 6 lag-filtered trades per type | Crude 11-11 15:30 and gas 11-12 15:30 are the next two events; at one release a week per type, the 8-event bar is about two months away. The first event had a lag ratio near 1 at 1 s, R370 found 0 of 24 and 1 of 21 filtered, and PASS needs 6 filtered trades in 8 events, so INCONCLUSIVE is the likely outcome; a pass is worth about $1 a trade (a probe, not a money lane) |
| **R406** locked cash-and-carry on Deribit (R335 forward) | Buy BTC or ETH with USDC, short the inverse dated future at 1x, hold to delivery: dollars fixed at entry | 2 paper locks open in book H0 (BTC-25DEC26, ETH-25JUN27), each locking about 4.3%/yr against a 4.03% T-bill (+0.29%/yr excess); no H3 offer (3%/yr above the T-bill) | First read at 4 settled H0 locks: every \|diff\| at most 10 bp and mean excess at least 0 | First settlement 2026-12-25 |
| **Cross-venue carry books** (R278 Gate/Binance/Hyperliquid, R279 KuCoin, R294 MEXC+Lighter, R285 mix; R220 is the single-venue book) | Long the low-funding venue, short the high-funding one, about 20 pairs at 1x | Gate 0 and replications: +5 to +10% a year at 2x, max drawdown under 1% (see above). Forward: 2 to 3 on-time days, about 0% | 90 / 180 scored days, NW t at least 2.5, 2x above 0, drawdown above -3% | About late January 2027 for 90 days |
| **Flow books** (R215, R218, R200, R214) | Order-flow shorts, universe-hedged | R215 +0.4%, R218 +0.7% over 10 on-time days at 1x; R200 -4.8%, R214 -5.0% | Day-90 futility, efficacy at 182 / 365 | Months |
| **Event shorts** (R266 unlocks, R268 delist, R270 Monitoring Tag, R272 announcements) | Short after unlock or notice | 0 to 1 scored | 12 to 120 scored events | Months |

## Tier B: dated reads that are already frozen
- **Reserved batch 1 (R286), read 2026-11-03 (done): 1 PASS, 5 FAIL, 4 UNREADABLE**
  (`experiments/reserved_batch1/FINDINGS.md`).
  - **C14 passes, the cross-venue carry binance+gate L14d th10% K20.**
    - 2020 at 1x/2x/3x: +2.86 / +1.86 / +0.85 %/yr.
    - NW t 4.03, p 2.8e-5 against α 0.0297. Trimmed, leave-two-coins-out and 2x means are all positive.
    - This is gate-1 evidence that the carry mechanism is real on unread days, at about 28% of its 2021-26 size.
    - It earns a new frozen forward paper lane for that exact set, which none of R278/R279/R294 trades.
  - **The unlock short C01 fails.**
    - 57 reserved events, -3.45% per event, t -0.87.
    - The four 2020 events averaged -55.7%; the 15 post-archive events made +3.36%.
    - R266 continues on its own rule.
  - **C10, C11a/b and C12d fail. C09 and C12a-c are unreadable** (no 2020 events).
- **R367 `hftlead_v1`, blocked by the outage.** It needs 3 usable recorded days (80% coverage); only 2026-10-29 qualifies
  (10-30 reached 65%). With the recorders back, 11-03 and 11-04 complete the set and the run is due on or after
  **2026-11-05 00:30 UTC**, by 11-08 at the latest, else INCONCLUSIVE. Its 200 ms rules sit below the measured 233-255 ms
  websocket round trip, so only the 500 ms rules are executable from this container. A NULL closes M427 as registered.
- **R390 `xfund_bg_fwd` (C14's forward lane), frozen 2026-11-03.** Binance+Gate carry book, first live day 11-04;
  looks at 90 scored days (2027-02-02) and 180 (2027-05-03). Power is modest: at the 2020 strength a 90-day PASS is
  about one chance in three.
- **Web-deep wave (2026-11-03, `research/intake/web_deep_20261103.json`): new queue rows M460-M467, nothing run.**
  The strongest, M460, was run the same day as **R387: NULL** (222 hourly-cycle Binance settlements, 9 coins, 30
  coin-days). The capture crowd's move is there (+54.5 bp a hop on Lighter) but Lighter settles at the same T near its
  clamp (-42.4 bp), leaving +9.2 bp at 1x, t 1.64; -7.2 bp with RIVER at its measured cost. The MEXC follow-up is dead:
  MEXC also settled at T on 205 of the 206 hops it lists.
  - **R388 (M461, forced hourly switch): NULL.** Post-rule floor prints are not followed by a stronger rebound
    (post − pre +166 bp, t 0.72). The long's +197 bp mean at 1x is ~+296 bp of hourly funding and a squeeze tail
    (median −174 bp, trimmed −105 bp).
  - **R389 (M462, Lighter BRENTOIL roll steps): frozen forward**, with `record_lighter_index.py` running since 11-03.
    The first step is 11-06; the decision comes after 20 traded steps (about 2027-03).
  - **M463 (ex-dividend): BLOCKED.** MEXC shows no credit row on 16 of 67 ex-dates, unexplained.
  - M466/M467 (HL vault and Lighter winner persistence) wait on the owner's yes for ~300 MB and ~1 GB pulls.
    Prediction markets are not legal for the owner (ANJ block of Polymarket, Kalshi restricts France).
- **Reserved batch 2 (R391), read 2026-11-03: PASS, small.** R275's carry book on the never-read KuCoin, dYdX and
  Lighter long tail with MEXC earns +2.48 / +1.93 / +1.38 %/yr at 1x / 2x / 3x (NW t 3.90). Only 5.3 of 20 slots
  fill, and the top 10 days are 95% of the sum. Next: measure the long-tail book costs, then a forward lane with a new
  id ([FINDINGS](../experiments/reserved_batch2/FINDINGS.md)).
- **Reserved batch 3 (R392: C17 on 2020, Gate long tail read 2), on or after 2026-11-17.** The PREREG is not frozen.
  It must be frozen before that read.

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

## Tier D: what five read-only subagents added on 2026-11-02 (hypotheses, nothing run)
Each came from a fresh reviewer with one lens (post-mortem of the nulls, structural costs, markets outside the crypto-perp
box, event timing, an auditor). Their claims about outside sources are unverified; the repo claims were checked above.
- **R332 `mlrank_v3`: done, NULL (run 2026-11-02, 7 trials).** The leak-free rerun that both the post-mortem and the
  auditor ranked first. R304's pick fails all three checks on the complete-metrics panel (validation net 1x -16.5 bp/day,
  t -1.02; 2x -18.7; without the 10 best weeks -245.7 bp/week). The presence book earns +50.3 bp/day net (t 4.47), so
  R304's PARTIAL is labelled `metrics-leak`, M042 closes on this panel and R304 gets no forward lane. It closes a lead; it
  does not open a profitable one.
- **R380, R382, R385: three cheap gate-0 lanes, all NULL (2026-11-02).** R380 (M457): 8-10 week reversal in the
  high-volatility tercile; all 8 books lose in validation (t -2.2 to -3.3), so the 2024-26 sign is continuation. R382
  (M455 sizing half): trailing-volatility scaling or gating of the R277 carry book does not beat the unscaled book
  (2nd-half 2x Sharpe 6.37 vs 6.88). R385 (M456 sort half): beta to DVOL changes sorts nothing net (pick t +0.15).
  The HAR-forecast and option-inventory halves remain untested. R381 and R383 are claimed and paused.
- **R386 `atlas_tape_v1`: a 303,520-cell screen of seconds-to-minutes conditional returns, NULL (2026-11-03).** Best
  validation net-1x t 4.21 against a placebo max-statistic 95th percentile of 5.25 (full-grid p 0.87); no candidate.
  A non-decisive count surplus (1,218 cells against a null 95th percentile of 899) sits in fades of extreme taker flow
  on SOL/BTC/ETH at 3-15 minutes, which is R349's seen family, so it is not new evidence. Block B (1-second tape,
  two validation days) has nothing. Costs are Lighter's $1k walk; latency and fills are unchecked.
- **Cost re-pricing (R371's parent, R300):** at MEXC's web taker (2 bp on 956 contracts, 0 on 142) rather than the lab's
  8.5 bp a side, R300 re-prices to about +61 bp/day and t about 2.0, on seen days only.
- **Untested directions with data on disk:** Deribit weekend defined-risk short volatility (needs chain-priced fills the
  repo lacks, which is why M249 is blocked); spot-hedged tokenised-gold carry (PAXG/XAUT); a MEXC-native index deviation
  on 0/0 contracts; a monthly supply-growth and fee-yield factor (R282 tested only 1 to 7 days).
- **Events with public timestamps and no recorder:** Binance pre-market, TradFi and pre-IPO perp launches (R271's
  perp_launch excludes them), earnings 8-Ks on stock perps (about 400 a year), CME-closure weekend convergence on gold,
  silver and WTI (the first closure, 10-30 to 11-01, fell inside the outage; the next is 11-06 22:00 to 11-08 23:00 UTC),
  Upbit and Bithumb listings (blocked by 403s), and new-instrument openings on Hyperliquid and Lighter. They cannot be
  backfilled, which is the argument for a first-sight detector.
- **Outside the box:** prediction-market structural bias (Kalshi 72M trades: takers -1.12%, makers +1.12% a trade, gross;
  needs data and an access check) and Polymarket against option-implied digitals. Rejected with reasons: DEX LP, depeg
  reversion, dated-futures carry (basis below T-bills).
- **Structural costs:** negative-cost tiers are out of reach at $10k; zero-cost venues only help a gross edge, so the PnL
  has to come from funding mechanics or house-side roles (Hyperliquid HLP measured +19% in 2025, +8.2% in 2026 to 10-21,
  4.3%/yr over the last 30 days; depositing needs a real order, which is the owner's).

## What would change the picture, in order
1. **Reserved batch 1 on 2026-11-03.** A pass on unseen days is the first real news in weeks; a null is also a result.
   The auditor notes that only about 2 of its 10 cells (carry C14 at alpha 0.0273, unlock short C01 at 0.0147) have a
   non-trivial alpha; the other eight sit at 0.001 and need N_min 8 events.
2. **R332 is settled: NULL.** The biggest backtest number in the program was the metrics availability rule. The cheap
   follow-up is M459, a presence-control audit of the few other lanes with a wide universe (R282 first), which can only
   remove evidence.
3. **Cross-venue carry forward lanes (R278, R279, R294).** Not exciting in dollars ($500 to $1,000 a year on $10k) but the
   only family with a replicated, net-of-2x-cost backtest; the Lighter sets are fading, the KuCoin sets are not yet.
4. **Settlement scalp (R364, R355).** Treat the +23.4 bp as an upper bound that the cost gate cuts to about +11.5.
5. **Nothing else in the queue is close.** More strategy descriptions will not move this faster than the forward clocks.

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
