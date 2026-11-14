# PREREG: settlehop_fwd (R355). R354's settlement hop, forward on paper, on the rate a trader sees

Freeze with `lab.prereg.freeze()` before the first ticket. Never edited afterwards; a change is a new lane.

- **Registry id:** R355
- **Method:** M267 (settlement-window cross-venue carry), its displayed-rate form. R353 tested the last-settled-rate
  form (NULL) and R354 the predicted-rate form (PASS at gate 0, recorded PARTIAL).
- **Claim:** issue #7, comment 6457499090, before this freeze. This file changes three things in that claim; see
  "Changes from the claim".
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`. The lane's daemon is the only
  writer of `experiments/settlehop_fwd/journal/`; it holds `journal/.writer.lock` and a second writer exits.
- **Date registered (UTC):** 2026-10-28
- **Gate:** 1. Every hop is entered after this freeze, on days no lane has read.
- **Execution mode:** manual-web, decided. Four orders a hop: two within 10 minutes after T − 1 h and two after
  T + 1 h. MEXC's API fee (8 bp a side) is reported, not decided on.
- **Paper only.** Public endpoints, no account, no key. Nothing in the code can place an order.

## Why this lane
- **The owner's format:** a two-hour hedged perp trade, not a long hold.
- **R354 (gate 0, PASS):** an hour before a 4 h or 8 h settlement, Binance's next rate, rebuilt from its premium index,
  forecast the lump to come. Hedged on hourly Lighter and held from T − 1 h to T + 1 h, the hop collected most of it.
  - Primary, Binance + Lighter at θ 0.5%: 87 hops, +30.9 / +10.4 / −10.0 bp a hop at 1x / 2x / 3x, daily NW t 3.24.
  - MEXC + Lighter at θ 0.5%, with Binance's premium as a proxy for MEXC's: 85 hops, +18.8 bp a hop at 8.5 bp a side
    (t 2.36), or +29.8 at MEXC's web fee (3 bp a side, reported only). Hop SD 75 bp; 0.163 hops a day.
  - Against it: the 10 best days held 72% of the sum; 7 hops at Binance's −2% floor held a third; fills after the
    published premium, depth during squeezes and margin were not measured.
- **What R354 earned:** this lane, on MEXC + Lighter with MEXC's own displayed rate, fills from live books, each
  venue's own settlements and the path of each leg.

## What the author has seen
- **R353 and R354 in full,** including their after-run tables.
- **Live plumbing on 2026-10-28, 00:47-00:52 UTC** (counts, fees and one dry read of every call; no hop entered or
  scored):
  - Settling at 04:00 UTC: 468 MEXC contracts (all on a 4 h cycle) and 419 Gate contracts.
  - Lighter: 215 active markets. 117 carry Lighter's crypto funding setting (premium multiplier 100). The other 98 are
    stocks, ETFs, FX, commodities, pre-IPO and pre-launch markets (multiplier 50 or 1).
  - 69 of the MEXC and 64 of the Gate contracts settling at 04:00 have a Lighter crypto market under the same base.
  - Taker fees: MEXC 0, 2, 4 or 10 bp by contract; Gate 7.5 bp on all; Lighter 0 on all.
  - The largest |displayed rate| among MEXC contracts with a Lighter market was 0.037%: no candidate existed.
  - One coin's MEXC and Lighter books, daily closes (correlation 0.987), funding history and contract size, and one
    Gate book, closes and funding history, all read as expected.
- **Before this live check,** the claim's draft let any Lighter market in. MEXC's palladium perp (XPD_USDT, typed as
  crypto by MEXC) matched Lighter's XPD. R354's books were crypto only, so the rule now requires Lighter's crypto
  setting. No rate or return of any TradFi market was read for this.

## The rule
Fixed in `scripts/settlehop_rule.py` (pure functions and constants) and run by `scripts/forward_settlehop.py`. A tick
runs at hh:00:20 UTC.
1. **Exits:** every open hop whose T + 1 h has passed is closed. A $1k market order is walked through each leg's live
   book (100 levels). An exit always closes: depth beyond the shown book fills at the last shown level and is flagged.
2. **The decision for T,** the next full hour, is taken once, at the first tick within 10 minutes after T − 1 h.
3. **Settling contracts** on venue S, read at the decision:
   - MEXC: USDT crypto contracts (type 1, state 0) whose `nextSettleTime` is T and whose `collectCycle` is 4 or 8 h.
     F is the displayed `fundingRate`. The contract list, sizes and fees are MEXC's daily snapshot.
   - Gate (reported only): USDT contracts not in delisting whose `funding_next_apply` is T, on a 4 or 8 h
     `funding_interval`. F is `funding_rate`.
4. **Hedge venue H = Lighter:** an active market whose funding premium multiplier is 100 (crypto), matched on the
   base without a 1000/1000000/k size prefix. h is Lighter's last hourly settlement at or before T − 1 h; with none in
   the 2 hours before T − 1 h, the contract is skipped.
5. **Signal:** e = F − 2h; d = sign(e). d = +1 shorts S and buys Lighter.
6. **Candidates:** |e| ≥ 0.3%, ranked by |e|, largest first. Every contract with |e| ≥ 0.2% is logged with its
   status.
7. **Entry,** candidate by candidate, until 5 hops are entered on the venue or 10 minutes after T − 1 h have passed:
   - R353's identity check: daily returns of the two contracts' 00:00 UTC closes, over the 31 closes up to the
     decision, correlate at 0.9 or more on at least 20 paired days.
   - A contract size must be known.
   - Both books are read. Each $1k leg must fill within the shown depth, or the hop is skipped.
   - The entry is ticketed at the time the books were read, with both fills, best bids and asks, and both fees.
8. **Path:** while a hop is open, each leg's bid, ask and mark (Lighter: last trade and mark) are logged every minute.
9. **Score,** 20 minutes after the exit:
   - **Prices:** gross = d·(r_H − r_S), each r from the entry mid to the exit mid.
   - **Funding:** each venue's own settlements in (entry, exit], from its history: fund = d·(ΣF_S − ΣF_H).
   - **Book cost:** the four fills against their mids.
   - **Fees:** manual-web: S's listed taker for the contract, a side, plus Lighter's (0). API: 8 bp a side on MEXC;
     Gate has one published fee.
   - net_k = gross + fund − k·(book cost + fees), for k = 1, 2, 3, as fractions of one leg's notional.
   - **On time:** entry and exit each within 10 minutes of their hour. A late ticket is kept and reported, never decided
     on.
10. **Status,** every tick: the decision below, the books, `lab.gate.go_real()` on the primary book and the other
    statistics, in `journal/status.json`.

## Books
| Book | Venues | θ (|e| ≥) | Role |
|---|---|---|---|
| **Primary** | **MEXC + Lighter** | **0.5%** | **decided: on-time hops, net at the web fee** |
| MEXC θ 0.3% | MEXC + Lighter | 0.3% | reported |
| Gate θ 0.5% and θ 0.3% | Gate + Lighter | 0.5%, 0.3% | reported |

## Decision (the primary book, on-time hops in entry order)
- **Futility:** if the mean 1x net of the first 20 hops, or of the first 40, is ≤ 0: **NULL**.
- **Interim look at 40 hops:** **PASS** if the CR1 t of the 1x net (standard error clustered by settlement time) is
  ≥ 2.97 and the 2x mean is > 0.
- **Final look at 80 hops, or on 2028-03-01 00:00 UTC on the hops scored by then (at most 80):** **PASS** if the CR1 t
  is ≥ 2.10 and the 2x mean is > 0; **NULL** otherwise. Fewer than 20 hops by then is **INCONCLUSIVE**, recorded NULL.
- **The verdict is final at its look.** Hops after it are reported only. `verdict()` reads only the first 20, 40 or 80
  hops, so a later hop cannot change it.
- **What a PASS earns:** gate 1 (CONFIRMED) for this book. `go_real()` on the same hops is reported for gate 2; gate 3
  (margin and liquidation) needs its own frozen PREREG, using the path recorded here. No money moves without the owner.
- **What a NULL means:** M267's displayed-rate form failed forward. R354 stays a gate-0 PARTIAL.

## Calibration and power (computed before the freeze, no forward data)
- **Bounds:** O'Brien-Fleming-shaped (interim bound √2 × the final). They were raised until R354's 85 MEXC θ 0.5%
  hops (79 settlements), resampled in whole settlements with the mean removed and run through `verdict()` with the
  futility looks, passed 2.5% of the time (12,000 draws; 0.3% at the interim).
- **Power,** the same resampling shifted to each mean (4,000 draws each; a normal model with R354's SD gives PASS
  rates within 2 points):

  | Mean net a hop | PASS, 80 hops by the end | PASS, 59 hops by the end | Of which at the interim (80) |
  |---|---|---|---|
  | 0 | 2.5% | 2.5% | 0.3% |
  | +18.8 bp (R354 MEXC, API cost) | 55% | 45% | 13% |
  | +25 bp | 78% | 67% | 26% |
  | +29.8 bp (R354 MEXC, web fee) | 89% | 82% | 39% |

- **80% power needs about +26 bp a hop over 80 hops.** Below that the lane is a **futility screen**, as `docs/GATES.md`
  requires it to say.
- **Speed:** at R354's 0.163 MEXC hops a day, 40 hops come in about 8 months (around 2027-06) and 80 by about
  2028-03-01. Fewer will come if books are thin, identity checks fail, Lighter lists fewer coins, or the container is
  down.

## Costs (1x, 2x, 3x)
- **1x web (decided):** the measured book cost of the four sides at $1k, plus MEXC's listed taker fee for the
  contract (two sides), plus Lighter's (0 now).
- **2x and 3x:** book cost and fees doubled and tripled.
- **API (reported):** 8 bp a MEXC side instead of the listed fee.
- **Gate (reported):** its published taker fee (7.5 bp on all contracts on 2026-10-28) plus its measured book. R353 and
  R354 charged Gate 7 bp a side in all; see the note in R354's FINDINGS.

## Reported (not decided on)
- For every book: hops, scored, on-time, mean net at 1x/2x/3x (web and API), hit rate.
- For the primary: the trimmed mean (10 best and 10 worst hops removed), the leave-two-coins-out mean (both coins with
  the largest summed net removed), `go_real()`, and the CR1 t.
- For each hop: F against its cap, Binance's displayed rate for the coin (Lighter's `funding-rates`), the settlements
  paid on both venues, an hourly switch after T, both fills against the mids, and the worst excursion of each leg and of
  the pair at the marks.
- Late decisions, venue errors and every skipped candidate with its reason.
- **Read against** `registry.program_trials()`: 9,479,087 on this branch before this lane and 9,479,088 after it (or
  9,479,104 → 9,479,105 counting #56's R338-R346).

## Code
```fixed
bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c scripts/settlehop_rule.py
```

| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `scripts/settlehop_rule.py` | bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c | fixed: the daemon checks it and this file before every tick and stops if either changed |
| `scripts/forward_settlehop.py` | 9c69d549a1f713da011d8241211f1976def358ecdff85fda5fc26880874082df | data plumbing only |
| `tests/test_forward_settlehop.py` | 7ed4e12586a9143300d4870ed2089c1762a82844e746035384d5a9ef0643412a | 27 tests (mocked venues) |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 | data plumbing only (Gate and Lighter clients) |
| `lab/mexc.py` | 7d371f0aba11aeaeaf3c050bfbc0f0f072c1c425786688ab2dbc7683c4c997d6 | data plumbing only (MEXC client) |
| `lab/gate.py` | 2658c3b776cf61d920f4d0542ebd4c4f2fda6efe5f0798bc7938b383983c8899 | `go_real()`, reported only |
| `lab/prereg.py` | 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 | freeze and verify |

- **Changes after the freeze:** data plumbing only (venue clients, retries, file handling). Each change needs the
  tests to pass and a line in `journal/CHANGES.md` with its commit. A change to the rule, the books, the accounting or
  the decision is a new lane.
- **Start and restarts:** the forward loop's hourly task runs `scripts/forward_settlehop.py` (`ensure`). It starts the
  daemon when no writer holds the lock, after checking this file and the fixed rule. After a container restart the
  journal resumes; hours the daemon missed are late and are never decided on.

## Changes from the claim (comment 6457499090), made before this freeze
- **Bounds 2.80 / 1.98 → 2.97 / 2.10.** The claim's bounds passed 3.0-3.1% of the time under the dependent null that
  `docs/GATES.md` requires (R354's hops resampled by settlement, 40,000 draws); its 2.1-2.6% came from independent
  hops. The new bounds pass 2.4% in the same draws and 2.5% through `verdict()`.
- **End date 2027-10-31 → 2028-03-01,** so that 80 hops are expected at R354's MEXC rate. The claim expected about 59.
- **Universe:** Lighter crypto markets only (premium multiplier 100), as R354's books were. See "What the author has
  seen".

## Deviations from R354, all fixed here
- MEXC's own displayed rate replaces Binance's rebuilt premium; Binance is not traded.
- Live books at the decision replace hourly closes. Fills are walked at $1k a leg, and a thin book skips the hop.
- Costs are the measured books plus listed fees, not flat levels by volume band.
- The decision is a hop-level clustered t with group-sequential looks, not a daily Newey-West t.
- Funding is each venue's own history over the hold, so an hourly switch after T is paid as it comes.
- The universe is MEXC crypto contracts with a Lighter crypto market under the same base, not Binance perps.

## Evidence lineage and admission
- **Method:** M267. **Parents:** R353 (NULL), R354 (PASS, gate 0), R223, R275, R277, R288.
- **Decision group:** M267's displayed-rate form, forward. One decision; the Gate and θ 0.3% books are diagnostics.
- **Samples:** every hop is entered after this freeze. There is no overlap with any archive any lane has read.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one decision per signal; strict on-time hops only (10 minutes, stricter than 60); a one-sided test calibrated
    under a dependent null; trimmed and leave-two-coins-out means reported (per hop, the lane's unit); power stated.
  - Labelled: a futility screen for edges below about +26 bp a hop.
  - Left for later: gate 3 (account risk) needs its own PREREG.
- **R354's PREREG:** sha256 `799ffb1bbb7367189dcb6294f75892979de580dedbca31d883b265cfa1426e05`.

## Stop rules
- The lane ends at its verdict. After it, the daemon is stopped by the owner of the lane, and no hop after the verdict
  is decided on.
- A changed PREREG or rule stops the daemon at its next tick. The lane is then over, and a new idea is a new lane.
- Not allowed after the first ticket: new thresholds, new books in the decision, a different cost, a different look
  schedule, or dropping hops.

## Known limits (written before the first ticket)
- **Fills are paper:** a walked book at the time it was read, with no queue, latency or partial fill. A real order
  comes seconds later, in a fast market.
- **Two venues, two margins:** each leg is margined on its own venue. No liquidation is modelled here; the path gives
  each leg's worst excursion at the marks for gate 3.
- **The container:** the daemon runs only while this container runs. Hours it misses are late and excluded, which
  slows the lane and can skip the largest squeezes if they come while it is down.
- **Same coin:** a 30-day correlation of 0.9 can still pass a contract that later diverges.
- **MEXC's displayed rate** is read once at T − 1 h + 20 s. It can still move before T. The lump paid is what counts.
- **Lighter's crypto flag** is Lighter's funding setting, not a list. A crypto market Lighter funds like TradFi is left
  out.
