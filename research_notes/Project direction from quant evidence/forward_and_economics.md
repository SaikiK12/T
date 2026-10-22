# Forward paper test and cost economics (as of 2026-10-20)

**Verdict:** Nothing has made money in a forward test that counts. The only positive paper numbers are 19-day replays, and no day is strictly on-time yet. The go-real gate is one scored day short on the best book and fails the hit-rate test on the MEXC books. The ZRO unlock score is not in this checkout.

Method: read-only. I ran `lab.gate.go_real()` and summed the journals with stdlib Python. Scripts are in `/tmp/claude-0/-home-user-T/62f4d126-48a1-555e-afe1-7e454d28bc35/scratchpad/` (`tickets_summary.py`, `gate_check.py`, `depth_summary.py`, `depth_by_snap.py`, `fee_by_snap.py`). `scripts/check_research_integrity.py` gave 0 errors and 12 warnings. Unit tests: `tests.test_lab` passes 15/15. The suite shows 18 error entries: 17 modules fail to import without numba, and one parquet test lacks pyarrow. Both are sandbox gaps, not investigated further.

## 1. Forward record

### Takeaway
Six lanes hold tickets for the same 19 days, 2026-10-01 to 10-19. These are replays, not on-time observations. The PREREGs count on-time days from 2026-10-20, so the decision count is zero today.

### Cited Findings
- **ZRO / unlock lane (R180).** The registry says 364 tickets were appended 2026-10-12, with the first ZRO entry dated 10-13 and scored 10-20 ([registry/rounds.csv:4](/home/user/T/registry/rounds.csv)). The folder `experiments/unlocks_sf` does not exist. Nor do any result file, ticket file or `ledger.csv` (the file AGENTS.md names). The integrity audit warns `EXPERIMENT_MISSING` for R180 and R181. The 364 figure also appears in [docs/FOUNDATION.md:53](/home/user/T/docs/FOUNDATION.md). Scored count, dates, returns and cost: **unverified**. The unlock data lives in the original project ([docs/OLD_SESSION_EDGES.md:60](/home/user/T/docs/OLD_SESSION_EDGES.md)).
- **Correlated tickets.** The 364 tickets share entry dates, so 20 "scored" tickets could be 2-3 market days ([docs/AUDIT.md:13](/home/user/T/docs/AUDIT.md)).
- **Lanes with tickets** (computed from each `journal/tickets.csv`; net = sum of daily unlevered returns; "x2/x3" = cost at 2x and 3x):

| Lane (book) | Days | On-time | Net 1x / 2x / 3x | Mean bp/day (1x) | Hit (1x) |
|---|---|---|---|---|---|
| R200 flow72_fwd2, A (Binance) | 19 | 1 (10-19) | +22.2% / +21.0% / +19.7% | +117 | 74% |
| R200, B | 19 | 1 | +9.5% / +9.2% / +9.0% | +50 | 68% |
| R214 flow72_fwd3, A | 19 | 0 | +22.6% / +21.5% / +20.3% | +119 | 68% |
| R215 mexc_fwd, A (MEXC) | 19 | 0 | +4.6% / +3.6% / +2.7% | +24 | 47% |
| R215, B | 19 | 0 | -0.1% / -0.3% / -0.4% | -0.6 | 42% |
| R218 mexc_fwd_sq, X2 (MEXC) | 19 | 0 | +5.9% / +5.0% / +4.0% | +31 | 47% |
| R220 carry_fwd, MEXC | 19 | 0 | -0.015% / -0.12% / -0.23% | ~0 | 58% |

  Sources: [experiments/flow72_fwd2/journal/tickets.csv](/home/user/T/experiments/flow72_fwd2/journal/tickets.csv), [flow72_fwd3](/home/user/T/experiments/flow72_fwd3/journal/tickets.csv), [mexc_fwd](/home/user/T/experiments/mexc_fwd/journal/tickets.csv), [mexc_fwd_sq](/home/user/T/experiments/mexc_fwd_sq/journal/tickets.csv), [carry_fwd/journal/status.json](/home/user/T/experiments/carry_fwd/journal/status.json) (BIN never invested, `days_invested` 0).
- **R200's "on-time" day is not strictly on-time.** 18 of its 19 days are flagged `late=1`. Its 10-19 hours were computed 22-555 minutes after close ([experiments/flow72_fwd2/DEVIATIONS.md, "Known and not changed"](/home/user/T/experiments/flow72_fwd2/DEVIATIONS.md)). The GATES rule for strict on-time days is "every hour computed within 60 minutes" ([docs/GATES.md](/home/user/T/docs/GATES.md), gate 1 rules).
- **R200 counts replays in its decision.** Its PREREG decides at 90 scored days, 2026-12-29 at the earliest ([experiments/flow72_fwd2/PREREG.md:50](/home/user/T/experiments/flow72_fwd2/PREREG.md)). Its DEVIATIONS file says the 18 replay days count. [docs/GATES.md:27](/home/user/T/docs/GATES.md) says "Replayed days are reported, never counted." GATES applies to new lanes only, so R200 is not retroactively changed. The `days_scored: 19` in its status overstates the evidence.
- **On-time decisions.** R215, R218, R220 and R221 count on-time days from 2026-10-20; the earliest 90-day decision is 2027-01-17 ([experiments/mexc_fwd/PREREG.md:31, 34](/home/user/T/experiments/mexc_fwd/PREREG.md)).
- **Replay contamination.** Replay tickets for 10-01..18 traded XAUUSDT as crypto, a TradFi contract ([experiments/mexc_fwd/DEVIATIONS.md](/home/user/T/experiments/mexc_fwd/DEVIATIONS.md)). Registry row R215 says "replay 10-01..18" but the journal runs to 10-19 (minor).

### Inferences
- The replay numbers were computed after the freeze, from data already seen. They are not a contemporaneous paper record ([docs/CAPITAL_GATE_REVIEW.md](/home/user/T/docs/CAPITAL_GATE_REVIEW.md), "weak screen" section).

### Gaps
- No file contains the 364 tickets, the ZRO return, or any unlock forward score.

## 2. Go-real gate

Rules: at least 20 scored tickets, mean > 0, hit rate >= 55%, worst day >= -40% ([lab/config.py:21](/home/user/T/lab/config.py), [lab/gate.py:7-29](/home/user/T/lab/gate.py)). The gate does not test significance, clusters or capacity ([docs/CAPITAL_GATE_REVIEW.md](/home/user/T/docs/CAPITAL_GATE_REVIEW.md)).

- **R200 A, all 19 days:** n = 19 (one short). Mean +117 bp, hit 74%, worst -3.1%. Three of four checks pass. On-time only: n = 1.
- **R215 A (replay):** n = 19, mean +24 bp, **hit 47% (fails)**, worst -2.7%.
- **R218 X2 (replay):** n = 19, mean +31 bp, **hit 47% (fails)**.
- **R215 B and R220 MEXC:** fail on mean.
- **Distance.** Twenty strictly on-time days from 2026-10-20 would complete on 2026-11-09 (inference). The PREREG decision needs 90 days, which points to 2027-01-17. Statistical strength: with the same daily spread (sd 124 bp for R215 A, 296 bp for R200 A, computed from the tickets), a 90-day iid t >= 2 needs a mean of about **26 bp/day** for R215 A, **31 bp** for X2 and **62 bp** for R200 A. R215 A's 2x mean is 19 bp, so it misses at the 2x cost. The iid figure is optimistic because the 72 h slices overlap ([docs/PAPER_REFINEMENT.md:17-20](/home/user/T/docs/PAPER_REFINEMENT.md) says ~5 annual Sharpe is detectable at 90 days).

## 3. Break-even table

Break-even gross per round trip (entry plus exit, bp of notional), before funding and hedge:

| Cost model | 1x RT | 2x RT | 3x RT | Source |
|---|---|---|---|---|
| Lab flat `COST` = 0.002 one way | 40 | 80 | 120 | [lab/config.py:13](/home/user/T/lab/config.py); round trip = 2 x one-way per [scripts/run_dow.py:41](/home/user/T/scripts/run_dow.py) |
| Lab tiers by rank 1-20 / 21-50 / 51-100 / >100 | 12 / 16 / 24 / 40 | 24 / 32 / 48 / 80 | 36 / 48 / 72 / 120 | [lab/engine.py:42-46](/home/user/T/lab/engine.py) |
| MEXC API taker, $10k, measured (median 9.29 bp/side) | ~19 | ~37 | ~56 | [experiments/mexc_costs/journal/status.json](/home/user/T/experiments/mexc_costs/journal/status.json), `median_over_coins.api_10k` |
| MEXC web taker, $10k, measured (median 4.65 bp/side) | ~9 | ~19 | ~28 | same file, `web_10k` |

- **The lab's 1x tier cost is below the measured API cost for every coin.** Lab tiers are 6 or 8 bp one way. The measured API taker cost at $10k is at least 8.01 bp, median 9.29. The file reports `share_api_10k_above_assumed` = 1.0, so the 2x column is the nearer proxy for API execution. For manual web orders, the 1x column is conservative.
- **Fees moved during the window.** Coins listed at 4 bp taker rose from 4 to 21 (of 31-32) between the 10-19 19:43 and 10-20 00:42 snapshots ([experiments/mexc_costs/journal/depth.csv](/home/user/T/experiments/mexc_costs/journal/depth.csv), `fee_taker`). The cause is **unverified**. [docs/EDGE_SCOREBOARD.md](/home/user/T/docs/EDGE_SCOREBOARD.md) quotes 2.5 bp web and 9.6 bp API, which matches the first snapshot only.
- **Costs are not the binding term.** R215 A costs 3.6 bp/day at 1x against a gross of +103 bp/day. Its hedge is -75 bp/day, the largest drag (19-day sums: gross +19.57%, cost -0.69%, hedge -14.33%, net +4.55%; [tickets.csv](/home/user/T/experiments/mexc_fwd/journal/tickets.csv)). Net = gross - cost + hedge holds on all 19 rows (max error 1e-17), so the hedge term includes hedge costs ([scripts/forward_mexc.py:121-123](/home/user/T/scripts/forward_mexc.py)).
- **Cost multiple to zero net:** R215 A about 5.9x the lab's 1x cost; R218 X2 about 7x; R200 A about 19x. R215 B and R220 MEXC are already at or below zero at 1x.
- **Implication:** a MEXC lane needs a gross edge above roughly 19 bp per round trip at measured API cost, and a 90-day mean of about 26 bp/day after 2x costs to pass t >= 2.

## 4. Capacity

- **Measured depth** (32 coins, 7 snapshots, 2026-10-19 15:45Z to 10-20 11:20Z; `status.json` `per_coin`). Smaller side, USDT within 0.5% of mid: median $1.37M, p10 $109k, 7 coins below $250k. The thinnest are BTW $21k, AKE $23k, Q $74k and RLC $109k. AKE cannot fill $50k in most snapshots. The median 50k impact is 2.8 bp, with a maximum of 43.8 bp (BTW). Source: [experiments/mexc_costs/journal/status.json](/home/user/T/experiments/mexc_costs/journal/status.json).
- **Stake translation (inference).** Each hourly slice is 1/(72 x 9.316) of stake per coin and cell ([experiments/flow72_fwd2/PREREG.md, frozen rules](/home/user/T/experiments/flow72_fwd2/PREREG.md)). The MEXC A book averages gross exposure 1.0 over 39 mapped coins, with a maximum of 1.49 (tickets, `gross_exposure`). Per coin that is about 2.6% of stake on average. If participation is capped at 20% of the 0.5% depth, the thin coins bind at stakes around $100-200k and the median coin only near $10M. These are my estimates, not repo results.
- **Repo gap.** No capacity figure, owner stake size or per-coin limit is stated. [docs/NEXT_SEARCH_SPACE.md:20](/home/user/T/docs/NEXT_SEARCH_SPACE.md) says "Do not claim capacity was tested." [docs/PERP_EXECUTION_AND_RISK.md](/home/user/T/docs/PERP_EXECUTION_AND_RISK.md) says flat multipliers cannot establish capacity. GATES proposes at most 2% of trading capital per book, with no account size ([docs/GATES.md:48](/home/user/T/docs/GATES.md)). A 50-coin hourly book is not hand-placeable; it needs a daily-netted version of 15 orders or fewer ([docs/GATES.md:37](/home/user/T/docs/GATES.md)).

## 5. Open questions

1. Where are the 364 unlock tickets and the ZRO score? They sit in the original project, and no file here reports them.
2. Will the owner decide whether replay days count? R200's 90-day decision (2026-12-29) includes them, which GATES forbids for new lanes.
3. Why did MEXC taker fees rise on about 17 coins between 10-19 and 10-20? R224 reports on 2026-11-03.
4. Hedge: the basket hedge is idealized (R200 PREREG: "idealized, as R197/R198"). R215 A's net depends on it (-75 bp/day).
5. The owner's own MEXC record (+$3,591 over 124 fills, "beta, not edge") is only an aggregate in [docs/OLD_SESSION_EDGES.md:149](/home/user/T/docs/OLD_SESSION_EDGES.md). Not verified.

**Not checked:** GitHub issue #7 (the AI room) was not read or posted to, because the brief limited me to the repo. [docs/ROOM.md](/home/user/T/docs/ROOM.md) was read. The ROADMAP named in FOUNDATION is not in the checkout. The FOUNDATION listing of open items and the "364 in total" figure have no data behind them in this checkout.
