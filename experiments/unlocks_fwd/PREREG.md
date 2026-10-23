# PREREG: unlocks_fwd (R266). The unlock short, forward on MEXC paper, with point-in-time events

Freeze with `lab.prereg.freeze()` before the first ticket. Never edited afterwards; a change is a new lane.

- **Registry id:** R266 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Owner (single writer):** the Claude session that froze it. It writes only `experiments/unlocks_fwd/journal/` and
  `data/mexc/`.
- **Code:** `scripts/forward_unlocks.py`. It uses `scripts/unlock_events.py` (`cliff_days`, the R265 event rule) and
  `lab/mexc.py`. It runs in every forward tick (`scripts/forward_all.sh`) and is idempotent.
- **Source:**
  - R265 (unlocks_v1) REPLICATES at gate 0: +3.24% net per event, t 3.19, 422 events in 2021-26.
  - Codex's R258 (daily bars) reproduces it: +3.26%, t 3.20.
  - Codex's R259 bounds settlement funding at 23-82 bp per event, and finds intraday highs far above the closes (STO
    +1,623%).
  - Both old reads are in-sample, so only forward events and the reserved samples are clean.
- **Gate:** 1 (forward, on-time). **Execution mode:** manual-web, two orders per event, at the owner's hand.
- **Paper only.** Nothing here places an order. Real money needs `lab.gate.go_real()` and the owner (AGENTS.md
  rules 5-6).

## What the author has seen
- R265 in full, and Codex's R258 and R259 summaries on issue #7.
- The 2026-10-20 calendar snapshot, including the list of events due after 2026-10-20: the first entries are RESOLV
  (unlock 10-27), GUN and ZORA (10-30), EIGEN (10-31), ZETA (11-01) and STO (11-02).
- A dry run of the event builder on the 2026-10-20 recorder snapshot, with today's MEXC contract list (no prices):
  - 437 events with E from 2026-10-21; 367 of them have a MEXC contract;
  - every R265 forward event is among them.
- No MEXC price, funding or spread after 2026-10-20 for any of these contracts. MEXC history files exist up to
  2026-10-20 (`scripts/fetch_mexc_history.py`) and have not been read for these events.

## Events (point-in-time)
- **Snapshot:** at each tick, the newest `data/recorders/unlocks/<YYYY-MM-DD>.json.gz` dated on or before the tick's
  UTC day. This is the DefiLlama emissions index, recorded daily by `scripts/record_unlocks.py`, and its sha256 is
  journaled in `experiments/recorders/journal/digests.csv`.
- **Token data:** for each index row with a gecko_id:
  - ticker = `tokenPrice[0].symbol`, upper case;
  - max supply = the index `maxSupply`;
  - the unlocks are the index `unlockEvents`.
- **Rule (R265's, unchanged):**
  - cliff allocations in insiders and privateSale, summed per UTC day D;
  - D qualifies at 1% of max supply or more;
  - per token, a qualifying day is kept only if it is at least 14 days after the last kept one, scanning that
    snapshot's whole history in order.
- **Exclusions:** tickers GRAM, ETH, BNB, POL and FTM.
- **Contract:**
  - The MEXC USDT perpetual of type 1 (crypto), state 0 (open), with base equal to the ticker, or to the ticker with a
    1000 or 1000000 prefix (multiplier 1e3 or 1e6), or to its `lab.mexc.ALIAS`.
  - **Check at ticket time:** MEXC last price / (index price x multiplier) must lie in [1/3, 3]. Otherwise skip with
    reason `mismatch`.
  - Tokens with no such contract are skipped with reason `no_contract`.
  - A second token on a contract that already has a ticket for the same D is skipped with reason
    `duplicate_contract`.
  - Binance-listed and MEXC-only tokens are both included, and reported separately.

## Ticket
- **Entry time:** E = 00:00 UTC of day D-6, the close of D-7.
- **When a ticket is written:** at a tick with E - 24 h <= now < E + 1 h, if the event qualifies in that tick's
  snapshot and has no ticket yet. `frozen_at` = now.
  - Missing that window means no ticket. The skip is journaled as `missed` once the window has passed.
- **Entry price:** the open of the MEXC Min60 bar starting at E + 1 h. This is one bar after R265's entry, so the
  ticket is always frozen before its entry bar opens.
- **Exit price:** the open of the Min60 bar starting at X + 1 h, with X = 00:00 UTC of D+1. If the contract has no bar
  then, the last close before it is used, and the ticket is flagged `stopped_trading`.
- **Gross:** `-(exit / entry - 1)`, unlevered.
- **Funding:** MEXC settled funding with settle time in (E + 1 h, X + 1 h]. The short receives `+rate` for each
  settlement.
- **Measured cost:**
  - 2 x the contract's taker fee (from today's contract list);
  - plus half the bid-ask spread at entry and at exit, from the MEXC ticker recorder's file for those hours
    (`data/recorders/mexc_ticker/<date>/<HH>.parquet`, bid1/ask1).
  - A missing spread uses 10 bp for that leg, and the ticket is flagged.
- **Model cost:** 20, 40 and 60 bp round trip (R265's 1x/2x/3x).
- **Path, logged and not traded:**
  - MAE = max high / entry - 1 over the bars held;
  - MFE = 1 - min low / entry;
  - liquidation flags at isolated leverage L = 1, 2 and 3 when MAE >= 1/L - 1%.
  - **No stop is applied.** Stops are a separate, later lane (the archive's paths are already seen).

## Scores and decision
- **Primary per ticket:** `net = gross - measured cost + funding`. Also reported: net at the model 1x/2x/3x cost
  (with funding), and gross.
- **Clustering:** week-cluster t (ISO week of D), as R265.
- **Decision at 120 scored tickets:**
  - **PASS (gate 1 forward)** if the primary week-cluster t >= 2 and the mean net at the model 2x cost with funding
    is > 0.
  - Otherwise **NULL**.
- **Futility:** at 60 scored, NULL if the primary mean is < 0 and t <= -1.
- **Deadline:** 2027-12-31. With fewer than 120 scored by then, the same rule applies to what exists, labelled
  underpowered.
- **Power note:** at R265's per-event signal-to-noise ratio (about 0.19), 120 events give an expected t of about 2.1.
  This is about one year of events.
- **Reported every tick, not gated:**
  - `lab.gate.go_real()` on the primary nets. Its no-tail rule (no event below -40%) failed 6 times in R265's archive.
  - Binance-listed vs MEXC-only subsets.
  - Dose bands as R265.
  - Liquidation-flag counts.
  - **A book line:** each open ticket holds 10% of capital at 1x notional, marked daily on MEXC closes; reports
    equity and max drawdown.
- **Trials:** 1.
- **What PASS earns:** the owner may consider a small real stake through `go_real()`, with a capital and protective
  model frozen separately (Codex's archive work) before any stake.
