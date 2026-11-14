# PREREG: lighter_flow_v1, do Lighter's public taker accounts stay informed out of sample, and does following them pay (WTI, BRENTOIL, NATGAS)

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R433
- **Owner (single writer):** Claude (hunt-mode fork of the 2026-11-09 session); the orchestrator commits and closes the row.
- **Date registered (UTC):** 2026-11-09
- **Method:** M441 (Lighter commodity perps, participant identity and toxicity).

The owner asked on 2026-11-09 for hunt mode. The thesis comes from `docs/INFRA_GAP.md`: order flow is the fast firms'
largest edge, and Lighter publishes account-level flow on every public trade.

## Question
**Part A:** Do Lighter taker accounts' signed markouts persist from train days (10-28, 10-29) to test days (10-30,
11-02..11-06)? The statistic is the out-of-sample rank correlation of account scores, and the informed accounts' test
markout minus everyone else's.

**Part B:** Does a slow follower of the 10 best-scored accounts (or a fader of the 10 worst) earn more than the
recorded book cost on the test days? The follower enters at the touch 1.3 s after the account's trade.

## Universe
- **Markets:** Lighter perpetuals WTI (market 145), BRENTOIL (159) and NATGAS (158).
- **Accounts:** every public taker account id on ordinary trades. Account ids are pseudonymous numbers. Nothing links
  one to a person, and one entity may run several accounts.
- **Days:**
  - Train: 2026-10-28 and 2026-10-29 (by Lighter trade time T, UTC).
  - Test: 2026-10-30, 2026-11-02, 11-03, 11-04, 11-05 and 11-06.
  - No other day exists in the folder, apart from replayed rows dated 10-21..10-27, which are dropped.

## Data
`scripts/record_lighter_trades.py` (Lighter's public websocket, `readonly=true`, no key) wrote the gitignored
`data/lighter_trades/`.
- **Contents:** 3,482 parquet files (trade and quote per market and UTC day) and `sessions.csv` (103 recorder
  sessions with local start and end times). Their hashes are in `data_manifest.json`; the runner re-hashes every file
  and refuses unlisted ones.
- **Recorder state:** it is not running, so the files are final.
- **Coverage (local recorder hours):** 10-28 1.0, 10-29 23.7, 10-30 15.4, 11-02 3.2, 11-03 3.2, 11-04 2.8,
  11-05 2.1, 11-06 1.4. Test-day evidence is therefore dominated by 10-30.
- **Plumbing (`plumbing.json`, counts only):**
  - **Rows:** 114,416 trades in train and test days.
  - **Dropped:** 253 liquidations; 3,086 replayed on reconnect (T earlier than 2 s after the session start); 2,957
    received more than 5 s after T.
  - **Eligible:** 111,310 taker trades.
  - **Train:** 1,585 taker accounts, of which 101 have ≥ 20 eligible trades. Those 101 made 49,866 of the test-day
    trades.
  - **Coverage:** the share of test trades with both entry and exit touches covered by the same session is 99.4% at
    10 s, 97.1% at 60 s and 87.2% at 300 s.
  - **Quote rows:** WTI 1,554,276, BRENTOIL 1,508,282, NATGAS 192,665.
- **What was looked at before the freeze:** counts, accounts, days, gaps, schemas, receive lags and clock offsets.
  - No markout, mid change, return or account score was computed on real data.
  - The synthetic dry run is guarded so that it fails if it opens any file outside its temporary folder.

**Previously seen data:** R426 read a 225 s fragment (2026-10-29 01:31:45-01:35:30 UTC, 94 trades here) for maker
economics. It falls in a train day and is excluded from scoring. R427 read 134 trades' position transitions, not
prices; it verified the role convention used here.

## Two clocks
- **Lighter's clock:** trades carry T (ms); quotes carry the ticker's `last_updated_at` (`upd`, µs), which is
  monotone over each market's file. Every price lookup is an as-of read in Lighter's clock: the last quote with
  upd ≤ x.
- **Local receive clock:** it is offset against Lighter by up to about ±1.5 s on these files (receive minus T at the
  1st percentile is −1.35 s), so it is used only for three things:
  - to tag each row with the recorder session that received it;
  - to drop replayed and queued trades;
  - to keep every lookup inside its own session, at least 2 s from the session's edges.
- A lookup whose last quote belongs to another session, or that falls within 2 s of an edge, is missing. A trade
  missing its entry or its exit is skipped and counted.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Taker account and side | `maker_ask`, `bid_acct`, `ask_acct` | Lighter public trade, per market | per trade | published at T, received ~70 ms later (p50) | yes, at T + receive lag; entry at T + 1.3 s | forward-captured | maker_ask=1 → the bid account is the taker and bought (R427) |
| Markout M_i(h) | trade `px`; touch as of T+h | Lighter quote, price units | as-of read in Lighter's clock | computed after T+h | **train only**, for scores | forward-captured | missing outside the session or near its edges |
| Score_h(a) | M_i(h) over train trades | pooled over 3 markets, bp | train days, R426 fragment excluded | fixed before any test day | yes: test days come after train days | forward-captured | accounts with < 20 finite markouts dropped |
| Informed / uninformed sets | Score_h | top 10 with score > 0 / bottom 10 with score < 0 | per horizon | fixed before test days | yes | forward-captured | ties broken by stable sort |
| Entry and exit touches | bid, ask, sizes | Lighter quote | as of E = T + delay and E + h | read at E and E+h | yes (Lighter state at E) | forward-captured | missing → trade skipped and counted |

Every input is forward-captured by this lab's recorder. Recorder gaps are missing, never zero or fresh.

## Rule
**Scoring (train days):**
- M_i(h) = side_i × 10⁴ × ln(mid(T_i + h) / px_i), for h ∈ {10 s, 60 s, 300 s}.
- score_h(a) = Σ M_i(h) / (n_a + 20), over account a's eligible train taker trades with a finite M. Accounts with
  n_a < 20 are dropped. The K = 20 shrinkage pulls thin accounts toward 0.
- Informed = the top 10 accounts with score > 0. Uninformed = the bottom 10 with score < 0.

**Trading (test days), per cell (direction, h, delay):**
- **Signal:** each eligible test-day taker trade by an account in the cell's set, in any of the three markets.
- **Direction:** follow (the account's side) for the informed set, fade (the opposite side) for the uninformed set.
- **Entry:** at E = T + delay, at the touch as of E (buy at the ask, sell at the bid).
  - delay ∈ {300 ms (Lighter's Standard taker delay alone: a counterfactual), 1,300 ms (primary: 1 s of reaction and
    transport plus 300 ms), 5,300 ms}.
- **Exit:** at E + h, at the opposite touch.
- **One position per market and cell:** a signal whose E falls before the previous exit in that market is skipped.
- **Controls:** follow every eligible test taker trade (all accounts), delay 1.3 s, each h: 3 cells.
- **Size:** $1,000 a trade. A touch thinner than $1,000 at entry or exit is flagged, not walked: there is no
  depth-of-book data.

## Splits and cost
- **Split:** the day split above. No parameter is fitted on test days.
- **Cost:**
  - **Standard account (1x):** 0 fee, plus both half-spreads from the recorded touch:
    cost = 10⁴ × [ln(ask_E/mid_E) + ln(mid_X/bid_X)] for a buy, and the mirror for a sell.
  - **Sensitivity:** 2x and 3x the book cost.
  - **Premium account:** 1x book cost plus 2 × 2.8 bp taker fee (`docs/VENUE_STRUCTURE.md`). Its 140 ms delay is not
    modelled.
- Funding is ignored: the holds are 10 s to 300 s.

## Gates
**Primary cell:** follow, h = 60 s, delay 1,300 ms, Standard cost, all three markets pooled.

**Verdict:**
- **PASS** needs all of:
  - n ≥ 100 trades;
  - mean net at 1x > 0, with the hour-block bootstrap 95% lower bound > 0;
  - mean net at 2x > 0;
  - the primary mean net beats at least 95% of 200 placebo sets.
- **INCONCLUSIVE:** n < 100.
- **NULL:** anything else.

**What a PASS earns:** a frozen forward paper lane on newly recorded days. It is not a live order. Lighter refused
the native runner's jurisdiction (R428), and the owner's eligibility to trade on Lighter is unknown.

Part A and every other cell are reported. They do not change the verdict.

**Power:** assume the per-trade net has a standard deviation of 6-8 bp at 60 s (assumed, not measured) and the
informed set yields 300-1,000 non-overlapping test trades. The minimum detectable mean (80% power, one-sided 5%) is
then about 1-2 bp, before the block dependence widens it. Test hours are about 28 (about 28-40 hour blocks).

## Null
- **Placebo:** 200 sets of 10 accounts drawn at random (seed 433) from the accounts eligible at h = 60 s, run through
  the primary cell's exact rule. The placebo percentile is the share of placebo means below the actual mean.
- **Bootstrap:** whole UTC-hour blocks of entry time, 2,000 replicas, seed 433.
- **Part A:**
  - Spearman correlation between train score and test mean markout, over accounts eligible in train with ≥ 10 test
    trades. Two-sided permutation p from 2,000 shuffles.
  - The informed set's test markout minus the rest's, with an hour-block bootstrap.

## Multiplicity
- **Trials:** 24 = Part B 2 directions × 3 horizons × 3 delays (18) + 3 controls + 3 Part A tests.
- **Not trials:** the placebo draws (a null distribution) and the cost multiples (sensitivity).
- **Program trials at freeze:** 9,784,685 (`registry.program_trials`, after R432). The result is read against it.
- **Decision family:** M441 only. No earlier round scored these accounts.

## Evidence lineage and admission
- **Canonical method ids:** M441. Related: M474, R426, R427, R428 and M467 (blocked, untouched).
- **Samples already seen:**
  - R426's 225 s fragment, disclosed above and excluded from scoring.
  - R427's 134 position transitions: roles only.
- **Fresh sample:** every markout on these days, train and test.
- **`docs/GATES.md`** SHA-256 `ed486814256194323dc2ee7d3375d16f8971a6f7b1775ddb2d6c9e476bf30070`.
  - **Met:** this is gate 1 on an unread recorded tape, as in R348's precedent.
  - **Not met:** it is not a reserved-sample batch, it has no 90 forward days, and it cannot admit real money.
- **Selection control:** the 24 trials are counted here, but there is no across-family correction. The result stays
  exploratory beyond its own verdict rule.

## Stop rules
- **One run.** No horizon, delay, set size, shrinkage, minimum count, split or filter changes after the result.
- **After a crash:** the lane is abandoned (R347), and any successor is a new id.
- **Nothing after the result:** no account is added, removed or relabelled after seeing it.

## Limits known before the run
- **Thin test days:** only 6 test days, and 10-30 carries most of the test trades.
- **No depth:** there is no depth beyond the touch, no queue, and no own-fill impact.
- **Account tiers:** fees differ by account tier and are read only as public fields. The follower is assumed to be a
  Standard account.
- **Access:** Lighter refuses the native runner's jurisdiction (R428), so execution access is unproven.

```inputs
8d01326b61b6f60b519fec8ed8cf187872c3cadc2536de75991203a37f3fa5c1 scripts/run_lighter_flow.py
3c663330eb6ecbaa82b55cb84e51cb184ec7a26f51304fc7bc4772af885bd5a6 tests/test_run_lighter_flow.py
739647623fe7538886aae10cb7dc4749dfad45be01edf0bf37a63ff7b34453ab experiments/lighter_flow_v1/data_manifest.json
164e97f2057a80556d27a9b1576adae0966aae4720a556eb8a065b0e7d0445a9 data/lighter_trades/sessions.csv
```
