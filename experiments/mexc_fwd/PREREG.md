# PREREG: mexc_fwd (R215), the R200 signals traded on MEXC prices and funding

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R215
- **Owner (single writer):** the session that froze it; it writes only `experiments/mexc_fwd/journal/` and `data/mexc/`
- **Code:** `lab/mexc.py` (public MEXC futures endpoints, no keys), `scripts/forward_mexc.py`
- **Source:** FOUNDATION (the owner's venue is MEXC alts); Codex review, `docs/CONFIDENCE_REVIEW.md` "recommended next
  research lane" (target-venue transfer).

## Why
Every lab result so far is measured on Binance USD-M prices. The owner trades MEXC. This lane holds the signal fixed
(R200's Binance-derived bins, unchanged) and measures the books on MEXC's own hourly closes and settled funding: a
transfer test of the signal to the owner's venue, not a new signal.

## What the author had seen
R200's 18 replayed days on Binance (A +22.2%, B +9.7%); R213 (delay costs 1-2%). MEXC: the contract list, that hourly
klines go back to 2021 and funding history is public; one BTC_USDT hourly range and three funding rows were printed while
probing the endpoints. No MEXC return of any altcoin and no book on MEXC prices has been computed.

## Rules
- Signals: R200's `signals.csv` (bins of top_vs_crowd, taker[24], taker[4]; eligibility; Binance liquidity rank).
- Tradable: an R200-eligible symbol whose MEXC crypto (type 1) USDT perpetual exists in that day's contract snapshot,
  matched by `lab.mexc.map_symbols` (base, base without a 1000/1000000 prefix, three aliases: FIL→FILECOIN,
  PUMP→PUMPFUN, TRUMP→TRUMPOFFICIAL). TradFi and unmatched symbols are excluded and counted.
- Entry one bar late as R214: a slice signalled at row t opens at row t + 1 if tradable there; held 72 h; size
  1 / (72 x 9.316); universe hedge over the tradable symbols; tier costs by Binance liquidity rank (as R200), 1x/2x/3x.
- Return: MEXC hourly close[t+1] / close[t] - 1, minus MEXC's settled funding rate at settlement hour t + 1 (longs pay
  positive rates). A missing MEXC close earns nothing that hour.
- Books: **A** (three cells, primary) and **B** (top_vs_crowd).
- Days: **on-time** from 2026-10-20 (UTC); 2026-10-01..19 computed for warm-up and reported as `replay`.

## Decision
At 90 on-time days (2027-01-17 at the earliest): `lab.gate.go_real()` on book A's daily 1x net. 30/60-day checkpoints
are monitoring only. B is reported, never promoted.

## Reported, not decided on
2x and 3x; gross, cost, hedge, funding per day; coverage (tradable / eligible slices, symbols dropped and why); daily
correlation with R214's A (same signals and delay on Binance prices) and the gap between them; MEXC's listed taker and
maker fee per contract next to the modeled tier cost.

## Multiplicity
Trials = 2. Program trials before: 9,471,712 (after R214).

## Expectations
MEXC perps track Binance closely for liquid alts, so the books should track R214 with correlation above 0.8; funding
differs by venue and could move the net either way. Coverage: most crypto names map; the TradFi names R200 carries do
not.
