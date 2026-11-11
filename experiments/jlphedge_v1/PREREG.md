# PREREG: jlphedge_v1 (R449). Perp-DEX liquidity-pool tokens held against perp shorts on Hyperliquid

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R449
- **Method:** M509 (a perp DEX's liquidity-pool token held with its crypto exposure shorted, so the depositor keeps
  the pool's fee income net of what it pays winning traders).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-11); FYI on issue #7.
- **Why now:**
  - The owner asked for experiments on high-return methods instead of more work for its own sake
    (`docs/reviews/pnl_ranking_20261111.md`).
  - Every high return in the lab so far was measured on venues closed to France. What France can reach and that held
    up earns about 10-14%/yr (R445-R447).
  - A hedged JLP position is a popular "delta-neutral yield" trade. Jupiter's terms do not name France among the
    prohibited localities, as read (below), and the hedge sits on Hyperliquid, which the lab already uses from France.
  - GMX v2's GM pools work the same way and get 63% of the fees they generate on Arbitrum.
- **Books:** two, decided separately. Two trials.
  - **J:** JLP (Solana), hedged with SOL, ETH and BTC perp shorts.
  - **G:** GM ETH-USDC (GMX v2, Arbitrum), hedged with an ETH perp short.
- **Gates:**
  - **Gate 0 (stops only):** 2024-02-01..2026-11-10. It can stop a book; it cannot pass it.
  - **Gate 1 (decides):** days from 2026-11-12, with tickets written before each day starts, read at 90 and 180
    scored days.
- **Paper only.** Nothing here deposits, orders or moves money.

## What the author has seen
- **General knowledge, before this lane:**
  - Both pools show double-digit APYs in their apps.
  - Hedged ("delta-neutral") JLP products have been marketed.
  - JLP holders lose when traders win.
  - GMX's older GLP pool (v1, not GM) was exploited in July 2025.
- **A helper's reads of 2026-11-11** (`lp_pools_research.md`, `lp_terms_check.md`; the claims used here were checked
  by the author):
  - **JLP:** 75% of the perps fees go to the pool and 25% to Jupiter. The app's APY excludes price change and trader
    P&L.
  - **Jupiter's prohibited localities:** jup.ag/mobile/terms, fetched again by the author, lists the US, China,
    Singapore, Myanmar, Côte d'Ivoire, Cuba, Crimea, the DRC, Iran, Iraq, Libya, Mali, Nicaragua, North Korea, Somalia,
    Sudan, Syria, Yemen and Zimbabwe. It also bars any region under US, UK or EU sanctions. France is not named.
  - **GMX:** docs.gmx.io/docs/providing-liquidity says LPs earn "63% on Arbitrum and Avalanche" of fees, liquidations
    and borrow fees. GMX's interface terms were not found, so France's status at GMX is unknown.
  - **JLP's price:** DefiLlama's one-year chart went from 4.998 to 4.034. That is the unhedged token, not a
    book.
- **The author's probes,** structure only:
  - DefiLlama's daily points stitch back to 2023-11-30 (JLP) and 2023-09-26 (GM).
  - Gate-0 inputs: JLP has 1,079 points and GM 1,134. Hyperliquid gives 1,168 daily closes and funding days per coin;
    2 funding days per coin have fewer than 24 hours.
  - Missing midnight stamps in the window: 6 for JLP and 5 for GM, listed by date.
  - The last points' times.
- **Not computed or read before the freeze:** any pool or book return, volatility or correlation.
- **Dry run before the freeze:** the forward ticket step ran once into a scratch journal. It printed only whether each
  ticket had ratios (both did, from 60 spans), not the ratios.
- Public APYs were known in general, so gate 0 stops only.

## Data
- **Gate 0:** `experiments/jlphedge_v1/data/`, fetched by `scripts/run_jlphedge.py --window fetch` on 2026-11-11
  00:33 UTC and pinned in the `inputs-gate0` block.
  - `pool_J.csv`, `pool_G.csv`: every DefiLlama daily point of each token (`coins.llama.fi/chart`, 365-point windows
    stitched) from 2023-09-01.
  - `close_<coin>.csv`: Hyperliquid's daily perp closes of SOL, ETH and BTC (`candleSnapshot` 1d), keyed by the
    midnight the candle closes at.
  - `funding_<coin>.csv`: Hyperliquid's hourly funding settlements summed per UTC day. A settlement at T pays for the
    hour before it, so it belongs to the day of T − 1 h.
- **Gate 1:**
  - Tickets: `experiments/jlphedge_v1/journal/tickets.csv`, append-only. `claude-flow-paper.yml` writes them, from the
    hourly run's live fetch of the same sources.
  - Realized returns: fetched from the same sources at the read.

## Rule (constants in `scripts/run_jlphedge.py`)
- **Stamps:**
  - A midnight's stamp is the pool token's DefiLlama point closest to it, within 60 minutes.
  - The hedge coins' prices at a midnight are their Hyperliquid daily closes at it.
  - A midnight is usable when the stamp and every hedge coin's close exist.
- **Spans:** between consecutive usable midnights a < b. A missing stamp lengthens a span. Each span is booked on
  day b − 1.
- **Hedge ratios at a:**
  - OLS with an intercept of the pool's span returns on the hedge coins' span returns. It uses the last 60 spans that
    ended by midnight a − 1 day and no earlier than a − 120 days.
  - Each slope is clipped to [0, 1]. These are the short notionals per unit of pool value, opened at a and held to b.
  - With fewer than 40 such spans the span is idle: zero return, hurdle still charged.
- **Span P&L per unit of pool value at a:**
  - pool return − Σ hᵢ × coin returnᵢ + Σ hᵢ × funding over the span, minus costs.
  - Funding is the summed hourly rates of days a..b − 1; positive rates pay the shorts.
- **Capital:** 1 + Σ hᵢ. Each short is margined with cash equal to its notional (no leverage, as in R447), and the
  span's return on capital is the P&L divided by it.
- **Costs, at 1x; 2x and 3x multiply them:**
  - 6 bp of each unit of short notional traded.
  - Turnover is |hᵢ(a) − the previous span's hᵢ drifted to its end|. The first span counts its entry.
  - One round trip of the pool token a year, 30 bp of its value, spread over the days.
- **Hurdle:** 4.0%/yr on capital, flat (R446).
- **Statistic:**
  - Each span's excess is its net return minus the hurdle × span days / 365.
  - The annualized excess is the sum over spans × 365 / days covered.
  - NW t at lag 10 (`lab.stats.newey_west_t`) on the calendar-day series, with each span's value on its booked day.
  - The maximum drawdown of compounded span nets.

## Gate 1 tickets
- During day D − 1, the hourly run writes day D's ticket: the hedge ratios for a position opened at midnight D. They
  come from spans that ended by midnight D − 1, as gate 0 computes them.
- The ticket is written only once midnight D − 1's stamp is settled: a point within 60 minutes of it, a later point
  past that, or the tolerance passed by an hour.
- A ticket is never rewritten. A day is scored only if its span starts at a ticket written before that midnight.
- Realized returns at the read use the ticket's ratios and the same span, funding and cost rules.

## Decision (each book on its own)
1. **Gate 0:** **NULL (stop)** for a book whose 1x annualized excess is below 0. Otherwise it continues to gate 1.
   Gate 0 cannot pass a book.
2. **Gate 1, at 90 scored days:**
   - **EARNED** when all of these hold: 1x annualized excess at least +3.0 points, NW t at least 2.0, 2x excess
     above 0, and 1x maximum drawdown above −5% of capital. The book continues to 180 days.
   - **NULL (stop)** when the 1x excess is below 0.
   - Otherwise **CONTINUE**.
3. **Gate 1, at 180 scored days:**
   - **CONFIRMED** when the same conditions hold with NW t at least 2.5.
   - Otherwise **NULL**.
4. A CONFIRMED book is paper evidence only. It admits nothing to real money. `lab.gate.go_real()` and the owner's own
   check decide, including each venue's status and the pools' tail risk.

## Power, reported before any read
- Not computed before the freeze, because that would read the data.
- Gate 0 reports each book's daily sd and the excess detectable at 90 and 180 days (t 2.5, 80% power). FINDINGS says
  whether gate 1 can decide at the excess gate 0 shows.

## Reported, not deciding
- **Gate 0:**
  - by year, the parts (pool, hedge, funding, costs), the unhedged pool's return, and the hedge ratios' mean and
    range;
  - the mean capital, the worst span and its date, and the idle spans.
- **After the frozen read, as diagnostics:**
  - regression windows of 30 and 120 spans;
  - the residual correlation of each book with its hedge coins;
  - the data-quality checks (repeated prices, irregular stamps).
- **Gate 1:** `--status` reads before a look. They carry no decision.

## Trials and reading
- Two trials (two books, one rule each). The program total before this lane is 9,784,993 (after R448).
- Read against `registry.program_trials()`.

## Limits
- **Tail risk:**
  - Each pool pays its winning traders and can be drained by an oracle or contract failure (GMX's GLP, July 2025).
  - Gate 0's window may hold few such events; the forward window may hold none.
- **Price source:** DefiLlama's daily point, not the pool's own on-chain virtual price. A stale or wrong point moves a
  span's return and the next one in opposite ways.
- **Daily hedge:** the hedge is rebalanced at midnights only. The pool's own exposure moves within the day with
  trader positions.
- **Transfers:** cash moving between the pool's chain and Hyperliquid to keep the shorts' margin is taken as free and
  instant. Bridges cost a few dollars and take minutes.
- **Jurisdiction:** Jupiter's terms, as read, do not name France; GMX's terms were not found. Hyperliquid is used as
  in R444-R446. This is not legal advice, and the owner checks.

```inputs
cf80d189cd384925b0f93b7c2eeb0feebc953f48762bd51ff543464e1a2cc4d2 scripts/run_jlphedge.py
65746c0f1ca3c9040ba55b34c45275c57088ec53c6cf3013b8fb4145a8f3d853 tests/test_run_jlphedge.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```

```inputs-gate0
eac2d4a7430a80c238bb5846f970dc2d7c573de1ad49c0bc6d67fc85cb4c6ac8 experiments/jlphedge_v1/data/pool_J.csv
4fa8b8c47a36e664718c490844a757bb47e90ff41839148d1b58a6ed6c6cd0c6 experiments/jlphedge_v1/data/pool_G.csv
0356a6c7c6197ff04b7bf667d635dd96958e81752b20c3e5a015d898450cbce2 experiments/jlphedge_v1/data/close_SOL.csv
115c8c1507c33a4fcb47a647adbd94df60f16a3308bc36598b1edfe3d1683aaf experiments/jlphedge_v1/data/close_ETH.csv
9868de86c8c0f5094912aedeaa5e7ffefce76392ac683a281e3e8eb0a400660c experiments/jlphedge_v1/data/close_BTC.csv
3907d866f7bccb9d6977916166b979b51fa63acc8a4d62aa8c7c8c3c1ea34ee9 experiments/jlphedge_v1/data/funding_SOL.csv
f328fbd655e0ee507ca7da8fa2eb87f888d9950e4cfdfc14078c2496bc898ef5 experiments/jlphedge_v1/data/funding_ETH.csv
6e4e0ccd84aca173420d67e7c01be48db369c1f9cdee59d42993bfad8d9a6a31 experiments/jlphedge_v1/data/funding_BTC.csv
```
