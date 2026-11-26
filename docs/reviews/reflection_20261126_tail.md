# Reflection 2026-11-26: how stake 1 loses its money, and what would warn early enough to exit (register Q20)

- **Lens:** invert, not used last cycle.
- **Family:** risk of the carry book, not a new payer. It binds because stake 1 may be placed in December, and
  Thorp's rule sizes by the jump, not by the variance.

## 0. What the lab already knows
- **The stake** (`docs/reviews/december_decision_20261125.md` §3):
  - €2,000 split between Kraken (EEA derivatives) and Hyperliquid;
  - cross margin on each account, at most 1.5x;
  - closed at −25% of the stake or at R509's kill switch (cumulative net below −3%).
- **The book's own tail** (R525, R526, R531's trade table):
  - the engine exits a pair whose price ratio moves more than 20% from entry (`lab/xfund_v2.py:29`, BLOWOUT 0.20);
  - LUNA (May 2022) is the worst trade, at −189% of a leg's notional at 2x, entered with a −51% basis, which R526's
    "agree" filter (|basis| > 2% at entry) blocks;
  - the next worst are all Bitfinex pairs entered in 2026-01..06: −36% to −74% of a leg over 100-200 days, beyond
    the 20% blowout. Explaining that is strand 1 below;
  - the worst 1% of trades carry 32% of all losses.
- **Venue failure:** the stake note's measured range is 1.5-5.5% a year of closure for venues like ours, with about
  half recovered (`docs/reviews/stake_dhl_20261123.md`).
- **The hourly stop is contested:** R525 recommends one, and R526's findings advise against it on last-trade
  prices. The stake does not use it.
- **Data held:**
  - wallet status for Bithumb, Gate, KuCoin, HTX and Bitget only, 2026-10-21..11-05: not the stake's venues, and
    too short;
  - every coin's daily prices and funding on the seven venues.

## 1. The economic question
How much of stake 1 can be lost in a year, through which mechanism? Is there an observable that precedes each
loss early enough, a day or more, for a daily-checked book to exit?

## 2. The mechanisms, from the book's structure
1. **A coin's hedge breaks.** One leg's price moves and the other does not, because of a delisting, a forced
   settlement at a different price, a halted market or a stale last-trade price. This is bounded per slot (5% of
   the book), unless the exit fails.
2. **A venue fails or freezes withdrawals.** The deposit on that venue is lost or locked: about half the stake.
3. **A liquidation on one account during a fast move.** Cross margin at 1.5x gives about 59% room (cycle 11).

## 3. The barrier
None; this is defence. The question is what the owner's daily checks can see, which is the stake's own "edge".

## 4. Fermi
- **Mechanism 1:** at about €100 a slot, one broken hedge costs at most about €100 at the 20% blowout, or more if the
  exit fails.
- **Mechanism 2:** €1,000 on one venue × 1.5-5.5% a year × 50% unrecovered ≈ **€8-28 a year of expected loss**.
  That is a large share of stake 1's expected €40-50 a year. **This is the binding risk of the stake,** and diversifying
  across venues lowers it more than any coin-level filter.
- **Mechanism 3:** small at 1.5x on a hedged book.

## 5. What we see that others do not
Each pair's own price ratio and funding, every day, across both venues.

## 6. The cheapest decisive observations
- **Strand 1 (held data, now).** Replay the frozen book on Kraken+Hyperliquid and the Bitfinex pairs. For the worst
  trades, list the coin, dates, exit reason, and the price and funding parts. Did the 20% blowout fail to fire, and
  why?
- **Strand 2 (the room).** Incident histories with dates and primary sources, and what holders received:
  - Hyperliquid (`room_20261126/hl_incidents.md`): manipulations, forced settlements, ADL, bridge, halts;
  - Kraken Futures (`room_20261126/kraken_incidents.md`): delistings, notice, halts, margin rules.
  Then: did anything observable precede them?

## Strand 1, read (replay of the frozen book on R525's panel; scratch code, descriptive, 0 trials)
- **Kraken+Hyperliquid, the stake's pair: 206 trades, mean +383 bp at 1x.** The worst trades:

| Coin | Entry → exit | Days | Exit | Price P&L | Funding |
|---|---|---|---|---|---|
| SYRUP | 2025-12-01 → 12-20 | 19 (11 with a stale leg) | blowout | −36.5% | +6.1% |
| MORPHO | 2025-12-01 → 2026-06-03 | 184 | spread | −23.9% | +18.5% |
| CAKE | 2025-12-12 → 2026-04-06 | 115 | spread | −13.9% | +8.2% |
| PEOPLE | 2026-02-20 → 03-04 | 12 | spread | −6.1% | −1.4% |

- **SYRUP, traced day by day.**
  - The Kraken leg was stale on 4 Dec, and again from 9 Dec. Its stale run reached 3 days on 11 Dec, when the cumulative
    price P&L was −1.3%.
  - **R509's live rule** exits a leg stale for 3 days (`experiments/xfund_eea_fwd/PREREG.md`). It would have closed
    there, at about −1% to −5%, where the historical engine (no stale exit) rode to −36.5%.
  - The engine also books only adverse moves while a leg is stale, so the historical tail is partly an accounting
    choice.
- **The Bitfinex 2026 tail** (COMP, JASMY, SAND, ALGO, CRV: −40% to −86% of a leg) comes from long Bitfinex legs that
  were stale on 46-85 of their 66-206 days.
  - This is a liquidity and data artefact under the losses-only rule. It is a warning that Bitfinex's thin books
    cannot be exited, not a measured hedge loss.
  - R524 (Bitfinex+Binance, forward) must watch staleness.
- **Conclusion for the stake (leaning; one pair's history).** Coin-level tails on Kraken+Hyperliquid are bounded
  near a slot's 20% blowout, and the live 3-day stale exit cuts the worst historical case to a few percent of a slot.
  On a €2,000 book with 20 slots of about €100, that is about €1-5 per event.

## Strand 2, Kraken (reader `room_20261126/kraken_incidents.md`; the delisting rule read on the page by me)
- **Delisting notice: none guaranteed.** Kraken: "When possible, we will notify clients in advance via platform
  notification. We reserve the right to take these actions without advance notice in extenuating circumstances."
- **Settlement:** "A fair and reasonable settlement price will be determined by Kraken at our sole discretion", by a
  "volume-weighted and time-segmented TWAP… in a 60-minute observation period" of spot on the constituent exchanges.
  The hedge leg on Hyperliquid must be closed by hand at about the same time; the risk is the TWAP-to-Hyperliquid gap.
- **Frequent delistings in the stake's universe.** PF_SSVUSD and PF_BBUSD were settled on 2026-11-23, and PF_ACEUSD
  (in R508/R509's universe, `symbols.csv:87`) is delisted on 2026-11-27. The reader's tally of about 310 delisted PF_
  symbols since 2022 is unverified.
- **Margin (reader's quotes, not re-read):**
  - no margin calls ("does not offer margin calls or any warnings");
  - the balance "can never go below zero";
  - post-only halts of 15 minutes to about 3 hours, during which "no executions or liquidations can occur".
