# Nagel, "Evaporating Liquidity" (NBER Working Paper 17653, December 2011; RFS 2012), read in full

- **Read 2026-11-25, in full:** the introduction, the model (section 2), the results (sections 3.1-3.4), the
  conclusion, and appendices A (proofs), B (data) and C (robustness). Legal copy:
  https://www.nber.org/papers/w17653.
- **Question I brought:** is the weekend fade on 24/7 stock perps (R462, R465, R463 forward) a payment for liquidity
  provision, and what does the theory say about how to build it and what to expect forward?

## Cards
### 1. Short-term reversal returns proxy the returns of liquidity provision (section 2, eqs. 5-11)
- **The model.** Market makers absorb order imbalances x with limited risk-bearing capacity γ (CARA; margin or
  risk-management constraints in reduced form).
- **Returns follow eq. 5:** R(t+1) = ξ + η + (1/γ + φ)·x(t+1) − (1/γ)·x(t).
  - The term −(1/γ)·x(t) is a predictable reversal that pays the market maker.
  - Price impact from private information (φ) is permanent and does not reverse.
- **Market makers' return per dollar** tends to √(2π)·(1/γ)·σx (eq. 7): it falls with their aggressiveness γ and
  rises with the volatility of order flow σx.
- **A reversal strategy on market-adjusted returns** (Lehmann weights, $1 long and $1 short) earns
  ρ·√(2π)·(1/γ)·σx (eq. 11).
  - ρ < 1 because past returns also carry public news, which does not reverse.
- **For us:** on a weekend, γ is small (a single name has no hedge) and σx is large (retail flow), so the fade
  should pay. The names whose weekend move is public news (crypto proxies, which follow BTC) dilute it through ρ.

### 2. About 40% of a closing-price reversal is bid-ask bounce (Table 1)
- **The numbers** (1998-2010, individual stocks, hedged): 0.29% a day on transaction prices against 0.17% on quote
  midpoints, with similar SDs (0.48% and 0.54%).
- **For us:** R462 measured on last trades (hourly closes). On mids, expect about 60% of +42 bp, so about +25 bp.
  Thorp's rule of using half the in-sample edge now has a mechanical reason as well as a statistical one.
- **R462's own bounce check** (W measured to 18:00, entry still at 19:00, +53.9 bp) argues the weekend effect is not
  mostly bounce. R463's tickets, which walk the book, will tell.

### 3. Hedge the conditional market exposure (section 2.4, eq. 18)
- **Why it is needed.** After the market rises, a market-adjusted reversal book is long low-beta and short high-beta
  stocks, so its beta turns negative, and the reverse after a fall.
- **Nagel's fix:** regress the book on the market and its interaction with the sign of the prior market move, then
  subtract β(t−1)·f(t). The mean is unchanged and the SD falls (0.56% to 0.48% a day).
- **For us:** a balanced weekend book carries the same conditional beta after a broad weekend move. Hedging it with an
  index perp (xyz:XYZ100 or SP500) is the textbook design.

### 4. Common-factor reversals do not pay in normal times (Tables 1-2)
- **Industry-portfolio reversal:** 0.02% a day, Sharpe 0.56. It pays only when the VIX is high (about 0.20% a day at a
  VIX of 60).
- **For us:** the common weekend move should not reverse in calm times. That matches R464 and R432, the index-perp
  nulls. Removing it from the book removes noise, not edge, except in turmoil.

### 5. The expected return from liquidity provision moves with market makers' capacity (Tables 2-5, Figure 4)
- **The VIX predicts reversal returns:** a coefficient of 0.22 per point of daily-normalized VIX; monthly R² 0.56;
  out of sample through 2007-09.
- **The Sharpe ratio rises too,** which points to funding and risk-management constraints, not only higher risk.
- **The weakest stocks pay most** (small, illiquid, high volatility). Liquidity withdrawal reaches the largest stocks
  as well.
- **For us:** the weekend fade should pay more on volatile retail names (R462's sums agree) and on weekends that
  follow high VIX.
  - This is a forward prediction to register, not to fit now.
  - It is also a risk: in calm, crowded times the rent shrinks.

## What I checked against our own data
- **Order of magnitude.** Nagel's 0.17-0.29% a day for a daily reversal sits beside R462's +42 bp per
  market-weekend, a three-hour hold after a 47-hour unhedged window. The weekend rent is the daily rent of a market
  whose market makers have no hedge for two days.
- **Not checked:**
  - the VIX dependence on our weekends (24 weekends is too few to fit);
  - the beta of R462's book.

## What it changes in the design (cycle 5)
- **The faster lane should be the textbook book:**
  - weights proportional to the market-adjusted weekend move (Lehmann), or a threshold on it;
  - $1 long and $1 short;
  - hedged for conditional beta with an index perp;
  - crypto proxies left out, if prediction 6b holds.
- **Forward expectations:**
  - the edge on mids is about 60% of the last-trade edge;
  - the edge rises after high-VIX Fridays;
  - it decays as weekend market-making capital grows.
