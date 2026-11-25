# Seo, Cha, Son, Lee, Lee & Sung, "When Cross-Venue Agreement Is Not Price Discovery: Disclosure Frontiers for 24/7 Equity-Perpetual Oracles" (arXiv 2608.09188v1, 10 Aug 2026), read in full

- **Read 2026-11-25, in full:** sections 1-9 (the model, Theorems 1-5 with proofs, the numerical illustration, the
  empirics, the limitations). Legal copy: https://arxiv.org/abs/2608.09188.
- **Question I brought:** what moves a 24/7 stock perp's price while the cash market is closed, and what does that
  say about the weekend fade (R462, R463, R530) and the cross-venue Sunday gap (R466)?

## Cards
### 1. A closed-window mark is the fixed point of an oracle network (Lemma 1)
- **The model.** Each venue's index is i = W·m + B·z + η.
  - W: weights on its own and peer venues' perp marks.
  - B: weights on external anchors (cash, futures, ETF, vendor feeds).
  - The mark is pulled toward the index at speed K.
- **The fixed point** is m* = (I − W)⁻¹(B·z + η). **K cancels:** funding and mark control set the speed of
  convergence, never the target. "Faster funding reaches the same endogenous target sooner."
- **For us:** on trade.xyz the closed-market oracle is an EMA of the venue's own book (W on itself, B ≈ 0 for a single
  name), so the weekend target is endogenous. That is the mechanism of R462, written as an equation.

### 2. Prices cannot tell anchoring from peer consensus; disclosure and the cash reopen can (Theorems 1-5)
- **Theorems 1-2:** the reduced form and even the full path law are the same for a purely external network and for
  infinitely many peer-referencing ones. Lead-lag or information-share tests "have power equal to size".
- **Theorem 5:** the reopen gap = anchor mismatch + (I − W)⁻¹-amplified oracle noise + the auction residual. A
  large gap that loads on own and peer drift is the sign of endogenous transmission.
- **For us:** the weekend fade is a bet on the second term, the network-amplified noise that the reopen removes.

### 3. Who copies whom (Table 1, June 2026)
- **OKX's AAPL index weights:** Hyperliquid oracle 0.343, OKX perp 0.057, Binance index 0.171, vendor feeds (Pyth,
  Ondo, dxFeed) 0.429. The same weights apply to NVDA, TSLA and AMZN.
- **Bybit** excludes stale components and clamps. **Gate** mixes its stock token, the US price, and its own contract.
  **Binance** uses its index, funding, book and own contract. **Hyperliquid** uses the median of the validator
  oracle, the local book and external perps.
- **For us:** OKX's closed-window mark imports a third of Hyperliquid's oracle. A Hyperliquid weekend overshoot
  propagates, damped, into other venues' marks. This is a cross-venue channel the lab has not mapped.

### 4. Empirics (small samples, descriptive)
- **Deep-closed panel** (11 April .. 9 June 2026; four names; six venue series):
  - marks move 20-123 bp from the last cash close;
  - they track ES/NQ futures (R² up to 0.42; BTC placebo under 0.07);
  - cross-venue dispersion is wider than in the regular session, with a "Saturday variance floor";
  - the closed-window drift matched the cash open's sign in 156 of 192 series-reopens.
- **Reopen study** (five opens): venue moves track the matched cash move (median error 4.49 bp), against 28.68 bp
  for a wrong-name control.

## What I checked against our own record
- **The common component tracks live index futures, so it is anchored.** That is R464's null and the reason R530's
  balanced book drops the common move.
- **The idiosyncratic part carries the endogenous network noise.** That is what reverses at the reopen.
- **156 of 192 drifts got the open's sign right.** The weekend move is mostly informative, which matches the
  vendor-side slope of 0.83: the fade is paid by the overshoot fraction, not by the move.

## What it changes
- **R530's rationale gets an independent, formal source.** No change to the frozen lane.
- **A new candidate for the map: the oracle network echo.**
  - Venues whose closed-window marks import Hyperliquid's oracle with weight below 1 (OKX 0.343) move less than xyz
    over a weekend, and all snap to the cash open (Theorem 5).
  - A hedged weekend pair between xyz and a damped venue is R466's family (xyz against Lighter, INCONCLUSIVE, n 55,
    +50 bp, 84% hit), with a mechanism now named.
  - OKX Europe's stock perps are reachable from France (R442).
  - The cheapest decisive observation: the ratio of OKX's weekend move to xyz's on the same names.
