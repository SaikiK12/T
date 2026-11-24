# Self-review 2, 2026-11-24: ten cycles of my own choices as data (L025-L033)

- **The rule.** `CLAUDE.md` step 5 asks for a self-review every tenth cycle: outcomes by lens, failure modes, what a
  better researcher would have done, and unasked work worth more than the plan.
- **The first review** was `self_review_20261123.md`.

## The ten cycles
| # | Work | Lens | Kind | Outcome | Changed a money decision? |
|---|---|---|---|---|---|
| 1 | R526 risk limits | Invert | test | PASS. Entry filters remove the tail; the stop is dropped | yes: live entry filters |
| 2 | R527 three-lane combined read | Change the scale (beat the plan) | test, frozen | pending (12-15 / 12-25) | yes: replaced the forward sleeves |
| 3 | Stake ticket on live books | The owner's reach | tool | Kraken's retail margin binds; one wrong access inference corrected | yes: leverage 2.5 → 2.0 |
| 4 | Thorp (Kelly) | Borrow a field | method reading | Leverage is needed to beat cash; the jump is venue failure | yes: half Kelly |
| 5 | Two-account simulation | What the engine cannot see | measurement | Found a bug in my own margin measure | yes: Kraken 1.5x, others 2x |
| 6 | Venue failure base rates | Borrow a field (credit) | reading + measurement | About 2%/yr of the stake | yes: a stake needs about 5%/yr forward |
| 7 | R528 closing momentum | Follow the plumbing (wide) | test | NULL ($0.97 of data) | no |
| 8 | Ioannidis + base rates | Count the chances | method reading + tool | Payer families pass 43-64%, pattern families 0-23% | process: forecast rule |
| 9 | R529 index-roll front-running | Who pays (wide) | test | NULL (forecast 15%) | no |
| 10 | dYdX premise | Small before big | measurement | Not a usable floorless venue | no (a lane avoided) |

## Outcomes by kind and lens
- **Money-station work (cycles 1, 3-6): 5 of 5 changed a concrete money decision.**
  - Two of them (3, 5) found errors in my own plan before any money moved.
  - Measured yield: the highest of any kind of work in these ten cycles.
- **Wide tests (7, 9): 0 of 2.** Both were honest nulls, cheap ($0.97, and no new data). The forecast written for R529
  said 15%. R528's would have said 5-10% if I had written one.
- **Method readings (4, 8): 2 of 2 changed a rule.** One more source was blocked (Tetlock), and none was bypassed.
- **Premise check (10):** it saved a registered round in about 30 minutes.

## Forecasts, scored
| Round | P(PASS) written before the freeze | Outcome | Brier |
|---|---|---|---|
| R529 | 0.15 | FAIL | 0.023 |

- One forecast scores nothing. The rule started on cycle 8, and the next review needs at least five.

## Failure modes in these ten cycles
- **A flaw in my own model, caught by an odd number:** the uniform-move margin on mixed accounts (cycle 5). It is the
  second Millikan save after L023; the rule already exists.
- **An inference from a field name:** Kraken's `dlt` and `europa` schedules (cycle 3). A search fixed it before anything
  was written.
- **A decision rule judged against the wrong base:** R526 compared each limit with the stressed base, so the stop
  passed while it doubled drawdowns.
- **Process slips:** five web searches unlogged for two cycles; one wide test (R528) chosen without a forecast.
- **The same family for six cycles (1-6).** I wrote the reason each time (the money station binds), and it was right
  to stay.

## What a better researcher would have done
1. **Write the forecast before every test from the start.** R528's 5-10% would have sent the wide cycle to a payer
   behind friction (L032) instead of a public pattern.
2. **Test risk code on mixed-direction cases before publishing its numbers.** The ticket's figures of 11-23 were wrong
   for a day.
3. **Ask "who is paid first?" before "who pays?"** Both wide nulls had real payers, with public schedules and arbitrage
   capital already in place.
4. **Check the venue's own API before writing a venue into a plan.** That was dYdX, and Kraken's EEA list before it.

## Unasked work worth more than the plan (ranked for real money)
1. **Intraday risk on the design gap.** Kraken, Hyperliquid and KuCoin are daily bars in every risk number so far.
   Hyperliquid's hourly candles from 2026-04 and Kraken's public hourly charts can measure the worst hour against a
   leg on the forward lanes' coins.
   - It is the largest unmeasured risk in the stake rule.
2. **A friction map** (L032). It would list products where arbitrage capital is barred: retail-only venues, KYC-gated
   mint and redeem, separate margins, mandates that forbid the trade.
   - It is a better source of new payers than published anomalies.
3. **Lane health before the December reads.** R524 scores from 2026-11-25, so check its first on-time day, and keep
   R509, R520 and R524 scoring for R527.

## Rules
- **No new rule.** The lessons of these cycles are already in `CLAUDE.md`:
  - the forecast and Ioannidis (cycle 8);
  - Thorp (cycle 4);
  - rule 7's "payers, not patterns" (cycle 8).
- **Candidate for promotion if it recurs:** "who is paid first?" (L032), as a second question in the "Who pays" lens.
- **Pruning check.** Every `CLAUDE.md` rule changed at least one decision in these ten cycles except "Tools are not
  goals", which had no occasion. It is kept: it costs nothing.

## Addendum, the same cycle: unasked item 1 started (intraday risk)
- **Result.** Intraday basket drops reach −44% (hourly closes) and about −65% (hourly lows, 2025-10-10). Daily closes
  showed at most −29%.
- **Effect on the stake.** Long altcoin accounts drop to leverage 1 until the venues' own mark prices on the wick
  days are measured. The previous rule (1.5-2x) would have been liquidated on 2025-10-10.
- **What it says about my process.** Every margin number I produced in five cycles rested on daily closes. Data
  resolution is part of the model, and checking it was the highest-value unasked item.
