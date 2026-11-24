# Reflection, 2026-11-24 (cycle 2 of rule 11): what "Fundamentals of Perpetual Futures" changes in how I see our edge

- **Source.** I read the paper in full ([card](../../research/intake/perp_fundamentals_20261124.md)), as the owner asked:
  "même pour lire les arXiv etc., fais-le en profondeur".

## 1. The economic question, now answerable
- **What does a perp's funding pay above cash, and why?**
- **Answer.** Funding above cash (ρ) is the price of leverage that end users pay. It is bounded by what arbitrageurs
  can absorb: W/m, their capital divided by the margin per dollar intermediated.
  - With unlimited capacity, every venue's funding equals the cash rate, and the design gap vanishes.

## 2. What this changes
1. **Our design gap is a limits-of-arbitrage rent, and its barrier has a name: m.**
   - A cross-venue hedge cannot be netted, because venues do not cross-margin with competitors. So m is high, and it
     stays high: that is structural.
   - The wick risk measured on 2026-11-24 is the same m, seen from our side.
   - The rent lasts as long as venues stay separate. It shrinks when a floorless venue lets its own spot and perp be
     netted (the Binance 2022 event, in reverse), or when much more capital enters.
   - **Watch item for the map:** margin-regime changes at Kraken, Deribit and Bitfinex.
2. **The rent decays, as the paper measures** (|ρ| −22 points a year; −80% after 2022). R508's monthly decline (4.5%
   to 0.9% from January to October) is the same force at small size. Plan on decay, not persistence: forward reads,
   then reassess each quarter.
3. **The search criterion for capacity rents is now precise.** A rent exists where all three hold:
   - leverage demand θ is high: extrapolative retail after rises, on thin coins;
   - capacity W/m is small: no netting, thin books, venues funds avoid;
   - we can reach it.
   That replaces "look for anomalies" with three things to measure.
4. **A second candidate inside the class: same-venue convergence with the clamp-correct target.**
   - The paper's strategy earned Sharpe 3-7 at retail fees on five large coins (2020-2024).
   - The lab tested premium cells and static carry, but always with the wrong target (premium = 0; M047, R185). That
     target halves the Sharpe, per the paper.
   - Thin coins are where θ is high and W/m small.
   - Supply counted on our data: 40-136 episodes per coin per year in 2025-26 beyond a retail round trip, with about
     8-11 bp left after costs.
   - It may be another capacity rent, uncorrelated with the cross-venue gap (it is a convergence trade inside one
     venue).

## 3. The barrier for candidate 2, and who is paid first
- **On liquid coins,** basis desks with portfolio margin and fee rebates are paid first (the post-2022 compression).
- **On thin coins:**
  - the impact depth is small;
  - the spot leg is costly;
  - a fund's fixed costs exceed the rent.
  That is our niche, if the depth exists at our size.
- **Venue for the owner:** Binance does not serve French retail with derivatives. The same idea on Kraken (its own spot
  and perp, but a floorless funding rule, so a different benchmark) is the accessible version. The benchmark there
  is Φ = κp = r.

## 4. The cheapest decisive observation for candidate 2 (next cycle)
- **What decides:** whether the 8-11 bp beyond cost survives the real depth and the real convergence time on thin
  coins.
- **Order of work:**
  1. **Kraken:** its premium against its own spot index, from the charts API, with trade and spot candles, on its thin
     coins, 2025-26. Count episodes beyond Kraken's retail round trip, using Kraken's own benchmark.
  2. **If the supply is there:** a registered test, with the forecast, pre-mortem and power written first, on hourly
     bars plus a book-depth haircut.

## How I approached the last subject, and what I would change
- **Last cycle** I reasoned about the design gap from the formula alone.
- **The paper adds the equilibrium** (funding = r without limits) and the formal barrier (W/m).
  - I had found half of it by intuition (the clamp band shields the floor).
  - The other half, why the floorless side does not close the gap, is the same W/m on the floorless venues.
- **What I would change:** read the theory of the market I trade before reasoning alone. A 37-page paper answered in
  two hours what my own reasoning had half-answered. I had listed this paper in the intake on 2026-11-20 and not read
  it.
