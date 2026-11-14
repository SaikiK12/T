# PREREG: settlelit_fwd (R364). R363's Lighter settlement scalp, forward on paper, on Binance's live predicted rate

Freeze with `lab.prereg.freeze()` before the first ticket. Never edited afterwards; a change is a new lane.

- **Registry id:** R364
- **Method:** M267 (settlement-window cross-venue carry), its Lighter-route form, forward. R363 tested it at gate 0
  (PASS by its frozen rule, recorded PARTIAL), and its PREREG names this lane as what a PASS earns.
- **Claim:** issue #7, comment 6472025942, before this freeze. This file changes the claim's trigger and adds a cost
  gate; see "Changes from the claim".
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`. The lane's daemon is the only
  writer of `experiments/settlelit_fwd/journal/` and `data/settlelit_fwd/`; it holds `journal/.writer.lock`, and a
  second writer exits.
- **Date registered (UTC):** 2026-10-28
- **Gate:** 1. Every hop is decided and entered after this freeze, on settlements no lane has read.
- **Execution mode:** API on Lighter (no fee on a standard account): two orders a hop, at T − 10 s and T + 60 s. The
  signal is Binance's public predicted rate; nothing is traded on Binance.
- **Paper only.** Public websockets and endpoints, no account, no key. Nothing in the code can place an order.

## Why this lane
- **The owner (2026-10-28, 13:42 UTC):** "We need a hft trading with good pnl troughout the day".
- **R363 (gate 0):** on R354's 134 θ 0.3-0.5% hops that R356 never read, a position on Lighter against the side that
  received Binance's deep lump, entered at the last trade before T and closed at the last trade before T + 1 min:
  - price +40.1 bp, Lighter's own settlement at T −12.9 bp, R354's band cost 3.8 bp a round trip;
  - net +23.4 / +19.6 / +15.8 bp a hop at 1x / 2x / 3x (CR1 t 4.34); all 221 hops +41.7 bp at 1x (SD 80.6 bp).
  - Not blind: R362 had read those hops' Binance seconds. Minute closes are not fills, the book around a settlement
    was never recorded, and the rate was rebuilt from Binance's archive, not read live.
- **R362 (NULL):** the move is a burst inside the first seconds after T (+44 bp by 1 s, +85 bp by 15 s on Binance), so
  a Binance taker who waits out Binance's 15-second funding deviation is too late. A Lighter position opened before T
  needs no speed: it rides the burst and pays one hour of Lighter's own rate.
- **What R363 earned (its PREREG's words):** "a forward paper lane on Lighter under a new id, frozen before its first
  ticket. It reads the predicted rates point-in-time at T − 1 h, as R355 does, places a paper ticket before T, and
  scores it on Lighter's live book."

## What the author has seen
- **R354, R356, R362 and R363 in full,** including their after-run tables. R355's journal (no hop yet).
- **Live plumbing on 2026-10-28, 14:50-15:45 UTC** (counts, formats and dry reads; no ticket of this lane):
  - Binance `!markPrice@arr` on fstream's `/market` path: 974 symbols, each with its predicted rate `r` (per
    settlement) and next funding time `T`. At 15:0x, 924 showed 16:00 UTC and 50 showed 0 (expired contracts).
    Messages carry a subset of symbols, about one a second. The local clock was within 1 ms of Binance's event time.
  - Lighter `market_stats/all`: 235 markets. `funding_rate` is the last hourly settlement in percent, signed
    (CASHCAT −0.0364 and CAP −0.0095 matched the REST history's "short 0.0364" and "short 0.0095"), stamped a few ms
    after the hour (14:00:00.003).
  - Lighter's REST market list: 241 perps; the crypto setting (premium multiplier 100) as in R355.
  - Binance's funding archive, its 2026 rows' interval column only: 1 h, 4 h and 8 h cycles (179, 507 and 345
    coins), none of 2 h. So a coin whose next funding time was T by T − 1 h − 60 s is on a 4 h or 8 h cycle.
  - A dry `select()` for 16:00 UTC with the first-seen times moved before 14:59: 858 eligible Binance perps, 106 with
    a Lighter crypto market, 0 candidates. The largest |r| settling then (BLUR −0.78%, DOOD −0.38%) had no Lighter
    market.
  - Lighter's `order_book` channel: one connection held four subscriptions; 930 updates each chained on the last
    nonce (`begin_nonce` = the previous `nonce`), with no gap. Size 0 removes a level. `trade` and `market_stats`
    channels as expected. Binance's per-symbol `markPrice@1s` and `aggTrade` streams answer on `/market`.
  - Lighter's `funding-rates` feed (the claim's trigger): 191 Binance rows keyed by Lighter market id, in 8 h terms
    (BTC 0.0072% against Binance's own 0.0065% per 8 h).
  - **End-to-end book window on a fake T** (15:16 UTC, not a settlement; BTC short, ETH long, KAITO short; temp
    folders; an invented settlement for the accounting):
    - all 15 walks on live books, on the right side, 1-3 ms after their instants; no thin walk, no REST exit;
    - 15 recordings in 13 minutes: 0.8 MB of gzip for the three coins;
    - the scores matched a hand check (BTC: gross −1.22, settlement −1.00, book 0.57, net −2.79 bp).
    - KAITO's book was about 1% wide: its round trip cost 81.6 bp at $1k.
  - **Lighter's books, cost data only** (`data/recorders/lighter_book/`, the six snapshots of 2026-10-27/28; no
    return of any kind). The $1k round trip, median per market:
    - KAITO 70, RIVER 61, AVNT 163 and BERA 22 bp. These are the four coins that held 77% of R363's sum.
    - BTC, ETH and SOL about 0.5 bp.
    - Across the 201 markets: median 9.4 bp; 52% at or below 10 bp.
    - R363 charged R354's volume-band costs instead (mean 3.8 bp a round trip), which put a thin coin in a busy hour
      on a deep book's cost. This is why the cost gate (rule 7) was added.
  - **The cost gate live,** in a dry `select()` for 20:00 UTC with θ set to 0 in the smoke script only: 12 REST books
    read in 15.8 s (BERA 21.9, RIVER 65.0, QNT 7.3, TRX 1.8 bp), 5 selected.
- **Before this freeze the rule was changed three times, on plumbing and cost data alone** (no return of any kind was
  read):
  - the trigger moved from the feed to Binance's own stream (see "Changes from the claim");
  - the look bounds were set from R363's hops (see "Calibration and power");
  - the cost gate was added after the book costs above (rule 7).

## The rule
Fixed in `scripts/settlelit_fwd_rule.py` (pure functions and constants) and run by `scripts/forward_settlelit.py`.
d is the position on Lighter: +1 long, −1 short. Rates are per settlement, positive when longs pay.
1. **Settlements:** every T on a 4 h boundary (00/04/08/12/16/20 UTC), Binance's 4 h and 8 h cycles.
2. **Decision window,** T − 1 h − 5 min to T − 1 h + 20 s: Binance's `!markPrice@arr` stream and Lighter's
   `market_stats/all` stream, plus Lighter's REST market list read once.
3. **Eligible Binance perps:** USDT-margined perpetuals (no underscore) whose next funding time is T and was already T
   in the stream by T − 1 h − 60 s. A coin on a 1 h cycle shows T − 1 h until it settles then, so it is left out, as
   R354 left out everything but 4 h and 8 h settlements. A window that opens after T − 1 h − 60 s sees no eligible
   coin, and its decision row says so.
4. **Lighter market:** active, premium multiplier 100 (crypto), under the same base without a 1000/1000000/k prefix.
   h is its last hourly settlement at or before T − 1 h (the stamp floored to the second), at most 2 h before
   T − 1 h; with none, the coin is skipped and logged when |r| ≥ 0.2%.
5. **Signal (R354's):** at T − 1 h + 20 s, r is the coin's latest predicted rate in the stream; e = r − 2h and
   d = sign(e). d = −1 (short Lighter) when Binance's longs receive the lump.
6. **Candidates:** |e| ≥ 0.3%, ranked by |e|, largest first (ties by symbol). Every coin with |e| ≥ 0.2% is logged
   with its status (signals.csv), and every decision writes one row (decisions.csv).
7. **Selection,** candidate by candidate:
   - identity: Lighter's mid (market_stats; its last trade if no mid) within 5% of Binance's mark;
   - one hop per Lighter market;
   - up to 5 hops a settlement;
   - the hop's base quantity is fixed here: q = $1,000 / Lighter's mid;
   - **cost gate:** q walked both ways on Lighter's REST book (100 levels a side), read at the decision, costs at
     most 10 bp of the mid, (buy average − sell average) / mid. A book that cannot hold q, or cannot be read, fails.
     Only a candidate that reaches this check has its book read; the round trip is logged.
   - A decision later than T − 1 h + 10 min selects nothing.
8. **Book window,** T − 7 min to T + 6 min, for the selected hops: Lighter's `order_book`, `trade` and `market_stats`
   channels and Binance's `markPrice@1s` and `aggTrade` streams for the coin. The book is held in memory; an update
   that does not chain on the last nonce, or a dropped connection, reconnects for a fresh snapshot, and the book is
   not live until it arrives.
9. **Entry (primary): at T − 10 s,** q is walked on the live book, selling into the bids for d = −1 and buying the
   asks for d = +1. The hop is entered when the book is live and two-sided, the shown depth holds all of q, and the
   walk comes before T − 1 s. Otherwise it is not entered, and the reason is logged.
10. **Exit (primary): at T + 60 s,** q is walked on the other side. An exit always closes, but never beyond a shown
    book: what the book cannot hold is walked again on the next second's book, and what is still owed at T + 6 min
    (or after a restart) on Lighter's REST book (100 levels) once a minute until it fills. The exit's time, parts,
    lateness and source are logged.
11. **Reported walks:** the entry side at T − 5 min, the exit side at T + 2 min and T + 5 min, all of q. With the
    primary walks they make R363's six trials (entries T − 5 min and T − 10 s, exits T + 1, 2 and 5 min).
12. **Score,** 20 minutes after the primary exit, as fractions of the entry notional q · m0 (m0, m1: the mids at the
    entry and exit walks; f0, f1: the walks' average prices):
    - **gross** = d (m1 / m0 − 1);
    - **book cost** = d (f0 − m0) / m0 + d (m1 − f1) / m0;
    - **fee** = Lighter's listed taker rate × (f0 + f1) / m0, on both fills' notional;
    - **funding** = −d × the sum of Lighter's settlements stamped in (entry, exit], from its funding history;
    - **net_k** = gross + funding − k (book cost + fee), for k = 1, 2, 3.
    - A settlement not in Lighter's history 24 h after T is scored as 0 and flagged.
13. **On time:** the decision at T − 1 h + 20 s (rule 7) and the primary entry within 5 s of T − 10 s on a live book.
    The exit is whatever came first after T + 60 s, so no entered hop leaves the decided book for a late exit; the
    exit's lateness is reported.
14. **Status:** `journal/status.json`, with the decision below, the books, `lab.gate.go_real()` on the primary book and
    the other statistics.

## Books
| Book | Hops | Role |
|---|---|---|
| **Primary** | **\|e\| ≥ 0.3%, entered on time at T − 10 s, exited at T + 60 s** | **decided, at 1x** |
| θ 0.5% | the primary's hops with \|e\| ≥ 0.5% | reported |
| R363's other five trials | entries T − 5 min / T − 10 s × exits T + 1 / 2 / 5 min | reported (1x) |

## Decision (the primary book, hops in entry order)
- **Futility:** if the mean 1x net of the first 20 hops, or of the first 40, is ≤ 0: **NULL**.
- **Interim look at 40 hops:** **PASS** if the CR1 t of the 1x net (standard error clustered by settlement time) is
  ≥ 2.80 and the 2x mean is > 0.
- **Final look at 80 hops, or on 2027-10-28 00:00 UTC on the hops scored by then (at most 80):** **PASS** if the CR1 t
  is ≥ 1.98 and the 2x mean is > 0; **NULL** otherwise. Fewer than 20 hops by then is **INCONCLUSIVE**, recorded NULL.
- **The verdict is final at its look.** `verdict()` reads only the first 20, 40 or 80 hops, so a later hop cannot
  change it; later hops are reported only.
- **What a PASS earns:** gate 1 (CONFIRMED) for M267's Lighter route. `go_real()` on the same hops is reported for
  gate 2. Gate 3 (account risk: margin and liquidation over the recorded seconds) needs its own frozen PREREG. No money
  moves without the owner, through `lab.gate.go_real()`, in small stakes.
- **What a NULL means:** R363's route does not survive live books on fresh settlements whose Lighter book passes the
  cost gate. R363 stays a gate-0 PARTIAL.

## Calibration and power (computed before the freeze, no forward data)
`scripts/calib_settlelit_fwd.py`, on R363's 221 primary nets (`experiments/settlelit_v1/results/hops.csv.gz`, sha256
`320f1e0d1656393b2443bb8a850c14ac11cad07546cd410b6ead597fc0b8731c`; mean +41.7 bp, SD 80.6 bp, 204 settlements):
- **Bounds:** O'Brien-Fleming for two equal looks at one-sided 2.5% (2.80 at 40 hops, 1.98 at 80), never lowered.
  With R363's nets resampled in whole settlements and their mean removed (12,000 draws, the 2x condition switched off;
  applied, it can only lower the rate), `verdict()` with its futility looks passes 1.94% of the time with 80 hops
  (0.16% at the interim) and 1.88% with 60 hops by the end date. No raise was needed.
- **Power,** the same draws shifted to each mean, with the 2x net charged R354's cost once more (4,000 draws each):

  | Mean 1x net a hop | PASS, 80 hops | Of which at the interim | PASS, 60 hops by the end |
  |---|---|---|---|
  | 0 (the size above: 2x off, 12,000 draws) | 1.94% | 0.16% | 1.88% |
  | +10 bp | 18% | 2% | 14% |
  | +15 bp | 36% | 5% | 28% |
  | +20 bp | 56% | 11% | 48% |
  | +23.4 bp (R363, unseen hops) | 71% | 17% | 61% |
  | +30 bp | 90% | 34% | 83% |
  | +41.7 bp (R363, all hops) | 99% | 71% | 98% |

- **80% power needs about +26 bp a hop over 80 hops.** Below that the lane is a **futility screen**, as
  `docs/GATES.md` requires it to say.
- **Speed:** R354's θ 0.3% Binance + Lighter book had 221 hops in 538 days (0.41 a day). At that rate 40 hops come in
  about 3 months and 80 in about 6.5. Fewer will come because of the cost gate, which R363's archive cannot price (no
  books then). On today's books it would keep about half of Lighter's markets but none of KAITO, RIVER, AVNT or BERA.
  Fewer still if Lighter lists fewer of the coins that settle deep (106 of 858 eligible Binance perps had a Lighter
  crypto market on 2026-10-28), or if the container is down. The final look on 2027-10-28 reads whatever has been
  scored by then.

## Costs (1x, 2x, 3x)
- **1x (decided):** the walked book at both orders against the mids, plus Lighter's listed taker fee on both fills (0
  on every market on 2026-10-28). Funding is not a cost multiple: it is Lighter's settlement, paid once.
- **2x and 3x:** book cost and fee doubled and tripled.
- **Size:** $1,000 a hop. Larger orders are not tested.

## Reported (not decided on)
- For the primary book: hops, mean net at 1x/2x/3x, hit rate, the trimmed mean (10 best and 10 worst hops removed),
  the leave-two-coins-out mean (both coins with the largest summed net removed), `go_real()` and the CR1 t.
- The θ 0.5% book and the five other trials, at 1x.
- For each hop: r at the decision and Binance's r and mark at each walk, Lighter's feed rate (8 h terms) beside r,
  h, e, both fills against the mids, levels walked, the exit's parts, lateness and source, the settlements held.
- Every decision (with its counts and errors) and every logged candidate with its status; entries not made and why.
- The recorded seconds (books, trades, Lighter's stats, Binance's marks and trades) under `data/settlelit_fwd/<T>/`,
  each file's sha256 in `journal/recordings.csv`. They are for later frozen lanes (fills, Lighter's settlement
  timing, gate 3); nothing here decides on them.
- **Read against** `registry.program_trials()`: 9,479,106 on this branch before this lane and 9,479,107 after it (or
  9,479,123 → 9,479,124 counting #56's R338-R346).

## Code
```fixed
5167ba1127f401122bec7db4ee69a1176778b6626800977be3fa5134fd0745e6 scripts/settlelit_fwd_rule.py
bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c scripts/settlehop_rule.py
```

| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `scripts/settlelit_fwd_rule.py` | 5167ba1127f401122bec7db4ee69a1176778b6626800977be3fa5134fd0745e6 | fixed: the daemon checks it and this file before every decision and stops if either changed |
| `scripts/settlehop_rule.py` | bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c | fixed (R355's rule; this lane imports its base matching, crypto flag, signal and statistics) |
| `scripts/forward_settlelit.py` | 3752176b72598c6a8e6b1550d0faba3346c6eceb2531cbe3958d9f7def6a06f8 | data plumbing only |
| `tests/test_settlelit_fwd.py` | f3307a8cb681c870eacfcfa8c6ff66f867de7a57b6cf3fa241d86a4f97c66081 | 32 tests (invented books, streams and journals) |
| `scripts/calib_settlelit_fwd.py` | afb531f3ae1bd7da332346e4535dd876b8ca2a7a5284f584884ddd0a5d41c491 | the size and power above |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 | data plumbing only (Lighter REST client and lock) |
| `lab/gate.py` | 2658c3b776cf61d920f4d0542ebd4c4f2fda6efe5f0798bc7938b383983c8899 | `go_real()`, reported only |
| `lab/prereg.py` | 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 | freeze and verify |

- **Changes after the freeze:** data plumbing only (stream clients, reconnects, retries, file handling). Each change
  needs the tests to pass and a line in `journal/CHANGES.md` with its commit. A change to the rule, the books, the
  accounting or the decision is a new lane.
- **Start and restarts:** the forward loop's hourly task runs `scripts/forward_settlelit.py` (`ensure`). It starts the
  daemon when no writer holds the lock, after checking this file and the fixed rule. After a restart the journal
  resumes: a book window still ahead is run, an entry whose instant passed is logged as missed (not entered), and an
  owed exit is walked on the REST book, late.

## Changes from the claim (comment 6472025942), made before this freeze
- **Trigger:** the claim named "Binance's displayed rate as Lighter's public `funding-rates` feed reports it". That
  feed states each rate in 8 h terms and gives no settlement time or cycle, so a coin on Binance's 1 h cycle cannot be
  told from a 4 h or 8 h one, and the per-settlement rate is unknown. This lane reads Binance's own public market
  stream instead (`wss://fstream.binance.com/market/stream`, which `scripts/record_tape.py` already reads): each
  perp's predicted rate per settlement and its next funding time. Binance's REST API, which answers HTTP 451 here, is
  not used, and neither is any other host for it. The feed's rate is logged beside r and never decided on.
- **Look bounds:** the claim gave none. They are fixed above from R363's hops.
- **Cost gate:** not in the claim. Added after Lighter's book costs above, before any ticket.

## Deviations from R363, all fixed here
- Binance's live predicted rate at T − 1 h + 20 s replaces R354's rate rebuilt from the archive's premium index at
  T − 1 h. The 4 h / 8 h cycle comes from the stream's next funding time instead of the archive's settlement times.
- Lighter's h comes from its market_stats stream instead of its archive (the same settlements).
- Identity is a 5% price check against Binance's mark instead of R353's symbol table.
- Entry at T − 10 s and exit at T + 60 s on the live book, instead of the last trades before T and before T + 1 min.
- Costs are the walked book at both orders, not R354's $1k band cost.
- **The cost gate** (rule 7) keeps only hops whose book costs at most 10 bp for a round trip at the decision. R363 kept
  every hop at its band cost. This lane tests the trade where Lighter can execute it cheaply. It cannot say whether
  the thin coins that carried R363 pay on their real books; their round trips are logged when they come up.
- Up to 5 hops a settlement, one per Lighter market.
- The decision is a group-sequential clustered t on fresh hops, not R363's five checks on the archive.

## Evidence lineage and admission
- **Method:** M267. **Parents:** R363 (PASS at gate 0, PARTIAL: this lane's warrant), R362 (NULL, the Binance seconds
  form), R356 and R354 (PARTIAL), R348 (Lighter follows Binance within a second). R355 keeps running the hedged hop,
  unchanged.
- **Decision group:** M267's Lighter-route form, forward. One decision; the θ 0.5% book and the other trials are
  diagnostics.
- **Samples:** every hop is decided and entered after this freeze. There is no overlap with any archive any lane has
  read.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one decision per signal; strict on-time entries (5 s); a one-sided test calibrated under a dependent null;
    trimmed and leave-two-coins-out means reported (per hop, the lane's unit); power stated.
  - Labelled: a futility screen for edges below about +26 bp a hop.
  - Left for later: gate 3 (account risk) needs its own PREREG.
- **R363's PREREG:** sha256 `d381b1a2461169ddfa36eca7379ae68ca740a14744ed01ab79c5607d7bfb2dd6`.

## Stop rules
- The lane ends at its verdict. After it, the daemon is stopped by the owner of the lane, and no hop after the verdict
  is decided on.
- A changed PREREG or rule stops the daemon before its next decision. The lane is then over, and a new idea is a new
  lane.
- Not allowed after the first ticket: new thresholds, new books in the decision, a different cost, a different look
  schedule, or dropping hops.

## Known limits (written before the first ticket)
- **Fills are paper:** a walked book at the instant, with no queue, latency, rejection or partial fill. A remainder is
  walked again on the next second's book, which may still show what the first walk took. A real order placed at
  T − 10 s meets a market in which the capture crowd is still buying or selling.
- **Lighter's settlement:** charged from its history at its stamp. Whether an account opened at T − 10 s pays it, and
  on what mark, cannot be seen without an account. The recorded market_stats shows when Lighter's stamp moves.
- **Binance's rate can move in the hour** after the decision. It is read once, at T − 1 h + 20 s, as R354 read it.
- **The gate reads the book an hour before T.** The book at T − 10 s can be thinner, and the 1x net charges that one.
- **The container:** the daemon runs only while this container runs. Settlements it misses enter nothing and slow
  the lane, and they can skip the largest squeezes if they come while it is down.
- **Same coin:** a 5% price check can pass two different coins priced alike. One hop per Lighter market.
- **Concentration:** 130 of R363's 134 decided hops were shorts before deeply negative settlements, on a few thin
  coins (KAITO, RIVER, AVNT and BERA held 77% of the sum). On today's books the gate would leave all four out, so
  the lane may see few hops, and those on deeper books than R363's winners.
- **Margin and liquidation:** not modelled. A hop lasts about 70 seconds; the recorded seconds give its path.
- **The crowd can adapt:** if more traders sell ahead of the lump's payout, the move can come before T and shrink.
