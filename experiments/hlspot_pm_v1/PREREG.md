# PREREG: hlspot_pm_v1 (R445). HYPE and BTC spot-against-perp carry on Hyperliquid, fully deployed

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R445
- **Method:** M504 (R444's one-venue cash-and-carry, on the two pairs that portfolio margin lists, fully deployed).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); FYI on issue #7.
- **Why now:**
  - R444 (`experiments/hlspot_carry_v1`) stopped at gate 0: +2.57%/yr on capital, excess −1.43 points. Every pair
    held was positive, but 3.8 of its 10 slots sat in cash. Per held slot it earned about +6.7%/yr on capital N × 1.5.
  - Hyperliquid's portfolio-margin docs (summarized fetch, 2026-11-10) list HYPE (LTV 0.65) and BTC (LTV 0.5) as
    collateral, and say that spot and perp P&L offset each other. Other Unit tokens are not listed.
  - So two changes could lift the book: no idle slots, and a spot leg that also backs the perp's margin.
- **Gates:** two reads.
  - **Gate 0 (stops only):** the rule on the held history 2025-01-01..2026-11-10. It can stop the lane; it cannot pass
    it.
  - **Gate 1 (decides):** the same rule on days recorded after this freeze, from 2026-11-11, read at 90 and 180
    scored days.
- **Paper only.** Nothing here can place an order or move money.

## What the author has seen
- Everything in R444's FINDINGS, including each pair's contribution to its book over 2025-01-01..2026-11-10:
  - HYPE: +0.93%/yr of book capital over 580 days held;
  - BTC: +0.28%/yr over 364 days held.
  - On the slot's own capital (N × 1.5) that is about +10.9%/yr for HYPE and +5.2%/yr for BTC.
- The two pairs were picked by the portfolio-margin list, but HYPE's past return was known when they were picked.
  That is why gate 0 stops only, and why only forward days decide.
- No statistic of this book (full deployment, these two pairs, this capital) has been computed.

## Data
- **Source:** `.github/workflows/claude-okx-recorder.yml` (twice a day) writes `hl_spot/` on the data branch
  `claude/okx-xperp-data` with `scripts/record_hl_spot.py`, as for R444.
- **Gate-0 data commit:** `814573be827553b62b286a73f66c8f649c69606c`
  - It is R444's: the data branch after the first run that recorded `hl_spot/`.
  - Gate 0 reads it and nothing else. The script refuses another commit.
- **Gate-1 data:** the same branch at the look date. Rows for days before 2026-11-11 are not scored.

## Rule (constants in `scripts/run_hlspot_pm.py`; loader R444's, report and gate-1 decision R441's)
- **Pairs:** HYPE (spot pair @107) and BTC (spot pair @142, UBTC), taken from `pairs.json` by their perp names. A pair
  can trade only from its first daily candle on both legs.
- **Daily axis, signal, exits and entries:** R444's, unchanged.
  - Signal at D: the perp's realized funding over prints with time in (D − 7 days, D], annualized (× 365 / 7). It
    needs a print at least 7 days before D.
  - Exits at D, first: the signal is below 5%/yr or missing, or a close on either leg was missing for the interval
    just booked (forced).
  - Entries at D: a pair not held whose signal is at least 10%/yr. It also needs both closes at D, and quote volume
    of at least $100k on each leg on the day closing at D.
  - Unlike R444, there is no slot limit: every pair that qualifies enters.
- **Position:**
  - After the day's exits and entries, the capital is split equally across the k pairs held. Each held pair is long
    its spot and short its perp, each leg with notional C / (k × 1.1), where C is the capital.
  - The spot is fully paid, and under portfolio margin it backs the short perp's margin. A USDC buffer of 10% of the
    notional is kept for the perp's losses. So capital is N × 1.1, where N is the total notional held. No USDC is
    borrowed.
  - When no pair is held, the capital is cash and earns nothing.
  - Weights change only when a pair enters or exits. Between those days notional is held constant, and drift is not
    rebalanced or costed (as R444).
- **Daily P&L, interval D − 1 → D, booked on day D at the weights set on D − 1:**
  - funding: the short perp receives its prints in (D − 1, D] (it pays when they are negative);
  - price: −(perp close D / close D − 1 − 1) + (spot close D / close D − 1 − 1).
- **Costs:** R444's, per unit of notional traded, on each leg and side.
  - Fees: 4.5 bp on the perp and 7.0 bp on spot per side (Hyperliquid's base-tier taker fees).
  - Impact: a flat 5 bp on the perp and 10 bp on spot per side.
  - The notional traded on a day is the sum over pairs of |new notional − old notional|. An entry, an exit and the
    reweighting of the pair already held are all costed.
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
   own legal check decide, including whether to use a venue that is authorised nowhere, its portfolio margin, and a
   bridged token.

## Power, reported before any read
- Not computed before the freeze, because that would read the data. Gate 0 reports:
  - the daily standard deviation of the excess;
  - the detectable annual excess (t 2.5, 80% power) at 90 and 180 days;
  - the long-run sd implied by its NW t.
- With one or two pairs carrying all the capital, the noise per unit of capital is several times R444's. FINDINGS
  states whether gate 1 can decide at all at the excess gate 0 shows.

## Reported, not deciding
- Gate 0's full read: 1x/2x/3x, NW t, drawdown, top-10-day share, funding and price parts, pairs held, forced exits,
  turnover, and each pair's days held.
- The same book without portfolio margin: the perp margined at 2x in USDC and the spot fully paid, so capital is
  N × 1.5.
- Gate 1 status reads before a look (`--status`). They carry no decision.

## Trials and reading
- One trial: one rule, no variants. The program total before this lane is 9,784,987 (after R444).
- Read against `registry.program_trials()`, and against R444.

## Limits
- **Portfolio margin unconfirmed for this account:**
  - The docs (summarized fetch, not a verbatim read) ask for an account value above $10,000 (or $5M of weighted
    volume) and below a cap, with no open positions when it is enabled.
  - Global caps apply, and accounts fall back to normal margin when they are hit.
  - Whether the spot alone backs the perp's margin with no borrow is not stated in the docs.
  - Liquidation is not modelled; the 10% buffer is an assumption, not a margin calculation.
- **Wrong-way risk:**
  - HYPE is the venue's own token. A failure of the venue would hit the spot leg and freeze the perp leg at the same
    time.
  - UBTC is a claim on Unit's bridge. The window holds no bridge failure.
- **Concentration:** on days with one pair held, all the capital is in that pair.
- **Fills:** at daily last-trade closes, not marks. There are no live fills.
- **Venue status:** Hyperliquid is authorised nowhere. Its own terms page returned 403, so the EU answer rests on
  secondary sources.
- **Gate 0:** today's pairs, seen funding and seen per-pair returns.

```inputs
926930d01f410a5a52d33102be7c4820c022443ebabc8b3fe7623983cdc95fb0 scripts/run_hlspot_pm.py
59667707f3e7833d680d9528444d4cf194c1edc56c64571318c4de145a163d03 scripts/run_hlspot_carry.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
1bb884e88ea18dcceb77518eeb649f569c66bcc07ca6890562b565dc4c928522 tests/test_run_hlspot_pm.py
896efef888a19ce7cb0e81a8d913d27ddea9cd8ddf9b738a237b7345306a2100 scripts/record_hl_spot.py
127382b43bfd688b3d8fca8961492d998560098387351afdee1cd7ca005567c9 scripts/record_hl_daily.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
