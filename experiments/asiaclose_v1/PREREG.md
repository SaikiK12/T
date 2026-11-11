# PREREG: asiaclose_v1 (R468). Do Asian single-stock perps overshoot the daily closure of their home exchange?

- **Registry id:** R468
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

Method M526 (new). Parents: M515 (US-stock perps over the weekend; R462 gate-0 PASS on trade.xyz, R465 PARTIAL on
Lighter), R464 (NULL on xyz's indices, commodities and FX). This file is frozen by `lab.prereg.freeze()` before any
price of these markets is fetched for this question. After the freeze it is never edited; a changed idea is a new lane.

## Question
trade.xyz and Lighter list perps on Korean, Japanese, Hong Kong and Shanghai stocks (Samsung, SK hynix, Hyundai,
SoftBank, Kioxia, MiniMax, Zhipu, Tencent, Xiaomi, SMIC, GigaDevice, Cambricon). The perps trade every hour; the home
exchange is shut about 17 hours every weekday, and over weekends and holidays. While it is shut, the perp is priced
from its own book.

M515 found that US-stock perps overshoot over the weekend and give part of the move back once external prices return.
Here the same kind of closure happens **every weekday night**, which gives about five times as many events per market.

Unlike a weekend, these nights hold the US session, where related US stocks (Micron, Nvidia, the ADRs) trade. The
perp's night move is therefore partly information. It could overshoot (fade it) or under-react (follow it). **The test
is two-sided:** sample A's sign picks the side and sample B must agree.

## Why this lane
- **The closure is documented [A].** trade.xyz `llms-full.txt` (sha256 `7ac7ef34…`, fetched 2026-11-11, read by the
  author; the same file waves 5 and 7 cite):
  - Korea: external prices 9:01 AM-3:20 PM and 4:05-8:00 PM KST; "Internal Coverage … 8:00 PM - 9:01 AM" on weekdays,
    "Friday 8:00 PM to Monday 9:01 AM" at weekends.
  - Japan: external 8:20 AM-4:30 PM and 5:00-11:59 PM JST; internal "11:59 PM – 8:20 AM JST".
  - Hong Kong: external 9:30 AM-12:00 PM and 1:00-4:00 PM HKT; internal "4:00 PM – 9:30 AM HKT".
  - Shanghai STAR: external 9:30-11:30 AM and 1:00-2:57 PM; internal "2:57 pm – 12:00 am" and "12:00 am – 9:30 am".
- **Lighter [A]** (`llms-full.txt`, sha256 `6f19423588574410…`): "Outside the underlying's trading hours, external
  prices can become stale and pricing switches to the price derived from the order book." Its Korean markets list
  "Pyth Pro, Chainlink, Hyperliquid" as oracles, the Hong Kong ones "pyth pro". No session times are given.
- **Cost:** Lighter charges 0 fee on a Standard account (`orderBookDetails`, 2026-11-11: taker and maker 0.0000 for
  all nine Lighter markets here). xyz runs these markets in growth mode (0.9 bp taker).
- Both venues are reachable from France (`docs/reviews/venue_access_fr_20261110.md`); R457, R459 and R467 already
  trade Lighter on paper.

## What the author has seen
- Both venues' documentation (sections above), market lists, ids, growth mode, fee scales, fees and Lighter listing
  times (`created_at`): Korean markets 2026-04-08, Hong Kong 2026-06-22, Kioxia 2026-08-13.
- The 2026-05-20 Korea Exchange notice of two 2026 closures missing from xyz's table (06-03 local elections, 07-17
  Constitution Day) [S, asiae.co.kr and sedaily.com news pages].
- R451 (`flow_hlstock_v1`) priced xyz SMSN and SKHY hourly inside R200's flow books. No closure, overnight or open
  statistic of any of these markets was computed there.
- **No price, move or return of these markets has been computed for this question.** The runner was run only on
  synthetic worlds (`tests/test_asiaclose.py`).

## Universe (`experiments/asiaclose_v1/universe.csv`, frozen)
- **Built by** `python scripts/fetch_asiaclose.py universe` on 2026-11-11: 18 markets.
  - **xyz (9):** SKHX, SMSN, HYUNDAI (KRX); SOFTBANK, KIOXIA (TSE); MINIMAX, ZHIPU (HKEX); GIGADEV, CAMBRICON (SSE).
  - **Lighter (9):** SKHYNIXUSD, SAMSUNGUSD, HYUNDAIUSD (KRX); KIOXIA (TSE); MINIMAX, ZHIPU, TENCENT, XIAOMI, SMIC
    (HKEX).
- **Left out:**
  - xyz SKHY (a second SK hynix market) and Lighter SKHY (the US ADR);
  - indices (KR200, JP225 and NIFTY have external futures quotes overnight);
  - pre-IPO perps;
  - RELIANCE (listed 2026-10-26).
- **SMIC's exchange is assumed.** Lighter does not say which listing SMIC tracks; HKEX (0981) is assumed. Shanghai's
  hours would give the same instants.
- **Survivorship:** markets delisted before 2026-11-11 are absent.

## Instants (`scripts/asiaclose_rule.py`, UTC; no exchange here uses daylight saving time)
- **D and P.** D is a local trading day; P is the local trading day before it.
- **Holidays:** xyz's 2026 holiday table, plus KRX 06-03 and 07-17. A half day (HKEX) never serves as P.

| exchange | R (on P) | E | X1 (on D) | X2 (on D) |
|---|---|---|---|---|
| KRX, TSE | 06:00 (15:00 local) | 23:00 the day before D (08:00 local) | 01:00 (10:00) | 06:00 (15:00) |
| HKEX | 07:00 (15:00) | 01:00 on D (09:00) | 03:00 (11:00) | 07:00 (15:00) |
| SSE | 06:00 (14:00) | 01:00 on D (09:00) | 03:00 (11:00) | 06:00 (14:00) |

- **R** is inside P's main session, so the last external price comes at or after R.
- **E** is before D's session and before xyz's external pre-open coverage (KRX 08:00-08:50 before an undated change;
  TSE from 08:20).
- **kind:** `night` when P is the calendar day before D; `gap` otherwise (a weekend or a holiday in between).
- **Prices.** P(T) is R462's `price_at`: the close of the last traded hourly candle that opens in [T - 3 h, T - 1 h].
  Only candles with volume > 0 count, on both venues.
- **Moves and returns:**
  - W = 1e4 ln(P(E) / P(R));
  - s = -sign(W) (the fade side);
  - c_k = s · 1e4 ln(P(X_k) / P(E));
  - f_k = funding the fade receives in (E, X_k];
  - g_k = c_k + f_k.
- **Corporate action:** Kioxia's 3-for-1 split (xyz settled and reopened KIOXIA at about 06:35 UTC on 2026-09-28).
  Openings with D on 2026-09-28 or 09-29 are dropped for Kioxia on both venues.

## Samples and data
- **A, decides:** D in 2026-04-27 .. 2026-08-31.
- **B, confirms:** D in 2026-09-01 .. 2026-11-10.
- **Bars:** each venue's 1 h candles and hourly funding over 2026-04-01 .. 2026-11-11 00:00 UTC.
  - They are fetched **after this freeze** by the frozen `scripts/fetch_asiaclose.py bars` into `data/asiaclose`,
    with a per-file sha256 manifest and a provenance record.
  - Hyperliquid serves only the latest 5,000 candles, so xyz history starts about 2026-04-17.
- **Eligibility:** the market's first candle is at least 7 days before R, and P(R) and P(E) exist.

## Cells
- **Grid:** venue {both, xyz, lighter} × kind {night, gap} × θ {0, 50, 100, 200} bp on |W| × exit {X1, X2}: 48 cells.
- **Diagnostics:** the decision configuration split by exchange (KRX, TSE, HKEX, SSE): 4 cells.
- **Each cell is read in A and B.**
- **Test:** two-sided sign flip with signs flipped together within each D (all markets and venues that day share
  news), 200,000 draws, seed 468 (`earnperp_rule.cluster_flip_p`).
- **Decision cell:** both venues, `night`, θ = 50 bp, X1.
- **The side is not fixed in advance.** A positive mean means fade, a negative one means follow.

## Trials
- 48 + 4 = **52** cells; registry trials 52.
- Program trials: 9,785,185 before this lane, 9,785,237 after.

## Decision
- **INCONCLUSIVE:** A has fewer than 150 events or fewer than 40 days.
- **PASS:** all of these.
  - A: p ≤ 0.05 and |mean| > 2 cost units.
  - B: at least 50 events over at least 15 days, the same sign as A, and |mean| > 1 unit.
- **PARTIAL:** A has p ≤ 0.05 and |mean| > 1 unit; B has its sizes and the same sign.
- **NULL:** otherwise.
- Read against 9.8 million program trials, any hit is weak. A PASS or PARTIAL earns a forward paper lane under a new
  id, with tickets at E and recorded book costs. It never earns a trade.

## Costs (1x, 2x, 3x)
- **One cost unit is a round trip:**
  - xyz: 2 × 0.9 bp growth-mode taker + 4 bp slippage = 5.8 bp;
  - Lighter: 0 fee + 4 bp = 4 bp.
  - A cell's unit is the mean over its events.
- These Asian books were not measured; their real cost may be higher. The 1x, 2x and 3x nets subtract 1, 2 and 3
  units from |mean|.
- Funding is charged inside g.

## Power (stated before the run)
- MDE80 = 2.8 sd / sqrt(n) is reported for every cell; the day-cluster test is wider.
- **Expected size of A:**
  - about 85 opening days;
  - about 6 Korean markets on most of them, 2-3 Japanese ones, and Hong Kong from late May or June;
  - roughly 400-700 night events at θ 50.
- **Detectable edge:** about 35 bp, assuming a day-level sd of the event-mean of 120 bp (2.8 × 120 / sqrt 85).
  - That compares with a 2x cost near 10 bp.
  - M515's weekend effect (+42 bp on xyz, +45 bp on Lighter) would be seen at this size. An effect a third as large
    would likely be missed.
- **Same stock on both venues.** The two venues' copies of a stock are nearly the same event. The day clusters absorb
  that dependence; the per-event n overstates the information.

## Code
```inputs
82bf82a7639f5dbcc2b1a4242dacf5f30d9e0e26e9c278488d8160d6b4a3afc3  experiments/asiaclose_v1/universe.csv
f45911db2ea7cedbdf9b751de5177cdaa8f4f6395e2eca43fc253c6049727672  scripts/asiaclose_rule.py
b09e903c2cfb19603dd1fc80cf29dd8a58e27b8f53881497c6f831417bbfb96c  scripts/fetch_asiaclose.py
9579b3225edb8fdfceb7c765dc6cdaf64cd892d0c192c2e0bf9514dc0cfe35fd  scripts/run_asiaclose.py
38dc4afd5543143b3cda0b9767b89e8f6e9b4a5c31c2d75bece8b5234617f7aa  tests/test_asiaclose.py
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a  scripts/xyzwknd_rule.py
6a9c4286ac1a12a391c0ebaca022510fb40d59affff9eb56ce71d44246a64ca1  scripts/earnperp_rule.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
```
The runner also re-hashes every bar and funding file against `data/asiaclose/manifest.json`.

## Feature lineage and point-in-time availability
- **W and s.** Source: traded candle closes before R and E. Available at E. Missing data: the event is dropped and
  counted.
- **Holidays.** Source: xyz's 2026 table plus the KRX notice. Published before the days used.
- **Fees.** Source: venue data on 2026-11-11. Not point-in-time.
- **c_k and f_k.** Source: candle closes before X_k, and funding in (E, X_k]. Outcome only.

## Evidence lineage and admission
- **Method:** M526, new. **Parents:** M515 (R462, R465), R464.
- **Decision group:** one pre-named cell, so no multiplicity correction within the lane.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: pre-named cell; 52 cells counted; costs at 1x/2x/3x; power stated; a confirmation sample.
  - Not met: gate 1 (forward, on-time, measured costs) and gate 3 (account risk). Exploratory.

## Stop rules
- The lane ends with its first complete run. Nothing is retuned afterwards. A changed idea is a new lane.
- **A PASS or PARTIAL earns** a forward paper lane under a new id, with tickets at E and recorded book costs.
- **A NULL** closes M526 in this form. M515 and its forward lanes (R463, R467) are unaffected.
- No orders, no money, no credentials. The run reads files and writes `experiments/asiaclose_v1/results/`.
