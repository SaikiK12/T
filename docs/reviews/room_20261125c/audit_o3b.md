# Audit O3b: is the Saturday BTC one-day straddle overpriced?

Auditor: independent re-computation from scratch (no import of `scripts/measure_daily_vrp.py`).
Scratch code: `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/audit_o3b.py` (+ run1-5.py).
Inputs read: `data/deribit_trades/BTC/flow/*.parquet` (58 months), `data/klines_1h/BTCUSDT.parquet`. No ETH, no journal, no commits.

## Core spec (my code)

```python
f = flow[flow.ts.dt.hour.isin([8, 9]) & (flow.exp - flow.D == pd.Timedelta(hours=32)) & flow.iv.notna()]
f = f[(f.strike / f.index_price - 1).abs() <= band]          # band = 0.02 unless stated
g = f.groupby('D').apply(lambda x: np.average(x.iv, weights=x.amt))   # amt = buy + sell
g = g[btc >= 5]; prem = 0.7979 * iv/100 * sqrt(23/8760) * 1e4
move = abs(log(P[D+32h] / P[D+9h])) * 1e4        # P(h) = Binance close of bar opening h-1
```

## 1. Reproduction: yes, exact match

| day | n | IV % | premium bp | move bp | mean(move-prem) bp | t | trim 5% | median |
|---|---|---|---|---|---|---|---|---|
| Sat | 248 | 30.49 | 124.64 | 76.83 | -47.81 | -7.34 | -53.0 | -61.3 |
| Tue (control) | 248 | 48.63 | 198.83 | 180.06 | -18.77 | -1.73 | -34.0 | -61.1 |

Script table (`docs/reviews/o3b_daily_vrp.md`): Sat 248 / 30.49 / 124.64 / 76.83 / -47.81 / -7.34, Tue 248 / 48.63 / 198.83 / 180.06 / -18.77 / -1.73. Identical.

By year, mean(move - premium) in bp (Sat / Tue), identical to the script's by-year table:
- 2022: -118.5 / +8.6
- 2023: -56.6 / -3.4
- 2024: -21.5 / -44.5
- 2025: -40.1 / -30.6
- 2026: +14.6 (n=39) / -25.1

Sat has no positive years except 2026, which is thin (n=39). Consistent with the "shrinking, gone in 2026" description.

## 2. Alignment: no confusion found

- Every Deribit expiry is 08:00 UTC (0 rows off the hour, all 83,163 hour-of-day samples at 8).
- The instrument name's date equals the expiry date for all 70,514 instruments.
- For hour-8/9 rows with IV, the expiry offset from D is 32h (61,166 rows), 56h, 80h, ... The same-day expiry (D+8h) is 4 rows, 1.1 BTC, and is excluded by the `== 32h` filter.
- Saturday D rows with expiry = D+32h: 6,474 rows, all expiring on Sunday.
- Examples (trade time, expiry, assigned D):
  - `BTC-2JUN24-64500-P`: traded 2024-06-01 08:00Z, expires 2024-06-02 08:00Z, D = 2024-06-01 (Sat)
  - `BTC-2JUN24-65000-P`: same
  - `BTC-9MAR25-78000-C`: traded 2025-03-08 08:00Z, expires 2025-03-09 08:00Z, D = 2025-03-08 (Sat)
- Saturday's "expires Saturday 08:00" option is never used: its offset is 8h, not 32h. The move window (D 09:00 to D+1 08:00) also matches the 23h premium.

## 3. Biases

**(a) Band width: the smile inflates the 2% band.**

| band | Sat n | Sat IV | Sat premium bp | Sat mean(e) bp | Sat t | Tue mean(e) bp | Tue t |
|---|---|---|---|---|---|---|---|
| ±0.5% | 217 | 27.42 | 112.12 | -32.32 | -4.57 | -19.66 | -1.80 |
| ±1% | 242 | 28.81 | 117.79 | -40.40 | -6.08 | -15.79 | -1.44 |
| ±2% | 248 | 30.49 | 124.64 | -47.81 | -7.34 | -18.77 | -1.73 |

Amount-weighted IV by |strike/index - 1| bucket (Sat): <=0.5%: 28.2; 0.5-1%: 28.8; 1-2%: 33.2. The wings carry about 5 vol points more. The 2% band therefore overstates the ATM vol by about 2.3 points, which is about 12 bp of premium. Half of the gap is the smile. At ±0.5% the gap is still -32 bp and t = -4.6.

**(b) Index vs Binance.** Median |index / Binance open - 1| is 18 bp, 95th percentile 85 bp. Redoing the band with Binance open: Sat n = 248, IV 30.43, premium 124.40, mean(e) -47.57, t -7.31. Tue mean(e) -19.03. No effect. The band absorbs the index/Binance gap.

**(c) Moneyness of the traded set.** Sat mean |K/S - 1| = 0.88% (unweighted), 0.85% (amount-weighted); 41% of traded BTC sits beyond 1%.
- A Black-Scholes check at 30% vol, 23h: a straddle at |m| = 0.85% costs 18.7 bp more than the ATM straddle at the same IV; the amount-weighted correction is +25.7 bp.
- So the ATM formula is not the right price for the 2% set, and the sign of this error is the opposite of the smile effect. The cleanest ATM estimate is the ±0.5% band, which still shows -32 bp.

**(d) Driven by a few days?** No, mostly.
- 5% trimmed mean of (move - premium): -53.0 bp. Median: -61.3 bp. Share of Saturdays with e > 0: 21% (Tue 34%).
- Dropping the 5 most negative Saturdays: mean -43.1 bp. Dropping 2022: mean -28.6 bp.
- Mean/median of |move| is 1.93 (normal theory: 1.18), so moves are fat-tailed. The big upside moves are what keeps the mean near the premium: trimming them makes the gap larger. This is the seller's tail cost, not a measurement error.
- Plain t (-7.34) overstates confidence. Clustered by month (57 months): t = -6.32. Lag-1 autocorrelation of e across Saturdays: 0.13.
- Move-implied annual vol: Sat 18.8% vs mean IV 30.5%. Tue 44.0% vs 48.6%. Saturday's realised vol is about 40% below its quote; Tuesday's is near fair.

**(e) Minute data check: skipped.** No BTC 1-minute bars for 2022-2026 in `data/`. `data/settlelit1h_1m` is a one-venue lighter folder; `data/hft/trades` starts 2026-10-28 and I did not open it. The hourly closes are checked only for structure: 0 gaps larger than 1h, 0 duplicates, 5 Saturdays dropped (flow present but under 5 BTC after the band; no Saturday lacks flow).

## 4. Sell-dominated rows only (row-level buy < sell)

- Sat: n = 242, IV 30.24, premium 123.65, move 76.35, mean(e) -47.30, t -7.14, trim -52.7, median -59.7.
- By year: 2022 -120.7, 2023 -56.2, 2024 -22.0, 2025 -41.1, 2026 +19.7.
- Tue: n = 243, mean(e) -18.09, t -1.67.
- A seller at the bid gets almost the same premium. The sell side moves the number by less than 1 bp.

## 5. Verdict

The Saturday overpricing survives every check I ran. The reproduction is exact, the alignment is clean, and the sell side changes nothing.

What moved it most: the moneyness band (check 3a). Narrowing from ±2% to ±0.5% cuts the gap from -47.8 to -32.3 bp (about a third), and the t from -7.3 to -4.6. The 2% band also has an offsetting strike-pricing effect (3c), so the ATM number should come from the ±0.5% band.

Not checked or weakest links:
- No 1-minute check (3e).
- Realised-vol comparison assumes normal |r| scaling, which the fat tails break.
- No trading costs or margin beyond the script's 16 bp reference.
- The 2026 sign flip rests on n = 39.

A caveat for the lab: at ±0.5% the gap is about 32 bp per Saturday. The round-trip cost is 16 bp, and tail losses are the seller's risk. This report does not size the trade.
