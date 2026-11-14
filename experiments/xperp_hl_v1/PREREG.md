# PREREG: xperp_hl_v1 (R443). Cross-venue funding carry between OKX Europe X-Perps and Hyperliquid perps

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R443
- **Method:** M502 (cross-venue carry on the two perp venues found reachable from France).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); FYI on issue #7.
- **Why now:** `docs/reviews/venue_access_fr_20261110.md` found two kinds of perp venue that do not exclude France:
  - OKX Europe's X-Perps, sold under a MiFID licence; OKX's guide says they are open in all 30 EEA countries.
  - Hyperliquid and Lighter, which exclude no EU country but are authorised nowhere.
  - R441 (OKX X-Perp short against OKX spot) earned about cash plus a point on its seen window. R288
    (Hyperliquid+Lighter) earned below cash.
  - This book pairs OKX with Hyperliquid instead: short the venue that pays more trailing funding, long the other.
- **Gates:** two reads.
  - **Gate 0 (reported, decides nothing):** the rule on the held window 2026-08-20..2026-11-10, survivor universe.
  - **Gate 1 (decides):** the same rule on days recorded after this freeze, from 2026-11-11, read at 90 and 180
    scored days.
- **Paper only.** Nothing here can place an order or move money.

## What the author has seen
- OKX: R430's cross-section of crypto X-Perp funding (median about 10.4%/yr on notional; BTC +1.5%, ETH +6.3%).
- Hyperliquid:
  - funding as a venue in R275, R288, R437, R439 and R440 (books, not this pair);
  - its rule that funding carries an interest part of 0.01% per 8 h, about 11%/yr.
- So the sign of the spread on majors was expected before this lane. Gate 0 decides nothing for that reason.
- No OKX-Hyperliquid spread, price or book statistic has been computed. The recorder test of 2026-11-10 counted
  files only.

## Data
- **Source:** `.github/workflows/claude-okx-recorder.yml` (twice a day) writes the data branch
  `claude/okx-xperp-data`:
  - OKX X-Perps (`scripts/record_okx_xperp.py`):
    - funding prints (realizedRate; fundingRate where blank);
    - closed 1Dutc mark and last-trade candles (quote volume);
    - book snapshots;
    - daily listings.
  - Hyperliquid, under `hl/` (`scripts/record_hl_daily.py`):
    - hourly funding prints;
    - closed 1d candles (last trades, base volume);
    - `coins.json`: the coins whose name, or name without a leading `k` (1000x contracts), is the base of an OKX
      crypto X-Perp.
- **Gate-0 data commit:** `8b0116763d2372d9ee54aa31f584edc050261068` (the data branch after the first run that
  recorded `hl/`). Gate 0 reads it and nothing else. The script refuses another commit.
- **Gate-1 data:** the same branch at the look date. Rows for days before 2026-11-11 are not scored.

## Rule (constants in `scripts/run_xperp_hl.py`; the report and decision are R441's `scripts/run_xperp_carry.py`)
- **Daily axis:** 00:00 UTC. A daily candle opened on day D − 1 gives the close at D. OKX prices are mark closes;
  Hyperliquid prices are last-trade closes.
- **Pairs:** an OKX crypto X-Perp in the latest listing held at or before D, and the Hyperliquid coin that
  `coins.json` maps to its base. Gate 0 has only the 2026-11-10 listing, so its universe is today's survivors.
- **Spread at D:** Hyperliquid's realized funding minus OKX's, each summed over prints with time in (D − 7 days, D]
  and annualized (× 365 / 7). Each side needs a print at least 7 days before D.
- **Direction:**
  - A spread of at least 10%/yr shorts Hyperliquid and buys the OKX X-Perp.
  - A spread of at most −10%/yr shorts the OKX X-Perp and buys Hyperliquid.
- **Exits at D, first:**
  - the held direction's spread (the spread, or minus it for an OKX short) is below 5%/yr, or missing;
  - the X-Perp is missing from the listing;
  - a price on either leg was missing for the interval just booked (forced).
- **Entries at D:**
  - Pairs not held whose absolute spread is at least 10%/yr.
  - They also need both closes at D and quote volume of at least $100k on the day closing at D on each venue.
    Hyperliquid's quote volume is base volume × close.
  - Pairs are taken by absolute spread, highest first, into free slots. There are 10 slots and no rank exit.
- **Position:** each slot is short N/10 on one venue and long N/10 on the other. Each leg is margined at 2x, so
  capital is N × (1/2 + 1/2) = N. Free slots hold cash, which earns nothing in the book. Notional is held constant;
  rebalancing and transfers between venues are not costed.
- **Daily P&L, interval D − 1 → D, booked on day D:**
  - funding: the short leg receives its venue's prints in (D − 1, D] and the long leg pays its own;
  - price: −(short close D / close D − 1 − 1) + (long close D / close D − 1 − 1).
- **Costs per entry and exit, both legs, at 1x:**
  - fees: 5 bp on OKX and 4.5 bp on Hyperliquid per side (OKX EEA regular taker; Hyperliquid base-tier taker);
  - impact: on OKX, the measured $1k cost of the action's side from the latest X-Perp book snapshot in the 24 h
    before D, floored at 0. When none is held, and always on Hyperliquid, 5 bp per leg.
  - Gate 0 has no snapshots, so it uses 5 bp.
  - The 2x and 3x reads multiply the total.
- **Hurdle:** 4.0%/yr on capital, flat.
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
3. A CONFIRMED result is paper evidence only. It admits nothing to real money. `lab.gate.go_real()` and the owner's
   own legal check decide, including whether to use a venue that is authorised nowhere.

## Power, reported before any read
- Not computed before the freeze, because that would read the data. Gate 0 reports:
  - the daily standard deviation of the excess;
  - the detectable annual excess (t 2.5, 80% power) at 90 and 180 days;
  - the long-run sd implied by its NW t.
- FINDINGS states whether gate 1 can decide at all at the excess gate 0 shows.

## Reported, not deciding
- Gate 0's full read: 1x/2x/3x, NW t, drawdown, top-10-day share, funding and price parts, average pairs held,
  forced exits, and the split of pairs by direction.
- Gate 1 status reads before a look (`--status`). They carry no decision.

## Trials and reading
- One trial: one rule, no variants. The program total before this lane is 9,784,985.
- Read against `registry.program_trials()`.

## Limits
- **Fills:** the book fills at daily closes. Hyperliquid's are last trades, not marks. There are no live fills.
- **Margin:** two venues hold margin separately. A leg can be liquidated while the other gains; at 2x that takes
  about a 50% move against one leg before the pair is closed. Transfers between venues are not costed.
- **Venue status:** Hyperliquid is authorised nowhere (venue note). Whether OKX Europe accepts a French resident's
  X-Perp account is unconfirmed by a register.
- **Gate 0:** survivor universe and seen funding on both venues.
- **Short history:** OKX's API keeps about three months, so the recorder is the only way to lengthen it.

```inputs
5d2c64c28ad58869d9336a674fb59c88ae2f9564c4700dc80bc3af3161bb4b67 scripts/run_xperp_hl.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
8cb3e71673d3cbbf50cdf521697e5b2c1f2a7cd037f7cd249f7006af53f51f90 tests/test_run_xperp_hl.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
127382b43bfd688b3d8fca8961492d998560098387351afdee1cd7ca005567c9 scripts/record_hl_daily.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
