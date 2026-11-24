# Reflection, 2026-11-24 (cycle 4 of rule 11): the closed-market class my map left out

## How I approached the last subjects, and what was wrong with it
- **Three cycles on one family.** Cycles 1-3 all studied the funding-design gap (why it exists, its theory, its price
  legs). `CLAUDE.md` says no family three sessions in a row without a written reason, so this cycle had to leave it.
- **I went looking for a "new" class and nearly re-derived an old one.** My first idea was 24/7 stock perps, which
  trade while the stock market is closed. A search of the registry showed the lab had already tested that class in
  eleven rounds on 2026-11-11 and 11-12, with two lanes running forward:
  - the weekend fade: R462 xyz (PASS at gate 0), R465 Lighter (PARTIAL), R467 and R463 forward;
  - Asian closures: R468 (PARTIAL);
  - index, commodity and FX perps: R464 (NULL), and R432 on Binance (NULL);
  - the cross-venue Sunday gap: R466 (INCONCLUSIVE);
  - earnings: R461 (NULL);
  - stock carry: R474-R480 (three forward lanes).
- **My mechanism map, built over three cycles, had no row for it.** It listed "mark price and oracle" as "not mapped",
  while the lab held seven weekend studies of exactly that rule.
- **The way of thinking that produced this.**
  - I read the lab's past as verdicts (PASS, NULL), not as evidence about mechanisms.
  - The base-rate tool (L031) labels families "payer" or "pattern" by name. It filed the weekend fade under patterns,
    so its prior was low, and I never asked what forces the weekend move.
  - So I built the map from primary sources only, as if the lab had no history.
- **What I change:** a map row starts from the registry (which rounds touched this mechanism, and what they found),
  then goes to the venue's rules. The lab's 280 rounds are the first primary source.

## 1. The economic question
Who moves a single-stock perp over the weekend, when no external price exists, and why is part of that move given back
when an external price returns?

## 2. The mechanism
- **The rule** (trade.xyz Specification Index, read 2026-11-11 for R462 and R464):
  - while the home market is closed, the oracle is a 30-minute EMA of the perp's own book, initialised from the last
    external price;
  - funding is charged against that oracle, so it does not pull the price anywhere;
  - nothing anchors the price but the market makers' quotes.
- **Who trades:** retail, mostly outside the US, reacting to weekend news and attention. It concentrates in volatile
  retail names (R462's largest sums: INTC, DRAM, GME, CRWV, RKLB, SKHY, SNDK, NBIS).
- **Who provides liquidity, and under which constraint:** market makers who cannot hedge a single name until an
  external market opens (Blue Ocean's overnight session from Sunday 20:05 New York, then the Monday open). Their risk
  capacity is small, so the price moves with order flow more than with information.
- **When the anchor returns, the price resets** toward the external price, and the overshoot is given back.
- **This is a known economic object:** the reversal is the price of immediacy when liquidity providers' capacity is
  limited (Grossman and Miller 1988; Campbell, Grossman and Wang 1993; Nagel 2012). It is the same object as He et
  al.'s ρ: demand θ against capacity W/m, here the market makers' capacity to carry unhedgeable single-name risk.

## 3. The barrier
- **On weekends no hedge exists for a single name,** so capacity is set by the market makers' tolerance for naked
  risk. More capital would shrink the overshoot. The barrier is risk, not access.
- **Indices are the control,** and they behave as the mechanism predicts:
  - an index's weekend move carries macro news;
  - many venues quote it (IG's weekend markets, Binance, Lighter, xyz);
  - so capacity is larger, and R464 and R432 found no fade.
  - The market-neutral book (each stock's move net of the weekend median) earned more than the raw one in R462
    (+55.8 bp against +42.4). The idiosyncratic part overshoots most, where nobody has information or a hedge.
- **A warning against fooling myself.** R464's PREREG predicted the same fade on indices from "the same oracle rule".
  It failed. The refined mechanism (market-maker capacity for unhedgeable idiosyncratic risk) was written after
  seeing that failure. It must earn its keep on fresh data: R463 and R467 forward, and a prediction stated before
  seeing it (section 6).
- **The later samples were weak, and I write it down:**
  - R462's B had 3 of 6 weekends positive;
  - R465's sample C (February to April) was flat at the Sunday exit and gave the overshoot back on Monday morning;
  - R468's B carried no effect.
  - One mechanism reading of C's timing: the reversal happens when the external anchor returns. If the oracle's
    anchor (Blue Ocean on Sunday evenings) changed during 2026, the reversal moved with it. That fits the mechanism
    but is untested.
- **Decay is the default here too.** Every new venue hour (24/5 brokers, tokenised stocks, more weekend market
  makers) adds capacity.

## 4. Fermi size and capacity
- **Supply:** R462 had 556 trades over 18 weekends, about 31 a weekend, or about 1,500 a year after holidays.
- **Edge:** +42.4 bp gross in A. Halved, as Thorp's rule requires, about +21 bp; less the fee (2 × 0.9 bp), about
  +19 bp.
- **What decides the size is the depth of the weekend book, which nobody has measured.** At a round-trip impact of
  10 bp:

  | Size per trade | Profit a year at about 9 bp net | Comment |
  |---|---|---|
  | $1k | about $1.4k | too small to matter |
  | $5k | about $7k | near the owner's target |
  | $10k | about $14k | above it |

- **Capital:** about 31 positions for three hours a week. The capital sits idle the other 165 hours. Per euro of
  capital per hour held, this is far more efficient than any carry book.

## 5. What we see or reach that others do not
- The oracle rule, and the time it re-anchors.
- Sunday-evening execution by script.
- A size small enough for thin books.
- Venues reachable from France: Hyperliquid's xyz and Lighter (zero fee).

## 6. The cheapest decisive observation, and the prediction stated first
- **Capacity decides whether this family can matter.** The xyz and Lighter books have been recorded hourly since
  2026-11-11 (`claude/xyz-books-data`), with walked costs at $1k, $5k, $10k and $25k. Two Sunday evenings are on
  record.
- **The observation:** the round-trip book cost by size on Sunday evening (entry 19:00 and exit 22:00 New York) and
  through the weekend, against the US weekday session.
- **What it reads:** costs only. No mid over time, no weekend move W, no return. R463's and R467's interim scores stay
  sealed, and their journals are not opened.
- **Prediction, written before measuring:** weekend books are thinner than weekday books. The median market gives at
  most $5k per trade inside 10 bp of round-trip impact on a Sunday evening, so the family is worth roughly $1-7k a
  year at the owner's scale, not more.

## 7. The rule, re-read in full from the venue (trade.xyz `llms-full.txt`, fetched 2026-11-24, 519,514 bytes, sha256 `9875b3f95a9cf90c…`)
- **Internal pricing moves the oracle only when the book's impact prices cross it.**
  - S_t = β·S + (1 − β)·(S + IPD), where IPD = max(impact bid − S, 0) − max(S − impact ask, 0);
  - τ = 30 minutes, with each step capped at about 9.5%;
  - the oracle follows the price that a configured notional can trade at, not the last trade.
- **The mark** is the median of three things: the oracle; the oracle plus a 150-second EMA of (mid − oracle); and the
  median of bid, ask and last.
- **Discovery bounds:** the mark stays within ±1/max leverage of the Friday close (±10% for 57 of R462's markets, ±5%
  for 15), with a set number of re-anchors. A liquidation price outside the bounds cannot be hit while they hold.
- **The changelog shows the venue deliberately moving who is paid.** The oracle's time constant during closures went
  from 8 hours to 1 hour on 2025-11-21, then to 30 minutes on 2026-04-30. In the venue's words, "traders who are
  directionally right on gap moves keep more of the move (87% vs 10%); shorts who sit through those gaps receive much
  less funding compensation."
  - Under the 8-hour constant, the rule itself paid the fader: funding against a lagging oracle.
  - The venue has removed that transfer. R462's decomposition agrees: price +41.2 bp, funding +1.1 bp.
  - What remains is the price reversal at re-anchoring, which is paid by market-maker capacity, not by a rule.
- **Funding was halved for every xyz market on 2025-12-19** (multiplier 0.5, so a baseline of about 5.5%/yr).
- **All 72 of R462's markets still listed have 24/5 external pricing** (overnight from Sunday 20:05).
- **Eleven other US markets are priced in regular hours only:** URNM, DKNG, BIRD, BX, ZM, EBAY, BB, BOT, SHAZ, NCLD
  and ICE.
  - Their stated internal session is Friday 16:00 to Monday 9:30.
  - They have no external data overnight, and the rule is internal pricing whenever external data stops for more
    than 15 seconds. So every weekday night is probably an internal session for them too: a closure five times a
    week.
  - That reading is not verified (the oracle path on a weekday night would show it), and no lane has looked at it.

## 8. The observation: capacity on Sunday evening (`scripts/check_wknd_depth.py`, costs only)
Hourly book snapshots from 2026-11-11 to 11-24, with two Sunday evenings. The figure is the median across markets of
each market's median round trip from mid, before fees.

| Window (New York) | xyz $1k | xyz $5k | xyz $10k | xyz $25k | Lighter $1k | Lighter $10k |
|---|---|---|---|---|---|---|
| Sunday 18:30-19:30 (entry) | 6.4 bp | 11.4 | 19.4 | unfilled | 4.9 | 11.7 |
| Sunday 21:30-22:30 (exit) | 5.7 | 8.2 | 9.9 | 17.1 | 4.1 | 8.8 |
| Weekend (Fri 20:00 to Sun 18:00) | 5.5 | 8.9 | 12.8 | 42.1 | 4.0 | 12.2 |
| US weekday session | 4.7 | 6.1 | 7.2 | 9.3 | 5.6 | 10.9 |

- **The entry hour is the thinnest of the week** on xyz. At $10k it costs 19 bp against 7 bp on a weekday, and 30 of
  the 76 markets cannot take even $1k inside 10 bp.
- **That is the mechanism showing in the book.** Market makers withdraw just before the anchor returns, and the fade
  is paid for supplying liquidity at that moment.
- **Capacity at the entry hour:**
  - inside a 10 bp round trip, the median market takes $1k;
  - inside 20 bp, it takes $10k (xyz) and $10k (Lighter).
- **Fermi size, with the measured costs** (round trip ≈ the mean of the entry and exit hours; fee 1.8 bp; 1,500
  trades a year):

  | Size per trade | Cost | Net at half the in-sample edge (21 bp) | A year | Net at the full edge (42 bp) | A year |
  |---|---|---|---|---|---|
  | $1k | 6 bp | 13 bp | $2k | 34 bp | $5k |
  | $5k | 10 bp | 9 bp | $7k | 30 bp | $23k |
  | $10k | 15 bp | 5 bp | $7k | 26 bp | $38k |

- **The prediction held:** about $5k per trade is the useful size. Lighter trades the same events (fade returns
  correlate at 0.92), so it adds capacity on top, not new evidence.
- **The family can reach the owner's target only if the forward edge stays near its in-sample size.** At half size it
  is worth about $7k a year.

## 9. Speed of proof: the evidence comes per weekend, not per trade
- **Venues add no independent evidence.** Lighter's and xyz's weekend moves correlate at 0.96 on shared weekends.
  Binance's stock perps (from February to April 2026) cover the same weekends.
- **R463's own power section,** from R462's weekends: SD of about 67 bp per traded weekend, and a pass about 87% of
  the time if the effect is the in-sample one.
- **At half the effect** (about 13 bp net at the measured cost), the t at 30 weekends is about 13 / (67/√30) ≈ 1.06.
  The bar there is p < 0.04, so power is roughly 20-25%.
- **R463 can confirm a full-size effect, and will probably miss a half-size one** that would still be worth about $7k
  a year. A NULL from R463 would not settle the family.
- **What would be faster.** The market-neutral book (`rel`: each market's move net of the weekend median) removes the
  common weekend shock, which is most of the per-weekend noise.
  - In R462 it earned +55.8 bp with 74% of trades winning.
  - A forward lane on it, frozen before a weekend, could decide in fewer weekends.
  - Its power must be computed before the freeze, from R462's own weekends (data refetched to 2026-11-09 only).
  - It would be a new lane with its trial counted. R463 is unchanged.
- **The first weekend it could catch** is Sunday 2026-11-29 (Thanksgiving weekend).

## 10. What it changes
- **The map has a new row:** "closed-market oracle", with the lab's eleven rounds, the rule, the changelog to watch
  and the measured capacity.
- **The money priority:**
  - The design gap's thin-coin sleeve (about $5-15k a year of capacity) and the weekend fade (about $7-23k a year
    at $5k a trade) are of the same order.
  - The weekend fade uses capital three hours a week.
  - Both wait on forward proof.
  - The weekend fade's proof is underpowered at realistic sizes. Making that proof faster is worth a cycle.
- **The base rate:** the weekend fade is a payer family (market makers' capacity, with a named barrier), not a price
  pattern. R464 was its negative control, not a failed replication. The prior for R463 and R467 is therefore higher
  than the pattern base rate. That is not a prior of certainty: two of three later samples were weak (section 3).
- **The watch item:** trade.xyz's changelog (oracle constant, session hours, bounds, funding multiplier). The venue
  has already moved the transfer once by changing one parameter.

## 11. What could make this wrong
- **Two Sundays of book data.** The entry-hour depth may vary with the weekend's news. The table is a first look.
- **Hourly snapshots at irregular minutes:** the entry window holds one snapshot per market per Sunday.
- **The capacity is per market,** not per traded market. The traded markets (the largest weekend moves, volatile
  names) may be thinner than the median.
- **The in-sample edge is from 24 weekends** under one oracle constant. Its later samples were weak.
- **The refined mechanism was written after R464's failure.** It is a hypothesis until R463, R467 or a forward `rel`
  lane says otherwise.
