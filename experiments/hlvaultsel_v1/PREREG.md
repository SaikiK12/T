# PREREG: hlvaultsel_v1 (R450). Hyperliquid user vaults picked by their past record

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R450
- **Method:** M507 (Hyperliquid user vaults picked by their past record, deposits only, net of the leader's share).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10; frozen 2026-11-11); FYI on issue #7.
- **Why now:**
  - Every France-reachable book tested on 2026-11-10 earns about the hurdle (R441-R445, R288). The protocol vaults
    HLP and LLP (R446) earned about +10.7%/yr in 2026, short the venue's tail.
  - Hyperliquid's user vaults take deposits from any wallet. The leader keeps a share of the profits (10% on the
    vaults read). "User vaults have a lock-up period of 1 day" (Hyperliquid docs, `hypercore/vaults/`
    `for-vault-depositors-legacy`).
  - The public list holds 9,478 vaults, 6,421 of them closed, so a rule can be read without survivorship.
  - The question: does a vault's steady past record predict its next month, net of the leader's share?
- **Book:** one, so one trial.
- **Gates:**
  - **Gate 0 (decides):** monthly formations 2024-01-31..2026-09-30, each held to the next month end. No vault's
    return has been read before this freeze, so gate 0 decides.
  - **Forward:** formations from 2026-11-30, read once after 12 held months.
- **Paper only.** Nothing here deposits, orders or moves money.

## What the author has seen
- The list's structure and counts: 9,478 vaults, 6,421 closed, 7 children of HLP. No APR or pnl summary was printed.
- Six vaults' `vaultDetails` structure: windows, point counts (35 to 97 `allTime` points) and spans (132 to 1,084
  days). One vault's fields: profit share 0.1, `alwaysCloseOnWithdraw` true.
- The recorder's smoke run on 20 vaults: counts only (4 of 20 reached $10k).
- General knowledge: leaderboards show high past returns, and many top vaults later lose. No figure was read.
- The gate-0 data commit's structure (2026-11-11 01:20 UTC): `last_run.json` (9,478 vaults, 9,471 fetched, 1,822
  kept with history, 7 children skipped, 0 failed) and the coverage check below. No return, APR or pnl was read.
- R452's result on Lighter (same score, mean over sd): it picked dormant pools. The activity condition below
  comes from that.

## Data
- **Source:** `.github/workflows/claude-hlvaults-recorder.yml` (weekly) on the data branch `claude/hl-vaults-data`,
  written by `scripts/record_hl_vaults.py`:
  - `index.csv`: every vault in the public stats list, closed ones included;
  - `meta.csv`: each vault's profit share and status as last fetched;
  - `hist/`: each vault's `allTime` account value and pnl, for vaults that ever reached $10k.
- **Gate-0 data commit:** `ed333fffd6707139f4c2564b15327d671750e6eb`
  - It is the first commit whose `meta.csv` covers every non-child vault in the list.
  - Gate 0 reads it and nothing else. The script refuses another commit.
- **Forward data:** the same branch at the read date.

## Rule
Constants are in `scripts/run_hlvaultsel.py`.
- **Formation:** at each month end t (end of the UTC day).
- **Eligible:** a normal vault (not HLP, not a child) at least 180 days old at t.
  - Its account value is at least $500k at its last `allTime` point at or before t.
- **Period return:** between consecutive `allTime` points, the pnl change over the capital at risk. That capital is
  the larger of the account value at the period's start and that value plus the period's net inflow (the account
  value change minus the pnl change). A deposit or withdrawal inside a period thus does not inflate its return. A
  period with no capital returns 0.
- **Signal:** the vault's period returns over the past 180 days. The window starts at the last point at or before
  t − 180 days and ends at the last point at or before t. The signal needs at least 6 periods, a pnl change in at
  least 80% of them, and a positive sum. Score: mean over sd.
  - The activity condition was added on 2026-11-11, before this freeze, after R452 (Lighter's pools, same score)
    found that mean over sd picks dormant pools: a rare small gain gives a tiny sd. No Hyperliquid vault's
    return was read.
- **Book:** the 10 vaults with the highest score, equal weight, a tenth of capital each. With fewer than 10
  candidates, an empty slot is held in cash and earns the hurdle (its excess is 0).
- **Held return:** the period returns chained from the last point at or before t to the last point at or before the
  next month end. A vault that closes keeps its return to closure; the slot then holds cash at 0 to the month end.
- **Leader's share:** the vault's own profit share on file (10% if missing) is taken from a positive held return.
- **Switching cost:** 10 bp of a slot's capital for each slot that changes vault, at 1x. The 2x and 3x reads multiply
  it.
- **Hurdle:** 4.0%/yr on capital, flat, over each month's days.
- **Statistic:** monthly net minus hurdle. Its annualized sum over the window's years, and its Newey-West t at lag 3
  (`lab.stats.newey_west_t`).

## Decision
1. **Gate 0:**
   - **EARNED** when all of these hold: 1x annualized excess at least +3.0 points, NW t at least 2.0, and 2x excess
     above 0. The forward read then runs.
   - Otherwise **NULL (stop)**.
2. **Forward, after 12 held months:** **CONFIRMED** if the 1x annualized excess is above 0, otherwise **NOT
   CONFIRMED**.
3. A CONFIRMED lane is paper evidence only. It admits nothing to real money. `lab.gate.go_real()` and the owner's own
   check decide, including the venue, each vault's deposit status and its tail.

## Reported, not deciding
- The equal-weight net return of every eligible vault (the same filters, no signal), by month and annualized.
- By year, the worst month, the maximum drawdown, picks and switches per month, and the leader's share in %/yr.
- Power: the monthly sd of the excess and the detectable excess (t 2.0, 80% power) over the window.

## Trials and reading
- One trial. The program total before this lane is 9,784,998 (after R452).
- Read against `registry.program_trials()`.

## Limits
- **Deposit status:** whether a vault took deposits at t is not on file; `allowDeposits` is today's. A picked vault
  that was closed to deposits could not have been entered.
- **Profit share:** today's value, applied monthly on gains. Hyperliquid's depositor page shows it charged on
  withdrawal against the deposit's own gain ("You withdraw 200 USDC (10%) less 10 USDC (10% profit share to the
  leader)"). A vault held through a loss month and then a gain month is therefore overcharged here, never
  undercharged.
- **Withdrawal slippage:** the same page says "There may be some slippage as you withdraw and open positions are
  closed". The 10 bp switching cost is an assumption; no fee on deposits or withdrawals is documented.
- **Resolution:** `allTime` holds about 100 points per vault, so an old vault's points are one to two weeks apart.
  Month ends use the last point at or before them.
- **Flows:** the capital at risk caps the bias from flows inside a period but does not remove it. A vault with
  large inflows has its return understated, and one with large outflows can have it slightly overstated.
- **Start lag:** a formation's held return starts at the last point at or before t, up to two weeks earlier. No
  information after that point enters the pick, but the held period is not the calendar month.
- **Vault tail:** a leader can lose a vault's capital in a day; one bad pick costs a tenth of the book.
- **Capacity:** $500k is the floor, so a $10k deposit is at most 2% of a vault.
- **Venue:** Hyperliquid is authorised nowhere; its terms were not read (403). Leaders are anonymous.
- **Jurisdiction:** not legal advice; the owner checks.

```inputs
67af4ce4f6e2f4d2f2c8b042721232b45f0dc18a054bf6c1572e593e2c484d73 scripts/run_hlvaultsel.py
e31d89516b8517bedebbe0990c92df047ecdb4beca4616ba365d9b610b2ed5ff tests/test_run_hlvaultsel.py
2e08010d1a9c6b7e8aa914010bca11eaacb3561d60059fc045d99bb75961963f scripts/record_hl_vaults.py
f1d1258247a5c3f88c797d1f5746d63555d6ea39cb373bafe156db7e7a58ecdf scripts/record_dex_vaults.py
127382b43bfd688b3d8fca8961492d998560098387351afdee1cd7ca005567c9 scripts/record_hl_daily.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
