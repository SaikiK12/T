# He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures" (arXiv 2212.06888v7, Sept 2026), read in full

- **Read 2026-11-24, in full:** the main text (sections 1-6, 37 pages) and Appendix G (the model), with Appendices D and
  F located. Legal copy: https://arxiv.org/abs/2212.06888.
- **Question I brought:** what sets the gap between a perp's funding and the cash rate, how large are arbitrage
  profits, and what limits them? That is the barrier behind the funding-design gap.

## Cards
### 1. In equilibrium, funding equals the risk-free rate (Proposition 1, eq. 3)
- **The result.** With no random-maturity arbitrage, F = (1 − Φ⁻¹(r))⁻¹ S, where Φ is the funding function. The key
  condition is Φ((F − S)/F) = r.
- **For Binance's clamp** (κ = 1, γ = 0.05%, ι = 0.01% per 8 h; Corollary 2): when r < ι, F = κ/(κ + γ − r) · S.
  - The no-arbitrage perp therefore trades below spot, at a premium of about −(γ − r) ≈ −0.046% per 8 h.
  - There, funding = p + clamp(ι − p, ±γ) = r: about 4%/yr, not 10.95%.
- **For a floorless venue** (Φ = κp), funding = r as well. **With unlimited arbitrage, the design gap is zero.** It
  exists only because arbitrage is limited.

### 2. The deviation ρ, and its size (eq. 17, Table 4)
- **Definition:** ρ = κ(F − S)/F + sgn(ι − r)γ − r = Φ − r, annualized.
- **Mean ρ on Binance, 2020-2024:** BTC 0.42, ETH 0.52, BNB 0.38, DOGE 0.50, ADA 0.51; mean |ρ| 52-90%/yr.
  - Before 2022: 0.69-0.99. After 2022: 0.09-0.18 (about 80% smaller).
- **Trend:** −22 percentage points a year in |ρ| (Table 10). It rises with past 120-day returns (extrapolative
  leverage demand) and does not rise with volatility.
- **Comovement:** ρ is highly correlated across coins (0.50-0.88). The authors read it as arbitrage capacity being
  common to all coins.

### 3. A convergence strategy with the clamp-correct target pays at retail costs (Tables 6-9)
- **The rule:** open when ρ is beyond ±κc (c = the round-trip cost of both legs); close when ρ returns to 0.
  - Targeting premium = 0, which ignores the clamp, halves the Sharpe (Table 7, "No Clamp").
- **At Binance's high (retail) fee tier, net of effective spreads, 2020-01..2024-03:** Sharpe BTC 3.27, ETH 4.45, BNB
  6.63, DOGE 3.45, ADA 3.80.
  - Returns per year on notional: 12.6, 18.2, 38.4, 35.5 and 23.1%.
  - Maximum drawdown 1.5-13.9%.
- **Returns come mostly from price convergence,** not from funding (Table 8). For BTC over the whole sample: 37.6
  points of convergence against 14.9 of funding.

### 4. The barrier is arbitrage capacity W/m (Appendix G, section 5)
- **Model:** end-user demand Q = θ − ηρ; arbitrageur supply X = min(Λ(ρ − k), W/m), with Λ = 1/(Aσ²h).
  - When capacity binds, ρ = (θ − W/m)/η.
  - k includes trading costs and "the expected cost of exchange default".
- **The evidence:**
  - Binance's portfolio margining (2022-04-20) let the spot and perp legs be netted, lowering m. Mean |ρ| fell by
    3.3-7.8 points against a pre-event mean of 23-27 (HAC t −1.7 to −4.1).
  - Order flow moves the premium three times as much in the high-deviation tercile (0.094 bp against 0.031 bp per
    point of imbalance).
- **Cross-exchange dispersion (section 2):** "exchanges do not offer cross-margining across venues", so each leg is
  funded and margined separately. Illiquid venues' funding responds more to venue-specific flow (Bitfinex was 0.2% of
  BTC perp volume).

## What I checked against our own data (2026-11-24, descriptive)
- **The test:** on Binance's hourly premium index (`data/premiumIndexKlines_1h`, about 780 USDT perps), how often does
  the premium exceed the clamp benchmark (−0.046%) by more than a retail round trip of 0.19%?
  - Each episode is a chance for the paper's short-perp, long-spot leg.
- **Result.** 2025: 38-87 episodes per coin. 2026 (to September): 56-136 per coin, in every liquidity tier.
  - The median excess beyond the cost is 8-11 bp per episode.
  - Supply did not dry up after 2022. It rose again in 2025-26.
- **Not checked:**
  - the depth behind the impact price on thin coins;
  - convergence inside the hour;
  - spot-leg costs on thin coins;
  - the opposite leg (short spot).
