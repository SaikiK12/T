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
| Prediction scout (3 candidates: maker-reward subsidy, same-event cross-venue gap, Kalshi per-order fee rounding on longshots) | Polymarket's geoblock page, read by me: France is listed under "Regulatory-Restricted Jurisdictions (Close-Only on Frontend and API)", where "users can close existing positions but cannot open new ones". The scout also quotes an ANJ blocking order of 2026-07-16 (not re-read by me) | **Research only; about zero money value for the owner.** The cross-venue gap (arXiv 2601.01706, "2-4% on average", not read by me) is the best of the three as knowledge. It is parked until a reachable venue lists the same events. Kalshi lists France as restricted (scout, from the lab's card; unverified) |
| Supply scout (airdrop-cliff short; Bitwise 10 forced rebalance; points-period volume clock) | Not re-checked line by line: none moves money at its stated size. The R529 conflict it flags is already resolved (`room_20261125/label_caveats.md`: FINDINGS say FAIL, the registry row is stale). It also found that `data/unlocks/2026-10-20`, named in DATA_SOURCES, is absent in this checkout (R265's calendar), and that DefiLlama's emissions API is now paid (HTTP 402, not bypassed) | **All three are low** (the scout's P 10-15%, value low): an airdrop cliff is a weak payer, since recipients sell at claim; the Bitwise 87.5/86% trigger rarely binds; a volume clock is not a return. Kept in the scout's file, not in the register |
| Korea scout (FX-act registration clock 2026-12-03; BTC-level premium; Upbit/Bithumb delisting clock) | I recomputed the premium. BTC on Upbit against KRW-USDT × Binance is median −0.005% to +0.034% by year (846 days), which only says BTC and USDT are aligned inside Korea. **The capital-control premium sits in USDT itself:** USDT/KRW against the official USD/KRW rate (Yahoo KRW=X, 591 days) had a median of +1.37% (2024) and +1.43% (2025), 95th percentiles of 3.5-5.9%, **then −0.04% in 2026**. More than 2% on 24.5% of days | **Knowledge, little money value:** no KRW account, so a French owner can reach only the global-perp side. The 2026 collapse of the USDT premium is a fact the FX-act clock (K2) can be read against. **K1, the delisting clock** (a 30-day clearing period, then 30 days of withdrawals, quoted from Upbit's policy PDF by the scout and not re-read by me), is the one reachable candidate: a short on the global perp. It needs a notice history (an aggregator; check its terms first) |

## The ranking for deep work (value × probability ÷ cost; the register rows carry the detail)
1. **Q01, Variational's frozen weekend index.** It has recorded since 2026-11-25, Q01's event was defined in the
   ledger before its first weekend (F034), and it is read on 2026-11-29. Forward, cheap and owner-reachable (rule 8).
2. **Q20, venue halts before gaps.** This is the stake's main jump risk (Thorp). It is reading-heavy, so it goes to
   the room.
3. **K1, the Upbit/Bithumb delisting clock on coins with a global perp.** New and reachable. P about 0.2 (the
   related M060 was NULL).
4. **O7d, BTC Sunday options:** forward only, read in 2027. **O7c tripwire:** quarterly.
5. **Parked as knowledge:** the cross-venue prediction-market gap (France is close-only), the Korean USDT premium,
   and the Boros fixed-floating spread (R412).
- **Closed tonight with data:** L1 (funding against basis, no rent); the rates scout's candidate 1 (R412 already
  answers it).

## Corrections after the room's critic (`critic_triage.md`; checked by me where marked)
1. **L1's level depends on the bars.** The critic's independent run gives +1.77, −0.53, −1.72 and −0.30 %/yr by year
   and a mean of −0.19, against my −0.03.
   - Read it as **"about −0.2 to 0.0%/yr; positive in 1 of 4 years"**. The verdict (no rent, forecast 0) is unchanged.
   - "Arbitraged" is my reading of a spread near zero, not an observed arbitrage.
   - The test used Binance's clamp, not Hyperliquid's floor. Binance's realized BTC funding had a median of 6.55%
     and a 5th percentile of −2.13%.
2. **The Boros item is closed too cleanly.** R412 also shows the Hyperliquid lock at +2.07 points over the T-bill
   (`experiments/boroslock_v1/FINDINGS.md:51`). The fixed-floating spread (+0.73) carries no cost line, and the
   scout's floor-band split was not tested. **Status: largely answered, not closed.**
3. **The Korean USDT premium.** The 2026 near-zero median comes from one source (Yahoo KRW=X), which was not saved
   in `data/` and was not checked for a break.
   - The timing mismatch (Upbit candles at 00:00 UTC against Yahoo's close) is hours and zero-mean. It widens the
     bands but cannot create a 1.4-point shift.
   - Drop the first candle (2024-06-07, +7.69%).
   - Write "**a 2026 level near zero, one source, unchecked**", not "collapse".
4. **K1 is ranked too high.**
   - The family has a NULL (M060/R267) and a running forward lane (R268, a MEXC spot delisting short on notices).
   - No delisted Korean market is held.
   - The aggregator's terms are unchecked.
   - **K1 moves below O7d.**
5. **Claims used here and not verified by me:**
   - the FX act's 2026-12-03 date (statute not opened);
   - the Upbit policy quotes;
   - the ANJ order;
   - Kalshi's France restriction;
   - arXiv 2601.01706's "2-4%".
   - The Polymarket France page I did read.

**The ranking, corrected:**
1. Q01, Variational (read 2026-11-29).
2. Q20, venue halts.
3. O7d / O7c (forward).
4. K1, with R268 named as its sibling.
5. Parked: prediction markets (close-only in France), the Korean USDT premium (K2 watches it), Boros (largely answered).
