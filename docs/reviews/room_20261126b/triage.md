# Breadth sweep 2026-11-26: four new families (rule 7's daily sweep)

- **Families, all different from 11-25's:**
  - liquidation engines and vaults;
  - stablecoin plumbing;
  - listing clocks (pre-launch perps);
  - equity events on 24/7 perps.
- **Not repeated, because already tested:** the weekend fade on xyz commodity, index and FX perps is R464, NULL
  (D1 +2.7 bp, p 0.86).

| Family | Candidates (scout's P) | What I checked | Verdict for the register |
|---|---|---|---|
| Stablecoins (`scout_stablecoin.md`) | 1. a USDT/EUR discount after the EEA's forced USDT sales (0.05); 2. USDe below $1 under negative funding (0.04); 3. USDH pinned to par during its sunset (0.10) | Lab rows: R460 (USDT mints, NULL), R488 (USDe flow, NULL), R483 (sUSDe benchmark); sUSDe is closed to EEA residents (M481). The scout quotes Binance's EEA delisting (2025-03-31) and MiCA Art. 49(6) (no redemption fee); not re-read by me | **Parked.** The forcing dates have passed, USDe redemption is for whitelisted minters only, and a French retail client cannot trade USDT/EUR in the EEA. Nothing reachable at more than 10% |
