# PREREG: xyzbal_fwd (R530). The balanced weekend fade of trade.xyz US-stock perps, tested forward

- **Registry id:** R530
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-25)
- **Date registered (UTC):** 2026-11-25

Method M563: the balanced, market-neutral form of M515. Parents: M515, R462, R463, R464, R465 and R467. This file is
frozen by `lab.prereg.freeze()` before the first weekend it scores (Friday 2026-12-04). It is never edited after the
freeze; a changed idea is a new lane.

## Question
On fresh weekends from Friday 2026-12-04, does a book on trade.xyz's US-stock perps beat its measured costs? The
book:
- **buys** every market whose weekend move is at least 50 bp below the weekend's median move;
- **sells** every market at least 50 bp above that median;
- holds equal notional on each side;
- trades from Sunday 19:00 to Sunday 22:00 New York.

## Why this lane
- **The mechanism.** On a weekend no external price exists for a single name, and market makers cannot hedge it. The
  perp's idiosyncratic weekend move overshoots and is partly given back when external prices return (R462 PASS at
  gate 0; R465 replicated on Lighter).
  - The common weekend move carries macro news and is hedgeable from the CME reopen. It does not reverse: R464 and
    R432, the index and commodity perps, are NULL.
  - Removing the common move removes noise, not edge. This is the textbook reversal book: market-adjusted, $1 long
    and $1 short (Nagel 2012, `research/intake/nagel_evaporating_20261125.md`).
- **The reason for a second forward lane: speed of proof.** R463 fades each market's whole move, so every weekend
  carries the common shock. On R462's weekends (`docs/reviews/reflection_20261125_power.md`):

  | Book | Net a weekend, A | SD, A | Net, B | SD, B | Power at half the effect, R463's schedule |
  |---|---|---|---|---|---|
  | raw (R463) | +43.7 bp | 49.7 | +21.9 | 106.1 | 32% |
  | balanced (this lane) | +52.0 | 27.7 | +22.2 | 35.9 | 92% |

  - At half the in-sample effect, R463 would most likely end NULL while the effect still paid. This lane would most
    likely decide by its 20th traded weekend.
- **Accessible to the owner:** Hyperliquid's xyz markets, at growth-mode fees.

## What the author has seen
- **R462's weekends, 2026-04-30 .. 2026-11-09** (its samples A and B), including its `rel` diagnostic cell. Also this
  book's per-weekend nets on those weekends, computed in cycle 5 by `scripts/check_wknd_power.py` from bars refetched
  with end 2026-11-10.
  - This lane's code reproduces them exactly: A gross +59.9 bp, SD 27.7; B gross +30.1 bp, SD 35.9.
- **Cycle 5's crypto-proxy split.** MSTR, COIN, HOOD, CRCL, BMNR, STRC and IREN faded +56.8 bp in A, against +44.1 bp
  for the rest.
- **The recorded xyz and Lighter book costs, 2026-11-11 .. 11-24** (cycle 4, `scripts/check_wknd_depth.py`): costs
  only.
- **Nothing after 2026-11-09** has been computed or looked at: no price, weekend move or return.
  - R463's and R467's journals were not opened: a_trades, b_trades, tickets and status.
  - The weekends of 11-13 and 11-20 are unseen, but this lane does not score them. It starts on 12-04 by its frozen
    rule.

## Universe
- **R462's 76 markets:** `experiments/xyzwknd_v1/universe.csv` (sha256 below).
- **Listing rule:** a market counts for a weekend if its first hourly candle is at least 7 days before Friday 20:00.
- **Pre-IPO weekends** are skipped (R463's rule).
- **Delisted markets** drop out when their candles stop. That is recorded as unpriced, not as zero.

## Data
- **Prices and funding:** Hyperliquid's public info API (`candleSnapshot` 1h and `fundingHistory` for
  `xyz:<coin>`), fetched by the scorer after each weekend.
- **Fees and book costs:** recorded on branch `claude/xyz-books-data` by `scripts/record_xyz_books.py`: `books/`
  hourly snapshots with walked costs; `markets/` fee settings.
- **The trade venue is the data venue,** trade.xyz on Hyperliquid.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Available by decision time? | Membership and coverage vintage | Missing-value rule |
|---|---|---|---|---|---|---|
| W (bp) = 10,000 · ln(P_E / P_R) | hourly candle close | Hyperliquid, xyz:<coin>, USDC | the close of the last candle opening in [t − 3 h, t − 1 h] (rule.price_at) for R = Friday 20:00 and E = Sunday 19:00 New York | yes: the candle closing at or before E | R462's 76-market universe, frozen 2026-11-11; listed ≥ 7 days | no price within 3 h → unpriced, not traded |
| median W | W of all priced markets that weekend | same | same | yes | same | fewer than 5 priced markets → no trade |
| rel W = W − median W | W, median W | same | same | yes | same | — |
| side | rel W | — | buy if rel W ≤ −50 bp, sell if ≥ +50 bp | yes | — | — |
| return | candle closes at E and X1 = Sunday 22:00; hourly funding settled in (E, X1] | Hyperliquid | rule.event_row | scored after X1 | — | no X1 price → unpriced |
| cost | `markets/` fee; `books/` walked $1k cost | `claude/xyz-books-data` | snapshot nearest E and X1 within 90 minutes | recorded forward | forward-captured | 10 bp a fill when no snapshot, counted |

- **Classification:** prices point-in-time; book costs forward-captured; the universe current as of 2026-11-11.
  Markets listed after that date are not added: this lane uses R462's universe.

## Rule (frozen)
- **Plain weekends only.** The weekends are R462's (`scripts/xyzwknd_rule.py`): R = Friday 20:00, E = Sunday 19:00,
  X1 = Sunday 22:00 New York. Excluded: a Friday that is not a trading day or is an early close, and a Monday that is
  not a trading day.
- **Each market's weekend move:** W from R to E, as in R462.
- **The book.** With at least 5 priced markets:
  - rel W = W − the weekend's median W;
  - buy every market with rel W ≤ −50 bp and sell every market with rel W ≥ +50 bp, from E to X1;
  - equal notional on each side.
  - A weekend with no market on one side does not trade.
- **Per trade:** g = side × (price move + funding) from E to X1, and net = g − cost.
- **Cost:**
  - two taker fees, from that day's `markets/` file under Hyperliquid's HIP-3 and growth-mode scales (R463's
    `taker_fee_bp`);
  - plus the walked cost of a $1k market order on the side traded, at E and at X1, from the snapshot nearest each
    instant within 90 minutes, else 10 bp a fill (counted).
- **Weekend net (decides)** = (mean net of the long side + mean net of the short side) / 2.
- **Costs at 2x and 3x:** gross − 2 × cost and gross − 3 × cost, per weekend.
- **Reported, not decided on:**
  - the weekend net at the $5k book cost;
  - the weekend's common move (the median unfaded E→X1 move);
  - trades on the crypto-proxy names (MSTR, COIN, HOOD, CRCL, BMNR, STRC, IREN);
  - fallback fills.

## Decision
On traded weekends in calendar order, with weekend nets at 1x. The bootstrap p is the share of 10,000 means of whole
weekends, drawn with replacement (seed 530), at or below 0.
- **NULL (futility):** at 15 traded weekends, if the mean of the first 15 is at or below 0. Later weekends cannot
  change it.
- **PASS at a look** (20 traded weekends with p < 0.01, or 30 traded weekends with p < 0.04), over the first 20 or 30
  weekends, when all of these hold:
  - the mean at 1x is above 0 with that p;
  - the mean at 2x is above 0;
  - the mean without the best 3 weekends is above 0.
- **At 30 traded weekends otherwise:** NULL.
- Between looks the lane is pending. The looks' alphas sum to 0.05.
- **What a PASS earns:**
  - a request to the owner for small calibration orders on Hyperliquid (hard rule 5);
  - the gates in `docs/GATES.md` and `lab.gate.go_real()`.
  - It does not authorize real money.
- **FINDINGS will report:**
  - per weekend and per trade, at 1x, 2x and 3x;
  - the $5k cost;
  - after France's 31.4% flat tax on the year's net;
  - against euro cash after tax (about 1.5%/yr: `docs/reviews/answers_20261124.md`), per unit of capital.

## Supply, break-even and power (written before the freeze)
- **Supply.** In sample, 28.6 (A) and 36.8 (B) trades a weekend, and 23 of 23 weekends traded.
  - About 45 plain weekends a year. The first are 12-04, 12-11 and 12-18, then 01-08: 11-27, 12-25 and 01-01 are
    excluded.
  - The 20th traded weekend falls about late April 2027, the 30th about early July 2027.
- **Break-even.** In-sample gross was +59.9 bp a weekend (A) and +30.1 (B).
  - At $1k the measured cost is about 7.9 bp a trade (1.8 bp of fee plus a 6.05 bp book round trip, the median of
    cycle 4's Sunday snapshots). So the break-even is about 30-60 bp of cost.
  - At $5k about 11.6 bp.
- **Power** (resampling R462's 23 weekends, R463's schedule):
  - **at the in-sample effect,** a pass 100% of the time;
  - **at half the effect,** 92% (63% by the 20th traded weekend; futile 1%). The expected t at 20 weekends is about
    18.2 / (32 / √20) ≈ 2.5.
  - **at zero effect,** 6% (the whole-weekend bootstrap is slightly liberal at 20-30 weekends).

## Forecast (outside view, written before the freeze)
- **The family's decided pass share.** `scripts/base_rates.py` files these lanes under "calendar": 23% of decided tests
  pass. The closed-market lanes alone pass 3 of 5 decided (R462, R465 and R468 against R464 and R432).
  - Their later samples were weak: R462's B had 3 of 6 weekends positive; R465's C was flat; R468's B was null.
  - One of the two predictions of the refined mechanism failed (the crypto proxies, cycle 5).
- **Prior π ≈ 0.35:** above the calendar share, because a mechanism and a negative control exist; well below the
  sub-family's 3 of 5, because of the weak later samples.
- **Power ≈ 0.92** at half the effect.
- **α ≈ 0.06.**
- **P(PASS) = 0.35 × 0.92 + 0.65 × 0.06 ≈ 0.36.** PPV = 0.322 / (0.322 + 0.039) ≈ 0.89.

## Pre-mortem (written before the freeze: "it failed because…")
1. **The in-sample edge was mostly bid-ask bounce in last-trade closes.** Nagel finds about 40% of a closing-price
   reversal is bounce. Forward costs measured on the book then took the rest. Bounded by the power at half the effect
   and by the 2x condition.
2. **Dollar-neutral is not beta-neutral.** After a broad weekend move the book is long the low-beta names and short
   the high-beta ones. If the common move continued on Sunday evening, the book lost. The common move is reported
   each weekend; no fix is made in sample.
3. **trade.xyz changed its closed-market oracle, its sessions or its bounds,** as it did twice in 2026. Stop rule
   below.
4. **More weekend market-making capital arrived** and the overshoot shrank below costs (decay). The futility read at
   15 weekends catches it.
5. **Plumbing.** A failed fetch or a stopped recorder priced fills at the 10 bp fallback and over-charged. Fallbacks
   are counted and reported.

## Multiplicity
- **Trials:** 1. One rule, one exit, one decision.
- **Program trials before:** 9,785,791 (after: 9,785,792). Read against `registry.program_trials()`.
- **Overlap.** The lane runs on the same weekends and markets as R463: their weekend nets correlate at 0.68 in sample.
  It also overlaps R467 (Lighter). These are three forward reads of one family.
- **Selection.** The balanced design was chosen after R462's `rel` cell was seen strong. The forward data is fresh,
  and the selection is disclosed here.

## Evidence lineage
- **Canonical method ids:** M563 (new), parent M515.
- **Parent rounds:** R462 (seen, both samples), R463 and R467 (forward, sealed, not opened), R464 and R432 (the
  negative controls).
- **Fresh sample:** weekends from Friday 2026-12-04, none of them seen.
- **Gate admissibility** is reported separately from this lane's verdict in FINDINGS.

## Stop rules
- **Nothing is retuned:** no other threshold, instant, universe, weighting, beta hedge, size, venue or exit. A
  changed idea is a new lane.
- **A fault in the script** is fixed with a test and a note in the lane's README. If the fix changes what a scored
  weekend means, the lane is stopped and re-registered.
- **If trade.xyz changes** its closed-market oracle (the 30-minute EMA), its US-stock hours or its discovery bounds,
  the weekends after the change are reported separately and the lane is re-registered.
- **R463 is unchanged** and keeps its own decision.
- No orders, no money, no credentials.

## Known limits (written before the first weekend)
- **Last trades.** Prices are hourly candle closes, as in R462 and R463's A. R463's B tickets walk the live book for
  the raw book's trades, and many of this lane's trades are the same names at the same instants. This lane has no
  tickets of its own.
- **One snapshot an hour.** The nearest book snapshot can be up to 90 minutes from the instant.
- **Size.** $1k a fill; the $5k cost is reported. The entry hour has the thinnest books of the week (cycle 4).
- **Fees.** Growth mode can end for a market; each fill is charged the fee listed that day.

```inputs
a134009df32bbbd18602da27f63308d96642db350586870c291a7c2176d00e42 scripts/run_xyzbal_fwd.py
181532ca9a41aa6d7295a8cac07ec07aaa694837df9d3b03e68bde6efe22bfa0 tests/test_xyzbal_fwd.py
d0caa3e1a6220301f7cd663157f105ee8bba816be61e30169c0262fd4c8b7d8e scripts/run_xyzwknd_fwd.py
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a scripts/xyzwknd_rule.py
746d69923e55a68a5fefad555afba4647eac8b41d355b460edaaa73c1f611373 experiments/xyzwknd_v1/universe.csv
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d lab/sessions.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
6198c5471c38e70834ca6faa04ae286cebce588836707237c3d5e890aecf5fb6 .github/workflows/claude-xyzbal.yml
f52fe602de61feadcf9f455e3b0f17cbcc8e5a6304102744c0f7b5f6dc80388e scripts/check_wknd_power.py
```
