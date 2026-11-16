# FINDINGS: gatemaker_v1 (R497), what a resting order earns or loses on Gate's USDT perps

**Answer: LEVER_HOLDS under the frozen rule.** In each of the four volume bands, an order resting at the touch and
hedged 5 seconds after its fill cost at most half of what a taker paid on Gate's USDT perps, 2026-11-02..2026-11-15.

**What it does not show:** that C14 makes money. The rule counts every trade at the touch as filling the resting
order. Queue position, the time to fill and the cost of chasing a price that runs away were not measured. The result
earns M546 the forward execution lane the PREREG names; that lane has to measure what this one assumed.

## Run
- **When:** one run, 2026-11-16 16:30-17:42 UTC, without `--limit`, after the freeze was pushed (4b7eb199).
- **Integrity:** PREREG sha256 `c70e99a30c5f7dce6f18a3f85bfbb6a7421522be6c640d990144339e1068b07b`, verified at start;
  the 4 frozen inputs matched.
- **Coverage:**
  - 60 contracts sampled with seed 497, 15 per band; 56 count (at least 100 core trades).
  - The 4 that do not count are all in the lowest band (MO, TMO, VIST, CLSK).
  - 28 one-hour windows per contract; 2,303,374 trades read.
  - 8 of 1,680 windows hit the 30-page cap and were measured on the span covered.
- **Sign check:**
  - The median over contracts is 0.907, so the tape's sign convention holds (the rule needs 0.6).
  - Two counted contracts in the lowest band are below 0.6 (NANYA 0.42, CLS 0.44). Leaving them out, as a check
    that decides nothing, changes that band's hedged-maker cost from −6.23 to −6.75 bp and nothing else.

## Band table (medians over counted contracts; bp per side)
Hedged maker = maker fee − 5-second notional-weighted markout. It is decided at a 2 bp maker fee. Taker = effective
half-spread + 7.5 bp.

| 24 h volume (USD) | counted | effective half-spread | taker | 5 s markout | hedged maker | half of taker | holds |
|---|---|---|---|---|---|---|---|
| < 50k | 11 | 11.25 | 18.75 | +8.23 | −6.23 | 9.38 | yes |
| 50k-500k | 15 | 10.37 | 17.87 | +1.95 | +0.05 | 8.93 | yes |
| 500k-5M | 15 | 4.47 | 11.97 | +1.00 | +1.00 | 5.98 | yes |
| > 5M | 15 | 2.03 | 9.53 | +0.17 | +1.83 | 4.77 | yes |

**How to read the markout:**
- A resting order fills at the touch, so it starts with the half-spread in hand.
- The markout is what is left of that half-spread after the price has moved for the stated time.
- In the two upper bands the move eats most of it: about 1 bp of 2-4.5 bp is left at 5 s.
- The 5 s markout is negative on 20-40% of the contracts in the three upper bands.

**Markout by delay** (notional-weighted, bp):

| band | 1 s | 5 s | 60 s | 300 s |
|---|---|---|---|---|
| < 50k | 8.05 | 8.23 | 5.10 | 5.57 |
| 50k-500k | 3.64 | 1.95 | 1.18 | 1.00 |
| 500k-5M | 1.38 | 1.00 | 0.30 | −0.37 |
| > 5M | 0.54 | 0.17 | 0.37 | −0.30 |

**Taker flow that could fill a resting order** (median taker notional per core hour, each side):
- < 50k: about $400-520. A $5k order at the touch would need about 12 hours of all of it.
- 50k-500k: about $2,700-3,300, so about 1.8 hours.
- 500k-5M: about $30,000, so about 10 minutes.
- > 5M: about $250,000, so about a minute.

## Maker fee sensitivity (in place of 1x/2x/3x, as the PREREG states)
Hedged-maker cost, bp per side; "holds" is against half of taker in the same band.

| band | listed rebate (−0.75 or −1 bp) | 2 bp (decided) | 4 bp |
|---|---|---|---|
| < 50k | −9.23 | −6.23 | −4.23, holds |
| 50k-500k | −2.95 | +0.05 | +2.05, holds |
| 500k-5M | −1.75 | +1.00 | +3.00, holds |
| > 5M | −1.13 | +1.83 | +3.83, holds |

- **The listed rebate:** the −0.75 / −1 bp is the contract field Gate publishes. Whether an ordinary account receives
  it is UNVERIFIED (`research/intake/fee_map_20261116.md`). Nothing here is decided on it.

## What it would mean for C14, if the assumption held (arithmetic, not a measurement)
- **The baseline:** R495 measured C14's universe at a median Gate half-spread of 8.93 bp, which is where the two lower
  bands sit. At $5k a leg, its pair cost is 31.7 bp per leg per side at taker:
  - Binance: 13.43 bp walk + 5 bp fee;
  - Gate: 37.52 bp walk + 7.5 bp fee.
- **With the Gate side at this lane's 50k-500k hedged-maker cost** (+0.05 bp at 2 bp maker), the pair cost falls to
  9.2 bp.
  - R495's linear fit to C14's published 1x/2x/3x nets is net ≈ 3.86 − 1.01 × (cost / 7 bp) %/yr.
  - On that fit, C14 at $5k a leg moves from about −0.7%/yr to about +2.5%/yr. At a 4 bp maker fee it is about +2.4%/yr.
- **That is the ceiling, not a forecast.**
  - A $5k order in those bands takes hours to fill even with no queue ahead.
  - While it waits, the price can leave, and then the order must be repriced or crossed at taker cost.
  - R495 is on unmerged PR #100. Its fit is its own approximation.

## Limits
- **Fill assumption, the main limit.**
  - The rule lets every trade at the touch fill the resting order. A real order joins the back of the queue.
  - The trades that reach the back of a queue are the larger ones, which tend to come before moves. The markout of a
    back-of-queue fill is therefore worse than the markout measured here.
- **Fill time and chasing are not measured.** In the lowest band a $5k order would wait about half a day.
- **The markout is Gate's outright move.** A hedged leg carries only the Gate-versus-Binance move until the hedge.
  This part is pessimistic.
- **Mid proxy.** The mid is the mean of the last taker buy and the last taker sell within 300 s. It is undefined when
  one side is quiet, and some bounce remains.
- **Sample.** Two hours a day for 14 days. Today's listing, so contracts delisted in the window are missing. Bands are
  as of the run. The lowest band is noisy: half-spreads up to 162 bp, and two contracts with a low sign check.

## Reading against the program
- R497 has 0 trials and tests no return; `registry.program_trials()` stands at 9,785,313.
- Nothing here is a significance claim. The forward lane that follows will be read against the program total.

## What follows (frozen rule)
- LEVER_HOLDS earns M546 a frozen forward execution lane on R390's own Gate contracts, under its own id. It must
  measure:
  - the displayed queue ahead at placement;
  - fills only by trade-through, or by volume beyond the queue ahead;
  - the time to fill;
  - the cost of repricing or crossing when the price leaves;
  - the markout to the Binance hedge.
- It is reported beside R390 and never changes R390's decision.
- Nothing here is retuned. No order was placed and no key or account was used.
