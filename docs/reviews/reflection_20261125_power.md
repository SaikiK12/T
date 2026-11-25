# Reflection, 2026-11-25 (cycle 5 of rule 11): how fast can the closed-market family be decided?

## How I approached the last subject, and what I would change
- **Cycle 4 found the family in the lab's own record** and measured its capacity (about $5k a trade). It ended on
  "build a faster forward lane (`rel`) before Sunday 11-29".
- **What I would change.** I named the remedy before measuring the disease.
  - I assumed `rel` is faster because its sample-B p (0.06) was smaller than the raw book's (0.59).
  - Six weekends cannot carry that comparison, and `rel` as R462 computed it is not a book anyone can trade: it
    subtracts the median market move.
  - The mechanism has to come first: why should removing the common move cut the noise? Only then a tradable design,
    and only then its power on R462's own weekends.
  - Feynman's rule applies too: reproduce R462's baseline before computing a variation.

## 1. The economic question
How many weekends must we watch before we know whether the single-name weekend overshoot pays at our size? Can a book
design, derived from the mechanism, cut that number?

## 2. The mechanism of the noise
- **Each weekend's fade return has two parts:**
  - the idiosyncratic overshoot, which the mechanism says reverses: retail flow in single names that market makers
    cannot hedge;
  - the common move, which the mechanism says does not reverse. It carries macro news, and from Sunday 18:00 market
    makers can hedge it with CME index futures. R464 and R432 found no fade on index perps.
- **The raw book fades every market's whole move.** Its weekend return therefore carries the common move with a sign
  that depends on the weekend's direction.
  - In a weekend where most names rose and the rise was real, it loses on most names at once.
  - This shared shock is why the evidence comes per weekend: R463's power section has an SD of about 67 bp per traded
    weekend.
- **A balanced book cancels the common move by construction.** Buy the names that fell most relative to the
  weekend's median move, sell those that rose most, with equal notional on each side. It needs no hedge instrument,
  and the common move enters with + on one side and − on the other.
- **Prediction from the mechanism:** the balanced book's mean is at least the raw book's (the idiosyncratic part
  overshoots more: R462's `rel` +55.8 bp against +42.4), and its per-weekend SD is clearly lower.

## 3. The barrier, and whether the design changes it
- **Same barrier:** no single-name hedge until the anchor returns.
- **One cost.** The balanced book trades a market that the threshold alone would not pick (a small relative move,
  but a large raw move) only if it ranks at the extremes. Its supply differs from the raw book's, and it must be
  counted.

## 4. Fermi size and capacity
- The capacity is the same books, so about $5k a trade (cycle 4).
- If the balanced book has the same mean per trade and half the per-weekend SD, the weekends needed for t = 2 fall
  to about a quarter, since the count scales with SD².

## 5. What we see that others do not
- The split between hedgeable common risk and unhedgeable idiosyncratic risk, read from the venue's oracle rule and
  the lab's index-perp nulls.

## 6. The cheapest decisive observation, with the prediction written first
- **Reproduce R462 on its own weekends** (bars refetched by the frozen `scripts/fetch_xyz_wknd.py` with end
  2026-11-10, so R463's forward weekends never reach the disk). Check that sample A gives back about +42.4 bp over
  about 556 trades. Hyperliquid's 5,000-candle limit now starts at 2026-04-30, so the first weekend (05-01) drops.
- **Then, on the same weekends, the per-weekend mean and SD at the measured costs** (6 bp a round trip, 1.8 bp fee):
  - the raw book (R462's D2);
  - the balanced book: rank markets by W minus the weekend's median W, take those with |rel W| ≥ 50 bp, fade them,
    and set equal notional on the long and short sides.
- **Then the power each design would have** under R463's decision schedule, at the in-sample effect and at half of it.
- **Prediction:** the balanced book's per-weekend SD is at most two-thirds of the raw book's. At half the effect, its
  power at 30 weekends is at least 50%, against about 20-25% for the raw book. If the SD is not lower, the faster
  lane is not built.

## 6b. A second prediction from the mechanism, written before the computation
- **Some single names are hedgeable at the weekend.** Crypto trades 24/7. A market maker short MSTR's weekend perp can
  hedge most of it with BTC perps, so for crypto-proxy names the barrier is low.
- **Prediction:** the crypto-proxy names fade less than the rest, near zero. The set is fixed here, before any number:
  MSTR, COIN, HOOD, CRCL, BMNR, STRC and IREN.
- **This is the second prediction of the refined mechanism.** It is computed on R462's seen weekends, but no lane
  has split them this way.
  - If it holds, it supports the mechanism and suggests excluding hedgeable names.
  - If the crypto-proxy names fade as much as the rest, the barrier story is wrong: the overshoot would be retail
    behaviour, not market-maker capacity.
- **A calendar fact found while waiting.** R463's rule skips weekends after an early close or before a holiday.
  - The next tradable weekends are 12-04, 12-11, 12-18 and then 01-08 (11-27, 12-25 and 01-01 are out).
  - A faster lane has until Sunday 12-06 to be frozen, not 11-29 as cycle 4 said.

## 6c. Read while the bars were fetched: the theory and Lighter's rule
- **Nagel, "Evaporating Liquidity"**, read in full ([card](../../research/intake/nagel_evaporating_20261125.md)).
  - Short-term reversal is the return of liquidity provision, √(2π)·(1/γ)·σx: market makers' capacity γ against the
    volatility of order flow σx. That is the mechanism of section 2, written as an equation.
  - **The textbook book is the balanced one:** $1 long and $1 short on market-adjusted moves, hedged for conditional
    market beta.
  - **About 40% of a closing-price reversal is bid-ask bounce** (0.29% against 0.17% a day). Expect R462's edge on
    mids to be nearer +25 bp than +42 bp. The halved edge in cycle 4's Fermi table now has a mechanical reason.
  - **Common-factor reversals pay only when the VIX is high,** which is consistent with R464.
- **Lighter's rule** (`docs.lighter.xyz/llms-full.txt`, read 2026-11-25):
  - external oracles first; internal pricing when they are stale for about a minute;
  - the internal index is an EMA of impact prices (τ = 30 minutes; the mark's τ = 2 minutes), capped at ±1/L around
    the last oracle price.
  - **The liquidity provider for its stock perps is named:** the LLP (Lighter Liquidity Pool), with "one strategy for
    Equities / RWAs".
  - The lab records the LLP's positions hourly (`llp/positions` on `claude/xyz-books-data`).
- **So the inventory that Nagel's model makes unobservable is observable here.** If the weekend move is liquidity,
  the LLP should end the weekend holding the opposite of the move: long the names that fell, short those that rose.
  That observation tells mechanism from pattern directly. It must be registered before it is looked at, because it
  touches forward weekends.

## 7. The observation (`scripts/check_wknd_power.py`; R462's weekends to 2026-11-09 only)
- **The baseline reproduces.**
  - Sample B: n 260, +36.2 bp, exactly R462's.
  - Sample A: n 531 over 17 weekends at +45.6 bp, against R462's 556 over 18 at +42.4. The first weekend (05-01)
    is past Hyperliquid's 5,000-candle limit, as predicted.
- **Per-weekend nets at the measured cost** (7.85 bp a round trip: fee 1.8 plus the recorded Sunday book 6.05):

  | Book | Sample | Weekends | Trades a weekend | Net a weekend | SD | t | Weekends > 0 |
  |---|---|---|---|---|---|---|---|
  | raw (R463's rule) | A | 17 | 31.2 | +43.7 bp | 49.7 | 3.63 | 13/17 |
  | raw | B | 6 | 43.3 | +21.9 | 106.1 | 0.51 | 3/6 |
  | balanced | A | 17 | 28.6 | +52.0 | 27.7 | 7.75 | 17/17 |
  | balanced | B | 6 | 36.8 | +22.2 | 35.9 | 1.52 | 5/6 |

- **The balanced book's per-weekend SD is 56% of the raw book's in A and 34% in B.** The prediction ("at most
  two-thirds") holds. The two books' weekend nets correlate at 0.68.
- **Power under R463's decision schedule** (weekends A+B resampled, 2,000 runs):

  | Book | Effect in sample | Half the effect | Zero (size) |
  |---|---|---|---|
  | raw | 95% | 32% (futile 20%) | 4% |
  | balanced | 100% | 92% (63% by the 20th weekend) | 6% |

  - The prediction (balanced ≥ 50% at half the effect; raw about 20-25%) holds; the raw book's 32% is a little
    better than my estimate.
  - **At half the effect, the balanced book would most likely be decided by its 20th weekend.** R463 would most
    likely not be decided at all.
- **Prediction 6b failed in sample A, and I record it as a failure.** Crypto-proxy names (MSTR, COIN, HOOD, CRCL,
  BMNR, STRC, IREN) faded +56.8 bp in A (n 59) against +44.1 bp for the rest. Only B (n 30) went the predicted way:
  +4.6 against +40.4.
  - By the criterion I wrote first, the "hedgeable names do not overshoot" part of the refined mechanism is not
    supported.
  - **What survives:** the common move does not reverse (R464, and the balanced book's lower SD with a higher mean),
    and the idiosyncratic part does.
  - **What does not:** that a hedge existing in principle (BTC for MSTR) is enough. Either xyz's market makers do not
    cross-hedge, or the overshoot is retail behaviour that no hedge removes. This test cannot tell them apart. The
    LLP-inventory observation (section 6c) can.

## 8. What it changes
- **Decision: a forward lane on the balanced book is worth building.** It will be a new id, frozen before Sunday
  2026-12-06, the next tradable weekend.
  - Design from the mechanism and Nagel:
    - rel W = W − the weekend's median W;
    - buy rel W ≤ −50, sell rel W ≥ +50;
    - equal notional per side, both sides required;
    - entry Sunday 19:00 and exit 22:00 New York;
    - the same universe and costs as R463 (the recorded books, at $1k and $5k).
  - Reported, not decided on: the conditional-beta hedge (Nagel) and the crypto-proxy split.
- **What it must include,** from the chain's step 4:
  - **Forecast.** `scripts/base_rates.py` files these lanes under "calendar" (23% of decided tests pass). The
    closed-market lanes on their own pass 3 of 5 decided (R462, R465, R468 against R464, R432). Their later samples
    were weak and 6b failed, so the prior is about 0.35; power at half the effect 0.92; P(PASS) ≈ 0.35 × 0.92 + 0.65 × 0.06 ≈ 0.36.
  - **Supply:** about 29-37 trades a weekend, about 45 weekends a year.
  - **Break-even:** about 8 bp a trade at $1k against a +52 bp in-sample edge; a $5k fill costs about 12 bp.
  - **Pre-mortem**, five lines.
  - **Trial count:** it is a second test on the weekends R463 already reads, correlated 0.68 with it.
- **R463 stays as frozen.** Its NULL at a half-size effect would not settle the family; the balanced lane would.

## 9. What could make this wrong
- **The balanced design was chosen after R462 showed its `rel` cell strong.** The SD reduction is a structural
  property and more trustworthy; the mean is in-sample.
- **23 weekends, one oracle constant, last-trade prices.** On mids, about 40% of the edge may be bounce (Nagel).
- **Bootstrap power from 23 weekends** understates tail weekends that have not happened yet.
- **Beta mismatch:** dollar-neutral is not beta-neutral. After a broad weekend move the book is short the high-beta
  names. That is reported forward, not fixed in sample.

## 10. Cycle 6 (2026-11-25, 02:24): the lane is frozen, and what the Fermi table missed
- **Why the same family a third session in a row** (`CLAUDE.md` asks for a written reason):
  - the binding constraint is time to evidence for the lab's strongest payer outside carry;
  - the freeze had to precede the next tradable weekend, 12-04;
  - nothing else on the list moves money or proof as much.
- **What was done.** R530 (`experiments/xyzbal_fwd`) was frozen with PREREG sha `4803b21a`. It has a daily scorer
  (`claude-xyzbal.yml`), and its decision follows R463's schedule.
- **Two checks before the freeze:**
  - on R462's weekends, the lane's own code reproduces the balanced numbers exactly (A gross +59.9 bp, SD 27.7);
  - a live-fetch plumbing run on the 11-06 weekend (R462's B, seen) gives the same weekend as R462's data: 76
    markets, 29 long, 27 short, +84.89 bp gross.
- **What the Fermi table of cycle 4 missed: margin, not depth, sets the owner's size.**
  - Primary source: the trade.xyz Specification Index and "Margin Modes". 58 of R462's 72 listed markets are
    "Normal Isolated" (10x or 20x); only 12 allow cross margin. Each position carries its own margin, so a balanced
    book gets no margin relief from being market-neutral.
  - At 3x per position (an adverse move of about 25% before liquidation), a $1k trade needs about $333 of margin.
    Thirty trades a weekend tie up about $10k for three hours.
  - **At the owner's €10k stage that is about $1k a trade.** That gives about $2k a year at half the edge, or about
    20% a year on that capital. $5k a trade needs about $50k. Capacity in the books (about $5k a trade) binds only
    above that.
  - Open, to answer from Hyperliquid's docs: whether a HIP-3 dex's margin comes from the same USDC balance as the
    validator perps that carry the design-gap legs. Capital that serves the weekend book for three hours could then
    serve carry the rest of the week.
- **How I approached the last subject, and what I would change.**
  - In cycle 4 I sized the family by the book's depth, because depth was the measurement I had just made. The
    owner's size is set first by their capital and the venue's margin regime.
  - The one-page approach asks for "a Fermi size and the capacity". The capacity that binds is the smaller of the
    market's depth and the owner's capital under the venue's margin rules. I now compute both.
