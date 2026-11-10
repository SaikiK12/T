# PREREG: dexvault_v1 (R446). Deposits in two public liquidity vaults: Hyperliquid's HLP and Lighter's LLP

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R446
- **Method:** M505 (a passive deposit in a perp DEX's public liquidity vault, held as a return on capital).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); FYI on issue #7.
- **Why now:**
  - Every France-reachable carry book tested on 2026-11-10 (R441-R445, R288) earns about the hurdle.
  - HLP (Hyperliquid) and LLP (Lighter) take USDC deposits from any wallet, with no KYC. Neither venue's terms, as
    read, exclude France. Their returns are public through each venue's API.
  - A vault is a different product from the carry books: the depositor shares the vault's market-making,
    liquidation and fee P&L, losses included.
- **Books:** two, decided separately: HLP and LLP. Two trials.
- **Gates:**
  - **Gate 0 (stops only):** the held history 2025-01-01..2026-11-10. It can stop a book; it cannot pass it.
  - **Gate 1 (decides):** days recorded after this freeze, from 2026-11-11, read at 90 and 180 scored days.
- **Paper only.** Nothing here deposits, orders or moves money.

## What the author has seen
- Before this lane, from general knowledge only: both vaults show an APR in their apps, and HLP had a loss event on
  the JELLY market in March 2025. No figure from either vault's return series has been read in this session.
- Probes of 2026-11-10 that read structure only:
  - HLP's `vaultDetails`: the window names and point counts, the first and last dates, and that each window's pnl
    starts at 0. HLP is a parent vault of 7 children, and the parent's latest account value is 1.07 times the sum of
    the children's.
  - LLP's `pool_info`: 663 daily share prices from 2025-01-16, and an operator fee of 0.0000. Its APR and Sharpe
    fields were not printed.
- Helpers' doc reads (summarized fetches):
  - HLP: a 4-day deposit lock-up; protocol vaults "do not have any fees or profit share"; depositors share profits
    and losses.
  - LLP: no lock-up; liquidations and bankrupt positions are backstopped by LLP; auto-deleveraging applies beyond
    it.
- Public APRs were known in general, so gate 0 stops only.

## Data
- **Source:** `.github/workflows/claude-okx-recorder.yml` (twice a day) writes `vaults/` on the data branch
  `claude/okx-xperp-data` with `scripts/record_dex_vaults.py`:
  - `hlp/snap/<fetch ms>.csv`: each run's `week`, `month` and `allTime` windows (account value and pnl);
  - `llp/share_prices/` and `llp/daily_returns/`: LLP's share prices and daily returns, merged by time.
- **Gate-0 data commit:** `55a0b58ef5b8d388ff86e7fcc2f58239591b93e2`
  - It is the data branch after the first run that recorded `vaults/`, with one HLP snapshot.
  - Gate 0 reads it and nothing else. The script refuses another commit.
- **Gate-1 data:** the same branch at the look date. Rows for days before 2026-11-11 are not scored.

## Rule (constants in `scripts/run_dexvault.py`; report and gate-1 decision: R441's `run_xperp_carry.py`)
- **Position:** the whole capital of each book sits in its vault for the whole window, with no switching and no
  leverage.
- **LLP return:** the share price ratio between consecutive stamps, using the last stamp of each UTC day and booked
  on the later stamp's day. A gap moves the whole change to the next stamp.
- **HLP return, gate 0:** from the gate-0 snapshot's `allTime` window, each period between consecutive points:
  (pnl − previous pnl) / previous account value, booked on the later point's UTC day. Points are about a week apart.
- **HLP return, gate 1:** for each UTC day D, over (00:00 D, 00:00 D + 1):
  - Take the earliest snapshot fetched at or after the day's end whose window holds a point at or before its start.
  - Windows are tried in order: `week`, then `month`, then `allTime`.
  - The return is (pnl at the last point at or before the end − pnl at the last point at or before the start) / the
    account value at that start point.
  - A day no snapshot covers is booked at 0 and counted as missing.
- **Costs:** one deposit-and-withdrawal round trip a year, 10 bp of capital a year at 1x, spread over the days. The 2x
  and 3x reads multiply it. Neither vault charges a fee on deposits, as read.
- **Hurdle:** 4.0%/yr on capital, flat.
- **Statistic:**
  - Gate 0: per period, net return minus hurdle × period days / 365. Its annualized sum over the window's days, and
    its Newey-West t at lag 4 for HLP and lag 10 for LLP (`lab.stats.newey_west_t`).
  - Gate 1: per day, R441's summary (daily excess, NW t at lag 10, cumulative drawdown).

## Decision (each book on its own)
1. **Gate 0:** **NULL (stop)** for a book whose 1x annualized excess is below 0. Otherwise that book continues to
   gate 1. Gate 0 cannot pass a book.
2. **Gate 1, at 90 scored days (2027-02-08):**
   - **EARNED** when all of these hold: 1x annualized excess at least +3.0 points, NW t at least 2.0, 2x excess
     above 0, and 1x cumulative drawdown above −5% of capital. The book continues to 180 days.
   - **NULL (stop)** when the 1x excess is below 0.
   - Otherwise **CONTINUE**.
3. **Gate 1, at 180 scored days (2027-05-09):**
   - **CONFIRMED** when the same conditions hold with NW t at least 2.5.
   - Otherwise **NULL**.
4. A CONFIRMED book is paper evidence only. It admits nothing to real money. `lab.gate.go_real()` and the owner's own
   check decide, including the venue's status and the vault's tail risk.

## Power, reported before any read
- Not computed before the freeze, because that would read the data. Gate 0 reports each book's period sd and, for
  LLP, the detectable annual excess (t 2.5, 80% power) at 90 and 180 days.
- FINDINGS states whether gate 1 can decide at all at the excess gate 0 shows.

## Reported, not deciding
- Gate 0: by year, the worst period and its date, the maximum drawdown, and the number of periods.
- Gate 1 status reads before a look (`--status`), with missing days. They carry no decision.

## Trials and reading
- Two trials (two books, one rule each). The program total before this lane is 9,784,988 (after R445).
- Read against `registry.program_trials()`.

## Limits
- **Tail risk:** a vault can lose on a single market (HLP on JELLY, March 2025). Gate 0's window may hold few such
  events; the forward window may hold none.
- **Venue risk:** both are smart-contract venues, authorised nowhere. Withdrawals can be delayed (HLP's 4-day
  lock-up) or halted.
- **HLP's measure:**
  - It is the parent vault's own account value and pnl, as the app shows them.
  - Flows are assumed to fall at period ends, so a large deposit or withdrawal inside a period biases that period.
  - Gate 0 has about weekly resolution.
- **Different clocks:** HLP's days run 00:00-00:00 UTC; LLP's stamps fall near 20:00 UTC.
- **Gate 0:** public APRs were known in general; the window is the vaults' history as served today.
- **Jurisdiction:** neither venue's terms, as read, exclude France. That is not legal advice, and the owner checks.

```inputs
a58005353bf406cb84998f12af83384c5b451f72629f5d89356ab651b0903e0f scripts/run_dexvault.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
15510f526815e6b1e18a0b05a115284fd165dc50e621de4ba8788bfafa2b75f9 tests/test_run_dexvault.py
f1d1258247a5c3f88c797d1f5746d63555d6ea39cb373bafe156db7e7a58ecdf scripts/record_dex_vaults.py
127382b43bfd688b3d8fca8961492d998560098387351afdee1cd7ca005567c9 scripts/record_hl_daily.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
