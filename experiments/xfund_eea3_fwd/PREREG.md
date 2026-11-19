# PREREG: xfund_eea3_fwd (R512). R511's three-venue carry book forward on paper from 2026-11-20, decided by a daily sequential monitor

Freeze with `lab.prereg.freeze()` before the first tick. Never edited afterwards; a change is a new lane.

- **Registry id:** R512
- **Gate:** 2 (forward paper). Only days decided live from 2026-11-20 count. Nobody had seen them when this was frozen.
- **Source:** R511 xfund_kaster_v1.
  - It PASSed on 31 never-read coins.
  - Its reported three-venue book (Kraken + Hyperliquid + Aster, 132 coins) made +25.04 / +23.43 / +21.81 %/yr at
    1x / 2x / 3x, NW t 6.23, 2025-12..2026-11.
- **Why:**
  - **More coins than R509.** Aster adds Kraken thin coins that Hyperliquid lacks, so the book has more slots to fill
    and more trades to measure.
  - **The owner's requests of 2026-11-18/19:** large or stable gains, and less waiting.
  - **A decision that can come as soon as the evidence suffices.**
- **Owner (single writer):** the session that froze it, then the GitHub workflow `claude-carry-paper.yml`, which
  ticks it.
  - It writes only `experiments/xfund_eea3_fwd/journal/` and `data/xfund_eea3_fwd/`.
- **Paper only.** Nothing here can place an order or move money.

## Book
| Book | Venue set | Lookback | Entry threshold | Slots |
|---|---|---|---|---|
| A | kraken + hyperliquid + aster | 14 d | 5%/yr | 20 |

- R275's rule as R509 runs it (`lab.carrylane`, `lab.xfund`). Per coin, the engine takes the widest eligible pair
  among the three venues.
- **Universe:** R511's frozen table (`experiments/xfund_kaster_v1/symbols.csv`, 132 coins).
- **Daily bars on all three venues; funding as each venue settles it:**
  - Kraken: hourly relative rate.
  - Hyperliquid: hourly.
  - Aster: per settlement of 1, 4 or 8 h.
- **Warm-up:** data from 2026-10-01, rebuilt from the public APIs. The book replays, then inherits its pairs at live
  prices on 2026-11-20; the inheritance is charged as entries.

## Accounting
- **Journal and book records as R509.** Every on-time ticket gets both legs' live books walked at $1,000 and $2,500
  (`scripts/forward_xfund_eea.py` `record_books`, with an Aster book client).
- **The decided series:** net_book (`scripts/read_xfund_eea3_fwd.py`).
  - It is R509's definition: the 1x fill-accounting net, with the flat 7 bp replaced by each leg-side's measured
    $1,000 cost plus the taker fee.
  - Fees: Kraken 5 bp, Hyperliquid 4.5 bp, Aster 4 bp.
  - A leg-side without a book record costs 21 bp.

## Decision: a daily sequential monitor (`lab.anytime`)
- **Statistic.** E_n is the asymptotic HAC mixture e-process of net_book after n scored days:
  - a one-sided normal mixture over the drift, on S_n / sigma_n;
  - sigma_n is the Bartlett long-run sd, bandwidth floor(n^(1/3));
  - the mixing sd rho is tuned to cross earliest at n = 90 for alpha = 0.025.
  - It is checked on every scored day from day 30.
- **PASS** on the first scored day n in [30, 180] with E_n ≥ 40.
- **FAIL:**
  - at once if cumulative net_book falls below −3% (kill switch);
  - at 90 scored days if the mean net_book over them is ≤ 0;
  - at 180 scored days without a crossing.
- **RUNNING** otherwise.
- **Why this rule.** A deep reading on 2026-11-19 compared exact and asymptotic sequential tests on this kind of series
  (`research/intake/anytime_valid_20261119.md`). Its simulations were re-run here, 4,000 paths of 720 days, daily sd
  18 bp, t5 tails:
  - **Size** (crossings with mean 0): 3.0% i.i.d., 2.2% with AR(1) −0.2, 4.2% with AR(1) +0.2.
  - **Speed at a mean of 6.6 bp/day:** median crossing on day 47 (i.i.d.) or 38 (AR −0.2); 82-93% cross by day 90.
  - **Speed at 3.3 bp/day:** median day 179.
  - **The exact alternative is slower.** Betting with a pre-registered loss bound is valid at any sample size, but the
    bound caps the bet: median about 80 days, and 0.16 by day 90 at a matched size.
- **What it does not guarantee.** E_n is valid only asymptotically, and its size is a simulation figure. It describes
  the mean of the window it saw; it does not prove persistence.
- **What a PASS earns.**
  - A frozen small-stake plan through `lab.gate.go_real()`, placed by the owner.
  - It requires first that the owner confirms access to Kraken EEA derivatives and to Aster, the contracts their
    account can trade, leverage and margin.
  - Nothing here moves money.

## Reported, not decided on
- fund_book, the funding net of measured costs;
- the flat-cost lines (1x, 2x, 3x) and close accounting;
- measured costs by venue and coin;
- the running e-value;
- the share of pairs by venue pair;
- forced exits and delistings;
- late days.

## Multiplicity
- **Trials:** 1. Program trials before this lane: 9,785,752; after it: 9,785,753.
- **Overlap.** R509 and R510 read a book that overlaps this one: the same Kraken coins against Hyperliquid. Their
  decisions are counted separately. A small stake would follow whichever passes first, sized to the smaller capacity.

## Not checked before the freeze
- **Access.** Aster from France beyond its terms. It is authorised nowhere, like Hyperliquid.
- **Margin.** Margin on three venues.
- **Delistings.** Thin perps delisted by Kraken or Aster, which force exits.
- **The monitor under strong positive autocorrelation.** The simulated size was 4.2% at AR(1) +0.2. A persistent
  regime, such as funding that drifts for months, can push it higher.

## Code
| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d | fixed; the tick refuses if it changes |
| `experiments/xfund_kaster_v1/symbols.csv` | c0d111aff76f6591f1e20af728a64347bb8e0e0adf75e3abce15ac198c6f10c7 | fixed; checked the same way |
| `lab/anytime.py` | 07e1a06eba8aee6518e25b9bff384fcade2686cc75ae75e65ea5fbc6bdfb79a2 | fixed; the decision rule |
| `scripts/read_xfund_eea3_fwd.py` | e20f356fc55980e4ff2a0c7fb02f846b9ce6f7151b2951478dad169e4b38ae3d | fixed; the decided series |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 | fixed |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 | pinned by other lanes; not edited |
| `lab/kraken.py` | 92ecfe0cfa2dae1f3ceef23f177fa84ad19f283d07036b2c1383566e022d0707 | data plumbing only |
| `lab/aster.py` | f338c3fc611fbadd40e9e508a07008652878376ebd802a5f1b49b221e866acea | data plumbing only |
| `scripts/forward_xfund_eea3.py` | 657857342e929263b7e975142a838ce5fd31c5905e27466f28628710ad9bfeb1 | data plumbing only |
| `scripts/forward_xfund_eea.py` | 5ea7908b79bcfc39bfa863fab8d35fc9d61794e2f2f988e2b192ff9d46863f3a | R509's; its recorder |
| `tests/test_anytime.py` | 7e328e92d68f9f5ab904db8d226d2f6b4076d93073f5ee74a9644d1641609ab3 | tests |
| `tests/test_forward_xfund_eea3.py` | 2484a1de952ae8b897fd4b547caa88541fc157a1672e7e77e79ca696086356e0 | tests |

**Dry run (2026-11-19, scratch folder, not this journal).** One tick from the public APIs with no archive: 132 Kraken,
101 Hyperliquid and 132 Aster files, 0 failures. Live books walked at 7-24 bp a side for $1,000.
