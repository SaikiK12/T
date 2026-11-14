# PREREG: levcarry_v1 (R280). How much leverage the forward carry books can carry before an intraday move liquidates a leg

Freeze with `lab.prereg.freeze()` before any run on market data. Never edited afterwards; a change is a new lane.

- **Registry id:** R280 (Claude block R280-R299, claimed on issue #7 on 2026-10-21).
- **Method:** M265 (leverage and liquidation, from the owner's 2026-10-21 ask about leverage and confidence per
  position).
- **Kind:** a measurement on archives already read by R275 and R277 (gate 0 data).
  - Trials: **0**. It chooses no book, rule or parameter, and its numbers are not evidence of an edge.
  - Its reading rules are fixed below, before any run.
- **Paper only.** Nothing here places an order.

## The question
The carry books earn about 5-12%/yr on capital at 1x legs, where each leg is fully collateralized. A trader can post
1/L of each leg's notional as margin and multiply the return by L. What intraday move liquidates a leg, how often did
it happen over 2021-2026, and what is left of the return after the liquidations?

## Books (fixed; the forward lanes' books, unchanged)
| Lane | Book | Set | Lookback | Threshold | Slots | Archive (engine run) |
|---|---|---|---|---|---|---|
| R278 | A | gate + hyperliquid | 14 d | 5%/yr | 20 | R275 xfund_v1 |
| R278 | B | binance + mexc | 14 d | 10%/yr | 20 | R275 xfund_v1 |
| R278 | C | gate + mexc | 7 d | 10%/yr | 20 | R275 xfund_v1 |
| R279 | A | gate + kucoin | 14 d | 5%/yr | 20 | R277 xfund_kd_v1 |
| R279 | B | binance + kucoin | 14 d | 5%/yr | 20 | R277 xfund_kd_v1 |

## The model (`lab/levcarry.py`)
- **Margin per leg:** each leg holds one unit of notional on its venue, backed by 1/L of margin.
- **Liquidation check, per leg and day:** the leg is liquidated when all of the following, summed, reach the
  maintenance margin `mm`:
  - its equity at the start of the day;
  - minus the funding it pays that day (all of it charged before the extreme: conservative);
  - minus its worst adverse move of the day from the day's opening close. For a long, the move is down to the day's
    low; for a short, up to the day's high.
- **Day range:** the high and low over the venue's bars that end in the day.
  - Hourly bars for Binance, Gate and MEXC; daily bars for Hyperliquid and KuCoin.
  - Where a leg has no range for a day, its move is the close-to-close move against it (a lower bound). Such leg-days
    are counted and reported as `unknown_range_share`.
- **Policies:**

  | Policy | Margin | Funds moved between venues |
  |---|---|---|
  | `iso_hold` | isolated, never topped up; equity is 1/L plus the leg's price returns and funding since entry | never |
  | `iso_daily` | isolated, reset to 1/L at every 00:00 | once a day |
  | `cross_daily` | one cross account per venue, reset to 1/L per leg held at every 00:00 | once a day |

  - Under `cross_daily`, an account is liquidated when its legs' summed risks of the day reach its equity. All the
    legs' extremes are assumed to fall at the same moment, which overstates the risk.
- **After a liquidation:**
  - the liquidated leg loses its margin and earns no funding that day;
  - the pair closes, with exit legs charged the next day, and the rule may enter it again later.
- **Net on capital:** L × (gross − cost × legs traded) / (2 × slots), at 7 / 14 / 21 bp per leg per side (1x / 2x /
  3x). Costs scale with L because notional does.
- **Grid:**
  - L ∈ {1, 2, 3, 5, 10};
  - the 3 policies;
  - mm ∈ {1%, 5%}. 1% is a typical altcoin tier-1 maintenance rate on Binance, Gate and KuCoin at small size. 5% is
    a stress value, nearer Hyperliquid's maintenance on low-cap coins (half the initial margin at the coin's maximum
    leverage).
  - 5 books × 5 × 3 × 2 = 150 runs.

## Parity guard (run first; aborts on failure)
- At L = 1 with no liquidation possible (mm = −1e9), each book's daily net at 1x cost must equal its engine run's own
  daily net (`results/daily.csv`) within 1e-9 on every day.
- This is the same check as `scripts/xfund_parity.py`, which passes for all five books
  (R275: 587 / 271 / 664 trades identical; R277: 1,153 / 1,168).

## Outputs (`experiments/levcarry_v1/results/`)
- **`summary.csv`**, one row per run:
  - annual net at 1x / 2x / 3x (%);
  - t and NW t (lag 10);
  - max drawdown and worst day (% of capital);
  - liquidated legs and pairs closed by a liquidation;
  - days;
  - `unknown_range_share`.
- **`events.csv`:** every liquidated leg, with date, coin, venue, leg, move and account flag.
- **`moves.csv`:** per book and leg side, the quantiles (50, 90, 99, 99.9, 100%) of the worst adverse price move per
  held leg-day.

## Reading rules (fixed now)
- **Safe leverage** of a book under a policy and mm: the largest L in the grid with **zero** liquidated legs over its
  whole window.
- **Kept share** at L: the 1x-cost annual net at L divided by L × the annual net at L = 1. It is 1 when liquidations
  cost nothing.
- **What the owner is told:** for each book, the safe leverage under each policy at mm 5%, and the net at 1x / 2x / 3x
  there. Below that, the worst liquidation days.
- **Pre-committed action:** the forward lanes stay at 1x unless both hold for a book:
  - its safe leverage under `iso_daily` at mm 5% is at least 3;
  - its kept share there is at least 0.9.

  If both hold, a leveraged forward paper lane for that book may be frozen as a new lane, with a new id, at that L
  under `iso_daily`.
  - Live money still needs the book's own forward PASS and `lab.gate.go_real()`.
  - A leverage the owner uses must not exceed the safe leverage found here.

## Not modelled (each one is a reason the safe leverage here is an upper bound or a lower bound)
- **Per-coin maximum leverage and tiered maintenance by position size.** Many low-cap coins cap leverage at 3-10x
  (Hyperliquid, MEXC). An L above the cap cannot be opened. → Upper bound on what is tradable.
- **Marks.** Venues liquidate on a mark or index price, not the last trade. Trade wicks (dYdX on 2025-10-11) overstate
  the move. → The model liquidates more often than a venue would.
- **Liquidation fees and partial liquidation.** A liquidation usually costs an extra fee; venues may reduce a
  position in steps instead. → Fee: the loss is understated. Steps: overstated.
- **Moving margin daily between venues** (`iso_daily`, `cross_daily`): transfer fees and delays, about one transfer a
  day per venue. Not costed.
- **Auto-deleveraging and funding-rate caps.**
- **Intraday path order:** funding and the extreme are both charged at the start of the day (conservative).

## What the author has seen
- **R275 and R277 in full:**
  - their daily net, trades and audits;
  - R277's dYdX crash days (2025-10-11/12), where trade prices moved −60% and +150% in a day on one venue.
- **R278's and R279's forward replays** (2026-08-22..2026-10-21, not scored), whose status shows each book's replay
  total.
- **`lab/levcarry.py`** has run on synthetic data only, in `tests/test_levcarry.py`.
- **Codex's review on #7 (2026-10-21),** with a synthetic counterexample: unknown ranges counted as zero risk, and
  `iso_hold` margin not charged for funding. Both are fixed in this version and tested.
- **Not computed on market data:** no day range, adverse move or liquidation for any book. No high or low column of
  any archive file has been read by a carry lane before this freeze.

## Inputs (frozen)

```inputs
lab/levcarry.py  e99679892c4f0704945af5492b3046c8fd5b73247ecfb200f6b1984891dd6d9c
lab/xfund.py  d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d
scripts/run_levcarry.py  36e5789028242ec90d1ce24493f34198c6cd965653b056bede05c3a6d7b265fc
scripts/xfund_parity.py  fc79c98b82a7daa277015fca054bad53ab1c71bab04563df89b7d42440b0b301
scripts/forward_xfund.py  de361e3a90583ba2c9fb7dbf8b5e28677404184cb2425e4bd9ddf88932d18baa
scripts/forward_xfund_kc.py  497b6c6f0e50331456559856608f98243371e283c7a9623dfca87a610cbce916
experiments/xfund_v1/symbols.csv  78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0
experiments/xfund_v1/spec.toml  ffab653a52f37385103bd89ad11fd5d925caf905d0ff5c0aa5af1674de135874
experiments/xfund_kd_v1/symbols.csv  15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b
experiments/xfund_kd_v1/spec.toml  03abb3bf671c018c38b641ebe3c7ccefa573e087a69212fb07fa491e0e584056
```

## Multiplicity
- Trials: 0 (a measurement).
- Program trials before this lane: 9,478,328, after R279.
