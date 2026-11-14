# PREREG: announce_fwd (R272). R271's two candidates forward on MEXC paper: funding-frequency long 1 h, pre-listing short 168 h

Freeze with `lab.prereg.freeze()` before the first ticket. Never edited afterwards; a change is a new lane.

- **Registry id:** R272 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 1 (forward). Only notices first seen from 2026-10-20 19:00 UTC count. They were unseen when this was
  frozen.
- **Source:** R271 announce_v1 (gate 0, family NULL). The two best strategies by t and by size:
  - **FF:** fund_freq long +1 h. +3.59% per notice, median +3.97%, t 3.31, n 35 (2021-26), 2x +3.19%, 3x +2.79%.
  - **PL:** prelist short +168 h. +11.48% per notice, median +18.05%, t 2.03, n 45 (37 from 2025-26), 2x +11.08%,
    3x +10.68%.
  - Neither cleared R271's family reality check. This lane asks whether they hold on days nobody had seen.
- **What the author knows that weakens FF:**
  - R273 (fundext_v1) found that the data-defined version, the onset of capped funding, does not reproduce it: neg1
    long +1 h -0.60%, t -2.81.
  - Since 2026, Binance titles funding-frequency changes "Important Updates on Funding Rate Settlement Frequency of
    USDⓈ-M Perpetual Contracts" or "Important Updates on the Funding Rate of USDⓈ-M XUSDT Perpetual Contract". R271's
    title rule (frozen in `scripts/announce_events.py`) matches neither, so FF may never fire.
  - FF is kept as frozen. A new rule for the new titles would be a new lane.
- **What weakens PL:** pre-listing notices came about once a month in 2026 (8 by June, none since July in the recorded
  catalogs). Many of the coins have no MEXC perp at the notice.
- **Execution mode:**
  - FF: API (a 1 h hold).
  - PL: manual-web. The entry and the cover a week later can be placed by hand when the owner is alerted.
- **Code:** `scripts/forward_announce.py` (tests: `tests/test_forward_announce.py`).
  - `scripts/notice_loop.sh` runs it every 5 minutes, right after the notice recorder.
  - `scripts/forward_all.sh` also runs it every hour.
  - Both runs share one lock with the notice recorder, so the catalogs have one writer.
  - Ticketing reuses R268's code: contract lookup, identity check and the missed rule.
- **Paper only.** Nothing here places an order.

## Events
- **Catalogs:** Binance's News, New Cryptocurrency Listing and Delisting catalogs, recorded by
  `scripts/record_notices.py` (`data/recorders/notices/binance_{news,listing,delisting}.csv`).
  - A notice counts if its `first_seen_utc` is at or after 2026-10-20 19:00 UTC.
  - One notice filed in two catalogs counts once.
- **Classification:** `announce_events.parse(title)` from R271, unchanged (sha256 37eba18f... as frozen in R271's
  inputs). FF uses type `fund_freq`; PL uses type `prelist`.
- **One ticket per (book, notice, ticker)** with an open MEXC USDT perp (R268's `contract_for`, including the 1000/1000000
  prefixes).
  - No perp: skipped `no_contract`.
  - If the MEXC last price and the Binance spot price for the ticker differ by more than 3× (after the multiplier),
    skipped `mismatch`. With no Binance spot price the ticket is kept and marked `unverified`.

## Trade (per ticket)
- **Ticket time:** the run that first sees the notice. It writes the ticket before its entry bar opens.
- **Entry:** the open of the first full hour after the ticket.
  - If that is more than 3 h after the notice's release, the notice is skipped `missed`.
  - With the 5-minute loop, entry is usually the first hourly open after the notice, as in R271.
- **Exit:**
  - FF: the open of entry + 1 h. Logged: entry + 24 h.
  - PL: the open of entry + 168 h. Logged: entry + 24 h and + 72 h.
  - If the contract stops trading, the last close before the exit is used, flagged `stopped_trading`.
- **Prices:** MEXC hourly bars (`mexc.fetch_klines`).
- **Funding:** MEXC settled funding in (entry, exit]. The short receives a positive rate; the long pays it.
- **Measured cost:** 2 × the contract's taker fee, plus half the bid-ask spread at entry and at exit, from the hourly
  MEXC ticker recorder (10 bp per leg when the recorder has no quote: `spread_flag`).
- **Model costs:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x (R271's).
- **Net:** gross minus cost plus funding (the long's funding is negative when it pays).
- **Logged, not gated:**
  - the MEXC funding rate at the ticket (for a signed FF rule later);
  - the maximum adverse move over the hold;
  - the logged horizons.

## Decision (each book separately)
- **Observation:** one per notice, the mean net (measured cost) of its tickets.
- **Scored:** once the last horizon's bar has closed (FF after 24 h, PL after 168 h).
- **Bonferroni over the two books:** PASS needs t >= 2.2 (one-sided 0.025 at 11 degrees of freedom).
- **Rules:**
  - **PASS (gate 1 forward):** at 12 scored notices, t >= 2.2 and the mean at 2x model cost > 0.
  - **NULL:** at 12 scored notices otherwise.
  - **Futility:** at 6 or more scored notices with a negative mean, NULL.
  - **Deadline 2028-06-30:** the rule above is applied to whatever is scored, marked underpowered.
- **go_real** (lab/gate.py) is reported, not gated.
- **A PASS goes to gate 2:** a frozen small-stake plan, placed by the owner. Nothing here moves money.
- **Registry:** R272 is RUNNING with 2 trials (the two books) until both books are decided.
