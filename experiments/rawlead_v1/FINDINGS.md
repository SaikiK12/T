# R431 rawlead_v1: NULL. Binance's USDT perp book does not lead its USDC book by anything a taker can use

**Registry:** R431, 148 trials (program total 9,784,511).

**Run:** once, 2026-11-09 22:05 UTC, by the frozen runner `scripts/run_rawlead.py`. PREREG `3db2f00f…`; all 22 inputs
matched. Outputs are in `results/`: `summary.json`, `cells.csv`, `partA.csv`, `partA_events.csv`,
`events_primary.csv` and `filters.csv`. Log: `run.log`.

## Verdict
**NULL.** In the primary cell (θ = 2 bp, this machine's delay, a 1000 ms hold), 325 events earned +0.08 bp gross on
average. The block-bootstrap 95% interval of the gross is −0.40 to +0.42 bp. A taker pays 8 bp a round trip.

| Cost | Mean net per trade | 95% interval (1x) |
|---|---|---|
| 1x (4 bp a fill) | −7.92 bp | −8.40 to −7.59 bp |
| 2x | −15.92 bp | |
| 3x | −23.92 bp | |

- **By asset:** BTC −7.83 bp (55 events), ETH −7.94 bp (270).
- **By day:** −8.08 bp (10-29, 41 events), −8.01 bp (10-30, 90), −7.85 bp (11-05, 194).
- **Delay:** the machine's median delay from the trigger's publication to arrival was 274 ms.
- **Thin touch:** 38% of fills met a touch under $5,000, so even these prices flatter the trade.
- **Break-even fee:** gross / 2 = 0.04 bp a fill. No Binance fee tier comes near that.

## The frontier (M431): there is no edge to decay, even 1 ms after publication
Mean gross by delay, θ = 2 bp, 1000 ms hold:

| Delay | 1 ms | 25 ms | 50 ms | 100 ms | 250 ms | 500 ms | 1000 ms | 1500 ms | This machine |
|---|---|---|---|---|---|---|---|---|---|
| Gross (bp) | −0.06 | −0.04 | −0.09 | +0.05 | +0.06 | +0.07 | −0.20 | −0.27 | +0.08 |

- **Every point is inside noise.** No point comes near the fee, so τ_50, τ_BE and τ_0 are all 0: the gross is at or
  below zero from the first point.
- **θ = 1 bp** (4,347 events) is slightly negative at every delay: −0.19 bp at 1 ms, about −0.05 bp elsewhere.
- **θ = 4 bp** (19 events) earns −0.2 to +1.1 bp at the delays up to 250 ms, +1.07 bp at this machine's delay. **θ = 8 bp** has 1 event. Both are far
  below 8 bp and too few to read.
- **Holds:** 300 ms and 3000 ms change nothing.
- **A colocated taker would fare no better.** One ms after the trigger's publication it already earns nothing on
  average. Shortening the 250 ms path through the proxy cannot fix that, and neither can a VIP fee tier.

## Why: what the USDC book does after the USDT book moves (M430, Binance's clock)
At θ = 2 bp (325 events), the first outcome within 3 s:

| Outcome | Share |
|---|---|
| USDC catches half the move | 45.5% |
| USDT gives half of it back | 53.2% |
| USDC moves the other way | 1.2% |

- **Half of the "leads" are noise on the USDT side.** The USDT book moves away and comes back before the USDC book
  follows.
- **The real catch-ups are almost instant.** Median 7 ms. 45% come within 5 ms, 69% within 25 ms, 87% within 100 ms
  and 95% within 250 ms. Binance's own arbitrage closes the gap in milliseconds. By the time an order from this
  container arrives, about 274 ms later, it is over.
- **At θ = 1 bp** it is worse for a follower: 31% catch-ups, 63% reversals, median catch 39 ms.

## The maker's side (Part C)
Of 869,117 USDC trades, 20% (23% of notional) came within 1 s after a θ = 1 crossing, in its direction. A further 27%
came in such a window the other way.
- **Takers on USDC are informed on average.** The aggressor's markout against the mid is +0.55 bp at 1 s and +0.59 bp
  at 10 s for trades outside lead windows. The resting side loses that, and the 0% maker fee does not pay it back: the
  USDC touch is about 0.01-0.04 bp wide.
- **Trades that follow a USDT move are less toxic, not more.**
  - With − out: −0.12 bp at 1 s (95% interval −0.22 to −0.01) and −0.51 bp at 10 s (−0.84 to −0.08).
  - Against − out: −0.08 bp at 1 s (−0.13 to −0.03) and +0.03 bp at 10 s (−0.31 to +0.31).
- **The first USDC trade in the event's direction:**
  - It came within 1 s after 89% of θ = 1 events.
  - Median 92 ms after the trigger; 20% within 5 ms and 29% within 25 ms.
- **For M427 and M433:** a USDC maker that stands down during USDT lead windows would avoid the less toxic flow and
  keep the rest. The premise of the selective maker does not hold on this tape. Part C is descriptive and was not
  part of the decision.

## Micro-problems this lane measured (useful beyond this verdict)
1. **The local receive order invents leads.**
   - On 10-29 and 10-30, most naive "stale USDC quotes" were moves that Binance stamped in the same millisecond on
     both books: 4-18 USDC rows with the same E as the trigger, read about 0.1 ms after it.
   - A machine that acts on the first message it reads trades those.
   - The naive cell was no better: +0.01 bp gross, 350 events.
   - Read the whole socket buffer before deciding, and align books of one venue in that venue's clock.
2. **This container's feed is not a real-time feed.**
   - 12-16% of USDT book rows queued over 100 ms above the floor on 10-29 and 10-30.
   - On 11-05, 51% of BTCUSDT rows queued over 1 s; the median queue was 1.1 s and the 90th percentile 15 s. The
     Python consumer fell behind exactly in the busy minutes.
   - The local clock drifted by up to 30 ms a minute.
3. **The proxy round trip is 249-253 ms.** The relevant catch-ups take about 7 ms. That is three orders of magnitude
   too slow for this game.
4. **The fee is the wall even with zero latency.** A 4 bp taker fee needs a round-trip gain of 8 bp. The primary
   events start from gaps of at least 2 bp, and half of them revert.

## Read against the program
- **Program total:** 9,784,511 trials (`registry.program_trials`).
- **The verdict:** a NULL with a precise zero. The gross interval is ±0.4 bp around 0 against an 8 bp cost, so no
  multiplicity correction could change it.
- **Prior lanes:** it agrees with R347/R348 (Lighter makers close a Binance lead within a second) and with the lab's
  repeated finding that maker entries are adverse-selected (R193/R194).

## What this means
- **The taker lead from Binance USDT to USDC is closed.**
  - Not from this machine, not colocated, at any listed fee.
  - M430 and M431 are TESTED; M433, which needed them to survive, stays blocked.
- **Speed-based HFT is not a game this lab can play.** The binding constraint is not the idea but latency and fees.
  The receive path through the agent proxy is ~250 ms with queueing spikes of seconds. Binance's own arbitrage
  settles in single-digit ms.
- **A maker form would need a new lane.** It would need a model of when *not* to quote that beats 0.55 bp of average
  toxicity at a 0.01-0.04 bp spread. The lead windows are not that model.

## Limits
- **Sample.** 7.9 hours on three afternoons. 11-05 is dominated by ETH (179 of 325 primary events). One regime.
- **Fills.** Taker fills at the touch with no queue, no rejection and no impact, and 38% of primary fills met a touch
  under $5,000. These limits all flatter the trade, and it still lost.
- **Arrival.** The arrival uses the stream gateway's ping. The order gateway's extra delay is unknown. It would only
  lengthen the delay; the frontier shows that shorter delays do not help.
- **Shared clock.** The two Binance books are assumed to share one clock. The 0-1 ms same-E clusters support this.
- **Part C** pools both assets and days. Its trades come from a second connection, aligned in Binance's clock. The
  markouts are against the mid and exclude fees.
- **Not tested:**
  - Bybit confirmation, M434's quote-FX residual and M438's intra-second phase;
  - a maker strategy and any other venue pair.
