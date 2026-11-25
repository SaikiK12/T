# Breadth sweep 2026-11-25 (evening): what the scouts found, what I verified, and the ranking

- **Why this sweep.** The owner, 2026-11-25 23:13: "rechercher de manière efficace mais extensive… savoir se varier".
  The new rule 7 asks for one sweep a day in at least four families.
- **The scouts:** Korean venues, prediction markets, rates plumbing, supply and index plumbing.
- **My own breadth item the same hour:** L1, funding floor against dated-futures basis.
- Each scout's claims are verified here before they move the register.

## Done in this sweep
| Item | What was checked | Result |
|---|---|---|
| L1 (mine) | Binance USD-M funding against the next COIN-M quarterly's annualized basis, BTC/ETH 2023-26, held data, registered first (ef11e775) | **No rent.** BTC mean spread −0.03%/yr (1 of 4 years positive), ETH +0.73% (below the cost of two legs and four rolls). Funding itself averaged 3-5%/yr in 2025-26, so the "floor" is a clamp. Forecast P 0.40 resolved 0 |
| Rates scout, candidate 1 (Boros fixed against the settled floor) | `experiments/boroslock_v1/FINDINGS.md` (R412), read by me | **Already measured by R412.** On Hyperliquid, naked funding minus the Boros lock averaged +0.73 points a year (6.59% against 5.86%), with a 5th-95th range of −4.7 to +4.6. Not a rent after costs. The scout's live check (Boros mid 6.4-12.8% in October 2025 while the settlement printed the floor) fits R412's spread of outcomes |
| Rates scout, candidates 2-3 (Aave kink, Ethena reserve) | not yet | Candidate 2 needs a utilization series the lab does not hold. Candidate 3 needs negative-funding hours, which are rare (R488 is NULL on the related USDe flow) |
