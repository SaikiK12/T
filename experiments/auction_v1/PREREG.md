# PREREG: auction_v1 (R290). Auction-market levels on 1-minute bars, from real session anchors and placebo clocks (M305)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R290 (Claude block R280-R299, claimed on issue #7 before the freeze). **Method:** M305.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_auction.py` (tested on planted setups in `tests/test_run_auction.py`). It calls `verify()`
  on this file first and checks every input's sha256 against the block below.
- **Source:** the owner's term list of 2026-10-21 (TPO, VWAP and SD bands, POC, VAL, VAH, initial balance, HVN/LVN,
  volume profile), `docs/AUCTION_AND_FLOW.md` section 3, point 1.
- **The question:** crypto trades around the clock, so every session level depends on a chosen anchor. If real
  anchors behave no differently from arbitrary clocks, the levels carry no session information in crypto. If they
  differ, something about real sessions is worth a forward test.
- **Gate:** 0. Every year read here was read by earlier lanes at hourly resolution, and R289 read these 1-minute files
  at two fixed clocks.
- **Execution mode:** API. Triggers fire at any minute, so a hand-placed order cannot follow them. The intended venue
  is Lighter (0 fee through the API, `docs/VENUE_STRUCTURE.md`).

## What the author has seen
- **The 1-minute files** (R289's PREREG):
  - row counts, first and last bars, and gaps;
  - R289's results at two clocks: the US-open flush and the Deribit Friday settlement window. Both are NULL; the
    Friday fade kept about +20 bp gross per trade.
- **Lighter's recorded cost** for BTC, ETH and SOL (5 hourly snapshots on 2026-10-21): at most 0.72 bp per side for a
  $10k market order, half-spread 0.07-0.28 bp, 0 fee.
- **The runner on synthetic data:**
  - planted setups (tests);
  - a random walk, for timing and trigger counts only.
- **Not computed:** no statistic of any auction level, rule or anchor on real data.
- **Earlier related lanes:**
  - R263: VWAP and Bollinger rules on 1 h to 1 d bars, NULL;
  - R246: the 8 AM New York range on hourly bars, NULL;
  - R203: the first UTC hour predicting the last, NULL.

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
966602440c3573e677b7578feed150b5065d2062d84869acd54e79ad58af1706  data/klines_1m/SOLUSDT.parquet
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
e110881032024bc2f52a14511c0d3a70a0a444db5b6f4499e31418e7e93c967e  data/fundingRate/SOLUSDT.parquet
a46446f7169b7fded8ec95f991ec779676f1404aff8b4f7ee5bb309497019114  lab/auction.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
da2d2355838fb8019a83c01c3ae5286d2188fe206a3325d1201b5c7be8448536  scripts/run_auction.py
```

## Data
- **Coins:** BTCUSDT, ETHUSDT and SOLUSDT, Binance USD-M perpetuals.
- **Bars:** open times from 2021-01-01 00:00 UTC to 2026-09-30 23:59 UTC. Earlier rows are dropped on load, because
  2020 is reserved.
  - A bar is valid when count > 0 and close > 0. Invalid or missing bars are NaN and carry no weight.
- **Price at an instant τ:** P(τ) is the close of the bar that opens at τ − 1 minute. It is undefined when that bar
  is missing.
- **Funding:** as in R289. A position with entry < F ≤ exit pays side × rate.

## Anchors
A session runs from the anchor on one calendar day to the anchor on the next. Every anchor applies on every calendar
day, weekends included.

- **Real (3):**
  - U00: 00:00 UTC;
  - NY: 09:30 America/New_York, which follows daylight saving;
  - LDN: 08:00 Europe/London, which follows daylight saving.
- **Placebo (8):** UTC clocks drawn with `numpy.random.default_rng(290)` before any statistic.
  - Excluded: anything within 60 minutes of 00:00, 07:00, 08:00, 13:30, 14:30 or 16:00 UTC (the real anchors in
    both daylight-saving states, and the funding hours).
  - Four are random minutes at least 90 minutes apart: 02:25, 04:47, 09:25 and 11:04.
  - Four are random whole hours: 06:00, 17:00, 19:00 and 23:00.

## Levels (lab/auction.py)
- **Prior session's volume profile:** the bars of session d − 1, with tick = 5 bp of that session's last valid
  close. Each bar's volume is spread evenly over the bins from its low to its high. The prior session needs at least
  1,200 valid bars, or there are no prior levels that session.
- **POC, VAL and VAH:** `value_area` at 70%. The value area runs from VAL to VAH + tick.
- **Session VWAP and bands:** `vwap_bands` of the typical price, cumulative from the anchor, with ±2 SD.

## Rules
Each rule fires at most once per coin and session, at a decision time τ, with a textbook side.

| Rule | Fires when | Decision τ | Textbook side |
|---|---|---|---|
| **VA80** (Dalton's 80% rule) | P(A) is outside the prior value area, and later two consecutive half-hour marks A + 30p and A + 30(p+1), p = 1..11, both have P inside it | A + 30(p+1) | toward the far edge: long if P(A) was below value, short if above |
| **IB60** (initial balance break) | the first 1-minute close beyond the high or low of the bars in [A, A+60), within the first 480 minutes; at least 48 valid bars in the IB | that bar's close | follow the break |
| **OR15** (opening range break) | the same with the first 15 minutes, at least 12 valid bars | that bar's close | follow the break |
| **VWAP2** | the first 1-minute close above the session VWAP + 2 SD or below VWAP − 2 SD, from minute 60 to minute 1,200 (bands through that bar) | that bar's close | fade, toward VWAP |
| **NPOC** (naked prior POC) | no bar in [A, A+60) traded in the prior POC bin | A + 60 | toward the prior POC (long if P(A + 60) is below the bin's middle) |

- **Sides:** "book" is the textbook side, and "anti" is its opposite.
- **Entry and exit:** entry at E = P(τ + 1 min), exit at X = P(τ + 1 min + h).
- **Holds:** h ∈ {60, 240} minutes.
- **Missing prices:** a trade is skipped when E or X is undefined.

**Variants:** 3 real anchors × 5 rules × 2 sides × 2 holds = **60 trials**. The 8 placebo anchors run the same 20
rule variants each (160). They are the null for the anchor test, not candidates.

**Book:** each coin is one third of capital, as in R289.
- A trade returns s × (X / E − 1) − 2c − funding.
- A day's net is the sum of that day's trades (by entry day, UTC) divided by 3.
- Every calendar day is in the series. Days with no trade are 0.

**Cost** c per side, API:
- 1x is 2 bp. That is Lighter's 0 fee plus its measured cost (at most 0.72 bp at $10k on these three), with a margin
  for its 300 ms taker delay.
- 2x is 4 bp, and 3x is 6 bp.
- Reported, not decided on: MEXC's API cost of 8.5 bp per side.

## Windows
- **Discovery:** 2021-04-01 .. 2023-12-31.
- **Validation:** 2024-01-01 .. 2026-09-30, with halves 2024-01-01 .. 2025-06-30 and 2025-07-01 .. 2026-09-30. Gate 0.

## Tests
**1. Anchor test (the mechanism question).**
- For each rule and hold (10 combos) and each of the 11 anchors, take the absolute Newey-West t (lag 10) of the
  textbook side's daily gross series over discovery. This is direction-free: it asks how much structure there is,
  not which way.
- Within each combo, rank the 11 anchors, 1 being the smallest |t| (ties averaged). S(set) is the sum of a set's
  ranks over the 10 combos.
- p is the share of all 165 three-anchor sets whose S is at least the real set's. This is an exact permutation test,
  and it keeps the dependence between combos.
- **ANCHOR EFFECT** if p < 0.05.

**2. Trading test.**
- A White reality check, studentized as in R289: over the 60 real variants' discovery daily net at 1x, with a
  stationary bootstrap (block 10, B = 2,000), seed 290. The result is rc_p.
- j* is the largest studentized discovery mean.
- **PASS** if all of these hold:
  - rc_p < 0.05;
  - j*'s validation Newey-West t (lag 10) at 1x is ≥ 2.0;
  - j*'s validation mean at 2x is > 0;
  - j*'s mean at 1x is > 0 in both validation halves.

**Verdict:**
- **PARTIAL** if the trading test passes. j* then goes to the reserved 2020 bars in a later batch (BTC and ETH from
  2020-01, SOL from 2020-09) and earns a forward paper lane with a new id, labelled API on Lighter.
- **NULL** otherwise.
- The anchor-test result is reported with the verdict either way. It is a finding about crypto sessions, and decides
  whether session levels stay in the queue.

**Power:** validation has 1,004 days. A t of 2 needs an annual Sharpe of about 1.7 on the daily series at 80% power.
IB60, OR15 and VWAP2 trade nearly every session, so their power is the highest of the family.

## Reported (not decided on)
- **Per variant (placebos included) and window:**
  - trades, hit rate, mean gross per trade in bp, and the gross t;
  - net per day at 1x/2x/3x and at the MEXC API cost;
  - Newey-West t at 1x, annual Sharpe at 1x;
  - break-even cost per side.
- **For j*:** net at 1x per year and per coin, and the five best days' share.
- **The anchor test's ranks per combo,** and the mean rank of each real anchor.
- **Read against** `registry.program_trials()`.

## Outputs
`experiments/auction_v1/results/`:
- `variants.csv`;
- `daily.csv.gz` (real variants, net at 1x);
- `trades.csv.gz` (real variants);
- `summary.json`.

FINDINGS.md is written after the run.

## Known limits (written before the result)
- **Prices are Binance's, and funding is Binance's.** Lighter's prices track within a few bp. Its funding history is
  being fetched for R288, not used here.
- **Fills** are the 1-minute close one minute after the decision. The 300 ms taker delay and queue position are not
  modelled beyond the 2 bp cost.
- **Every rule is one reading of a discretionary idea.** One tick size, one acceptance rule for VA80, and a 60-minute
  IB are fixed here; other readings are not tested.
- **Real anchors apply on weekends too,** where New York and London are closed. A weekday-only reading is not in the
  test.
- **The placebo set is 8 clocks**, so the smallest attainable p is 1/165 and the test has modest power. A real but
  small anchor effect can be missed.
