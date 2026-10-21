# Gates: from an idea to the owner's money

Written 2026-10-20 from `docs/CAPITAL_GATE_REVIEW.md` and the critics in `docs/CRITIQUE.md`. It replaces "go_real
passed" as the meaning of "ready". `lab.gate.go_real()` stays as one step inside gate 2; it is not the decision.

Nothing here changes a frozen PREREG. Lanes frozen before today keep their own rules. This file says how their results
are read and what a new lane must pre-register.

## The funnel

| Gate | Question | Evidence that counts | Who decides |
|---|---|---|---|
| 0. Screen | Is there anything here at all? | Any archive window, including the spent holdout. Labelled **exploratory**. | the loop |
| 1. Research | Does the signal predict, net of costs, on days nobody had seen? | Only on-time forward days after the freeze, or an archive window never read by anyone (another venue, held-back history). | frozen PREREG |
| 2. Execution | Can the owner's venue fill it at the owner's size? | Paper fills at fixed notionals on MEXC contract rules: delay, depth, partials, funding events. `go_real()` runs here. | frozen PREREG |
| 3. Account risk | Can it blow up the account? | Replay on MEXC margin tiers, fair-price liquidation, squeezes and gaps, failed hedges, with gross and per-contract caps set first. | frozen PREREG |
| 4. Owner | Does the owner accept a small, bounded stake? | Gates 1-3 written up, with the max loss stated. | **the owner only** |

A result is named by the highest gate it passed. "In-sample", "holdout" and "replay" are all gate 0. The registry's
`CONFIRMED` on R181, R185, R190, R192, R195 and R197 means in-sample (gate 0). R191 carry passed a single holdout test
at 1x costs, which is also gate 0 now that the holdout is spent.

## Rules for gate 1 (new lanes from 2026-10-20)
- **One decision per signal.** Lanes that share cells (R200, R214, R215, R218, R225 all use the same flow cells) are
  diagnostics of one signal, not separate chances. A new lane names which decision it feeds.
- **Days counted:** strict on-time days only (every hour computed within 60 minutes, `scripts/forward_lag.py`).
  Replayed days are reported, never counted.
- **Test:** a one-sided test whose threshold is calibrated by simulation under a dependent null (block bootstrap of
  the lane's own archive returns with the mean removed), not a hit rate. Report the trimmed mean (top and bottom 10
  days removed) and a leave-two-coins-out mean next to the plain mean.
- **Power:** the PREREG states the days needed for 80% power at the Sharpe it expects. If that is longer than the
  decision date below, the lane says so and is labelled a futility screen.

## Reserved samples (gate 1 from archive data, decided 2026-10-20)
These are two samples nobody in the lab has read for the question at hand. They give gate-1 answers in days instead of
waiting for forward days. Each is spent in scheduled batches, never by a single lane.

**Samples**
- **2020 crypto.** Binance perps 2020-01-01..2020-12-31: 81 symbols with price, funding, premium and taker volume.
  There are no top-trader ratios before 2021.
  - The research panel starts on 2021-01-01, and no crypto lane PREREG reads 2020.
  - Partial reads, disclosed:
    - R244 used BTCUSDT 2020 weekend moves as a predictor of QQQ;
    - the old session's prop-challenge sims (R143/R144) used 2020-22 starts of the chase rules.

    So a BTC-only time-series rule or a chase rule is only partly fresh there. Altcoin and cross-sectional rules are
    fresh.
  - `lab.panel.load_panel` raises for rows before 2021 unless it gets a frozen PREREG that contains the token
    `RESERVED-2020-READ`. So do `lab.daily` and every qx subcommand (`engine/src/reserved.rs`, through the spec's
    `reserved_prereg`), which also guard the venues' `reserved/` folders with their own tokens.
- **MEXC-only coins**, 2025-04-01 onward: MEXC perps with no Binance perp in the archive. The set is fixed by a frozen
  PREREG before the first read.
- **Gate long tail and Gate 2020** (added 2026-10-20 with `scripts/fetch_gate_history.py`):
  - every Gate USDT perp whose base has no Binance perp (the same name rule as R274's `binance_perp`), all months,
    delisted contracts included;
  - every Gate contract's 2020 rows.

  The build writes them to `data/gate_hist/reserved/` and nothing else. They are read only by a frozen batch PREREG
  that declares `RESERVED-GATE-READ`, under the rules below. The MEXC-only coins overlap this set: a batch that reads
  one names the other's overlap.
- **KuCoin and dYdX long tail and 2020** (added 2026-10-20 with `scripts/fetch_venue_history.py`): the same rule as
  Gate's, per venue. The build writes them to `data/kucoin_hist/reserved/` and `data/dydx_hist/reserved/`. Only a
  frozen batch PREREG that declares `RESERVED-VENUE-READ` reads them, and it names its overlap with the Gate and
  MEXC-only sets.

**Rules**
- **Batch reads only.** One frozen batch PREREG lists every candidate, with Bonferroni over the batch, 1x/2x/3x costs,
  a trimmed mean and leave-two-coins-out. Each sample is read once per batch.
- **Read budget:** 4 batches per sample, about every 2 weeks from 2026-11-03. After the 4th, the sample is spent like
  the old holdout. The panel counts the reads.
- **Pre-committed entries:** R263's best single strategy and its walk-forward stream enter the first batch whatever
  they score, so the choice cannot follow the result.
- **What a pass earns:** a frozen forward paper lane, labelled manual-web or API by the execution mode it needs.

**Reads so far**
| Batch | Round | Frozen | Reads | Candidates | Read on |
|---|---|---|---|---|---|
| 1 | R286 `experiments/reserved_batch1` | 2026-10-21 | 2020 1/4, Gate 1/4, MEXC-only 1/4 (KuCoin and dYdX 0/4) | 10 | on or after 2026-11-03 |

## Rules for gate 2
- `go_real()` at the PREREG's day count, never earlier. `forward_tick.py` now writes `verdict: PENDING` until day 90.
- Costs at 1x, 2x and 3x of MEXC's measured cost (R224), plus the API fee of 6 / 8 bp in force since 2026-06-01.
- A book the owner cannot place by hand (50 coins, hourly slices) needs a daily-netted version of 15 orders or fewer,
  frozen as its own lane before it is scored.

## Rules for gate 3
To be set before any result is read, in the lane's PREREG:
- max gross exposure and max per-contract notional (per MEXC risk tier);
- daily stop and account drawdown stop;
- the replay of margin and liquidation on fair price for every day of the paper record.

## Gate 4: what the owner sets (proposals, not decisions)
The owner fills these in; the lab proposes, it does not decide.
- **Small stakes**: proposed at most 2% of the account's trading capital per book, and no single contract above its
  MEXC base risk tier.
- **Max loss**: proposed hard stop at 25% of the stake; the book is switched off and re-registered after that.
- **Calibration orders**: the strategy critic proposes 20-30 tiny live orders to measure real fills against paper.
  That would be a carve-out from rule 6 of `AGENTS.md` and only the owner can grant it.

## Dates
- **2027-01-18**: first 90-on-time-day looks for R215, R218 and R220 (R221's futility look). A book with t <= -2 stops.
- **2027-01-31**: lane count frozen. No new forward lane on the flow cells after this date unless one passes gate 1.
- **2027-04-20**: review of the whole program against this file. If nothing has passed gate 1, the search is
  re-budgeted towards event lanes and other markets, and the review is written up for the owner.
- **2027-10-20**: R221's last look (365 days).
