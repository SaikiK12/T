# Critic report on the tail reflection (2026-11-26)

Reviewed: `docs/reviews/reflection_20261126_tail.md`, the two reader reports beside it, and the addendum in
`docs/reviews/december_decision_20261125.md` (lines 109-116). Scratch checks only; no other file edited. Verdict: the arithmetic holds, but the venue Fermi uses one venue where the stake has two, and "coin tail handled" rests on a paper rule that was never replayed.

## 1. Venue-failure Fermi (lines 45-47)

- **Arithmetic correct:** 1,000 × 1.5% × 0.5 = 7.5; 1,000 × 5.5% × 0.5 = 27.5.
- **Source:** `docs/reviews/stake_dhl_20261123.md:170-171`: "Kraken 2.9%, Binance 1.5%, Bitfinex 4.0%, Deribit
  2.9% and Hyperliquid 5.5% a year". Table: `research/intake/venue_failure_20261124.md:46-50`.
- **Per venue, not overall.** The 1.5-5.5% is the min and max over five venues. Binance (1.5%) is not a stake venue.
- **Two deposits:** `december_decision_20261125.md:46`, "split ... between Kraken ... and Hyperliquid". Kraken 14.5
  + Hyperliquid 27.5 = **about €42 a year**, which matches "about 2% a year of the stake" (`stake_dhl_20261123.md:172`).
- **Already netted:** `december_decision_20261125.md:19`, "minus venue-failure cost (about 2% a year of the stake)".
  The reflection sets €8-28 against the €40-50 gain as if the cost were not netted. Error.
- **"Diversifying lowers it" (line 47): wrong.** The model is linear in deposit share (`stake_dhl_20261123.md:96-97`).
  Splitting leaves expected loss unchanged; it only shrinks one jump.

## 2. Strand 1, SYRUP (lines 72-86)

- **"R509's live rule": wrong.** `experiments/xfund_eea_fwd/PREREG.md:6`: "Gate: 2 (forward paper)".
- **Exit quote correct:** `PREREG.md:37`, "a stale leg (3 days)". The engine defines stale at `lab/xfund_v2.py:14`:
  "a stale print is not a fill", "(a loss is kept)". So "books only adverse moves" is right.
- **"About −1% to −5%" is not on the page.** The page has one number: "cumulative price P&L was −1.3%" on 11 Dec
  (line 74). I found no "−4.9%" for 12-13 Dec in `docs/reviews/*.md`. The "would have closed there" replay was never
  run; the page says the engine has "no stale exit".
- **Real exit price:** a stale leg has not printed (`PREREG.md:28-29`, "It is fresh when that candle traded").
  The fill is the first print after the stale run: unknown in advance, possibly far away on a thin coin.
  −1.3% is a historical mark, not a fill.
- **Gap risk:** the blowout test runs on the day's close (`lab/xfund_v2.py:15-16`, "exits that day"), so a move
  through 20% can close far beyond it.
- **Contradiction:** lines 84-85 say tails "are bounded near a slot's 20% blowout"; line 67 shows SYRUP exiting at
  "blowout" with "−36.5%".
- **"Handled" (line 133) overclaims:** a paper rule with no replay; the page's own open question (lines 55-56) stands.
- **Not checked by me:** Bitfinex "46-85 of 66-206 days" (line 80), "32% of losses" (line 18), LUNA −189% (line 15).

## 3. ADL "ranks by profit and leverage" (line 125)

- Sourced in the room, not cited in the reflection: `room_20261126/hl_incidents.md:58`, "ranked by unrealized pnl and
  leverage used". Kraken ranks the same way (`room_20261126/kraken_incidents.md:77-78`).

## 4. Strand 2

- **"No public signal leads" at n = 8: misread.** The reader calls 3 of 8 "close to the 11.9% base rate"
  (`hl_incidents.md:126-127`). 37.5% is not close; P(3+ of 8 | 0.119) is about 0.06 (my check). A weak lead, not a verdict.
- **"Its falls come after the events" (line 111): wrong.** Three of eight day-before falls came before the event
  (`hl_incidents.md:114`, `:118`, `:119`).
- **"Halts ... about 3 hours" (line 100):** only 18 min is confirmed (`kraken_incidents.md:39-43`); 3 hours is from
  isdown.app, marked unverified (`:55-58`).
- **"PF_SSVUSD and PF_BBUSD were settled on 2026-11-23" (line 94):** the page shows a delisting batch, no settlement
  date (`kraken_incidents.md:22`).
- **"EU-regulated derivatives entity" (line 123):** no source; EEA coverage of Equity Protection is "an inference,
  not a quote" (`kraken_incidents.md:79-82`).
- **Omitted:** "ADL on majors ... not measured" (`hl_incidents.md:94-95`), the one mechanism that can hit a majors hedge.

## 5. Addendum rules, for a person by hand

- **"Close the other leg within the same hour" at 3 a.m.:** no alert exists. The watch script (T1) is to be built
  "before the stake goes live" (`december_decision_20261125.md:114-115`).
- **The close may not fill:** in post-only, "no executions or liquidations can occur" (`kraken_incidents.md:39-40`,
  `:53-54`); the auto-cancel bug kept orders open about 18 hours (`:47-48`).
- **Delisting rule (lines 131-132):** Kraken settles at a 60-minute TWAP it sets (`kraken_incidents.md:16-18`).
  Closing Hyperliquid in the same hour can open a gap against it. Give an ordered list instead.
- **"Plus a 25% buffer" (addendum line 111):** the stake note uses 30%/35% as rebalance triggers and 25% as the cut
  level (`stake_dhl_20261123.md:37-38`). The addendum's 25% is unexplained.
- **Collateral moves take time:** "needs a withdrawal and a deposit" (`stake_dhl_20261123.md:45`).
- **"Every few hours" on a 10% fall day:** neither threshold nor frequency is measured.

**A better researcher would:**
- Make the rules entry rules: no new position in a coin on Kraken's delisting list, no thin coins on Hyperliquid.
- Cap each venue's deposit in euros from the loss accepted on its failure, using the note's λ* (`stake_dhl_20261123.md:100`).
- Write ADL and delisting actions as an ordered list, tested on the two known events (ADL 2025-10-10, JELLY 2025-03-26).
- Label unmeasured numbers (1 hour, 25%, 10%, "every few hours") as assumed.

## 6. Cleaner than the evidence

- "No public signal leads" (3 of 8, p about 0.06).
- "Coin tail handled" (paper rule, not replayed); "bounded near a 20% blowout" (table shows −36.5%).
- "R509's live rule" (paper); "about −1% to −5%" (only −1.3% on the page).
- "Diversifying lowers the binding risk" (expected loss unchanged).
- "EU-regulated Kraken entity" (no source).
- The €8-28 is called the binding risk but covers one venue. The two-venue figure is about €42.

## 7. Fine

- Fermi arithmetic; Kraken quotes (`kraken_incidents.md:13-14`, `:64`, `:75`); JELLY facts (`hl_incidents.md:41-45`).
- PREREG exit quote (`PREREG.md:37`); BLOWOUT = 0.20 (`lab/xfund_v2.py:29`); PF_ACEUSD at `symbols.csv:87` (under
  `experiments/xfund_eea_v1/`).
