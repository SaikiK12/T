# FINDINGS: locked_carry_v1 (R335), the guarantee engine on BTC and ETH

**Answer: USEFUL (registry DATA_PASS).** A coin-margined cash-and-carry held to expiry, entered only when its locked
yield beat the 3-month T-bill by 3%/yr, earned **9.47%/yr on BTC against 3.39%/yr for the T-bill**, 2021-01..2026-09.
Its excess over the T-bill was +6.08 / +5.58 / +5.08 %/yr at 1x / 2x / 3x costs, positive in 5 of 6 years.

No lock earned less than the T-bill actually paid over its life, at any cost level. Each lock's return was fixed the
hour it was entered; nothing here is a forecast.

The catch is that the offer comes and goes:
- **Rich:** 2021 and 2024.
- **Thin:** 2022, 2023 and 2025.
- **2026 to date:** absent. The engine has been in cash all year, because BTC's best offer never reached 3% over the
  T-bill.

**Lane details**
- **Registry row:** R335, 6 trials (2 coins × 3 hurdles). PREREG sha256 `3ec2a7f3…16b6`, frozen and pushed in `b531c69`
  before the run.
- **Run:** 2026-10-26 21:07 UTC. All 60 inputs matched their frozen hashes.
- **Reproduce:** `python scripts/run_locked_carry.py --run` writes `results/summary.json`, `results/locks.csv` and
  `results/calendar.csv`. The run log is `run.log`.
- **Gate 0, on seen data.** R301 read these COIN-M hours. No 2020 row was loaded: the loader filters at read and raises
  otherwise.

## What is locked, and what is not
**The equation.** Hold B coins bought at S0, then short Q = B·F0 dollars of the coin's inverse quarterly at F0. At
expiry the account holds B + Q·(1/F_T − 1/F0) = B·F0/F_T coins, worth **B·F0 dollars for every settlement price
F_T**. The equity always equals the short's notional, so at 1x the short cannot be liquidated.

| Locked return to expiry | Locked yield | Lock when |
|---|---|---|
| F0/S0 − 1 − costs | × 365/τ | yield − T-bill ≥ hurdle |

**Between entry and expiry,** the account is marked at B·F0·S_t/F_t. If the basis widens, it shows a temporary loss,
which converges back by expiry. This lane did not measure that path.

## The engine against the T-bill, 2021-01..2026-09 (Binance spot, USDT at one dollar)
The T-bill alone returned 3.39%/yr.

| Coin | Hurdle | Locks | Time locked | Return 1x | Excess 1x | Excess 2x | Excess 3x | Years > 0 at 2x | Locks below the T-bill paid, 1x/2x/3x |
|---|---|---|---|---|---|---|---|---|---|
| **BTC** | **3%** | **11** | **68%** | **9.47%** | **+6.08** | **+5.58** | **+5.08** | **5 of 6** | **0 / 0 / 0** |
| BTC | 0% | 15 | 95% | 8.84% | +5.45 | +4.79 | +4.14 | 4 of 6 | 2 / 6 / 6 |
| BTC | 6% | 8 | 52% | 8.89% | +5.50 | +5.13 | +4.77 | 5 of 6 | 0 / 0 / 0 |
| ETH | 3% | 10 | 58% | 8.00% | +4.61 | +4.15 | +3.70 | 5 of 6 | 0 / 1 / 1 |
| ETH | 0% | 13 | 83% | 7.46% | +4.08 | +3.49 | +2.90 | 5 of 6 | 2 / 5 / 5 |
| ETH | 6% | 8 | 46% | 7.71% | +4.32 | +3.96 | +3.60 | 5 of 6 | 0 / 0 / 0 |

- All six rules beat the T-bill at 3x costs, by +2.9 to +5.1%/yr.
- Excess is in %/yr. The 1x round trip is 25 bp: spot taker 10 bp each way plus futures taker 5 bp.
- A hurdle of 0 locks thin offers that later trail the T-bill when rates rise, as in 2022 and 2023. The 3% and 6%
  hurdles avoid that.

**By year, primary (BTC, 3% hurdle), excess over the T-bill in %:**

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to Sep) |
|---|---|---|---|---|---|---|
| 1x | +12.59 | +4.01 | +1.82 | +10.66 | +6.22 | 0.00 (no lock) |
| 2x | +11.78 | +3.76 | +1.28 | +9.83 | +5.70 | 0.00 |
| 3x | +10.97 | +3.50 | +0.75 | +9.01 | +5.18 | 0.00 |

2022 is positive because a lock taken on 2021-12-31 (+8.84%/yr over the T-bill, 175 days) ran through the bear market.

## The offer on each hour (BTC; ETH is close)
The best locked yield over the T-bill at 1x costs, at each bar close:

| Year | Mean gross basis, %/yr | Median excess | Hours ≥ 3% | ≥ 6% | ≥ 10% |
|---|---|---|---|---|---|
| 2021 | 16.97 | +11.40 | 98.5% | 89.2% | 55.1% |
| 2022 | 2.61 | −0.20 | 18.8% | 4.7% | 0% |
| 2023 | 6.17 | −0.52 | 13.9% | 3.1% | 0.9% |
| 2024 | 13.58 | +5.71 | 81.1% | 47.5% | 20.2% |
| 2025 | 7.29 | +1.94 | 25.8% | 9.6% | 0.4% |
| 2026 to Sep | 3.40 | −1.15 | 0% | 0% | 0% |

The offer follows leverage demand, as R301's basis by year and funding do. It was richest in the 2021 and 2024 rallies.

## The 11 BTC locks (3% hurdle)

| Entry (UTC) | Contract | Days | Locked gross | T-bill | Excess, %/yr |
|---|---|---|---|---|---|
| 2021-01-01 01:00 | BTCUSD_210326 | 84 | 3.76% | 0.08% | +15.14 |
| 2021-03-26 09:00 | BTCUSD_210625 | 91 | 5.65% | 0.02% | +21.65 |
| 2021-06-25 09:00 | BTCUSD_211231 | 189 | 3.47% | 0.05% | +6.17 |
| 2021-12-31 09:00 | BTCUSD_220624 | 175 | 4.51% | 0.05% | +8.84 |
| 2023-02-27 15:00 | BTCUSD_230630 | 123 | 2.93% | 4.86% | +3.12 |
| 2023-11-01 21:00 | BTCUSD_231229 | 57 | 1.78% | 5.60% | +4.13 |
| 2023-12-29 09:00 | BTCUSD_240329 | 91 | 4.02% | 5.44% | +9.69 |
| 2024-03-29 09:00 | BTCUSD_240628 | 91 | 6.39% | 5.45% | +19.18 |
| 2024-06-28 09:00 | BTCUSD_241227 | 182 | 5.37% | 5.50% | +4.78 |
| 2024-12-27 09:00 | BTCUSD_250627 | 182 | 7.00% | 4.40% | +9.13 |
| 2025-07-13 21:00 | BTCUSD_251226 | 165 | 3.61% | 4.41% | +3.00 |

The engine re-locked within an hour of most expiries in the rich years, which is a few orders a quarter: manual web
is enough.

## Robustness
- **Dollar spot (Coinbase) instead of Binance USDT spot:** BTC at the 3% hurdle earns +6.04 / +5.53 / +5.03, against
  +6.08 / +5.58 / +5.08. ETH earns +4.50 / +4.09 / +3.69.
- **USDT against the dollar:** 0.9984 to 1.0017 at the 1st and 99th percentiles (47,408 Coinbase hours). Taking USDT
  at par moves a lock by at most about 0.2%.
- **Thin bars:** futures bars under 10 trades are dropped. They are under 6% of each contract's hours.

## Reading against the program
- **Trials:** program trials go from 9,478,976 to 9,478,982 with R335's 6.
- **Selection noise:** a locked return leaves no noise to mine, because each lock's result was set at entry. All six
  rules land within 3 points of each other, and all beat the T-bill at 3x.
- **The real risk is not overfitting.** The offer is a property of past markets: speculators paying for leverage in
  2021 and 2024. It may not come back, and in 2026 it has not.
- **Consistency:** R301 found +12.6% (2021) and +9.8% (2024) mean basis across its coins. Codex's R328 found a small
  offer today.

## Not guaranteed, and not measured here
- **Venue default or a withdrawal freeze.** FTX in 2022 is the reference. Splitting locks across venues (Binance, OKX,
  Deribit, Bybit) is the usual answer.
- **Auto-deleveraging.** In a crash a venue can close profitable shorts. A 1x short ranks low in that queue but is not
  exempt, and if it is closed the coins are unhedged until shorted again.
- **The mark-to-market path** between entry and expiry, as described above.
- **Costs and access:**
  - fees above the taker assumption, the account's tier, and maker fills that would cost less;
  - the settlement index against the spot sale after expiry;
  - access by country.
- **Untested refinements:** early exits when the basis collapses, rolls before expiry, and altcoin quarterlies.

## What this changes
**This is the lab's first result whose payoff does not depend on a forecast.** It answers the owner's request for
something that guarantees a result. The guarantee covers the locked dollar amount at expiry, net of costs, while the
venue stays solvent. It does not guarantee that the offer will be rich when you look.

**Proposed, not started (the owner decides):**
1. **A live offer board:** an hourly record of the locked excess on BTC and ETH quarterlies from public quotes on
   Binance, OKX, Deribit and Bybit. It alerts when a lock beats the T-bill by 3%/yr at 1x costs.
2. **A paper lock ticket** when the alert fires, frozen at entry and checked against the settlement, to prove the
   mechanics.
3. **A real lock** only after that check, placed by the owner, small, through `lab.gate.go_real()`.
