# PREREG: sizecarry_v1 (R281). Does sizing each carry pair by confidence beat equal slots, on the same pairs?

Freeze with `lab.prereg.freeze()` before any run on market data. Never edited afterwards; a change is a new lane.

- **Registry id:** R281 (Claude block R280-R299, claimed on issue #7 on 2026-10-21).
- **Method:** M266 (confidence-sized carry, from the owner's 2026-10-21 ask about "confidence per position").
- **Kind:** a family on archives already read by R275 and R277 (gate 0).
  - Trials: **30** (6 books × 5 sized variants). The equal book is the control, not a trial.
- **Paper only.** Nothing here places an order.

## The question
The carry books hold up to 20 pairs, each with one equal slot. Does giving more notional to the pairs the rule is more
confident in, at the same total notional, earn more after the extra trading it causes? The pairs, entries and exits
stay exactly R275's: only the size of each open pair changes.

## Books (fixed; none is chosen here)
| Label | Set | Lookback | Threshold | Slots | Archive (engine run) | Why this book |
|---|---|---|---|---|---|---|
| R278 A | gate + hyperliquid | 14 d | 5%/yr | 20 | R275 xfund_v1 | forward lane R278 |
| R278 B | binance + mexc | 14 d | 10%/yr | 20 | R275 xfund_v1 | forward lane R278 |
| R278 C | gate + mexc | 7 d | 10%/yr | 20 | R275 xfund_v1 | forward lane R278 |
| batch | binance + gate | 14 d | 10%/yr | 20 | R275 xfund_v1 | the reserved 2020 batch's carry book |
| R279 A | gate + kucoin | 14 d | 5%/yr | 20 | R277 xfund_kd_v1 | forward lane R279 |
| R279 B | binance + kucoin | 14 d | 5%/yr | 20 | R277 xfund_kd_v1 | forward lane R279 |

## The sizing (`lab/sizecarry.py`)
Each day d, after the rule's exits and entries, each open pair gets a score computed from data up to day d only.

| Score | Definition |
|---|---|
| `equal` (control) | 1: R275's book, reproduced exactly |
| `spread` | the pair's funding spread today (short venue minus long venue, annualized over the lookback) |
| `persist` | the share of the last `lookback` days on which that spread was at or above the entry threshold |
| `spread_persist` | spread × persist |
| `inv_vol` | 1 / the standard deviation of the pair's daily price-leg return (long minus short), last 30 days, at least 10 fresh days |
| `spread_vol` | spread / that standard deviation |

- **Weights:** proportional to the scores, averaging 1 over the open pairs, so the book's gross notional is the
  equal book's. No weight exceeds **3**; the excess goes to the others (water-filling).
- **Undefined score:** a pair takes the mean of the defined scores, or 1 if none is defined.
- **Trading:** a pair is resized only when its target weight moves by more than **0.2**.
  - An entry trades its target and an exit the weight held.
  - Every unit of notional traded is charged on both legs.
- **Net on capital:** (gross − cost × notional traded) / (2 × slots), at 7 / 14 / 21 bp per leg per side (1x / 2x /
  3x). That is R275's accounting.
- The cap (3), the band (0.2), the 30-day volatility window and the lookback come from M266's queue entry or from the
  books. None is tuned here.

## Parity guard (run first; aborts on failure)
For every book, `equal` at 1x must equal its engine run's own daily net (`results/daily.csv`) within 1e-9 on every
day.

## Decision (fixed now)
- **Per book:** Hansen's SPA (`lab.inference.spa`, consistent p) over its 5 sized variants. The streams are each
  variant's daily net at **2x** cost minus the equal book's. Stationary bootstrap: block 10, 2,000 draws, seed 281.
- **A book's sizing passes** when all hold:
  - its SPA p ≤ **0.05 / 6 = 0.0083** (Bonferroni over the 6 books);
  - its best variant (SPA's `best`) beats the equal book at 2x cost in both halves of the book's window;
  - that variant also beats the equal book at 3x cost.
- **Verdict:** PARTIAL if at least one book passes, else NULL. Gate 0 either way: these years were read by R275 and
  R277.
- **What a pass earns (pre-committed):**
  - **batch passes:** its best variant joins the reserved 2020 batch next to the equal book, which is the only
    out-of-sample read these years allow.
  - **A forward book passes:** a sized paper lane for that book, with its best variant, may be frozen with a new id.
    - It runs next to the equal lane, which keeps running unchanged.
    - It is decided on its own forward days and on its difference from the equal lane over the same days.
  - **No book passes:** the forward lanes stay equal-weighted, and M266 is recorded as tested.

## Reported, not decided on
- annual net at 1x / 2x / 3x, t and NW t (lag 10), max drawdown;
- notional traded per day;
- the mean largest weight;
- the difference from the equal book at 2x (mean, NW t, halves) and at 3x;
- White's reality-check p next to SPA's.

## Not modelled
- Order-book depth at 3x weight: a $10k book puts up to $750 on one leg. R278's capacity note covers $250.
- Venue-level margin: total notional per venue is unchanged at 1x (Σ weights ≤ slots), as R280 assumes.
- The same limits as R275: marks, fills, collateral moves.

## What the author has seen
- **R275 and R277 in full:** the daily net, trades and audits of every book here, including R275's note that funding
  is 96-105% of the gross.
- **R280:** the books' liquidation days and the pumps on short legs.
- **R278's and R279's forward replays** (2026-08-22..10-21, not scored).
- **R217 (sizing_v1)** found that confidence scaling of the flow books had no out-of-sample support, so the prior for
  this family is weak.
- **`lab/sizecarry.py`** has run only on synthetic data:
  - in `tests/test_sizecarry.py`;
  - in a smoke run of `scripts/run_sizecarry.py` on a synthetic universe, on which wider-spread pairs earn more by
    construction.
- **Not computed on market data:** no score, weight or sized return for any book.

## Inputs (frozen)

```inputs
lab/sizecarry.py  85a4ebe43c617a2b2e7483540130bb37fb4489a70dfd14cf78883926fd683cc9
lab/xfund.py  d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d
lab/inference.py  96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f
lab/stats.py  bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34
scripts/run_sizecarry.py  76d10f2311decb7452829f96000544e65423481236922bade188b152557504d5
scripts/xfund_parity.py  fc79c98b82a7daa277015fca054bad53ab1c71bab04563df89b7d42440b0b301
experiments/xfund_v1/symbols.csv  78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0
experiments/xfund_v1/spec.toml  ffab653a52f37385103bd89ad11fd5d925caf905d0ff5c0aa5af1674de135874
experiments/xfund_kd_v1/symbols.csv  15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b
experiments/xfund_kd_v1/spec.toml  03abb3bf671c018c38b641ebe3c7ccefa573e087a69212fb07fa491e0e584056
```

## Multiplicity
- Trials: 30.
- Program trials before this lane: 9,478,328, after R280.
