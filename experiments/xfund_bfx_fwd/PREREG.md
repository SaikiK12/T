# PREREG: xfund_bfx_fwd (R524). R507's carry book on Binance + Bitfinex, forward on paper

Freeze with `lab.prereg.freeze()` before the lane's first tick. Never edited afterwards.

- **Registry id:** R524
- **Owner (single writer):** the Claude session that froze it. The carry workflow's tick
  (`scripts/forward_xfund_bfx.py`) is the only writer of `experiments/xfund_bfx_fwd/journal/` and
  `data/xfund_bfx_fwd/`.
- **Date registered (UTC):** 2026-11-23

**Methods:** M552 (forward). Carry, candidate C13.
- **Paper only:** nothing here can place an order.

## Why
- **The owner, 2026-11-23:** frameworks above strategies.
- **R507 has the longest evidence of the four design-gap pairs.** +5.21%/yr at 1x over 2,078 days, NW t 11.94; 2025-26
  about +3.1%/yr.
- **It diversifies the others.** In sample its daily net correlated −0.02 to +0.15 with Kraken+Hyperliquid,
  Kraken+Aster and Deribit+Hyperliquid (`docs/reviews/framework_20261123.md`).
- **It is the one pair without a forward lane.** Alone it is near cash. In the portfolio it adds breadth.

## Rule
- **The book:** R275's unchanged (`lab.xfund` through `lab.carrylane`):
  - binance+bitfinex, lookback 14 days, entry 5%/yr, exit below half, 20 slots;
  - correlation guard 30 days >= 0.9 on 20 observations.
- **Symbols:** R507's 69-coin table (`symbols.csv`, copied from `experiments/xfund_bfx_v1/results/symbols.csv`).
- **Venues:**
  - Binance through `lab.carrylane`, as R278 uses it on GitHub;
  - Bitfinex through the new `lab/bitfinex.py`, which uses R507's frozen client (`scripts/fetch_bitfinex_history.py`:
    status-history funding per 8 h period, hourly candles closing at 00:00 UTC).
- **Clock:** warm-up from 2026-10-01; scored from 2026-11-25; ticked by `claude-carry-paper.yml` with its own cache.
- **Costs:** R509's book walks ($1,000 / $2,500) at each on-time ticket. The read adds taker fees of Binance 5 bp
  and Bitfinex 6.5 bp; a leg with no record costs 21 bp.

## Decision (`scripts/read_xfund_bfx_fwd.py`)
- **Series:** R512's net_book and fund_book (funding net of measured costs) per scored day.
- **Looks at 90 and 180 scored days:**
  - PASS if NW t (lag 5) of fund_book ≥ 2.5 and the cumulative net_book > 0;
  - FAIL if the mean fund_book ≤ 0, or if the cumulative net_book falls below −3%;
  - otherwise CONTINUE after look 1, and FAIL at look 2.
- **Power and size** (`CLAUDE.md` step 4), on R507's 2025-26 days with sliding windows: power 0.77 at 90 days and
  1.0 at 180; size 0.0 on the demeaned series.
  - Rejected first: R520's net-based looks had power of only about 0.5 by 180 days at this level, and a 30/45-day
    fast read had size 0.07-0.09.
- **Portfolio role.** Its days can join a later combined read (as R523 does for R509 and R520), under a new id.

## What the author has seen
- R507's full history (2021-01..2026-09).
- A dry run of this lane's code on 3 coins (BTC, DOGE, ETH) in a scratch folder on 2026-11-23. It printed only row
  counts.
- **Nothing from 2026-11-25 on.**

## Trials
- **This round:** 1.
- **Program trials:** 9,785,771 before, 9,785,772 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/forward_xfund_bfx.py` | 91cdd35f990c99752fe843d1b784af6f8847141c09344191cafa3b8261a03bb3 |
| `scripts/read_xfund_bfx_fwd.py` | bcecaf8616a91207e94ad932f03f28c3eee4a9d083973454a7ccdc7602e9004b |
| `tests/test_forward_xfund_bfx.py` | 04f26bbf27b4ada10ee10a2b67fdc4706bf11949856b52acdbca1e179b1309b9 |
| `lab/bitfinex.py` | e30e18ae521b5f1719a7aa99b7607a11f76cb07c4a0c8b4b0dee187fde98883e |
| `scripts/fetch_bitfinex_history.py` | 424442fdec25bb5ed9112bc5333baa348499d7c9b029067202f2e0b4b4907baf |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `scripts/forward_xfund_eea.py` | 5ea7908b79bcfc39bfa863fab8d35fc9d61794e2f2f988e2b192ff9d46863f3a |
| `scripts/read_xfund_dhl_fwd.py` | 71b0dd622e1a5ddfc0c5c410358ff8f7786c1900b75dad1b11845e771c429735 |
| `scripts/read_xfund_eea3_fwd.py` | e20f356fc55980e4ff2a0c7fb02f846b9ce6f7151b2951478dad169e4b38ae3d |
| `experiments/xfund_bfx_fwd/symbols.csv` | 524e01b9ea14c118094a4826c15c2d7fc514e067890d7b183f6130c8656ee66a |
