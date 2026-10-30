# PREREG: venue_gap_v1 (R216), how much of the flow books' PnL is crypto, and how much survives on MEXC?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R216
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_venue_gap.py`, `lab/slices.py`, `lab/mexc.py`
- **Source:** R215's first replay read; Codex review (`docs/CONFIDENCE_REVIEW.md` gap 2: the target venue and coin set).

## What the author had seen
R215 (mexc_fwd) replay, 2026-10-01..18, entry one bar late: book A on MEXC prices +4.7% vs +22.5% for the same signals
on Binance (R214), correlation 0.40; book B -0.1% vs +9.7%, correlation 0.11; mean coverage (slices with a MEXC crypto
contract / all signalled slices) 56% for A and 33% for B. Unmapped are Binance TradFi perpetuals (stocks, metals, oil:
NVDA, MSTR, MU, XAG, CL, ...) and two non-ASCII coins. Binance lists 221 TRADIFI_PERPETUAL contracts, the first (XAU)
from 2025-12-11, so the R198 holdout (2025-07..2026-09) can contain them; the in-sample period cannot. No per-symbol or
crypto-only split of any book has been computed.

## Definitions
- **TradFi:** a symbol whose current Binance exchangeInfo entry has contractType TRADIFI_PERPETUAL or an underlyingType
  other than COIN and PREMARKET (any status); the list is saved with the results. Others, and archive symbols absent
  from exchangeInfo, count as crypto.
- **Crypto-only book:** the same book with signals, eligibility and the universe hedge restricted to crypto symbols
  (bins as computed, not re-ranked).

## Measurements
1. Archive, R198 book A (three cells) and B (top_vs_crowd, unit of R200), zero delay as R198, windows in-sample
   2021-01..2025-06 and holdout 2025-07..2026-09: per-symbol gross contribution; the share of the book's gross from
   TradFi symbols; the crypto-only book's net at 1x/2x/3x.
2. Forward replay 2026-10-01..18, entry one bar late (as R214), Binance prices: the crypto-only book, and the crypto
   book restricted further to symbols with a MEXC crypto contract (R215's mapping). With R215 this splits the gap:
   (all, Binance) - (MEXC-mapped crypto, Binance) = coverage; (MEXC-mapped crypto, Binance) - R215 = venue prices and
   funding.

## Reading rule (fixed now)
If TradFi symbols carry **30% or more** of book A's holdout gross, or of its replay gross, MAP and CLAIMS must say the
evidence is partly non-crypto, and the crypto-only numbers become the reference for the owner's venue. Nothing here
changes R198's or R200's frozen verdicts.

## Multiplicity
Trials = 4 (crypto-only A and B in the archive; crypto-only A and B on the forward replay). Program trials before:
9,471,714 (after R215).

## Expectations
Top-trader positioning on stock and metal perps is a new, thin market, and Binance's top-50 in 2026 contains several of
them, so a material TradFi share is plausible. Guess: TradFi carries 20-50% of the 2026 PnL; crypto-only holdout t
falls below 1.
