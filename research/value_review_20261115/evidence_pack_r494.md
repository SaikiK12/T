# EVIDENCE PACK (verbatim repo facts, 2026-11-15)

## Owner goal
Reproducible positive NET return at executable costs on MEXC altcoin perps, comparable capital/risk. Public data, API latency, small capital. ~50 registered nulls. Program trials 9,785,316. Holdout 2025-07..2026-09 is SPENT at program level; only never-read windows or on-time forward days give clean evidence. No edge has an on-time forward day yet.

## Costs (measured, R224, 37 coins 102 snapshots)
MEXC API taker 8 bp/side since 2026-06-01; median half-spread 0.6765 bp; median impact at $10k 1.3635 bp; median all-in $10k API 9.3635 bp/side. ALL 37 coins above the assumed 8 bp at $10k. Web taker 2 bp most, 0 on some, 4-10 on a few; web maker 0 on 1106/1200 contracts but API maker 6 bp.

## Power reality (docs/EDGE_SCOREBOARD)
With ~90 days of paper, a one-sided 5% test has 80% power only for annual Sharpe ~5. A Sharpe-1.5 book needs ~1000 days. Event lanes need ~130 events for t 2.

## The only out-of-sample confirmed edge
| **Funding carry**: short perp + long spot when trailing 72 h funding > 20% APR | Discovery +12.7%/yr, t 3.80; validation +5.9%/yr, t 2.82 (R190) | **+1.45% over 457 d, t 2.07: passed at 1x only** (R191) | Holdout 2x +0.66%, t 1.14 | Funding on MEXC matches Binance (median trailing-APR gap 0.0004 on 40 coins, `experiments/carry_fwd/venue_check.json`). **MEXC lists spot pairs for small alts Binance lacks** (AKE, BR, BTW, Q, USELESS). Replay: MEXC invested 18/18 days, net about 0; Binance 0/18 (R220) | **R220** carry_fwd (Binance and MEXC), decision at 90 on-time days | **The only edge confirmed on a holdout.** Small (about 1%/yr since 2025; "economically small", R191), very low risk (holdout max DD 0.07%). Not usable in a prop account (R202) |

## Strongest per-event edge: R265 unlocks_v1 (gate 0, PARTIAL)
# FINDINGS: unlocks_v1 (R265). The unlock short replicates here, at gate 0

**Verdict: REPLICATES (gate 0).** Shorting at the close of D-7 and covering at the close of an insider or
private-sale cliff unlock (at least 1% of max supply) earned +3.24% net per event at 1x. That is over 422 events on 69
Binance perps, 2021-02..2026-09. All four of the old session's gates pass.
- **Why only gate 0:** the old session read 2021-26 for this family, and the calendar is today's snapshot, not
  point-in-time. **This is not a confirmation.** Clean evidence must come from the reserved events and forward tickets
  (see "Next").
- **Registry:** R265, 10 trials. Program trials become 9,472,071. The registry has no REPLICATES verdict, so the row
  reads PARTIAL (passes its gate-0 rule, not confirmed out of sample).
- **Reproduce:** prereg sha 4c630003, frozen in commit 83554e1 before any return. Then run
  `python scripts/run_unlocks.py` (about 1 minute).
  - The runner first rebuilds the event list and symbol map from the snapshot and checks them byte for byte against
    the frozen files.
- **Execution mode:** manual-web. Two orders per event, about 2 events open on an average day since 2023, 9 at most.

## Primary (funding excluded, as in the old R179 primary)
| Cost (round trip) | Mean net per event | Median | Hit | Week-cluster t |
|---|---|---|---|---|
| 1x (20 bp) | +3.24% | +4.61% | 63.5% | 3.19 |
| 2x (40 bp) | +3.04% | +4.41% | 63.0% | 2.99 |
| 3x (60 bp) | +2.84% | +4.21% | 62.1% | 2.79 |

- **Sample:** 422 priced events, 170 weeks.
  - 108 of the 530 candidates had no market at entry, because the perp was not yet listed: 66 of them in 2021-22.
  - No position was delisted inside a hold.

## Gates (1x)
| Gate | Rule | Result |
|---|---|---|
| G1 | week-cluster t >= 2 | 3.19, pass (2x 2.99, 3x 2.79) |
| G2 | matched random-date null p < 0.05 | p 0.0005. Null mean -0.25%, null 95th pct +1.19% (2,000 reps, same perp on random days away from its unlocks). Pass |
| G3 | both halves positive | +2.10% to 2025-10-13, then +4.37%. Pass |
| G4 | positive without the top 3 perps (H, EIGEN, ZORA) | +2.38%. Pass |

## Logged variants (10 trials in all, with the primary)
| Variant | n | Mean | Week-cluster t |
|---|---|---|---|
| Net including funding (the short paid 0.43% per event on average) | 422 | +2.81% | 2.71 |
| Dose 1-2% of max supply | 246 | +1.47% | 1.21 |
| Dose 2-5% | 141 | +4.66% | 3.27 |
| Dose >= 5% | 35 | +9.94% | 4.03 |
| R181 split: unlock >= 0.82 days of ADV | 131 | +6.29% | 5.35 |
| R181 split: below 0.82 | 284 | +1.69% | 1.34 |
| Short alt, long BTC (gross) | 422 | +3.54% | 4.01 |
| Same, net of two legs at 1x | 422 | +3.14% | 3.56 |
| D-30 to D (net 1x) | 414 | +5.91% | 1.75 |
| D to D+7 (net 1x) | 415 | +0.24% | 0.25 |

- **Dose-response:** monotone in unlock size, both as a share of supply and relative to volume, as in the old session.
- **Market exposure:** the BTC-hedged version is stronger (t 4.0), so the effect is not short market beta.
- **After the unlock:** the drift ends on the unlock day. The week after is flat.

## Risk: the tail is large
- **Per-event spread:** sd 16.7%. 1st percentile -41.9%; 99th percentile +41.9%.
- **Six events lost more than 40% gross (short squeezes):**

  | Day | Perp | Gross loss | Funding |
  |---|---|---|---|
  | 2026-01-22 | RIVER | -132% | -45% |
  | 2026-09-27 | GRASS | -81% | |
  | 2025-05-12 | BB | -57% | |
  | 2025-08-14 | CYBER | -50% | |
  | 2025-11-13 | STRK | -42% | |
  | 2021-04-30 | ALPHA | -41% | |

  - The old go-real rule ("no event loses more than 40% unlevered") would already have failed six times in this
    archive.
  - **Seen after the run, not tested:** all six had unlock/ADV below 0.82.
- **Funding:** the short pays funding on average, -0.43% per event. On crowded events it is extreme (RIVER -45% in a
  week).
- **Sizing:** any forward or real version needs a per-event size cap and a written plan for squeezes. That is decided
  in the next PREREG, not here.

## Robustness (not counted)

## R266 forward lane status
84:R266,2026-10-20,unlocks_fwd,"R265 unlock short forward on MEXC paper: events from the recorded daily calendar snapshot (point-in-time), tickets frozen before the entry bar, measured fee/spread and settled funding",RUNNING,PENDING,1,8a7028cc9609df9f9a062d859fe8f8834ddc6efea1bde7e8be73c7b1e1909b15,experiments/unlocks_fwd,"Forward, gate 1, manual-web. Decision at 120 scored tickets (week-cluster t>=2 on net incl. measured cost and funding, and mean at model 2x >0); futility at 60; deadline 2027-12-31. MAE and 1/2/3x liquidation flags logged, no stops. First ticket RESOLV_USDT (unlock 2026-10-27), frozen 2026-10-20T16:29Z."

## Gate 4 owner-set limits (docs/GATES.md)
## Gate 4: what the owner sets (proposals, not decisions)
The owner fills these in; the lab proposes, it does not decide.
- **Small stakes**: proposed at most 2% of the account's trading capital per book, and no single contract above its
  MEXC base risk tier.
- **Max loss**: proposed hard stop at 25% of the stake; the book is switched off and re-registered after that.
- **Calibration orders**: the strategy critic proposes 20-30 tiny live orders to measure real fills against paper.
  That would be a carve-out from rule 6 of `AGENTS.md` and only the owner can grant it.

## Prop firm lanes present
experiments/propfirm_v1 (FINDINGS+PREREG), experiments/propsim_v1 (cost_map.csv, edge_map.csv). Carry is stated NOT usable in a prop account (R202).

## Newest session lane result (R493, this session)
Session-split continuation on top-50 alt perps: NULL. No factor passes discovery/validation at 1x/2x/3x; family-wise p 1.000/0.790/0.780. Rank ICs mildly NEGATIVE (reversal); unsplit control identical, so an imposed UTC cut adds nothing.

## NEW verified arithmetic (coordinator, computed on committed experiments/unlocks_v1/results/events_priced.csv, 422 events)
- Robustness of the edge: median +4.61%, hit 63.5%, skew -1.66, kurtosis 11.91. Sign test one-sided p=1.6e-8. Week-clustered bootstrap (4000 reps) mean 95% CI +1.21%..+5.24%, P(mean<=0)=0.001. Trimmed mean (10%) +4.06% (HIGHER than raw mean, so the edge is not tail-driven).
- Tail vs ADV: all 6 events worse than -40% gross have V<0.82. Fisher exact one-sided p=0.101 -> NOT significant on 6 events. High-ADV bucket worst -32.8% (n131), low-ADV worst -132.3% (n284).
- Fixed-fraction sizing, sequential compounding over all 422 events INCLUDING the -132% event, gross+funding, no stop: cap 2% of equity -> terminal 1.286x, max DD -4.04%. cap 3.8% -> 1.605x, DD -7.56%. cap 5% -> 1.856x, DD -9.85%.
- Worst single event equity hit at cap 2% = -3.55%; at 3.8% = -6.75%.
- Events per year: 2021:11, 2022:16, 2023:41, 2024:52, 2025:134, 2026:168 (rising).
- The committed per-event file has NO intrabar path (no high/low/MFE/MAE), so a stop-loss rule CANNOT be tested on it; that needs hourly bars.
- Owner Gate 4 proposal: at most 2% of trading capital per book, hard stop at 25% of the stake.

## DECISION NOW ON THE TABLE (design, not discovery)
The coordinator will freeze a RISK-MODEL PREREG for the unlock-short family. It is NOT a new signal
and NOT a new filter. The edge, the sample and the direction are already frozen in R265. The only
open question is: what sizing and exposure rules make the book survivable, and what does each rule
cost in return?

Candidate rules to critique (choose, refine, or reject with reasons):
R1 per-event notional cap c in {1%, 2%, 3%} of equity.
R2 portfolio gross cap G in {10%, 20%, 30%}: scale every open position by min(1, G/(n*c)).
R3 cluster limit: refuse a new entry if the sum of open notional would exceed G, or if >=K positions
   on the same unlock day are already open.
R4 funding veto: skip an event whose trailing funding implies the short pays more than X% annualised.
   NOTE: the committed file has only the REALISED funding over the hold, not the trailing rate at
   entry, so a trailing-funding veto CANNOT be tested on it. Say so if you propose it.
R5 no stop-loss (the committed file has no intrabar path; R208 found stops harmful on flow books).

Hard facts you must respect:
- 422 events, mean net1x +3.24%, median +4.61%, sd 16.7%, worst gross -132% plus -45% funding.
- Concurrency: mean 1.47 open, MAX 9; 169 of 2016 days have >=5 open. Worst concurrent cluster
  sums to -179.5% of notional (2026-01-17). Worst single week -124.6% over 5 events.
- Sequential (one-at-a-time) compounding at c=2% gives max DD -4.04%, terminal 1.286x.
  That is NOT the portfolio path: concurrent positions must be marked together.
- Events/yr rising: 11,16,41,52,134,168.
- Costs already inside net1x/2x/3x (20/40/60 bp round trip). MEXC API all-in measured 9.36 bp/side.
- The unlock/ADV>=0.82 TAIL filter is REJECTED as post-hoc (Fisher p=0.101, n=6). Do not resurrect it.
- Gate 4 (owner): at most 2% of trading capital per book; hard stop at 25% of stake. Owner decides.

Answer for your role only. Be concrete and pre-registerable. State what you cannot know from the pack.
