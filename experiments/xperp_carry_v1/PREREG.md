# PREREG: xperp_carry_v1 (R441). OKX Europe alt X-Perp carry, short the X-Perp and long spot, a France-reachable book

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R441
- **Method:** M490 (cross-sectional alt X-Perp carry on OKX Europe).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); FYI on issue #7.
- **Why now:** `docs/reviews/venue_access_fr_20261110.md` found that Binance, Gate, MEXC and KuCoin do not serve
  French residents with perps. Every confirmed carry book has a leg on one of them. OKX Europe's X-Perps are sold
  under a MiFID licence (OKX Europe Markets Ltd, Malta). OKX's own X-Perps guide says they are available in "all 30
  European Economic Area countries", France included, subject to KYC, an appropriateness test and "Availability may
  vary". No register entry for a French passport was reached (venue note, later section). Hyperliquid and Lighter are
  authorised nowhere.
- **Gates:** two reads.
  - **Gate 0 (reported, decides nothing):** the rule on the held window 2026-08-20..2026-11-10, survivor universe.
  - **Gate 1 (decides):** the same rule on days recorded after this freeze, from 2026-11-11, read at 90 and 180
    scored days.
- **Paper only.** Nothing here can place an order or move money.

## What the author has seen
- R430 (`experiments/okxcarry_v1/FINDINGS.md`): BTC and ETH X-Perp static carry. NULL; ETH realized +6.31%/yr on
  notional, BTC +1.51%. Its reported cross-section of all 167 crypto X-Perps' realized funding over 2026-08-06..11-09:
  median about 10.4%/yr on notional, top decile above 14%, highest names about 24-31%/yr.
- That cross-section was seen. It is why gate 0 decides nothing here.
- The thresholds below were set from R275's family (enter at 10%/yr) and round numbers, not fitted to it.
- No price, basis, cost or book statistic of any alt X-Perp or spot pair has been computed by the author. The recorder
  test run of 2026-11-10 counted files only.

## Data
- **Source:** `scripts/record_okx_xperp.py`, written by `.github/workflows/claude-okx-recorder.yml` (twice a day) to
  the data branch `claude/okx-xperp-data`.
  - Funding prints by instrument (realizedRate; fundingRate where realizedRate is blank).
  - Closed 1Dutc candles: X-Perp mark, X-Perp last trades (quote volume), and the spot pair {base}-USDC, else
    {base}-EUR, on OKX EEA.
  - Book snapshots: $1k market-order cost in bp from mid, per leg and side.
  - Daily listings.
- **Gate-0 data commit:** `013dc728946cc5cf7c3177050a01ae7167049826` (the data branch after its first recorder run,
  2026-11-10 17:58 UTC). Gate 0 reads it and nothing else. The script refuses another commit.
- **Gate-1 data:** the same branch at the look date. Rows for days before 2026-11-11 are not scored.

## Rule (constants in `scripts/run_xperp_carry.py`)
- **Daily axis:** 00:00 UTC. A 1Dutc candle opened on day D − 1 gives the close at D.
- **Universe at D:** crypto X-Perps (instCategory 1) in the latest listing held at or before D. Gate 0 has only the
  2026-11-10 listing, so its universe is today's survivors.
- **Signal at D:** realized funding over prints with fundingTime in (D − 7 days, D], summed and annualized (× 365 / 7).
  It needs a print at least 7 days before D.
- **Exits at D, first:** a held name exits when its signal is below 5%/yr, when it is missing from the listing or has
  no signal, or when a mark or spot close was missing for the interval just booked (forced).
- **Entries at D:** names not held with signal at least 10%/yr. They also need a spot pair, mark and spot closes at D,
  and X-Perp quote volume of at least $100k on the day closing at D. Names are taken by signal, highest first, into
  free slots. There are 10 slots and no rank exit.
- **Position:** each slot shorts N/10 of the X-Perp and buys N/10 of spot. Capital is N × (1 + 1/2): the spot is fully
  paid and the X-Perp is margined at 2x. Free slots hold cash, which earns nothing in the book. Notional is held
  constant; rebalancing is not costed.
- **Daily P&L, interval D − 1 → D, booked on day D:**
  - funding: prints in (D − 1, D], received by the short;
  - price: −(mark close D / mark close D − 1 − 1) + (spot close D / spot close D − 1 − 1).
- **Costs per entry and exit, both legs, at 1x:**
  - fees: 5 bp on the X-Perp and 10 bp on spot per side (OKX EEA regular taker, M484 note);
  - impact: the measured $1k cost of the action's side from the latest book snapshot in the 24 h before D, floored at
    0, or 5 bp per leg when none is held.
  - Gate 0 has no snapshots, so it uses 5 bp.
  - The 2x and 3x reads multiply the total.
- **Hurdle:** 4.0%/yr on capital, flat. DTB3 was about 3.9% on 2026-11-09 (R430).
- **Statistic:** daily net on capital minus hurdle / 365. Its annualized mean and its Newey-West t at lag 10
  (`lab.stats.newey_west_t`).

## Decision (gate 1 only)
1. **At 90 scored days (2027-02-08):**
   - **EARNED** when all of these hold: the 1x annualized excess is at least +3.0 points, NW t is at least 2.0, the 2x
     excess is above 0, and the 1x cumulative drawdown is above −5% of capital. The lane continues to 180 days.
   - **NULL (stop)** when the 1x excess is below 0.
   - Otherwise **CONTINUE**.
2. **At 180 scored days (2027-05-09):**
   - **CONFIRMED** when the same conditions hold with NW t at least 2.5.
   - Otherwise **NULL**.
3. A CONFIRMED result is paper evidence only. It admits nothing to real money (`lab.gate.go_real()` and the owner's
   own check of OKX Europe's terms for France decide).

## Power, reported before any read
- Not computed before the freeze, because that would read the data. Gate 0 reports the daily standard deviation of
  the excess and the detectable annual excess (t 2.5, 80% power) at 90 and 180 days. FINDINGS states whether gate 1
  can decide at all at the excess gate 0 shows.

## Reported, not deciding
- Gate 0's full read (1x/2x/3x, NW t, drawdown, top-10-day share, funding and price parts, average names held, forced
  exits).
- Gate 1 status reads before a look (`--status`). They carry no decision.
- 2x and 3x costs at each look.

## Trials and reading
- One trial: one rule, no variants. The program total before this lane is 9,784,983.
- Read against `registry.program_trials()`. The inherited selection is R430's seen cross-section (gate 0 only).

## Limits
- **Fills:** the book fills at daily closes (mark for the X-Perp, last trade for spot). There are no live fills in
  gate 0, and spot is held at OKX EEA itself. Transfers and custody are not costed.
- **Currency:** a EUR-quoted spot leg carries the EUR/USD move against the USD X-Perp. The book does not hedge it.
- **X-Perp specifics:** 5-year expiry; whether the funding-like payment stays as recorded is the venue's call.
- **Gate 0:** survivor universe and seen cross-section.
- **Short history:** the API keeps about three months, so the recorder is the only way to lengthen it.

```inputs
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
ed9369e2ecae2831309746b63bb73da853b1096d2cccf7e257203aeb639b674d tests/test_run_xperp_carry.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
