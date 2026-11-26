# Reflection 2026-11-26: the owner's "maps", and @vince.quant as a paper index

- **The owner's message:**
  > "https://www.tiktok.com/@vince.quant … is tiktok talk about many researches papers so hé Can help because you Can
  > efficiently search for them https://www.instagram.com/reel/DgL5rhoJnDF/ … and for this why dont we have maps like
  > those ? Unefficient?"
- **Lens:** "Have you seen it before?" (Pólya). I checked the lab's record before reasoning.
- **Evidence:**
  - The reel was downloaded with yt-dlp and three frames were viewed. Its caption: "Low-latency, live CME futures and
    options data down to level 3 is coming to QuantPad". The speech was not transcribed.
  - The TikTok's 87 descriptions were read by a Haiku reader: `room_20261126/vince_quant_papers.md`.

## 1. Numbers (from code or quoted lines; anything else says "assumed")
| # | Quantity | Value | Source |
|---|---|---|---|
| 1 | QuantPad's own demo: ES 15-minute opening-range break, long, past five years | 1,027 trades; target first 72, stop first 124, neither 831 | reel frame `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/reels/frames/f_070.png` |
| 2 | Its hit rate against its break-even | 36.7% (95% interval 30.3-43.7%) against 50.2% | frame f_070 |
| 3 | Its net after costs, 2021-11-29 to 2026-11-24, one contract | +$10,128; the curve peaked near $40k and fell back | frame f_070 (peak read off the chart) |
| 4 | ES continuous, nearly the same window (the panel ends 11-24, the lab's bars 11-20) | 4,630 (2021-11-29 15:00 UTC) to 6,944 (2026-11-20 20:00 UTC): +2,314 points, +50%. Gross, unadjusted for rolls and margin, so not comparable with row 3's net | `data/databento/es_1h/` (ES.v.0 ohlcv-1h), read with pyarrow this hour |
| 5 | Round numbers as levels (R246) | RN_CROSS −84.8 bp/day, t −9.93 (gross −17.7, cost 67.1) | `registry/methods.csv:12` |
| 6 | Round numbers, replicated as a difference (R249) | round minus shifted +4.8 bp/day, t 2.53; the book +0.2 bp/day, t 0.03 (gross 13.7, cost 13.5) | `registry/rounds.csv` row R249 (notes) |
| 7 | Pivot levels (R243) | pivot breaks −14.5 bp/day, t −1.99 | `registry/methods.csv:204` |
| 8 | Liquidation cascades on Gate (R206) | net −36 bp/day, t −1.96 (gross +4, cost 40); long cascades continue, short squeezes revert +10 to +26 bp gross, below cost | `registry/rounds.csv` row R206 (notes) |
| 9 | Liquidation proxy: OI drop with a wick (R252) | ALL/24 +2.0 bp/day, t 1.93; NULL; the long bounce is mostly market-wide | `registry/rounds.csv` row R252 (notes) |
| 10 | Base rates of the families these tests belong to | charts (R243, R246, R249): 0 of 15 decided; flow (R206, R252): 2 of 12 (17%) | `registry/lane_families.csv`; `scripts/base_rates.py`, run this hour |
| 11 | The lab's maps | `docs/EDGE_MAP.md` (generated from the registry), `docs/MAP.md` (793 lines), the control room (Performance, Leaderboard, Funding board, Coverage; `docs/BENCHMARK.md:120`) | files |
| 12 | Funding board recorder | last snapshot folder 2026-11-06; it ran in a container, never as a GitHub workflow | `ls data/recorders/funding_board`; `.github/workflows/` |
| 13 | @vince.quant | 87 videos, 84 paper entries; about 12 rated High, none for the carry family (A) | `room_20261126/vince_quant_papers.md` §2 |
| 14 | Video numbers checked against the paper | 6 checked: 1 matches exactly (Brunnermeier-Pedersen's 116 → 100 → 110); 2 partly match (van der Beck's $500M and 0.78/0.33 match, "1,868 ETFs" and "2 to 3%" not found; Baltussen's 1.73 is the top of a 0.87-1.73 range); 1 not found (Khandani-Lo's daily losses and 9:1); 2 not confirmable from the abstract read | same file §4 |
| 15 | Harvey, Liu and Zhu's hurdle | "a t-ratio greater than 3.0" | NBER w20592 abstract, quoted in the same file §3.5 |
| 16 | A3 (Bitfinex + Binance) | t 2.95 | `docs/strategies/STRATEGY_BOOK.md:67` |
| 17 | QuantPad's net per trade | $10,128 / 1,027 = $9.86, under one ES tick ($12.50) | arithmetic on rows 1 and 3 |
| 18 | R524 (A3's paper lane) under the Harvey floor | 54%: blocked; a pass buys a second forward period | `docs/reviews/december_decision_20261125.md`, addendum b |

## 2. What the reel's map is, and the mechanism behind it
- **The picture:**
  - An ES one-minute chart with "Big levels": horizontal lines where large resting orders sit in the CME book.
  - A level-3 book (each order, not only the totals).
  - A panel that backtests a question asked in plain words.
- **The mechanism (approach page, items 2-3):** a resting limit order is optional. Its owner can cancel it before the
  price arrives, and a large visible one may be there to be seen (spoofing is the extreme case). Nobody must trade at
  a "big level", so the map shows intentions, not obligations.
- **The orders that must trade are the forced ones:** stop-losses and liquidations. Osler (2003, 2005) is the FX
  version (not re-read this hour), Brunnermeier and Pedersen (2005) the theory (§4). A map of forced orders points at
  a payer; a map of resting orders does not.
- **QuantPad's own example (rows 1-3, 17):**
  - The 196 trades that reached a target or a stop lose: 36.7% hits against a 50.2% break-even.
  - The total is still +$10,128, so the 831 trades that hit neither carry it. That is an inference from the
    arithmetic, not shown in the frame. With a bracket near 1:1 they need about +$44 each, which a market that rose
    50% over the window can give (row 4, assumed bracket).
  - The net is $9.86 a trade, under one ES tick, so the cost assumption decides its sign, and the frame does not
    state it.
  - So the demo shows a below-break-even rule whose small net rides the market's rise. It is not evidence for the map.

## 3. Have we seen it before? Yes, five times, with lower resolution
- **Levels (charts family, 0 of 15 decided):**
  - Round numbers: R246 lost (row 5). R249 is NULL as a book; one variant replicated a round-minus-shifted
    difference (+4.8 bp/day, t 2.53), and R246's post hoc had the opposite sign (t −3.30). Not reconciled (row 6).
  - Pivots: R243 lost (row 7).
- **Forced orders, by proxy (flow family, 2 of 12):**
  - Gate's liquidation cascades (R206, row 8). Long cascades kept going, and squeezes reverted below cost.
  - OI drop with a wick (R252, row 9, mostly 2022-23 data): NULL.
- **What our tests did not have:** the reel's data. The lab holds ES hourly bars, not a CME level-3 book, so the
  resting-order question was tested on crypto price levels and proxies, not on the book itself. The tests answer
  "do price levels pay after costs", not "does a visible wall predict a move".

## 4. The one new angle: a forced seller everyone can see
- **Brunnermeier and Pedersen** (abstract, room §3.1): "if one trader needs to sell, others also sell and subsequently
  buy back the asset. This leads to price overshooting". Checked by me in the author's copy (October 2004 version):
  - the model's distressed trader's need "is known by the other strategic traders";
  - predation matters "if the distressed trader's position is large relative to the buying capacity of other traders.
    Further, predation is most fierce if there are few predators."
  - The size condition is the lab's own ratio (net forced trade ÷ liquidity in the window, L052).
- **On Hyperliquid the need can be read.** Positions are served by address on the public info API (the lab's
  `scripts/stake_watch.py` already reads fills by address), so liquidation prices can be computed. JELLY
  (2025-03-26): HLP inherited a large short, and CoinDesk's headline calls it a "vault squeezed"
  (`room_20261126/hl_incidents.md:22, :46`). Reading it as predation is mine.
- **An observational test on observed levels,** not a natural experiment: the levels are seen, not assigned.
  The lab's proxies (R206, R252) used price, OI and Gate's liquidation spikes, not position-level liquidation prices
  (assumed from their titles; their PREREGs were not reopened).
- **Approach page for this question:**
  1. Economic question: do known liquidation clusters on HL attract the price and then revert (the overshoot)?
  2. Mechanism: a position past its maintenance margin must be closed by the engine at market. Others who see it
     sell first and buy back after.
  3. Barrier: none for seeing it. Public trackers show HL whale levels (assumed, not checked this hour). The barrier
     is speed and size, which favours the predators, not us.
  4. Fermi: not computed. Size it before any recorder is built.
  5. What we see: nothing others do not.
  6. Cheapest observation: the size first. Read the clearinghouse states of the largest addresses once, put their
     liquidation prices against the book depth, and stop if the ratio is below 0.5%.
- **Prior: low, and from the right family.** The flow family passes 2 of 12 (row 10). The owner is small and slow,
  and point 3 gives us no barrier. It goes into the register as P1, not as a lane.

## 5. "Inefficient?" Partly yes, and not where the reel suggests
- **We have maps (row 11), all in text or on a page built locally** (`scripts/build_dashboard_standalone.py`; whether
  the owner ever opened it was not checked). The funding board's last snapshot is 2026-11-06 (row 12); why it stopped
  is assumed (it ran in a container).
- **The gap is visibility, not data.** The owner reads the lab through my French messages, so the whole state (which
  strategies, what evidence, which read on which date) is rarely in front of them at once.
- **Fix, this hour:** a private page, the lab map in French, with every number linked to its file. It holds the
  mechanisms, the strategies, the decision calendar and the open leads. It shows no forward lane's interim and no
  live funding.
  Published 2026-11-26 (private): https://claude.ai/artifact/1pmeLasqosYVc2bgx6shZu; source
  `docs/guides/carte_du_lab.html`. To refresh, edit the source and republish to that URL.
- **Not fixed:** the funding board recorder. No open question needs it now, and the carry reads use the venues'
  own history. Restarting it as a workflow waits for a question that does.

## 6. @vince.quant as a paper index
- **Useful as an index, not as a source.** About 12 High papers in 87 videos (row 13). The lab already knew 5 of
  them (Lou-Polk-Skouras, deflated Sharpe and PBO, Kelly-Thorp, DeMiguel; Baltussen only as an intake pointer).
- **The video's numbers are not the paper's (row 14).** Of six checked, one matched exactly. Every number goes to the
  paper before it moves anything.
- **What it changes:**
  - **Harvey, Liu and Zhu's t > 3.0 (row 15)** is a bar for a new factor among hundreds of tried ones. As a reference
    bar only, A3's t 2.95 (row 16) sits just under it. R524, A3's paper lane, is already blocked at its first look by
    the Harvey floor (row 18), so no rule moves. The card now notes the bar.
  - **Brunnermeier-Pedersen** gives §4's question.
  - **Nothing for the carry family.** Its next idea has to come from its own data (room §5).
- **Not read in full here:** Shumway-Warther (paywalled); Harvey-Liu-Zhu beyond the abstract.

## 7. How I approached it, and what I would change
- **Right:** I checked the record before reasoning (§3), in minutes.
- **Missed at first:** I nearly read the QuantPad demo as a loss from the hit rate alone. The net was positive, and
  only the "neither" column explains it (row 1). Read the whole panel before naming a result.
- **Missed again, caught by the critic:** I quoted the micro family's 0 of 6 for tests that belong to charts and
  flow. The flow family's 17% is the honest prior for P1, and it is higher. Before quoting a base rate, look up the
  lane's family in `registry/lane_families.csv`.
- **Would change:** the owner's view of the lab should not depend on my messages alone. The private page is
  refreshed at each money read.

## What could invalidate this page
- **The frames:** the reel's speech was not transcribed. QuantPad may claim more than the three frames show.
- **§2's inference** about the 831 trades assumes a bracket near 1:1; the frame does not give the bracket or costs.
- **§3:** the lab never tested a level-3 book. "Big levels" on a real book are untested here.
- **Row 12:** the funding board may have been restarted elsewhere. I found no workflow for it.

## Corrections after the room's critic (`room_20261126/critic_maps.md`; each checked by me)
- Row 10: the level tests are charts (0 of 15) and flow (2 of 12), not micro (0 of 6). Checked in
  `registry/lane_families.csv`. §3, §4 and §7 corrected.
- Row 4: the windows differ by four days, and a gross buy-and-hold is not comparable with a net rule. "Eleven times"
  is removed; row 17 adds the net per trade.
- Row 13: 84 entries, not about 75. Row 16: line 67, not 66.
- §3: "the visual map would have shown us the same data" was wrong (no level-3 book here); "R249 found the mechanism
  real" was a status word on a NULL round.
- §4: "the overshoot is largest when…" is replaced by the paper's own lines, checked by me; "natural experiment" is
  now "observational test".
- §6: "A3 was already outside money" was wrong. R524 is a scale decision, blocked at its first look by the Harvey
  floor (54%).
- Five of the critic's errors leaned toward a cleaner story, again (L064).
