# Reflection, 2026-11-24 (cycle 1 of rule 11): why the design gap exists, who takes it, and what that says

These are the six-question approach of `CLAUDE.md`, applied to the subject the lab depends on. No test was run for
this page. One observation was made: Kraken's own mark prices on 2025-10-10, as the reflection asked.

## 1. The economic question
Why do leveraged longs on floor venues keep paying about 10.95%/yr while the same position on a floorless venue costs
about the premium alone? And why has arbitrage not closed the gap?

## 2. The mechanism (from the formula, `research/intake/library_20261119/deriv.md`)
- **On a floor venue,** funding = P + clamp(0.01% − P, ±0.05%) per 8 h. It is **flat at 0.01% while the premium P
  stays between −0.04% and +0.06%**.
- **An arbitrageur who shorts the floor venue** pushes P down, but inside that band the funding does not move. The
  formula shields the floor from the very pressure that would erase it.
- **The gap can only close from the floorless side.** Arbitrageurs buying the floorless perp raise its premium, and so
  its funding.
- **So capacity is set by the depth and the long-side elasticity of the floorless venues,** not by the floor venues.

## 3. The barrier: who could take it, and what stops them
- **Ethena-type basis traders** take the floor at scale, but against spot (long spot, short perp). They do not need the
  floorless venues.
- **A perp-perp arbitrageur** needs the floorless venues and meets four things:
  - their thin books (Kraken's small coins, Deribit's new perps);
  - two separate margin accounts, so leverage is capped by wicks (measured 2026-11-24);
  - venue credit risk (about 2%/yr of the stake, measured 2026-11-24);
  - operational work across five venues.
- **So the gap has two parts, which the lab had mixed together:**
  - **on liquid pairs (Deribit BTC/ETH, Bitfinex majors),** it is mostly a risk premium for venue risk and split-margin
    wick risk. Its +4-7%/yr unlevered is about cash plus those costs. That is why funds leave it there.
  - **on thin coins (Kraken's small perps, +22-31%/yr in sample),** it is a capacity rent. It is too small for anyone
    with a cost of capital, and that is exactly where a small, patient account has an edge.

## 4. Fermi size and capacity
- **Kraken's thin coins:** R508 put the capacity at about $40-100k of capital. At a halved +11-15%/yr, that is about
  $5-15k a year, several times the planned $2,000 stake.
- **Liquid pairs:** capacity in the millions, but the excess over cash after venue risk is near zero at leverage 1 (the
  Kelly note).

## 5. What we see or reach that others do not
- The cross-venue comparison of funding formulas.
- The willingness to run many small, thin books by hand or by script.
- Patience: no redemptions.
- Access to Kraken's EU offer (all R509 coins are on its EEA list).

## 6. What it changes
- **The money case is the thin-coin sleeve, not the liquid one.**
  - The liquid sleeve is mainly a carrier of venue risk, worth having only as breadth.
  - The forward reads should be read the same way: R509/R510 (Kraken) decide the money; R520/R524 decide the class.
- **The next search is "capacity rents behind thin books".** Where else does a rule force a payment on a market too
  small for funds?
  - thin perps on any venue whose funding rule differs from its neighbours';
  - new listings with funding caps;
  - per-account incentive caps;
  - small spot-lending markets with formula rates.
- **The wick question is a question about each venue's liquidation price,** not about Binance's prices. It is answered
  per venue below and in `mechanism_map.md`.

## How I approached the last subject, and what I would change
- **On 2026-11-24 I measured intraday wicks on Binance perps** and concluded "leverage 1 on long alt accounts".
- **I measured before asking the mechanism question:** on which price does each venue liquidate? The docs answer it:
  - Kraken: the spot index plus a 30-second smoothed premium, capped at 1%;
  - Deribit: kept within bands around the spot index;
  - Hyperliquid: a median of its oracle, its book and the large CEX perps.
- **Then the data:** Binance's spot lows on 2025-10-10 were as extreme as its perps (mean −69%). So the decisive number
  is Kraken's own mark history, which its charts API serves (measured below).
- **The better order:** rule first, then the data that the rule says matters, then the number.

## Kraken's own prices on 2025-10-10 (the observation the reflection asked for)
- **Source:** Kraken Futures charts API (`/api/charts/v1/{mark,spot,trade}/PF_x/1h`, public). 126 of R509's coins; the
  low within 2025-10-10 UTC against the previous close.

  | Kraken price | Mean low | Median | Worst | Share below −40% |
  |---|---|---|---|---|
  | **mark (used for liquidation)** | **−43.8%** | −47.5% | −62.8% | 65% |
  | spot index | −43.2% | −47.3% | −62.9% | 63% |
  | last trade | −46.2% | −47.7% | −78.7% | 77% |

- **Kraken's mark fell far less than Binance's prints** (−65% to −69%), but still about −44%.
- **An account with every leg against it is liquidated after (1/L − mm)/(1 + mm):**
  - at mm 5% (the EU entity's retail schedule), L = 1.5 survives (59%) and L = 2 does not (43%);
  - at mm 25% (the most conservative retail schedule), only L = 1 survives (60%), and 1.25 is borderline (44%).
- **The rule is refined, not reversed:** the Kraken lane at 1.5x if Kraken confirms 5% maintenance for an EU retail
  client, otherwise 1x. The question to Kraken (owner) is now the key input.
