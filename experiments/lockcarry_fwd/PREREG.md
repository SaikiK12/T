# PREREG: lockcarry_fwd, the locked cash-and-carry forward on paper on Deribit

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R405
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); claimed on #7, comment 6661005961
- **Date registered (UTC):** 2026-11-05

## Question
Can the locked cash-and-carry of R335 be executed now, at the prices shown on Deribit's books? R335 measured it on
Binance history and found it beat the T-bill when the basis was rich, and was absent in 2026. The trade buys the coin
with USDC on the spot book, shorts the coin's inverse dated future at 1x, and holds to delivery. Its dollar payoff is
fixed at entry for any delivery price, up to contract rounding and the exit cost.

This lane does not test whether prices move. It checks three things before any real money:
1. **Executable at $10k?** At what yield over the T-bill can $10k lock, given the shown books and the listed fees?
2. **How often?** How often does such an offer exist?
3. **Settled as computed?** Does each paper lock settle at the dollars computed at entry, using Deribit's published
   delivery price?

## Owner's question that led here (2026-11-05)
"What makes a trade 100% going through... we need to build confidence." The answer offered is this lane: the only
trade family in the lab whose payoff is fixed at entry. Its remaining risks are stated below and are not measured
away.

## Data
All inputs are public Deribit API v2 endpoints, read live at each run; no key, no order:
- `get_instruments` (spot and future: contract size, expiry, listed taker commission);
- `get_order_book` (depth 50);
- `get_delivery_prices` (the delivery price per day).

The T-bill is FRED DTB3 (3-month, discount basis, percent), cached to `journal/tbill.csv`. A value dated d is used from
d + 2 days on, as in R335. Coins: BTC and ETH, spot pair `<coin>_USDC`, every dated (non-perpetual) future listed at
each run.

## Rule (scripts/lockcarry_rule.py, frozen)
**At each run, for every listed future of each coin (an "offer"):**
- **Spot leg:** spend $10,000 walking the USDC spot asks; the spot taker fee is taken in coin.
- **Futures leg:** short Q dollars of the future, Q = coins x best bid rounded down to whole contracts, walking its
  bids. Deduct the listed futures taker fee and an assumed delivery fee of 2.5 bp of notional, both in coin.
- **Exit:** at delivery the coins are sold at the delivery price less the spot taker fee and the entry half-spread.
- **Locked return and yield:** the locked return is the dollars out over $10,000 minus 1. The locked yield is that
  return x 365 / days to delivery. The excess is the locked yield minus the T-bill. Whether $100,000 would also fill
  is recorded.

**Eligible offers:** 7 or more days to delivery, both books deep enough for $10k.

**Books (one open lock per coin in each book; a lock is held to delivery, never closed early):**
- **H0:** the shortest eligible offer whose excess is at least 0.
- **H3:** the eligible offer with the highest excess, if that excess is at least 3%/yr (R335's primary hurdle).

**Settlement:**
- **When:** a lock is settled from Deribit's published delivery price for its expiry date, at the first run at
  least 1 hour after delivery.
- **Dollars out:** (coins + Q (1/P - 1/F)) x P x (1 - exit cost).
- **Reported per lock:**
  - `diff_bp`: dollars out minus the dollars locked at entry, in bp of $10k;
  - the T-bill actually paid over the lock's life: the mean DTB3 dated in that span, simple;
  - `excess_ann`: the realized return minus what the T-bill paid, annualized.

**Runs:** the forward task graph runs this lane every hour the host is up. Hours when the host is down have no
offers and open no locks. Settlement does not need the host up at delivery.

## Decision (first read)
**When:** once 4 locks have settled across both coins in book H0, or on 2027-10-01, whichever comes first.

**MECHANICS PASS** needs both of these:
- every settled lock in either book has |diff_bp| <= 10;
- the mean `excess_ann` of H0's settled locks is >= 0.

**Also reported:** the share of hourly runs with a best eligible excess >= 0 and >= 3%/yr, capacity at $100k, and
every lock.

**What PASS means and does not mean:** it says the paper mechanics hold on live books and real delivery prices. It
does not prove real fills, account fees, withdrawal access or venue safety. The next step after a PASS is a separate,
owner-placed small lock through `lab.gate.go_real()`, compared to its paper twin to the bp.

**Otherwise:** FAIL, naming the lock or the shortfall. Trials: 2 (two books).

## Risks this lane does not remove (stated now)
- **Venue:** Deribit holds both legs and the coins. A venue failure or a withdrawal freeze is a total loss of the
  stake; no paper run measures it. Real size is therefore capped by what the owner can lose to one venue, not by
  the yield.
- **Stablecoin:** USDC is assumed worth $1, at entry and at exit.
- **Fees:** the delivery fee is assumed (2.5 bp); the account's real fee tier and Deribit's access rules for the
  owner's country are not known.
- **Fill quality:** books are snapshots. Both legs are assumed filled at the same instant; a real entry has leg risk
  of a few seconds.
- **Path:** at 1x the short is not liquidated, but the account can show a mark loss before delivery when the basis
  widens. This is not measured.
- **Benchmark:** the T-bill is the dollar benchmark. A euro holder carries EUR/USD risk unless hedged.

## Inputs frozen with this file
`scripts/lockcarry_rule.py` and `scripts/forward_lockcarry.py`, by the sha256 below, which is written at freeze time.
755aa2373bb43f2febc6abd5d357cca60b5c2deb972cab1279a270e03c4e28bf  scripts/lockcarry_rule.py
676802707d71497451770772d3e3ab4d7ab8438379e84a5a117639af2245a44d  scripts/forward_lockcarry.py
