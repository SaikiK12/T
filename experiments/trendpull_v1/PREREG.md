# PREREG: trendpull_v1 (R284). Visser's trend pullback: buy a rate-of-change reset inside a rising 200-day trend (M277)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R284
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_trendpull.py`. It calls `verify()` on this file first and records every input file's sha256.
- **Source of the claim:** Jordi Visser (former president and CIO of Weiss Multi-Strategy Advisers), TikTok
  2026-10-19, in `docs/VIDEO_DIG.md`. His words: "I only care about them if they're above the 200 day moving average
  and the 200 day moving average is pointed upward. Then what I want to look for is situations where the rate of change
  has reset... close to zero after being higher... I want to be riding a trend that lasts for three months."
- **Gate:** 0. The index years were read by R239 and R247, and the crypto years by many lanes.

## What the author has seen
- **R229** (nine-horizon daily trend, six spot coins): NULL.
- **R242** (vol-managed daily trend, full perp universe): discovery t 2.07, validation t 0.52.
- **R247** (R243's seven chart rules on these 10 indices): NULL.
- **R201 and R204** (1 h dip-in-trend books): NULL.
- None of these used a rising 200-day average together with a 63-day rate-of-change reset, and none held for 3 months.
- No statistic of this rule has been computed.

## Universes
- **IDX:** the 10 world equity indices of R247: ^GSPC, ^NDX, ^DJI, ^RUT, ^GDAXI, ^FTSE, ^N225, ^HSI, ^STOXX50E,
  ^AXJO.
  - Yahoo daily, loaded as in `scripts/run_chartxm.py` `bars()`. Rows with a non-positive open, high, low or close are
    dropped.
  - Bars on or before 2026-09-30.
- **CRYPTO:** every Binance USD-M perp file in `data/klines_1h` (delisted ones included).
  - Rows before 2021-01-01 are dropped on load (2020 is reserved, `docs/GATES.md`).
  - A UTC day is kept if its hourly bars have a total trade count > 0. Its open is the first hour's open and its close
    the last hour's close.
  - Days on or before 2026-09-30.
  - Funding: `data/fundingRate/<SYMBOL>.parquet` from 2021-01-01. A coin without a funding file pays none.

## Rule (per asset, on its own calendar of rows)
**Signal on row D**, known at D's close. All of these must hold:
- **above:** close(D) > SMA200(D), the mean of the 200 closes ending at D;
- **rising:** SMA200(D) > SMA200(D−20);
- **hot:** peak(D) > 0 and peak(D) ≥ q80(D), where:
  - ROC63(t) = close(t) / close(t−63) − 1;
  - peak(D) = the maximum of ROC63 over rows D−63..D−1;
  - q80(D) = the 80th percentile (numpy linear) of ROC63 over rows D−252..D−1;
- **reset:** |ROC63(D)| ≤ k × peak(D).

**Trade:**
- Enter long at the open of row D+1. Exit at the close of row D+H.
- Return = close(D+H) / open(D+1) − 1, minus funding.
- **Funding (CRYPTO):** the sum of rates settled after 00:00 UTC of D+1 and up to 24:00 UTC of D+H. A long pays a
  positive rate.
- **One position per asset:** a signal is acted on only if it comes after the previous trade's exit row.
- **Costs per round trip at 1x:** 2 bp for IDX (R247's 1 bp one-way) and 14 bp for CRYPTO (R275's 7 bp per side).
  Twice and three times that at 2x and 3x.

**Variants:**
- k ∈ {0.25, 0.5};
- H ∈ {63, 21} rows for IDX, and {90, 30} rows for CRYPTO. 90 crypto days span about the same time as 63 trading days.

**Trials:** 2 universes × 2 k × 2 H = **8**.

## Test
For each cell (universe, k, H):
- **Eligible rows:** in each asset, every row D with SMA200(D−20), q80(D) and a full hold to D+H, formed exactly like a
  trade, without the cost. m_a is the mean of those rows' H-returns for asset a.
- **Excess:** a trade's excess is its return minus its asset's m_a. Costs and funding are inside both terms for CRYPTO,
  so the cost is the only thing that differs.
- **The statistic:** the mean excess over all of the cell's trades, with a cluster-robust standard error (CR1) by
  entry calendar quarter. One-sided p from Student's t with G−1 degrees of freedom, G being the number of quarters.
- **Pass:** p ≤ 0.05 / 8 = 0.00625, and the mean net return at 2x > 0, and a positive mean excess in both halves:
  - IDX: entries before 2014-01-01 and from it;
  - CRYPTO: entries before 2024-01-01 and from it.

**Verdict:**
- **PARTIAL** if any cell passes. Gate 0, so a pass earns a forward paper lane with a new id. A CRYPTO pass is also a
  candidate for a reserved read. The rule needs a year of history, so 2020 alone is too short; that read would be the
  MEXC-only coins.
- **NULL** otherwise.

## Reported (not decided on)
- **Per cell:**
  - trades, assets traded and quarters;
  - mean return at 1x, 2x and 3x;
  - mean excess, t and p;
  - hit rate, median, worst trade;
  - the halves;
  - the five best trades' share of the summed excess.
- **The trend-state baseline:** the mean excess over m_a of all eligible rows that are above and rising. It answers
  whether the reset entry adds anything to simply being in a rising trend.
- **Trades per year.**
- **Read against** `registry.program_trials()`.

## Outputs
`experiments/trendpull_v1/results/`:
- `cells.csv`;
- `trades.csv` (one row per trade: cell, asset, entry and exit day, gross, funding, excess);
- `inputs.csv` (every input file's sha256), and `summary.json` (verdict, their combined digest);
- `FINDINGS.md` by hand after the run.
