# FINDINGS: xfund_lt_v1 (R288). R275's carry book replicates on Lighter in 5 of 6 venue sets, but the Lighter sets earn 3.5-6.2%/yr, near the T-bill hurdle and far below the KuCoin sets

**Verdict: CONFIRMED (venue replication, gate 0): 5 of 6 sets replicate.**
- **Trials:** 6, gate 0 in time. Lighter is new evidence in venues only: the other venues' years were read by R275
  and R277.
- **Read:** frozen PREREG 80e6023d, run 2026-10-22 02:27 UTC with `qx spread`. The 13 inputs matched their frozen
  hashes, and the symbol table rebuilt byte for byte.
- **Audit:** `scripts/audit_xfund_lt.py` → `results/audit.json`. The PREREG set out these checks before the
  result. The script that runs them was written after the run, and all checks pass (below).
- **Order:** the PREREG was frozen at 02:26:54 UTC (`PREREG.sha256`), and the run read it at the same second
  (`qx_run.log`). The draft was committed in f06682c; the frozen PREREG, run and result land in one commit.
- **Program trials** after this round: 9,478,568 (`registry.program_trials()`).
- **Paper only.** No Lighter account exists, and nothing here places an order.

## What was tested
- **The book:** R275's best carry book, unchanged:
  - lookback 14 days, entry when the 14-day funding spread is at least 5%/yr, exit below half that, 20 slots;
  - each pair is long the venue that pays less funding and short the one that pays more.
- **The pairing:** Lighter (0/0 fees) against each of six venues.
- **Costs per leg per side:** 5.5 / 11 / 16.5 bp at 1x / 2x / 3x. That is the mean of 7 bp on the other venue and
  4 bp on Lighter (no fee, plus the median cost of a $10k market order in one hour of Lighter books).
- **Window:** from 2025-02-07 (Lighter's history plus the 14-day lookback; MEXC's from 2025-05-12) to 2026-09-30.
  That is about 600 days, against R275's 2,000.

## Result

| Set | From | Days | 1x %/yr | 2x | 3x | NW t | Halves bp/day | Max DD | Top-10-day share | Funding share | Trades | Replicates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mexc+lighter | 2025-05-12 | 507 | **+6.20** | +5.00 | +3.79 | 6.77 | +1.94 / +1.46 | −0.2% | 26% | 0.94 | 305 | **yes** |
| kucoin+lighter | 2025-02-07 | 601 | +5.57 | +4.20 | +2.84 | 6.71 | +1.68 / +1.37 | −0.5% | 28% | 1.04 | 408 | **yes** |
| gate+lighter | 2025-02-07 | 601 | +4.78 | +3.57 | +2.35 | 7.62 | +1.65 / +0.97 | −0.4% | 24% | 1.04 | 364 | **yes** |
| binance+lighter | 2025-02-07 | 601 | +4.53 | +3.32 | +2.11 | 6.55 | +1.45 / +1.04 | −0.9% | 29% | 1.03 | 363 | **yes** |
| hyperliquid+lighter | 2025-02-07 | 601 | +3.53 | +2.01 | +0.49 | 7.34 | +1.01 / +0.93 | −0.3% | 32% | 0.97 | 455 | **yes** |
| dydx+lighter | 2025-02-07 | 601 | +2.65 | +1.96 | +1.27 | 1.11 | +1.11 / +0.35 | −9.0% | 269% | 0.90 | 207 | no (NW t) |

- **The rule** (frozen): a set replicates when NW t > 2.64, both halves are above 0 and the 2x net is above 0.
  Five sets meet all three, so the verdict is CONFIRMED (at least 4 of 6).
- **The engine's own family gates** are reported, not decided on:
  - reality check over the 6 books: null 95th percentile t 2.00, p 0.0005 for the five;
  - RECENT, TRIM, COST2X and HALVES pass for the five.
  - The engine's HURDLE (4.13%/yr) fails hyperliquid+lighter, so its `pass` column lists 4 survivors.
- **The books are near-pure funding:**
  - funding is 0.94-1.04 of the net gross;
  - all books hold about 20 pairs, at 30-47 eligible coins a day;
  - each has 1 forced exit (a coin delisted on one venue).
- **The books are mostly short Lighter.** Lighter is the long leg in only 37-51% of trades. Lighter's longs paid
  more than Binance's in 2025 (BTC: 8.9% against 5.1% over the year).

### By year (net %/yr on capital, 1x / 2x / 3x)

| Set | 2025 | 2026 (to Sep) |
|---|---|---|
| mexc+lighter | +7.3 / +6.1 / +4.9 (from May) | +5.3 / +4.0 / +2.8 |
| kucoin+lighter | +6.0 / +4.6 / +3.3 | +5.1 / +3.7 / +2.3 |
| gate+lighter | +6.2 / +5.0 / +3.8 | +3.1 / +1.9 / +0.6 |
| binance+lighter | +5.4 / +4.2 / +3.1 | +3.6 / +2.3 / +1.0 |
| hyperliquid+lighter | +3.8 / +2.2 / +0.7 | +3.2 / +1.7 / +0.3 |
| dydx+lighter | +3.7 / +2.7 / +1.8 | +1.4 / +1.1 / +0.7 |

- **Every set shrinks from 2025 to 2026.** The spread between Lighter and the other venues is narrowing.

### Against the lab's other carry books, same years
- **R277's KuCoin sets** (gate+kucoin, binance+kucoin) earned +20 to +24%/yr at 1x in 2025-26. That is 3-4 times
  any Lighter set.
- **R275's gate+hyperliquid** earned +5.0 (2025) and +8.4 (2026) at 1x.
- **So Lighter is a working carry venue, not the best one.** Its zero fee does not make up for a narrower funding
  spread.

### The fee's share
At R275's uniform 7 / 14 / 21 bp per leg (from the same daily file, `results/audit.json`):

| Set | 1x %/yr | 2x | 3x | NW t at 1x / 2x / 3x |
|---|---|---|---|---|
| mexc+lighter | +5.88 | +4.34 | +2.80 | 6.37 / 4.53 / 2.79 |
| kucoin+lighter | +5.19 | +3.46 | +1.73 | 6.20 / 3.91 / 1.83 |
| gate+lighter | +4.45 | +2.90 | +1.36 | 7.03 / 4.36 / 1.90 |
| binance+lighter | +4.20 | +2.66 | +1.11 | 5.97 / 3.48 / 1.33 |
| hyperliquid+lighter | +3.12 | +1.18 | −0.75 | 6.30 / 2.07 / −1.14 |
| dydx+lighter | +2.46 | +1.58 | +0.70 | 1.03 / 0.66 / 0.29 |

- **Lighter's zero fee is worth about 0.3-0.4%/yr** at 1x on these books (5.5 bp against 7 bp per leg).
- At R275's 2x cost (14 bp per leg), every set except dydx+lighter still nets above 0.
- At 3x, hyperliquid+lighter turns negative.

## Audit (committed before the result; all pass)
- **Sign and units: pass.** Median BTC funding per settlement in 2025:

  | Venue | Median | Settlements | Annualized |
  |---|---|---|---|
  | Lighter | 1.20e-5 per hour | 8,358 | 10.5%/yr |
  | Binance | 4.83e-5 per 8 h | 1,095 | 5.3%/yr |

  - Same sign, ratio 2.0 (the void bar is 10).
  - Hyperliquid's hourly median (1.25e-5) is close to Lighter's, which fits two hourly venues with the same base rate.
- **Funding recomputed from the raw files: pass.** 12 trades, 2 per set (seed 288), all equal the engine's to
  5e-9. The engine writes 8 decimals, so 5e-9 is its rounding.
  - One sampled trade (gate+lighter SOXL) was still open at the end. Its funding runs to the book's last daily row,
    as the engine books it.
  - The audit script's first draft missed that and showed a 0.003 gap. The fix is in the committed script.
- **Concentration: pass.**
  - The five replicating sets trade 92-125 coins.
  - Their top 5 coins carry 21-25% of the gross, and their top 10 carry 34-39%.
  - dydx+lighter (34 coins) has a top-5 share of 144%: its result is a few coins and the crash days.
- **The 2025-10-10 crash (post hoc, decides nothing):**

  | Set | Net on 10-12 Oct | NW t with them | NW t without them |
  |---|---|---|---|
  | dydx+lighter | −8.9% and +9.1% | 1.11 | 5.16 |
  | the other five | between −0.10% and +0.12% | | moves by at most 0.1 |

  - dydx+lighter's crash days are the engine's known flaw: one venue's bad hourly print books a round trip.
  - Without the crash days dydx+lighter's t would clear the bar, but its net is still 2.6%/yr.

## What this does and does not show
**It shows:**
- R275's carry rule is not specific to its venues: it earns a positive net on five more venue pairs over 20
  months;
- the net is positive in both halves and survives R275's own 2x cost;
- the funding accounting checks out against the raw files;
- the result is spread over about 100 coins.

**It does not show:**
- **An unseen-time pass (gate 1).** The years were read on the other venues by R275 and R277. Lighter's own series
  is new.
- **Real fills.**
  - Lighter's cost comes from one hour of books.
  - Closing two legs at the 00:00 close on two venues at once is assumed.
- **That it pays.**
  - At 1x on total capital the best set nets 6.2%/yr, about 2 points over the 4.13% hurdle.
  - Leverage would scale it, with liquidation risk that R280 measured for the other carry books but not for these.
- **That Lighter is safe.** It is an on-chain venue with a bridge, and that risk is not priced. The book is mostly
  short Lighter, so a Lighter failure would hit the short legs' collateral.
- **Survivorship.** Lighter's contract list is from 2026-10-21, so markets it removed may be missing.

## Costs
- **This lane's costs:** 5.5 / 11 / 16.5 bp per leg per side in the main table.
- **R275's costs:** 7 / 14 / 21 bp in the fee table.
- **MEXC API taker:** about 8.7 bp with spread, which puts mexc+lighter at about 6.4 bp per leg. That falls between
  the 1x and 2x columns.

## Read against the program
- **The bar:** NW t > 2.64 is Bonferroni over this lane's 6 sets, and the lane replicates one book R275 picked out
  of 560.
- **R275's own reality check** covered its family (null p95 t 4.27). The five Lighter sets clear 4.27 too
  (NW t 6.55-7.62).
- **Against 9.48M program trials,** a two-sided Bonferroni bar is t 5.84. All five sets clear it on NW t
  (6.55-7.62). That bar treats every program trial as a search for this book, which they were not.
- **Venue replication is what the lab can do at gate 0.** Unseen time comes only from the forward lanes.

## Next
- **Forward paper lane for mexc+lighter (new id).** The PREREG allows it, and it is the set closest to the owner's
  MEXC account. It needs Lighter's daily funding and candles in `lab/carrylane.py` (data plumbing) and a frozen
  PREREG before its first on-time day.
- **Not changed:** R278 and R279 keep their frozen books.
- **M059** (cross-venue funding carry) stays TESTED. Its best book now has two venue replications (R277 KuCoin and
  R288 Lighter), and still no gate-1 pass.
- **For the owner:** using Lighter needs an on-chain wallet and a bridge. That is an account and a key, so it is
  the owner's call (AGENTS.md rule 5). Until then the lane is paper only.
