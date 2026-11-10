# R434 wti_residual_v1: NULL

On the 24/7 commodity perps, the venue that deviates from the others is almost
always Lighter, and Lighter leads. A taker who trades Lighter back toward the
other venues earns nothing, because the gap closes when the other venues move
to Lighter.

- Registry R434, method M443. 228 trials (19 instrument/venue scopes × k ∈ {2, 3}
  × H ∈ {10, 60, 300} s × CME open/closed). Program total 9,784,937.
- Run once on 2026-11-10, 02:59-03:00 UTC (1 min 17 s, exit 0), by the frozen
  `scripts/run_wti_residual.py` (sha 541703d0…).
- PREREG sha 0e334ec6… was frozen and committed in 4dbb8ae before the run.
  Before the run, `prereg.verify` passed and all 6 frozen inputs matched.
  All 9,268 files in `data_manifest.json` also matched their sha256.
- Outputs:
  - `results/cells.csv`: all 228 cells.
  - `results/events_primary.csv`: the primary trades.
  - `results/summary.json`.
  - `run.log`.

FINDINGS was written by the orchestrator from the lane agent's text. The harness does not let subagents write it.

## Verdict

**NULL.** The primary cell is WTI, all venues pooled, k = 2, H = 60 s, CME open.
The PREREG passes a cell only if its 1x lower bound is above 0 and its 2x mean is
above 0. Here the whole 1x interval is below zero.

| Cost | Net mean (bp/trade) |
|---|---|
| gross | -0.19 |
| 1x | -1.16 (hour-block 95%: -1.84 to -0.52) |
| 2x | -2.14 |
| 3x | -3.11 |

- 468 trades: Lighter 465, Binance 3, Hyperliquid xyz 0, Kraken 0.
- 55 UTC-hour blocks, 10,000 bootstrap draws, seed 434.
- Mean round-trip cost at 1x: 0.97 bp.
- P(mean ≤ 0) = 0.9998.
- Detectable effect at 80% power: 0.94 bp.
- 309 buys and 159 sells.
- 79% of entries met a thin touch (under $5k displayed).

The intervals are computed only at 1x, the bound the gate uses. At 2x and 3x the
mean alone already fails the gate.

### By day (primary, net 1x)

| Day | Trades | Net 1x |
|---|---|---|
| 10-29 | 172 | -1.38 |
| 10-30 | 183 | -0.96 |
| 11-02 | 32 | -0.61 |
| 11-03 | 20 | +0.26 |
| 11-04 | 15 | -0.75 |
| 11-05 | 31 | -3.83 |
| 11-06 | 15 | +0.90 |

Five of seven days are negative. The two positive days have 20 or fewer trades
each. The first two days hold 355 of the 468 trades.

### By venue (primary)

| Venue | Trades | Gross | Net 1x |
|---|---|---|---|
| Lighter | 465 | -0.14 | -1.05 |
| Binance | 3 | -7.27 | -18.26 |

Venue selection is driven by fees. The trigger is
|d| ≥ max(k·(spread + 2·fee), 4 bp), so zero-fee Lighter triggers near the 4 bp
floor. Kraken and Binance (5 bp a side) and Hyperliquid xyz (9 bp) trigger only
on deviations of 20 to 36 bp or more.

## Why it fails

These diagnostics describe the primary trades. They were not decision cells.

- The trigger fires near the floor: median |d| is 4.85 bp.
- The gap does close. The median share closed by the exit is 0.85 (IQR 0.60-1.05).
- It closes at the other venues:
  - Lighter's own move toward the consensus has a median of 0.0 bp (mean -0.32).
  - The other venues' move toward Lighter has a median of +3.39 bp (mean +4.02).
- Stale quotes are not the cause.
  - Quote age: median 0.06 s, 90th percentile 0.7 s, 2.1% over 5 s.
  - Keeping only quotes up to 5 s old leaves 458 trades at net -1.17.

The residual is real and it reverts, but it reverts on the venues we do not trade.
Lighter is the only venue cheap enough to trigger often, so a Lighter trade earns
Lighter's own move, which is about zero. The opposite trade sits on venues whose
taker round trip costs about 11 to 19 bp before spread, against a median move of
about 3.4 bp. No cell here measured that opposite trade.

## Sensitivity and other instruments

All rows are pooled across venues, k = 2, CME open, unless stated.

| Cell | Trades | Gross | Net 1x |
|---|---|---|---|
| WTI H=10 | 1,123 | -0.04 | -0.97 |
| WTI H=60 (primary) | 468 | -0.19 | -1.16 |
| WTI H=300 | 205 | -1.89 | -2.88 |
| BRENT H=60 | 846 | -0.02 | -2.18 |
| NATGAS H=60 | 489 | -0.23 | -6.80 |
| NATGAS Lighter H=60 | 450 | +0.46 | -3.89 |

- WTI at k = 3, H = 60: 436 trades, net -1.03.
- NATGAS Lighter at H = 300: gross +1.94, net -2.70 (95% -5.74 to +0.14).
  This is the only gross drift worth noting, and wide spreads more than cancel it.
- Gold: no triggers in any cell.

Across the lane:
- 99 of 228 cells have trades.
- 36 of them have positive gross.
- None is net positive at 1x.
- The best is -0.40 bp (WTI k = 3, H = 10, CME closed: 74 trades in only 2 blocks).

## CME-closed stratum

The recording holds only 2.46 h of CME-closed time:
- the daily 16:00-17:00 Chicago hours, Monday to Thursday;
- Friday after 16:00 Chicago;
- no weekend.

The primary cell in this stratum has 23 trades in 2 blocks, net -1.12 bp. That is
INCONCLUSIVE under the PREREG minimum of 30 trades and 4 blocks. The half of M443
about CME being closed is **untested**, not null.

## Read against program trials

Program total: 9,784,937 trials, including this lane's 228. No cell is positive,
so there is nothing to deflate. The best of the 228 cells is still negative at 1x.
The NULL holds under any correction for multiple testing.

## Limits

1. **Sample.**
   - About 52 h over 7 weekdays, 2026-10-29 to 11-06, and no weekend.
   - Only 2.46 h with CME closed.
   - 355 of the 468 primary trades fall on the first 2 days.
2. **Fills.**
   - Fills are modelled at the displayed touch: no queue, no partial fills, no impact.
   - 79% of entries met a thin touch (under $5k).
   - The result is already negative before any of this, so it could only get worse.
3. **Fees are assumed.**
   - Per side: Lighter 0, Hyperliquid xyz 9 bp, Kraken 5 bp, Binance 5 bp.
   - I did not read Binance's fee schedule for TradFi perps.
   - Lighter's zero fee is why 465 of the 468 primary trades are on Lighter.
4. **Local receive clock.**
   - "Lighter leads" may partly be feed latency at our recorder: the other
     venues' messages may arrive later rather than move later.
   - This lane cannot tell the two apart.
5. **Latency is assumed.**
   - Entry is 1.3 s after the signal on Lighter and 1.0 s on the others.
   - The order path was not measured.
6. **Access.** Lighter jurisdiction and access (R428) are still unresolved.
   Nothing here authorizes paper or real trading.
7. **Diagnostics are descriptive.** Gap closure, who moved, quote ages and sides
   were not decision cells. They suggest hypotheses and test nothing.

## What it means

- **Taker form of M443: closed** for CME-open hours on these recordings.
  Taking the deviating venue toward the cross-venue median loses 1 to 7 bp a
  trade at 1x.
- **CME-closed form: untested.** Reopen it only with recorded weekend or other
  CME-closed hours, and only under a new lane id.
- **"Lighter leads" is a new hypothesis, not a result.**
  - Its trade would be on the other venues, toward Lighter.
  - As a taker it does not pay: about 11-19 bp round trips against a ~3.4 bp
    median move.
  - A maker version needs two things first: a check of feed latency on the
    receive clock, and a measured fill model.
