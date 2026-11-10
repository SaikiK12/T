# PREREG: hlspot_carry_v1 (R444). Hyperliquid spot-against-perp carry on one venue

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R444
- **Method:** M503 (cash-and-carry on Hyperliquid alone: long its spot, short its perp).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); FYI on issue #7.
- **Why now:**
  - `docs/reviews/venue_access_fr_20261110.md` found Hyperliquid among the perp venues that exclude no EU country.
    It is authorised nowhere.
  - Hyperliquid's funding carries an interest part of 0.01% per 8 h (0.00125% an hour, about 11%/yr). Its docs say
    so (trading/funding page, read by a helper on 2026-11-10).
  - Hyperliquid also lists USDC spot pairs for HYPE and for coins bridged by Unit (UBTC, UETH, USOL and others).
  - So a long-spot, short-perp book can be held on one venue, with no transfer between venues.
  - R441 tried the same rule on OKX Europe (X-Perp short, OKX spot long) and earned about cash plus a point.
- **Gates:** two reads.
  - **Gate 0 (stops only):** the rule on the held history 2025-01-01..2026-11-10, today's pair universe. It can stop
    the lane; it cannot pass it.
  - **Gate 1 (decides):** the same rule on days recorded after this freeze, from 2026-11-11, read at 90 and 180
    scored days.
- **Paper only.** Nothing here can place an order or move money.

## What the author has seen
- Hyperliquid funding:
  - as one venue of cross-venue books in R275, R288, R437, R439 and R440 (spreads against other venues, not this
    book);
  - its interest-part rule;
  - one BTC print of 2023-05-12, returned by a probe of how far back the funding history goes.
- Hyperliquid spot: the list of pairs, token names and full names (a metadata probe on 2026-11-10). No spot price,
  spot volume or spot-against-perp statistic has been computed.
- The sign of the funding on majors was therefore expected before this lane. That is why gate 0 stops only.

## Data
- **Source:** `.github/workflows/claude-okx-recorder.yml` (twice a day) writes `hl_spot/` on the data branch
  `claude/okx-xperp-data` with `scripts/record_hl_spot.py`:
  - `pairs.json`: each run's pairs, by this rule:
    - a spot pair quoted in USDC whose base token is HYPE, or whose full name starts with "Unit ";
    - and whose name without the leading U is a listed perp (UBTC → BTC).
    - Plain name matches are excluded, since Hyperliquid spot names are first come, first served.
  - The pairs' hourly funding prints, from 2024-11-01.
  - Closed 1d candles of both legs (last trades, base volume).
- **Gate-0 data commit:** `814573be827553b62b286a73f66c8f649c69606c` (the data branch after the first run that
  recorded `hl_spot/`). Gate 0 reads it and nothing else. The script refuses another commit.
- **Gate-1 data:** the same branch at the look date. Rows for days before 2026-11-11 are not scored.

## Rule (constants in `scripts/run_hlspot_carry.py`; report and gate-1 decision: R441's `run_xperp_carry.py`)
- **Daily axis:** 00:00 UTC. A daily candle opened on day D − 1 gives the close at D. Both legs use last-trade closes.
- **Pairs:** those in `pairs.json`. Gate 0 has only the 2026-11-10 file, so its universe is today's survivors. A pair
  can trade only from its first daily candle on both legs.
- **Signal at D:** the perp's realized funding, summed over prints with time in (D − 7 days, D] and annualized
  (× 365 / 7). It needs a print at least 7 days before D.
- **Exits at D, first:** the signal is below 5%/yr or missing; or a close on either leg was missing for the interval
  just booked (forced).
- **Entries at D:**
  - Pairs not held whose signal is at least 10%/yr.
  - They also need both closes at D and quote volume of at least $100k on each leg on the day closing at D (base
    volume × close).
  - Pairs are taken by signal, highest first, into free slots. There are 10 slots and no rank exit.
- **Position:** each slot is long N/10 of the spot pair and short N/10 of the perp. The perp is margined at 2x and the
  spot is fully paid, so capital is N × (1 + 1/2). No portfolio margin is assumed. Free slots hold cash, which earns
  nothing in the book. Notional is held constant; rebalancing is not costed.
- **Daily P&L, interval D − 1 → D, booked on day D:**
  - funding: the short perp receives its prints in (D − 1, D] (it pays when they are negative);
  - price: −(perp close D / close D − 1 − 1) + (spot close D / close D − 1 − 1).
- **Costs per entry and exit, both legs, at 1x:**
  - fees: 4.5 bp on the perp and 7.0 bp on spot per side (Hyperliquid's base-tier taker fees, docs fees page);
  - impact: a flat 5 bp on the perp and 10 bp on spot per side. No book is recorded for this lane.
  - The 2x and 3x reads multiply the total.
- **Hurdle:** 4.0%/yr on capital, flat.
- **Statistic:** daily net on capital minus hurdle / 365. Its annualized mean and its Newey-West t at lag 10
  (`lab.stats.newey_west_t`).

## Decision
1. **Gate 0:** **NULL (stop)** when the 1x annualized excess is below 0. Otherwise the lane continues to gate 1. Gate 0
   cannot pass the lane.
2. **Gate 1, at 90 scored days (2027-02-08):**
   - **EARNED** when all of these hold: the 1x annualized excess is at least +3.0 points, NW t is at least 2.0, the 2x
     excess is above 0, and the 1x cumulative drawdown is above −5% of capital. The lane continues to 180 days.
   - **NULL (stop)** when the 1x excess is below 0.
   - Otherwise **CONTINUE**.
3. **Gate 1, at 180 scored days (2027-05-09):**
   - **CONFIRMED** when the same conditions hold with NW t at least 2.5.
   - Otherwise **NULL**.
4. A CONFIRMED result is paper evidence only. It admits nothing to real money. `lab.gate.go_real()` and the owner's
   own legal check decide, including whether to use a venue that is authorised nowhere and a bridged token.

## Power, reported before any read
- Not computed before the freeze, because that would read the data. Gate 0 reports:
  - the daily standard deviation of the excess;
  - the detectable annual excess (t 2.5, 80% power) at 90 and 180 days;
  - the long-run sd implied by its NW t.
- FINDINGS states whether gate 1 can decide at all at the excess gate 0 shows.

## Reported, not deciding
- Gate 0's full read: 1x/2x/3x, NW t, drawdown, top-10-day share, funding and price parts, average pairs held,
  forced exits, and each pair's days held and net.
- What portfolio margin would change: capital N × (1 + 1/2) against N × 1/2 (Hyperliquid's docs give BTC an LTV of
  0.5); reported, never used by a decision.
- Gate 1 status reads before a look (`--status`). They carry no decision.

## Trials and reading
- One trial: one rule, no variants. The program total before this lane is 9,784,986 (after R443).
- Read against `registry.program_trials()`.

## Limits
- **Fills:** the book fills at daily last-trade closes, not marks. There are no live fills.
- **Bridged tokens:** UBTC and the other Unit coins are claims on Unit's bridge. A bridge failure would break the
  hedge; the history may hold no such event.
- **Margin:** the short perp can be liquidated in a fast rise even while the spot gains; at 2x that takes about a 50%
  move before the pair is closed. It is not modelled.
- **Venue status:** Hyperliquid is authorised nowhere. Its own terms page returned 403 to the helper, so the EU answer
  rests on secondary sources.
- **Gate 0:** survivor universe, and seen funding.

```inputs
59667707f3e7833d680d9528444d4cf194c1edc56c64571318c4de145a163d03 scripts/run_hlspot_carry.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
b0e4fc4f52c21d5fceb6ab124424d8146d3fee03324071bd28d3c68c334f99af tests/test_run_hlspot_carry.py
896efef888a19ce7cb0e81a8d913d27ddea9cd8ddf9b738a237b7345306a2100 scripts/record_hl_spot.py
127382b43bfd688b3d8fca8961492d998560098387351afdee1cd7ca005567c9 scripts/record_hl_daily.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
