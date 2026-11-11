# PREREG: usdtmint_v1 (R460). After Tether mints USDT, does BTC rise more than at random times, net of costs?

- **Registry id:** R460
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

Method M512, from idea wave 4 (2026-11-11). The owner asked for wide batched web research for new ideas; this one
came from the on-chain lens. Frozen by `lab.prereg.freeze()` before any price, return or test of the bars is computed
around a mint. After the freeze this file is never edited; a changed idea is a new lane.

## Question
For every Tether USDT mint of at least 100 million USDT on Tron or Ethereum from 2021-01-02 to 2026-09-28 (an `Issue`
event of the token contract, timed by its block), does a long BTC position held 24 hours (or 4 hours) from two minutes
after the block earn more than the same holding started at random times? Does it earn more than a Hyperliquid taker
round trip plus funding?

## Why this lane
- A common crypto claim is that "Tether prints" are followed by BTC rises. Griffin and Shams (Journal of Finance, 2020,
  "Is Bitcoin Really Untethered?") reported that Tether flows on 2017-2018 data followed BTC declines and were followed
  by rises. **That paper was not read for this lane.** The claim reached the lab through a helper's search summary,
  which said the effect was reported for 2014-2021. It is a reported claim, which is why this lane tests it.
- A mint is public on the chain within seconds. Free APIs give every one without a key: TronGrid for Tron and
  Blockscout for Ethereum. The test needs no purchase. BTC trades on Hyperliquid, which can be reached from France,
  at a 4.5 bp tier-0 taker fee.
- No lane in the lab has used stablecoin issuance (`registry/methods.csv` and `registry/rounds.csv` have no
  "tether", "mint" or "stablecoin issuance" row before this one). BTC's price has been read by many lanes in every
  split (for example R229, R242 and R263), so the only new thing here is the event timing.
- A NULL is the likely result and will be recorded as one.

## What the author has seen
- **Events.** `scripts/fetch_usdt_mints.py` wrote 262 Issue events: 136 on Tron and 126 on Ethereum, from
  2021-01-01 11:16 UTC to 2026-08-21 14:55 UTC. Six Ethereum events were re-checked on a second provider and matched.
  The author looked at:
  - counts and USDT sums per year and chain (2021: 46 Ethereum / 54 Tron; 2022: 0 / 11; 2023: 14 / 16; 2024: 31 / 16;
    2025: 32 / 26; 2026: 3 / 13);
  - the amount distribution (the median and both quartiles are 1e9; minimum 1 USDT; maximum 2e9; 261 events of at
    least 1e8 and 208 of at least 1e9);
  - the trade counts per cell and split from `--plumbing` (below), which reads no price.
- **Bars and funding.**
  - Bars: only the parquet schema and row counts (`data/klines_1m/manifest.json`: BTCUSDT and ETHUSDT 3,549,600 rows,
    2020-01-01 to 2026-09-30 23:59 UTC).
  - Funding: the column names and, by accident while checking them, the last two BTCUSDT funding rows of the archive
    (2026-09-30: -0.000002 and 0.000066). No other funding value was read.
  - **No price, return, prior-day move or test around any event has been computed or looked at.**
- **Code.** The rule was exercised only on synthetic random walks, with a planted drift and with none
  (`tests/test_usdtmint.py`).

## Data
- `experiments/usdtmint_v1/events.csv`: a byte-identical copy of `data/usdt_mints/events.csv`. It holds chain, block,
  ts_ms (block time, UTC ms), amount_usdt and tx. Sources and the cross-check are in `docs/provenance/usdt_mints.json`
  and `data/usdt_mints/manifest.json`. Mints on other chains (Solana, TON and others) are not in it, and that limit is
  stated. Redemptions (`Redeem`) are not used.
- `data/klines_1m/BTCUSDT.parquet` and `ETHUSDT.parquet`: Binance USD-M one-minute klines (columns `t` and `open`).
  The runner re-hashes each file against `manifest.json` and reads only rows with t >= 2021-01-01 00:00 UTC, through a
  parquet filter. **2020 is a reserved sample** (`docs/GATES.md`) and no 2020 row is read.
- `data/fundingRate/BTCUSDT.parquet` and `ETHUSDT.parquet`: Binance funding settlements (t, rate), re-hashed the same
  way and read from 2021-01-01. They stand in for Hyperliquid's hourly funding, which is not archived for the whole
  window, and that limit is stated.
- Price data are Binance perp opens. The trade venue is Hyperliquid's BTC perp. Basis between the two is not modelled.

## The rule (scripts/usdtmint_rule.py)
All times UTC. A bar is labelled by its open time.
- **Event:** an Issue event with amount_usdt >= 1e8.
- **Entry instant:** E = block time + 120 s, rounded up to the next minute. The entry price is the open of the first
  bar in [E, E + 5 min).
- **Exit instant:** X = E + H. The exit price is the open of the first bar in [X, X + 5 min). If either price is
  missing, the trade is dropped and counted.
- **Return:** r = 1e4 ln(exit / entry), in bp, long.
- **Funding:** f = 1e4 times the sum of the funding rates settled in (E, X]. A long pays a positive rate.
- **Net at k x cost:** r - k * 10 bp - f.
- **No overlap:** events are taken in time order, and an event whose entry falls before the previous taken trade's
  exit is skipped.
- **Circle:** entries are kept in [2021-01-02 00:00, 2026-09-30 00:00 - H).
- **Horizons:** H in {1, 4, 24} hours.
- **Subsets:** `all` (>= 1e8), `big` (>= 1e9), `tron`, `ethereum`, and `down` (the traded asset's own return over the 24
  hours before E is below 0; that window uses 2021 bars only).
- **Assets:** BTCUSDT (decides) and ETHUSDT (reported).
- **Test:** a one-sided circular-shift placebo, 2,000 draws, seed 460. Every trade's entry is moved by the same random
  offset around the circle, between 7 days and the circle's length minus 7 days, keeping the minute grid. The placebo
  is the mean H-return at the moved entries.
  - p = (1 + number of placebo means >= the observed mean) / 2,001.
  - The shift keeps the events' clustering and spacing, and compares them with the same period's drift.
- **Excess:**
  - Pooled: the observed mean minus the mean of the placebo means.
  - Per split: the split's trade mean minus the mean H-return over every hourly start of that split.
  - Splits are from `lab/config.py`: disc before 2024-01-01; val 2024-01-01 .. 2025-06-30; hold from 2025-07-01.
- **Decision cells:**
  - D1: BTCUSDT, `all`, H = 24 h.
  - D2: BTCUSDT, `all`, H = 4 h.
  - Holm adjustment over these two p values.

## Trades per cell (from `--plumbing`, no price read; `down` depends on prices and is not counted yet)
| subset | H | trades | disc | val | hold |
|---|---|---|---|---|---|
| all | 1 | 229 | 121 | 65 | 43 |
| all | 4 | 223 | 116 | 64 | 43 |
| all | 24 | 201 | 99 | 61 | 41 |
| big | 24 | 173 | 71 | 61 | 41 |
| tron | 24 | 122 | 72 | 34 | 16 |
| ethereum | 24 | 96 | 40 | 31 | 25 |

## Trials
- Cells: 2 assets x 5 subsets x 3 horizons = **30 cells**, of which 2 are decision cells.
- Registry trials: 30.
- Program trials: 9,785,007 before this lane, 9,785,037 after.

## Decision
- **PASS:** a decision cell meets all of these:
  - at least 40 trades;
  - a Holm-adjusted p of at most 0.05;
  - per-split excess above 0 in disc, val and hold;
  - a pooled net mean above 0 at 2x cost (20 bp plus funding).
- **PARTIAL:** the same cell has at least 40 trades, a Holm p of at most 0.05, excess above 0 in at least 2 of the 3
  splits, and a net mean above 0 at 1x.
- **INCONCLUSIVE:** neither decision cell has 40 trades.
- **NULL:** otherwise.
- The best state of the two cells is the lane's verdict. Nothing else is decided on.
- A p of 0.05 is weak against 9.8 million program trials. The FINDINGS read any hit against `program_trials` and
  treat it as a candidate for forward paper, never as proof.

## Costs (1x, 2x, 3x)
- One cost unit is a 10 bp round trip of price: Hyperliquid's tier-0 taker fee of 4.5 bp each way, plus 1 bp for the
  spread and slippage of both fills on BTC (an assumption, not measured for these instants). 1x, 2x and 3x subtract
  10, 20 and 30 bp per trade.
- Funding is charged at Binance's settled rates. Every cell reports nets at 1x, 2x and 3x, and the mean is the
  break-even cost.

## Power (stated before the run)
- MDE80 = 2.8 sd / sqrt(n), reported for every cell.
- If BTC's 24-hour sd is about 330 bp and its 4-hour sd about 130 bp (assumptions, not measurements):
  - D1 (n = 201) detects about 65 bp;
  - D2 (n = 223) detects about 24 bp.
- So the lane screens for a large drift. A NULL whose MDE80 exceeds the 2x cost is recorded as "NULL, underpowered
  for an effect of the cost's size".

## Reported (not decided on)
- Every cell's n, mean, sd, t, hit rate, MDE80, placebo mean, pooled and per-split excess, p, mean funding and 1x/2x/3x
  nets.
- The trade table (`results/trades.csv`).
- These explain a result and open nothing.

## Code
```inputs
5e16ac8d848db8a5d2333212bf5d3ad9bcc91fae14771814aa12807bd6c6094c  experiments/usdtmint_v1/events.csv
b7912c065a59210f3d7423b80449a0c11703c3e13055e25dee12eaf25570f49c  scripts/usdtmint_rule.py
ffc5d5d5d5416a10a34fb6d42282fc8581ec6e1bc3660fd8119b4a26274b3915  scripts/run_usdtmint.py
a6aa35ce137ae155e52a948c641d3f471e5ec76d136e2d99b306ba06e565f76c  scripts/fetch_usdt_mints.py
4cf1c0c00945691e42aff04bcd9a0510d39aa2d97e6bc450587911c072f04043  tests/test_usdtmint.py
32898c4d9960874189e12df8a36c8eeb2949031386c4edfb3948a27b94d2470f  docs/provenance/usdt_mints.json
f4dfccfc5a765543436d020d944601a6c80555a33cd95bcb6662fee8b6cd7adf  data/usdt_mints/manifest.json
f575a7c9632c84df2860c20c2de5d37b52e21a4961b518284c1962a670accae6  data/klines_1m/manifest.json
4599f9d4b7de402778a7f46e90652229206d1c5537a98ea69479893b481c925a  data/fundingRate/manifest.json
8bd9a1236948344161bc651a6c6eb08d0af7b3f3703556a2a7d770b63d152e73  docs/provenance/klines_1m.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
bcfb9b3376e8f7be62940288a8d358f72597a2b95bbde84f76d409b00f4b8e59  lab/config.py
```

## Feature lineage and point-in-time availability
- **Mint event.**
  - Source: the Issue amount and block time, from TronGrid (confirmed events) or Blockscout, in USDT.
  - Window: one block. Available at the block time plus about a minute to confirm.
  - Available by decision time: yes; entry is at +2 minutes or later. Point-in-time chain record.
  - Missing data: none; an event exists or it does not.
- **Prior 24-hour return (subset `down`).**
  - Source: opens of Binance USD-M 1-minute bars (BTCUSDT or ETHUSDT), over [E - 24 h, E).
  - Available by decision time: yes, at E. Point-in-time.
  - Missing data: the event is dropped from `down` if a price is missing.
- **r and f.**
  - Source: Binance 1-minute bars and Binance funding, over (E, E + H].
  - Outcome only, known after X. Point-in-time.
  - Missing data: the trade is dropped and counted.

Single-instrument time-series lane: no cross-section and no universe membership. Every input is point-in-time.

## Evidence lineage and admission
- **Method:** M512. **Parents:** none; no lane has used stablecoin issuance.
- **Decision group:** M512 on BTC. One verdict from the two pre-named cells; everything else is a diagnostic.
- **Samples:**
  - BTC's 2021-2026 bars have been read by earlier lanes for other questions. The mint timing has not.
  - No 2020 row is read.
  - Fresh forward mints after 2026-09-30 (the bars' end) are the natural replication sample.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one verdict from two pre-named cells; multiplicity (Holm over 2; 30 cells counted); cost sensitivity; power
    stated; a placebo that keeps the clustering.
  - Not met: gate 1 (a forward, strict on-time sample) and gate 3 (account risk). This lane is a gate-0 screen, and
    its result stays exploratory.

## Stop rules
- The lane ends with its first complete run. Nothing is retuned afterwards (no other threshold, lag, horizon, subset,
  asset, cost or window); a changed idea is a new lane.
- **A PASS or PARTIAL earns** a forward paper lane under a new id: live mint detection (TronGrid and Blockscout
  polling), BTC on Hyperliquid at measured book cost, its own PREREG, and at least 40 new trades before any verdict.
  It does not earn trading.
- **A NULL earns** M512 closing NULL for BTC on 2021-2026 at this lag. The intraday (1-hour) and ETH cells stay
  diagnostics; they do not reopen it.
- No orders, no money, no credentials. The run reads files and writes `experiments/usdtmint_v1/results/`.
