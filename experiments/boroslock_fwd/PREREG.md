# PREREG: boroslock_fwd, Boros funding locks forward on paper on live order books

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R413
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); claimed on #7, comment 6674170087
- **Date registered (UTC):** 2026-11-06
- **Method:** M480 (`docs/IMPROVEMENTS_20261105.md`, item 97); follows R412

## Question
Can a Boros funding lock be taken now at the prices on Boros's live order book, and does each paper lock settle at what
it locked? R412 found, on matured markets from 2025-08 to 2026-09, that the oracle copied the venue's funding on 99.7-99.96% of
events and realized equalled locked to the bp at the median, but that the margin over the T-bill was thin after an
indicative hedge round trip.

This lane checks three things before any real money:
1. **Executable at $10k?** At what locked APR, net of Boros's listed fees, can $10k be sold into the shown bids?
2. **How often worth it?** How often does the locked APR clear the T-bill plus an indicative hedge round trip?
3. **Settled as locked?** Over each paper lock's life, does Boros's floating leg equal the venue's funding?

## Owner's question that led here (2026-11-06)
The owner asked for a method whose gain is controlled, fixed in advance, because confidence matters more than chasing
gains. A lock fixes the funding income at entry. This lane is the paper check of that claim on live prices.

## Data
All inputs are public, read live at each run. No key, no wallet and no order.
- **Boros** (`api-boros.pendle.finance/apis/v1`):
  - `markets` (fees, payment period, maturity, best bid and ask, open interest);
  - `assets` (the collateral's USD price);
  - `markets/order-book` at tickSize 0.0001 with the AMM included;
  - `historical-data.boros.finance/settlement/<market>/<YYYY-MM>.ndjson.zip` for settlement.
- **Venue funding at settlement:**
  - Hyperliquid's public `info` API (`fundingHistory`);
  - Binance's monthly archive on `data.binance.vision`. It is published after each month ends, so a Binance lock
    settles only once its maturity month is published.
- **T-bill:** FRED DTB3, cached to `journal/tbill.csv` by R406's frozen helper (`scripts/forward_lockcarry2.py`). A
  value dated d is used from d + 2 days on (`scripts/lockcarry_rule.py`).
- **Markets in scope:** live, non-spread, BTC or ETH, on Binance or Hyperliquid, every collateral.

## Rule (scripts/boroslock_fwd_rule.py, frozen)
**An offer, at each run, for every market in scope:**
- **Fill:** walk the bids ("long" side) for $10,000 of YU. The YU count is $10,000 divided by the collateral's USD
  price. fill = the size-weighted APR.
- **Locked:** fill − takerFee − settleFeeRate (the market's config, as APR).
- **Eligibility:** at least 7 days to maturity, and bids deep enough for $10k. Whether $100k would fill is recorded.
- **Measures:**
  - excess = locked − T-bill;
  - carry = locked − 0.30% / τ − T-bill, with τ in years to maturity.
  - The 0.30% is a stated spot-plus-perp round trip (2 × (10 + 5) bp, Binance VIP0 taker). It is not measured.

**Books (one open lock per coin in each book; a lock is held to maturity, never closed early):**
- **K0:** the coin's offer with the highest carry, if that carry is at least 0.
- **K1:** the same, if that carry is at least 1%/yr.
- The lock's leg on the perp is on the market's own venue.

**Settlement:**
- **When:** at the first run at least 2 hours after maturity at which both of these are available:
  - Boros's settlement files for every month of the lock's life, including a settlement after maturity;
  - the venue's funding up to maturity.
- **Computed with t0 the lock's run time and T its maturity:**
  - V = Σ venue funding (per-period rates) at events in [t0, T];
  - B = Σ settlementApr × paymentPeriod / 365 d over Boros settlements in (t0, T + 10 min].
- **Reported per lock:**
  - diff_bp = (V − B) in bp of notional;
  - fidelity = (V − B) / τ, and realized = locked + fidelity;
  - misses: venue events in [t0, T] with no Boros settlement within 10 minutes after them;
  - the T-bill paid over the lock's life (the mean DTB3 dated in that span, annualized);
  - excess_m = realized − (m − 1) × Boros fees − m × 0.30% / τ − T-bill paid, for m = 1, 2, 3.

**Runs:** the forward task graph runs this lane every hour the host is up. Hours when the host is down have no offers
and open no locks. Settlement does not need the host up at maturity.

## Decision (first read)
**When:** once 4 locks have settled across both coins in book K0, or on 2027-10-01, whichever comes first.

**MECHANICS PASS** needs both of these:
- every settled lock in either book has |diff_bp| ≤ 5 (bp of notional over its life);
- the mean excess_1x of K0's settled locks is ≥ 0.

**Also reported:**
- every lock, with its oracle misses;
- the share of hourly runs whose best carry is ≥ 0 and ≥ 1%/yr;
- capacity at $100k;
- the gap between the book's best bid and the listed best bid;
- excess_2x and excess_3x.

**What PASS means and does not mean:** it says the paper lock holds on live books and real settlements. It does not
prove real fills, the hedge legs' real costs, margin, or venue and contract safety. The next step after a PASS is a
separate, owner-placed small lock through `lab.gate.go_real()`, compared to its paper twin to the bp.

**Otherwise:** FAIL, naming the lock or the shortfall. Trials: 2 (two books).

## What was seen before this freeze
- R412's results (above).
- One live read of the offers on 2026-11-06 around 02:40 UTC, used to check the parser. No journal was written.
  - Hyperliquid BTC and ETH, 25 December 2026 (48.6 days): locked 7.9-8.3%, carry +1.6 to +2.0%/yr.
  - The 27 November markets (20.6 days) and every Binance market: carry below 0.
- These are live quotes, not outcomes. No lock has settled.

## Risks this lane does not remove (stated now)
- **Hedge legs:** the spot purchase and the perp short are not priced from books. Their fees, basis at entry and exit,
  and the perp's margin and liquidation are outside this lane. That is the 0.30% assumption and its 2x and 3x.
- **Capital:** Boros and perp margin make the capital larger than the notional, so return on capital is below the
  locked APR.
- **Contract and oracle:** Boros runs on Arbitrum. A contract exploit, an oracle stall (R412 saw a 14-hour gap and a
  crash hour) or a governance change can cost more than the lock earns. A paper run does not measure a hack.
- **Venue and access:** whether the owner can use Boros, Hyperliquid or Binance from their country is not known here.
- **Fill quality:** the book is a snapshot from a public API whose sync timestamp is recorded. A real order lands
  seconds later, against a book that may have moved.

## Inputs frozen with this file
`scripts/boroslock_fwd_rule.py` and `scripts/forward_boroslock.py`, plus R406's helpers they import, by the sha256
below.

c028068712bd79e49c338372b59ac4bfe47131a9c0216da11721cc6f15284a6f  scripts/boroslock_fwd_rule.py
d1c28ca10c3607d197beb0f3f5eb2ce84bda44c9251aed666ecc0fe2bc575d0f  scripts/forward_boroslock.py
2a7e16a7f53f2633395e5b8fe2b05822e230b582fce930beab17702fe8ffe5ba  scripts/forward_lockcarry2.py
755aa2373bb43f2febc6abd5d357cca60b5c2deb972cab1279a270e03c4e28bf  scripts/lockcarry_rule.py
c3d54505559360c49aed9e1b9684a1391e39938a03dc2b0158fab04bd0fd753a  tests/test_forward_boroslock.py
