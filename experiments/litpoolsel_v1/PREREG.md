# PREREG: litpoolsel_v1 (R452). Lighter's public pools picked by their past record

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R452
- **Method:** M507 on Lighter (public pools picked by their past record, deposits only, net of the operator's fee).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-11); FYI on issue #7.
- **Why now:**
  - The owner asked (2026-11-11) to look past HLP and LLP, at their competitors and at what beats them, with
    results that a real deposit would reproduce.
  - Lighter publishes every public pool's daily share price from its start, through public endpoints with no
    account. A depositor's value is shares × share price, so the share price is what a deposit earns, before the
    operator's fee.
  - Lighter's docs (docs.lighter.xyz/trading/public-pools, read 2026-11-11):
    - the operator's fee is "the percentage of profits allocated to the operator upon participant withdrawals";
    - "Public Pools do not impose lockup periods".
  - LLP needs a LIT stake (R447) and earned about +10.8%/yr in 2026 (R446). The question: does a pool's steady past
    record pick pools that beat the hurdle over the next month, net of the operator's fee?
- **Book:** one, so one trial.
- **Gates:**
  - **Gate 0 (decides):** monthly formations 2025-11-30..2026-09-30, each held to the next month end. No operator
    pool's return has been read before this freeze, so gate 0 decides.
  - **Forward:** if gate 0 earns, a new lane registers the forward read before its first formation.
- **Paper only.** Nothing here deposits, orders or moves money.

## What the author has seen
- **The pool list's structure** (`publicPoolsMetadata`, 2026-11-11):
  - 347 pools: 195 of Lighter's own 1x-3x long/short index pools (master account 4, fee 0), the 2 protocol pools
    (LLP and XLP, account type 3), and 150 operator pools (82 with status 0, 68 with status 1). One operator pool
    is named like an index pool ("3x long") but run by another account and charges 10%.
  - The operator pools' names, fees (0 to 30% of profits), creation months (most in 2025-09 and 2025-10) and today's
    asset values. The largest are LLP ($99.7M), then pools of $1.7M, $0.69M, $0.56M and $0.41M; most hold under $10k.
- **Two pools' account structure** (Edge & Hedge, XLP): fields, and the share-price series' length (414-419 daily
  points from 2025-09), first and last dates. No return was computed.
- **Printed by accident:** the list's first row, LLP's displayed APY (13.6) and Sharpe ratio. LLP is outside the
  universe. No other pool's APY or Sharpe was printed. Also printed: Edge & Hedge's first two share prices
  (2025-09-18 and 09-19), its fee 20% and minimum operator share 5%. Both prices precede every formation's
  signal window.
- **Helpers' reports of 2026-11-11** (`research/intake/perp_vaults_20261111.md`): competing vaults' terms and data
  access; Lighter's pool fees and LLP's rules. They computed no return.
- **The gate-0 files' structure:** 347 pools, 150 in the universe, all with prices; 133,782 share prices (45,369
  in the universe) from 2025-01-16 to 2026-11-10, stamped at 20:00 or 21:00 UTC.
- **Not seen:** any operator pool's return, APY, Sharpe or share-price level.

## Data
- **Gate 0:** `experiments/litpoolsel_v1/data/`, fetched by `scripts/run_litpoolsel.py --window fetch` on
  2026-11-11 and pinned in the `inputs-gate0` block. Lane data stay out of git.
  - `pools.csv`: every pool in `publicPoolsMetadata` (filter all), with today's type, master account, creation time,
    status, operator fee, minimum operator share, asset value and shares.
  - `share_prices.csv`: every pool's daily share prices from `account?by=index` (`pool_info.share_prices`).

## Rule
Constants are in `scripts/run_litpoolsel.py`.
- **Universe:** operator pools. Lighter's own index pools (master account 4) and the protocol pools (account type 3:
  LLP, XLP) are excluded.
- **Formation:** at each month end t (end of the UTC day).
- **Eligible at t:**
  - created at least 90 days before t;
  - its last share price at or before t is no older than 3 days (a pool that stopped pricing is out).
- **Signal:** the daily log returns of the share price over the past 90 days. They run from the last price at or
  before t − 90 days to the last price at or before t. The signal needs at least 60 prices in the window and a
  positive sum. Score: mean over sd.
- **Book:** the 5 pools with the highest score, equal weight, a fifth of capital each. With fewer than 5
  candidates, an empty slot is held in cash and earns the hurdle (its excess is 0).
- **Held return:** the share price at the last point at or before the next month end over the one at or before t,
  minus 1. A pool whose prices end keeps its return to its last price.
- **Operator's fee:** the pool's fee on file (today's) is taken from a positive held return.
- **Switching cost:** 10 bp of a slot's capital for each slot that changes pool, at 1x. The 2x and 3x reads
  multiply it.
- **Hurdle:** 4.0%/yr on capital, flat, over each month's days.
- **Statistic:** monthly net minus hurdle. Its annualized sum over the window's years, and its Newey-West t at lag 3
  (`lab.stats.newey_west_t`).

## Decision
1. **Gate 0:**
   - **EARNED** when all of these hold: 1x annualized excess at least +3.0 points, NW t at least 2.0, and 2x excess
     above 0.
   - Otherwise **NULL (stop)**.
2. An EARNED lane is paper evidence only. A forward read is registered as a new lane before its first formation. It
   admits nothing to real money: `lab.gate.go_real()` and the owner's own check decide, including each pool's
   capacity, operator and tail.

## Reported, not deciding
- The equal-weight net return of every eligible pool (same filters, no signal), annualized.
- LLP and XLP over the same months (no fee; LLP needs a LIT stake).
- By month: eligible pools, candidates, picks and switches. The worst month, the maximum drawdown, and the fee in
  %/yr.
- The last formation's picks with today's asset value and status (capacity).
- Power: the monthly sd of the excess.

## Trials and reading
- One trial. The program total before this lane is 9,784,997 (after R451).
- Read against `registry.program_trials()`.

## Limits
- **Short window:** 11 held months. Most pools started in 2025-09 or 2025-10, so earlier formations have no
  eligible pool. A real effect of a few points a year cannot reach t 2.0 here; the read can stop a weak rule, not
  prove a strong one.
- **Survivorship:** the list holds closed pools (status 1), but a pool that Lighter deleted would be missing. Not
  checked.
- **Capacity:** pool sizes at t are not on file; only today's are. A pool of a few thousand dollars cannot take a
  real deposit of that size, and an operator's minimum share caps deposits. A pick that could not be entered is
  booked anyway; the report gives today's sizes.
- **Fee:** today's fee, applied monthly on gains. Charged at withdrawal against the deposit's own gain, a fee on a
  month after a loss month is overcharged here, never undercharged.
- **Share-price timing:** prices are stamped once a day (20:00 or 21:00 UTC in the series read), so a month end uses the
  last price before it.
- **Operator tail:** an operator can lose a pool's capital in a day; one bad pick costs a fifth of the book.
- **Venue and jurisdiction:** Lighter's terms as read for R446/R447; operators are anonymous. Not legal advice; the
  owner checks.

```inputs
0272d3fd4722b5caf2f154474372088072ba4d04632602c6aaab8e7b42690cac scripts/run_litpoolsel.py
7bf7771ef005ada606ac9e11549dfc905fcd808d32adcb758e416fda3922193a tests/test_run_litpoolsel.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```

Gate 0's input files (they stay out of git as lane data; the run checks them):

```inputs-gate0
9b2468003211603bdcf25f69614026656a37bca6d9eaf6b3f7f404b169d6ee09 experiments/litpoolsel_v1/data/pools.csv
1d39fbe514f15ec244baf94dbd367f7105de3886eaffc646efcd6f6258e40549 experiments/litpoolsel_v1/data/share_prices.csv
```
