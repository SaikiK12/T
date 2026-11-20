# PREREG: passive_kraken_v1 (R513). What a passive entry costs on Kraken's perps against a taker entry, at the carry book's decision time

Freeze with `lab.prereg.freeze()` before any intraday Kraken candle in the window is fetched. Never edited afterwards.

- **Registry id:** R513
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_passive_kraken.py` is the only writer of `experiments/passive_kraken_v1/results/` and
    `data/kraken_passive/`.
- **Date registered (UTC):** 2026-11-20

**Methods:** M555 (new: passive entries on thin perps for the carry book). Execution, for candidate C13.
- **Gate 0, cost measurement.** No return is tested.
- **Paper only:** public endpoints, no key; nothing can place an order.

## Why
- **The owner, 2026-11-19 and 2026-11-20:** "go, do everything" after the library digest.
  - The digest ranked passive entries first, as the largest lever on the carry books' cost.
  - Microstructure sources: Said et al. on passive impact; Huang-Lehalle-Rosenbaum on queue-reactive fills.
- **The cost problem.**
  - R508-R512's books pay a taker walk on every leg.
  - On Kraken's thin coins, the session's book snapshots (2026-11-18/19) put the median half-spread at 9.6 bp and the
    $1,000 walk at 14.4 bp a side, before the 5 bp taker fee.
  - Measured costs were about 2-3x R508's 7 bp a leg.
- **The opportunity.** The carry book holds a pair for weeks, so it can rest an order and wait.

## Question
For Kraken perps trading under $100k a day, does a resting order at the carry book's decision time cost less than a
taker order, net of the fill risk and of the drift that keeps it from filling?

## Universe and data
- **Coins.** The Kraken contracts of R511's frozen table (132 coins) that have a book snapshot and a volume figure.
  - Decided on the thin coins: median daily volume on Kraken under $100k over 2025-11..2026-11 (68 coins, from
    R508's and R511's frozen diagnostics).
- **Data, fetched after this freeze** by `run_passive_kraken.py fetch`, for 2026-08-17..2026-11-17 (exclusive end),
  from Kraken's public charts API:
  - 5-minute trade candles (`/api/charts/v1/trade/<symbol>/5m`; a candle with volume 0 has no trade);
  - 1-hour mark candles (`/api/charts/v1/mark/<symbol>/1h`).
  - One receipt per symbol with both files' sha256. `run` refuses any mismatch.
- **Fixed inputs.** The spread and walk of each coin are taken from the session's book snapshots, frozen below. They
  are held constant over the window.

## Rule (`scripts/run_passive_kraken.py`)
For each coin, each decision day D in 2026-08-17..2026-11-15 and each side (buy, sell):
- **The decision.** t = D 00:00 UTC, the carry book's decision time. mid_t is Kraken's mark at t (the 1 h mark
  candle opening at t). hs is half the coin's quoted spread in its snapshot.
- **Taker now:** the $1,000 walk (`cost_1000_bp`) plus the 5 bp taker fee.
- **The passive order:** a limit at mid_t × (1 − hs) to buy, mid_t × (1 + hs) to sell, resting from t.
  - **Conservative fill** (decided): a 5-minute trade candle with volume > 0, closing in (t, t + H], trades strictly
    through the limit: low < limit to buy, high > limit to sell.
    - A print through the level means the level was cleared, so the order filled in full at its limit.
    - Cost: −hs + the 2 bp maker fee.
  - **Not filled by t + H:** a taker order at t + H. Cost: side × (mid_{t+H} / mid_t − 1) + `cost_1000_bp` + 5 bp.
    This charges the drift that kept the order from filling.
  - **Optimistic fill (reported):** touching the limit counts.
- **saving** = taker cost now − passive cost, in bp of notional per leg-side.
- **Horizons:** H = 1, 6 and 24 hours. **Decided: H = 6 h.**
- **Fees:** Kraken Pro futures tier 1 (July 2026 table, via search; the live schedule was not opened): maker 0.02%,
  taker 0.05%.

## Decision (one candidate, alpha 0.05)
- **The series.** Each day's mean saving across the thin coins and both sides, at H = 6 h, conservative fill.
- **UNREADABLE:** fewer than 30 days.
- **PASS:** the mean is above 0 and its Newey-West t (lag 5) is at least 2.0.
- **FAIL:** anything else.

**Reported, not decided:**
- by liquidity bucket and horizon: fill rates (conservative and optimistic), passive and taker cost, saving;
- the thin coins at H = 1 h and 24 h;
- the optimistic rule.

## What a PASS earns
- **A forward check.** A paper lane (a new id) that charges the carry book's Kraken legs the passive-then-taker cost,
  from live books and trades.
- **Better capacity estimates** for R509-R512's coins.
- **No money.**

## What the author has seen
- The session's book snapshots of 2026-11-18/19 (spreads and walks, used as fixed inputs) and Kraken's daily candles
  and funding for R508 and R511.
- Probes on 2026-11-20 of PF_NEIROUSD 1-minute trade and mark candles: 60 candles at each of four depths, and 2,000
  candles over 10 days to check paging.
- Order-event and execution page counts for five thin coins (density only).
- No 5-minute candle in the window was summarised.

## Not checked before the freeze
- **The spread changes** over time and with volatility. Held constant here.
- **The mark is not the mid.** On a thin book they can differ by a few bp.
- **Queue and partial fills.** The conservative rule needs a print through the level, so a fill is certain. The
  optimistic rule ignores queue position.
- **Order size.** A $1,000 resting order can be larger than the displayed size at the level on the thinnest coins.
- **The other venue.** Hyperliquid and Aster are not modelled; their books are deeper (6-11 bp a side at $1,000).

## Trials
- **This round:** 1.
- **Program trials** before it: 9,785,753 (`registry.program_trials`); after it: 9,785,754.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_passive_kraken.py` | b86298ff0b2fc4623113f341d6dd6c10ea3236b853a2a4bc69a8c341a595f0b3 |
| `tests/test_passive_kraken.py` | 436699459a3e0ceff07ea5d9acd0073f3879d6003da78b369c6cdf0787a5de4a |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `experiments/xfund_kaster_v1/symbols.csv` | c0d111aff76f6591f1e20af728a64347bb8e0e0adf75e3abce15ac198c6f10c7 |
| `experiments/xfund_eea_v1/diagnostics/books_20261118.json` | 720e0c1597a6369848a80a771719cf534caecd5a77bb4d15d4a9a701990e9ec1 |
| `experiments/xfund_kaster_v1/diagnostics/books_20261119.json` | 705b73f6dd5c7eae19ac7cd8a17303a37b488a2abbe922dd9c3307141f456292 |
| `experiments/xfund_eea_v1/diagnostics/kraken_volume.csv` | e01953b14bb204a73fed2eaaa08a58a33a2d0b711d7200c64b5876fd898da8ae |
| `experiments/xfund_kaster_v1/diagnostics/volume.csv` | c904750bb1b09a7c38309f6481a8eb294a42f0c4ccb0717c399974a5a57f60a1 |
