# FINDINGS: hlvaultsel_v1 (R450), gate 0

**NULL (stop)**, by the frozen rule. The 1x book lost 23.2% a year, net. Its excess over the 4% hurdle is −27.2
points a year, with an NW t of −2.26: significantly below the hurdle, not just short of it.

**The main readings:**
- **Following Hyperliquid's best-looking user vaults lost money.** Picking the 10 steadiest vaults of the past 180
  days (mean over sd, at least $500k, active in at least 80% of periods) and holding them a month lost in 16 of 33
  months.
- **The losses are real blowups, not data artifacts.** In October 2025 (2025-09-30 formation), three picks lost
  over 90% (TAPTRADE −98%, Spitfire −93%, Stabilizer −91%). Their own pnl fell by $1.1-1.5M each, and two ended
  near $0. In October 2026, drkmttr lost $4.7M (−35%) and two others lost over half.
- **The steady record picked worse than chance in 2026.** Every eligible vault, equal weight, earned +8.2% a year in
  2026; the book lost 31% a year.
- **For the owner's question** (do HLP's competitors do better?): Hyperliquid's user vaults, as a class and as
  picked here, do worse than HLP. A deposit in HLP or LLP (R446) remains the better book among the vaults tested.

- **Frozen:** PREREG sha256 `a329f8cc…`, commit `4801da8`, before any vault's return was read.
- **Run:** `python scripts/run_hlvaultsel.py --data <data branch at ed333ff> --window gate0` on 2026-11-11. It
  checked the 9 pinned code files and the data commit `ed333fffd6707139f4c2564b15327d671750e6eb`. Output in
  `results/gate0/`: `months.csv` and `report.json`.
- **Inputs:** the data branch `claude/hl-vaults-data`, commit above (1,821 vaults with history read).

## Gate 0: formations 2024-01-31..2026-09-30, 33 held months
| Cost | Net, %/yr | Excess over 4%, pts | NW t (lag 3) |
|---|---|---|---|
| **1x** | **−23.21** | **−27.21** | **−2.26** |
| 2x | −23.44 | −27.44 | −2.28 |
| 3x | −23.68 | −27.68 | −2.29 |

- **Month by month:**
  - Worst month −35.2% (formation 2025-09-30, the 2025-10-10 crash).
  - The maximum drawdown is −64.2% (sum of monthly nets).
  - The monthly sd of the excess is 7.8%.
- **Picks:** 5.1 slots filled on average, 1.7 new picks a month. Before 2024-12 at most one vault was eligible, so the
  book was mostly cash in 2024.
- **The leader's share** took 3.9 points a year.
- **Power:** at this sd, an excess the test detects (t 2.0, 80% power) is about 46 points a year. The test is weak
  for small gains, but the point estimate is far below 0.

**By year (1x net, diagnostic):**
| Formations in | Book, %/yr | Every eligible vault, equal weight, %/yr |
|---|---|---|
| 2024 | −13.0 | −149.7 (one vault in most months) |
| 2025 | −27.5 | −63.8 |
| 2026 (9 months) | −31.1 | +8.2 |
| Whole window | −23.2 | −75.6 |

## What the loss rests on (diagnostics, read after the freeze)
- **Two months:** without the 2025-09-30 formation the book is −10.8% a year; without that one and 2026-09-30 it is
  −2.8%, still below the hurdle.
- **2025-09-30 picks** (held return, account value at t → at the month end, pnl change):
  - TAPTRADE −98% ($1.33M → $0.02M, pnl −$1.13M), Spitfire −93% ($1.57M → $0, −$1.12M), Stabilizer −91%
    ($2.08M → $0, −$1.45M), Hyperrr −60%, Martyrbit −38%.
  - The best two, Growi HF +21% and Systemic Strategies +18%, could not offset them.
- **2026-09-30 picks:** "Long LINK Short XR…" −58%, Brob −56%, drkmttr −35% ($13.5M → $8.3M, pnl −$4.7M),
  Hyperliquidity Trader −31%, BredoStrategy −27%. One pick gained (+19%).
- A steady 180-day record fits a short-volatility profile: small steady gains, then one large loss, here inside a
  single leader's account.

## Program
- One trial. Program total 9,784,999 (`registry.program_trials()`).

## Limits
- **Deposit status at t** is not on file. Some picks may have been closed to deposits; that does not change the sign
  of the loss.
- **Profit share:** today's value, applied monthly on gains. That overcharges a vault that lost first, by at most the
  3.9 points a year the share took.
- **Resolution:** `allTime` points are one to two weeks apart for old vaults, so a held month can start up to two
  weeks before t.
- **Flows:** the capital at risk caps flow bias but does not remove it. The large losses above are pnl changes in
  dollars, so they are not flow artifacts.
- **Survivorship:** none expected. The list holds closed vaults, and vaults that never reached $10k cannot be
  eligible at $500k.
