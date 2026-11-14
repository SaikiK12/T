# PREREG: oilwknd_fwd (R459). R432's oil weekend fade, on fresh weekends, on Lighter

Freeze with `lab.prereg.freeze()` before the first weekend. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R459
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_oilwknd.py` is the only writer of `experiments/oilwknd_fwd/journal/`.
  - It runs daily in `.github/workflows/claude-oilwknd.yml`.
- **Date registered (UTC):** 2026-11-11

**Methods:** M188 and M321 (TradFi perps' weekend move against the reopen). **Parent:** R432 (`weekend_reopen_v1`,
PREREG `c6472f1c…`), whose FINDINGS name this lane's question as its only lead.
- **Paper only:** public endpoints, no account, no key; nothing in the code can place an order.

## Question
R432 found one lead, picked from 144 cells on Binance's CL and BZ perps: fade an oil weekend move of 1% or more by
entering before the CME Sunday reopen and exiting at the Monday cash open. It gave +102 bp net per trade at 1x over 32
trades on 16 weekends. On fresh weekends from 2026-11-13, traded on Lighter's WTI and BRENTOIL perps (a venue a French
resident can use, Standard account, no fee) at Lighter's own prices, funding and recorded book cost, is the mean net
per traded weekend above 0, with a one-sided weekend-bootstrap p < 0.05 at the 40th traded weekend?

## Why this lane
- **R432 asked for it.** Its FINDINGS: "a new lane id, frozen before new weekends ..., the funding of that hold
  charged, a measured weekend spread". This lane does all three.
- **The venue fits the owner's rules.** Lighter's terms do not exclude France
  (`docs/reviews/venue_access_fr_20261110.md`) and its Standard account pays no fee, so the book is the whole cost.
  Binance stopped serving France in 2026.
- **The owner asked on 2026-11-11 that real trading match paper.** Fills are one-minute opens after the decision,
  funding is charged, and the cost is read from Lighter's recorded book.

## What the author has seen
- R432's PREREG and FINDINGS (Binance CL/BZ/NATGAS, XAU/XAG, QQQ/SPY weekends 2025-12-12..2026-10-23).
- R434 (`wti_residual_v1`) read Lighter WTI quotes on weekdays from 2026-10-29 to 11-06, and no weekend.
- **Plumbing, counts only.** On 2026-11-11 the author ran this lane's code once on the weekend of Friday 2026-11-06,
  with live endpoints and no book files. WTI: 199 one-minute bars and 19 funding rows fetched, status `ok` (so its
  |W| was at least 100 bp), entry, exit and S + 60 min bars found, 2 fills at the fallback cost. BRENTOIL: status
  `no_trade`. No price, W value or return was printed. That weekend is before the first weekend and is in no statistic.
- **Lighter's API:** one candles request returns at most 500 bars, the last ones of the range asked; the code asks
  three short ranges per asset (checked 2026-11-11).
- **Book costs:** `lighter/books/` on `claude/xyz-books-data` holds WTI and BRENTOIL from 2026-11-11; no cost value
  was read.
- **Code tests:** `tests/test_run_oilwknd.py` on stub venues.

## Data
- **Prices and funding:** Lighter's public API, WTI and BRENTOIL perps: `candles` at resolution 1m and `fundings`
  hourly (through `scripts/run_usopen_dex.py` and `lab/carrylane.py`).
- **Book costs:** `lighter/books/` on `claude/xyz-books-data` (`scripts/record_lighter_costs.py`, hourly on GitHub):
  the cost in bp of a $1k market order on each side.
- **Calendar:** `lab.sessions.NYSEHolidays`.

## Rule
Constants are in `scripts/run_oilwknd.py`. Times are New York local time (DST-aware) unless marked UTC.
- **Weekends:** every Friday from 2026-11-13. A weekend whose Friday or following Monday is an NYSE holiday is skipped
  (written as `holiday`).
- **Anchors:** F = Friday 17:00; S = Sunday 18:00 (the CME reopen); E = S − 5 min (the decision); C = Monday 09:30
  (the cash open).
- **Price P(τ):** the close of the last one-minute bar that opened in [τ − 60 min, τ). None: the asset's weekend is
  `unpriced`.
- **Signal:** W = 10,000 × ln(P(E) / P(F)), in bp, for WTI and BRENTOIL separately.
- **A trade:** when |W| ≥ 100 bp. Fade: short when W > 0, long when W < 0. Otherwise `no_trade`.
- **Entry:** the open of the first one-minute bar that opened in [S − 4 min, S − 1 min], before the reopen.
- **Exit:** the open of the first one-minute bar that opened within 5 minutes after C ([C, C + 5 min]).
- A trade with no entry or exit bar is `unpriced` for good.
- **Return:** side × (exit / entry − 1), plus the funding received: Lighter's hourly settlements whose hour is after
  the entry minute and not after the exit minute, positive rates paid by longs.
- **Cost of a fill:** Lighter's Standard account pays no fee. The cost is that of a $1k market order on the side
  traded, read from the asset's `lighter/books/` snapshot nearest the fill if it is within 90 minutes. Otherwise the
  fill costs 10 bp, and it is counted.
- **Net:** gross − k × (entry cost + exit cost), for k = 1, 2, 3.
- **Weekend net:** the mean net over the assets traded that weekend (one or two). A weekend with no trade is not
  counted.
- **Reported only:** the same entry exited at the open of the first bar within 5 minutes after S + 60 min (R432's
  other lead exit), at 1x.
- **Scoring:** a weekend is scored once, at the first daily run at least 3 hours after C. A fetch error leaves it for
  the next run; Lighter keeps at least 20 days of one-minute bars. Rows are append-only.

## Decision
On traded weekends in calendar order, with weekend nets at 1x:
- **NULL (futility):** at 15 traded weekends, if the mean of the first 15 is at or below 0. Later weekends cannot
  change it.
- **PASS:** at 40 traded weekends, over the first 40, all of the following:
  - the mean at 1x is above 0, with a one-sided p < 0.05 (the share of 10,000 bootstrap means of whole weekends, drawn
    with replacement, seed 459, at or below 0);
  - the mean at 2x is above 0;
  - the mean without the best 3 weekends is above 0.
- **NULL:** at 40 traded weekends otherwise.
- A PASS earns a request to the owner for small calibration orders on Lighter (hard rule 5), the gates in
  `docs/GATES.md`, and `lab.gate.go_real()`. It does not authorize real money.

## Costs (1x, 2x, 3x)
1x is the measured cost above. FINDINGS reports per traded weekend and per trade, at 1x, 2x and 3x: mean, bootstrap p,
hit rate and the mean without the best 3. It also reports the S + 60 min exit, funding paid, the share of fallback
fills, and the no_trade, unpriced and holiday counts.

## Trials
One rule with two exits read: the Monday cash exit decides and the S + 60 min exit is reported. **Trials:** 2. Program
trials before: 9,785,005 (9,785,007 after). R432's 174 trials were counted in its row; this lane does not reset them.
Read against `registry.program_trials()`.

## Power
- R432's lead was picked from 144 cells: +102 bp net per trade over 16 weekends. Expect much less.
- If a traded weekend's net has an SD of about 180 bp, the standard error at 40 weekends is about 28 bp. The lead's
  size would give a t of about 3.6. A third of it (34 bp) gives about 1.2, and a PASS is unlikely.
- Oil's weekend moves were large in 2026 (a median |W| of 170-190 bp on Binance), so most weekends should trade. The
  futility read should come in about 4 months and the final read in about a year.

## Stop rules
- Nothing is retuned: no other threshold, anchor, asset, venue, exit, lag or size. A changed idea is a new lane.
- A fault in the script is fixed with a test and a note in the lane's README. If the fix changes what a scored
  weekend means, the lane is stopped and re-registered.
- No orders, no money, no credentials.

## Known limits (written before the first weekend)
- **Reference.** No CME price is read. The re-anchoring is inferred from Lighter's own prices.
- **Selection.** The lead is the best of 144 cells on one year with large oil moves. Fresh weekends are the test.
- **Size.** $1k a fill. Lighter's weekend oil books may be thin; the 2x and 3x reads bound that. One snapshot an hour.
  A delayed recorder leaves fills at the 10 bp fallback.
- **Holidays.** Only NYSE holidays are skipped. A CME-only closure is traded as a normal weekend.
- **Latency.** The Standard account's taker delay (about 300 ms) is far shorter than the one-minute lag used here.
- **Two correlated assets.** WTI and BRENTOIL move together, so a weekend counts once, as their mean.

```inputs
032c86f0cce65ab54b52fbbab47c1e892c503cb65721203ca5a80f82e071efcd scripts/run_oilwknd.py
f0a334b6bea1fe730a44614e624956d744ab64319ac5060b684f92008e17b880 tests/test_run_oilwknd.py
1147f5c10e44c4733e5d96d259148c52fe1c69d9d435242b846980b8815fd8df scripts/run_usopen_dex.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 lab/carrylane.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d lab/sessions.py
f691695930719a89ae4ededcd5b952f3aa6aabefbe8ea939970acd009e16b297 scripts/record_lighter_costs.py
c6472f1c4cc13bcdfb51335beeb2e6e00378e7816b397568c67c7eb207820126 experiments/weekend_reopen_v1/PREREG.md
bf6338e250fe5acf016f62b6c1e904bb116a91f147b90f73b216a51ec13863e2 experiments/weekend_reopen_v1/FINDINGS.md
```
