# FINDINGS: rebalfront_v1 (R472). Front-running balanced-fund rebalancing on SPY/IEF closes

**Verdict: NULL.** The construction does not reproduce the paper's Calendar × week4 slope at the frozen bar
(HC1 t −1.67 against −2.0 required). After the published span the rule earns nothing net:
- **U (2023-03-20 .. 2026-11-11):** +0.05 bp a day at 1x (NW t 0.05) and −0.61 at 2x.
- **2026 alone:** −2.11 bp a day at 1x.

PREREG `78340957`, frozen and pushed (`11d84748`) before any SPY, IEF or TLT price was read. One frozen run on
2026-11-12 at 07:58 UTC (`results/run.log`, `results/summary.json`, `results/daily.csv`). One trial; program trials
9,785,259 (`registry.program_trials`).

## Data (deviation from the PREREG's source, not its content)
- SPY, IEF and TLT came from Yahoo's chart API through the frozen fetch, unchanged. SPY has 6,152 days from
  2002-06-03; IEF and TLT have 6,112 from 2002-07-30; all end on 2026-11-11.
- **The bill (DTB3) came from the Federal Reserve Board's H.15 archive**, series RIFSGFSM03_N.B, through
  `scripts/fetch_rebalfront_h15.py`.
  - Why: FRED refused the frozen client from the cloud container and from a GitHub runner; the client was not
    altered to get past that.
  - The file is byte-identical to FRED's DTB3 CSV of the same morning (sha256 `f524d676…`, 19,006 rows).
  - DTB3 enters only the reported equity-only line.
- Provenance: `docs/provenance/rebalfront.json`; lane README, "Faults and notes".

## Results (mean bp a day, Newey-West t, %/yr, Sharpe, maximum drawdown %)
Unit cost 4.2 bp per unit of |Δw|: the xyz SP500 leg plus TLT at 0.45 of the notional, each at 2.9 bp.

| Sample | Days | Two-leg gross | 1x | 2x | 3x |
|---|---|---|---|---|---|
| R 2002-09-03 .. 2023-03-17 | 5,171 | +3.44 (t 4.20), 8.7%, 0.97 | +2.69 (t 3.31), 6.8%, DD 14.7 | +1.93 (t 2.40) | +1.17 (t 1.47) |
| **U 2023-03-20 .. 2026-11-11** | 916 | +0.72 (t 0.65), 1.8%, 0.34 | **+0.05 (t 0.05)**, 0.1%, DD 7.0 | −0.61 (t −0.56) | −1.28 (t −1.18) |
| U2026 (unseen by anyone) | 216 | −1.47 (t −0.80) | −2.11 (t −1.14) | −2.76 | −3.41 |

| Sample | Equity-only gross | 1x | 2x | 3x |
|---|---|---|---|---|
| R | +2.85 (t 4.09) | +2.33 (t 3.36) | +1.80 (t 2.63) | +1.28 (t 1.88) |
| U | +0.63 (t 0.64) | +0.17 (t 0.17) | −0.29 | −0.75 |
| U2026 | −0.75 (t −0.39) | −1.20 | −1.64 | −2.09 |

| Slopes on next-day SPY − IEF (b, HC1 t) | R | U | U2026 |
|---|---|---|---|
| Threshold (needs t ≤ −2 in R) | −0.350 (t −4.71) | −0.206 (t −1.22) | −0.068 (t −0.39) |
| Calendar × week4 (needs t ≤ −2 in R) | **−0.155 (t −1.67)** | +0.170 (t +1.13) | −0.011 (t −0.06) |
| Calendar alone | −0.028 (t −0.47) | −0.187 (t −1.49) | +0.012 (t +0.11) |
| Paper (futures, 1997-09 .. 2023-03) | Threshold −0.414 (t −3.6); Calendar × week4 −0.303 (t −3.7) | | |

| Legs (gross) and position | R | U | U2026 |
|---|---|---|---|
| Threshold leg alone | +4.65 (t 3.74) | +0.13 (t 0.11) | −0.55 (t −0.34) |
| CalMod leg alone | +2.24 (t 2.20) | +1.31 (t 0.79) | −2.38 (t −0.80) |
| Turnover \|Δw\| a day | 0.180 | 0.159 | 0.154 |
| Mean \|w\| / mean w / max \|w\| | 0.265 / −0.099 / 1.23 | 0.267 / −0.138 / 0.82 | 0.257 / −0.100 / 0.82 |

## Reading
- **The paper's Threshold effect is visible on ETFs in its own span; the calendar part is weaker.**
  - Threshold reproduces at about the expected size (t −4.71; the PREREG expected about −3.2).
  - Calendar × week4 has half the paper's slope on SPY/IEF (−0.155 against −0.303). The PREREG gave this joint
    replication about 0.8 power, so the miss is informative but not proof of a construction error. IEF is not the
    10-year note future, and settlement prices are not closes (PREREG, Limits).
- **The money was in the published span, not after it.**
  - In R the rule earned +2.69 bp a day net (6.8%/yr, Sharpe 0.76).
  - In U both legs are near zero, and in 2026 both are negative.
  - The authors' footnote says results through 2025 "become even stronger" on their futures. On ETF closes from
    2023-03 we do not see that: Threshold +0.13 bp a day, CalMod +1.31.
- **Funding would make U worse, not better.**
  - The book is short stocks / long bonds on average (mean w −0.14 in U). The TLT leg would then be long xyz:TLT
    most of the time, about 0.45 × 0.27 ≈ 0.12 of capital.
  - xyz:TLT longs paid a mean 20%/yr funding since its listing (R473 post hoc). That is about −1 bp a day of capital,
    more than U's entire 1x mean.
  - Funding on the SP500 leg is smaller; mean w is negative, so the book would mostly receive it.
- **Against program trials (9,785,259):** a null under one pre-named rule. Nothing to adjust.

## What this closes
- M522 on SPY/IEF closes: TESTED, NULL. The forward lane on xyz SP500 + TLT is not earned.
- Reopen only with something genuinely different. Examples:
  - the paper's own futures, with settlement prices and the 10-year note;
  - a measured month-end flow signal (fund flows, not a simulated portfolio).
  Retuning bands or windows on these ETFs would be a new lane against this null.
