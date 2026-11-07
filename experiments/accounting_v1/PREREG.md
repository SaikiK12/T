# PREREG: accounting_v1 (R264). How much do zero-filled gaps move the flow books?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R264 (Claude block R260-R279, claimed on issue #7)
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_accounting.py`. It reuses `build()` and the windows of `scripts/run_regime.py` (R233), unchanged.
  Books A, B and X2 must equal R217's `daily.npz` (max |diff| < 1e-12) on 2021-01..2025-06 before anything else.
- **Origin:** docs/DIRECTION.md step "survivor re-check", and item 4 of the PR #25 integrity audit. The audit says
  `lab/slices.run` (legacy) gives a held coin with a missing next return 0 and keeps it held. Its size was never
  measured.
- **Gate:** 0. **This is a measurement, not an edge test: trials = 0.** No rule or parameter is selected.

## What the author has seen
- The books' legacy nets at 1x/2x/3x (R217, R233, R260, R262). Book A validation: +13.6 bp/day at 1x.
- R222/R261 checks: 29 top-20 member cells with a missing next return over 2021-2026. That was R263's universe, not
  these books.
- No bridged return has been computed for these books.

## Definitions
- **Positions:** `P[t, s]` from `build(u)`, unchanged. Legacy accounting earns `nan_to_num(ret[t, s])`.
- **A gap episode in coin s:** a maximal run of rows i..j with `ret[t, s]` not finite.
  - It is **held** if `P[i, s] != 0`.
  - Its **start price** is the last finite `close[., s]` at or before row i.
  - Its **end price** is the first finite close after row j. If there is none, the coin never traded again in the
    archive: the episode **never resumed**.
- **Bridged return of a held, resumed episode:** `P[i, s] x (end price / start price - 1)`.
  - It is the price move over the gap at the position held when the gap began, booked on the day of row j.
  - Positions cannot trade inside the gap, so their changes there are left as legacy (cost included).
  - Funding inside the gap is ignored (not observed).
- **Corrected daily net** = legacy daily net + the day's bridged returns. This is at tier costs 1x/2x/3x, with the
  same hedge as legacy.

## Reported per book (A, B, X2) and window
Windows:
- discovery 2021-01-01..2023-12-31;
- validation 2024-01-01..2025-06-30;
- spent 2025-07-01..2026-09-30, exploratory and not decided.

Measures:
1. **Exposed-missing share:** the sum of |P| over cells with a non-finite `ret`, divided by the sum of |P| over all
   cells.
2. **Episode counts:** held episodes, resumed or never resumed. For never-resumed ones, their |P| at the start, summed.
3. **Bridging impact:**
   - signed: the mean bridged return in bp/day;
   - bound: the mean of |P| x |gap move| in bp/day;
   - both also as shares of the legacy 1x mean net.
4. **Corrected vs legacy net:** mean bp/day and NW t (lag 10) at 1x/2x/3x.

## Decision
**DATA_PASS** if, for every book in the discovery and validation windows:
- |signed impact| < 10% of |legacy 1x mean net|; and
- the bound < 25% of it.

Otherwise **NULL** ("the accounting matters"). In that case the panel and EDGE_SCOREBOARD say so next to the forward
lanes on these books. Frozen lanes keep running; only their reading changes.

## Not covered
- Delisting settlement prices. Never-resumed episodes are counted, not valued.
- Carry R191 (its own runner); R263 (it uses `missing="legacy"` and reports its own exposure count).
- Hedge-leg gaps: the legacy hedge already averages only coins with a finite return.
