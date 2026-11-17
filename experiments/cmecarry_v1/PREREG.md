# PREREG: cmecarry_v1 (R501). CME bitcoin futures against the Binance perp: funding versus basis, 2021-05..2026-09

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R501
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_cmecarry.py` is the only writer of `experiments/cmecarry_v1/results/` and of the git-ignored
    `data/databento/cmecarry/`.
- **Date registered (UTC):** 2026-11-17

**Methods:** M548 (new: dated-future basis on a regulated venue against perp funding, same coin). Carry family; the
CME leg is new to the lab. R370 is the only earlier lane with CME data (EIA ticks).
- **Paper only:** it reads public and metered historical data; nothing in the code can place an order.

## Question
The owner asked on 2026-11-17 for lanes on bigger markets with long recorded histories, "with all their specifics".
Our one strong result is perp funding carry between crypto venues. The same idea with a CME future as one leg:

- long the CME future and short the Binance perp earns the perp's funding and pays the future's basis;
- the reverse earns the basis and pays the funding.

Each CME settlement day the signal is **s = f7 − b** (both %/yr):
- f7 = Binance funding over the last 7 days, annualized;
- b = (F / P − 1) × 365 / τ for the held future (F its settlement, P the perp at the same minute, τ days to its final
  settlement).

At $10k, the only CME contract that fits is the micro (MBT, 0.1 BTC, about $8-10k at today's prices). After
MBT's fees, spreads, rolls and calendar, is this book above R275's 4.13%/yr hurdle, 2021-05-03..2026-09-30?

## What the author has seen
- **No CME price, basis or settlement inside the window was read before this freeze.**
- **Format samples outside the window** (read for column names and flags only):
  - BTC.c.0/c.1 statistics for 2019-06-03..04: settlements are stat_type 3, preliminary (flag 2) at 15:00 Chicago
    and final (flag 3) after midnight UTC, with `ts_ref` the trading day;
  - MBT.c.0/c.1 bbo-1m for 5 minutes of 2026-10-14: one-tick ($5) front spread, $35 second-month spread.
- **Web, secondary sources (2026-11-17), not checked against data:**
  - the CME basis was typically 5-15%/yr, with 25-50% peaks in 2021 and about 3% by mid-2026 (Glassnode, via
    crypto press);
  - Binance BTC funding was 11.9 / 5.1 / 3.1%/yr in 2024 / 2025 / 2026 to date (room 2 agent, Binance archive);
  - He, Manela, Ross and von Wachter (arXiv 2212.06888) report a perp-versus-spot funding Sharpe of 1.8 for BTC;
  - a preliminary AEA 2026 paper finds quarterly-future basis drawdowns about 3 times those of perp strategies.
- **Binance data** (`data/klines_1h`, `data/fundingRate`, BTC and ETH) were used by earlier lanes. Their file
  spans were read: 2020-01-01..2026-09-30.

## Data
| Input | Source | Used |
|---|---|---|
| CME settlements | Databento GLBX.MDP3 `statistics` (stat_type 3), BTC.c.0/c.1 from 2020-01-01 and ETH.c.0/c.1 from 2021-02-01, to 2026-10-01 | the last publication for each contract and day |
| CME top of book | Databento `bbo-1m`, MBT.c.0/c.1 (from 2021-05) and MET.c.0/c.1 (from 2021-12): the hour before settlement on each month's second Wednesday | median half-spread per month and contract rank, when at least 30 of 60 minutes have both sides |
| Perp price | Binance USDT-M 1h klines (BTCUSDT, ETHUSDT): the close at the CME settlement minute | P |
| Perp funding | Binance funding history (BTCUSDT, ETHUSDT) | f7 and the funding paid or earned |

- **Spend cap.** Every pull is quoted first. Caps: $0.20 per statistics request, $0.02 per bbo-1m hour. Quoted
  total is about $0.25 for the statistics and under $0.20 for the hours. The Databento spend before this lane was
  $0.6756.
- **No look-ahead in the contract calendar.** Expiries come from the contract rule, not from the data. The data's
  roll dates are only checked against the rule; mismatches are reported.

### Frozen inputs
| File | sha256 | After the freeze |
|---|---|---|
| `scripts/run_cmecarry.py` | 15491d1bfad4c4d03e6631712c6a48680665d9d94efe136c64085fe1cfdd02e8 | fixed; `run` refuses to start if any row here changed |
| `scripts/fetch_databento.py` | b2a03bdcbcd64412c83eec66751ccbbecc3ab3b3bd34a273f1847a0aebea95b2 | fixed |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 | fixed (Newey-West t) |
| `data/klines_1h/BTCUSDT.parquet` | ee2577fa45bdbb6b8582ab86c63958bf53717db638ae2fe4a76d32000f45cb3b | fixed (git-ignored data) |
| `data/fundingRate/BTCUSDT.parquet` | b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3 | fixed (git-ignored data) |
| `data/klines_1h/ETHUSDT.parquet` | 071f96b6f779a6a69a08610ccf21e14905466a9941b14f3bcbdaaf192409fbb5 | fixed (git-ignored data) |
| `data/fundingRate/ETHUSDT.parquet` | 3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89 | fixed (git-ignored data) |

The Databento files are fetched after the freeze. Their names, quotes and sha256 are in
`data/databento/cmecarry/manifest.csv`, copied into FINDINGS.

## CME specifics in the rule
| Specific | How it enters |
|---|---|
| Daily settlement at 15:00 Chicago | decision and marks at that minute: 20:00 UTC in US summer time, 21:00 UTC in winter |
| Monthly contracts, last Friday of the month (preceding business day on a holiday), final settlement 16:00 London | τ from that rule; hold the front month while τ ≥ 14 days, else the second month |
| Roll | a held position switching contract pays two CME sides (close the old, open the new) |
| Contract sizes | MBT 0.1 BTC, MET 0.1 ETH; BTC 5 and ETH 50 (big contracts, reported only) |
| Fees per contract per side (exchange + clearing + NFA + a retail commission) | MBT $2.50, MET $0.60, big contracts $7.00. In bp: fee / (units × F) × 1e4, so cost falls as price rises |
| Tick | MBT $5 per BTC, MET $0.50 per ETH; one tick is the half-spread when the month is unmeasured |
| Product dates | MBT from 2021-05-03, MET from 2021-12-06; earlier windows use the big contract, reported only |
| Weekend closure until 2026-05-29 | no settlement means no decision; positions are carried and marked at the next settlement |
| Margin | not modeled. The return is per dollar of one leg's notional, read as return on capital equal to that notional (CME margin is about 20-30% of notional, the perp leg needs its own) |

Binance perp side: taker 5 bp plus 0.5 bp of book, per side.

## Rule
1. **Days.** CME settlement days with both c.0 and c.1 settled and a Binance close at the settlement minute.
2. **Held contract.** c.0 if its τ ≥ 14 days, else c.1.
3. **Signal.** s = f7 − b, as defined above.
4. **Position** (hysteresis):
   - +1 (long future, short perp) when s ≥ 10;
   - −1 (short future, long perp) when s ≤ −10;
   - back to 0 when |s| < 5 on the held side.
5. **Return from day D to the next settlement day.**
   - Gross = w × [(F′/F − 1) − (P′/P − 1) + Σ funding rates paid in between].
   - F′ is the same contract's next settlement, never another contract's.
6. **Costs on day D.**
   - CME: sides traded × (fee bp + half-spread bp).
   - Binance: sides traded × 5.5 bp.
   - A position open at the window's end pays its closing sides.
7. **Book.** One unit of notional per leg. %/yr = Σ net / years × 100, years = calendar span / 365.25.
   Newey-West t on the per-interval nets, lag 10.

## Verdict (primary: BTC, MBT costs, 2021-05-03..2026-09-30, 1x costs)
- **CARRY_PASS:** net ≥ 4.13%/yr and Newey-West t ≥ 2.0.
- **CARRY_WEAK:** net above 0, not PASS.
- **CARRY_NULL:** net 0 or below.

**Cost sensitivity.** The same at 2x and 3x every cost (fees, spreads, Binance).

**Also reported, never chosen among:**
- every year, and 2024-01..2026-09 alone, with mean f7 and mean b by year;
- ETH at MET costs (2021-12-06..2026-09-30) and a BTC/ETH half-and-half book;
- the big contracts: BTC 2020-01-08..2021-04-30 and ETH 2021-02-15..2021-12-03 (before the micros), and BTC and ETH in
  the primary windows at big-contract costs;
- thresholds 5/2.5, 20/10 and 0/0 (always in the sign of s);
- trades, rolls, share of days in position, share long-future, mean CME cost in bp, share of days with a measured
  spread;
- the expiry rule's mismatches against the data's roll dates.

## Null and multiplicity
- **No placebo null.** Like R275's carry books, the book is read against the T-bill hurdle with a Newey-West t.
  - The threshold variants are reported, never chosen.
  - Registry trials: 1.
- **Program trials so far: 9,785,313.** A PASS is read against them: this is a single textbook rule with a published
  prior, not a selected hit. It still earns only a forward paper lane, not money.
- **Power, stated before the read.**
  - Guess: the daily net of a basis-versus-perp book has 5-8%/yr volatility.
  - With a true net of 5%/yr over 5.4 years, t ≈ 5 / (6.5 / √5.4) ≈ 1.8: about a 40% chance of t ≥ 2.
  - A true 8%/yr gives t ≈ 2.9.
  - So a WEAK verdict at a positive net is weak evidence either way. A NULL at 1x is informative.

## Evidence lineage
- **Parents:**
  - R275, R437 (cross-venue perp carry, the family);
  - R301 (dated-futures basis cross-section on crypto venues);
  - R370 (CME data plumbing);
  - room 2 (2026-11-17, the owner's request).
- **One decision this feeds:** whether a CME-leg carry is worth a forward paper lane and a broker check for the owner
  (CME through a retail broker from France is not established).
- **Fresh data:** CME settlements and books never read by the lab.
- **docs/GATES.md** sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. This is gate 1
  on history.

## Not checked before the freeze
- **Fees.** The exact fees an owner in France would pay: broker, exchange tier, non-US clearing surcharge.
- **Margin and weekends.** CME margin calls on the futures leg while the perp leg is on another venue; weekend gaps
  before 2026-05-29.
- **Settlement versus fill.** Whether settlement prices could be traded at settlement: TAS availability on MBT is
  unverified.
- **Funding rule changes.** Binance funding interval changes (4h or 1h for some coins); the rates are summed as paid.
