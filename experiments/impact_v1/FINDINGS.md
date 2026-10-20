# FINDINGS: impact_v1 (R262). Square-root market impact on the flow books

**Verdict: DATA_PASS.** At $10k, impact is 0.4-1.4% of each book's validation net. The tier cost model is
adequate at the owner's scale.
- **Where impact matters:** in the millions.
  - Books A and X2 lose half their validation net to impact at about **$12M** of capital (Y = 1).
  - They reach zero at about $50M.
  - Book B, which trades a fifth as much, keeps half up to about $130M.
- **Caveat:** these are Binance volumes. Capacity scales linearly with volume, so if MEXC trades a quarter of
  Binance's volume, MEXC capacity is a quarter of these figures.

- **Registry row:** R262 (trials 0, a measurement). Program trials stay at 9,472,061.
- **Gate:** 0.
- **Reproduce:** prereg sha 1a3eaf0d, frozen in commit 50408a9 before the run. Run `python scripts/run_impact.py`
  (about 2 minutes).
- **Parity:** books A, B and X2 equal R217's `daily.npz` exactly.
- **Origin:** queue M006 (Donier and Bonart; Toth et al. 2011).

## Turnover and trade size

| Book | Traded notional per day / capital (disc / val) | Median trade's Q / daily volume at $10k | Notional with filled σ, V |
|---|---|---|---|
| A | 0.41 / 0.76 | 6.5e-8 (val) | 2.8% / 3.8% |
| B | 0.07 / 0.16 | 6.2e-8 | 4.1% / 3.1% |
| X2 | 0.50 / 0.95 | 5.5e-8 | 3.3% / 3.7% |

- A $10k book's median hourly trade is about one 15-millionth of the coin's daily volume. Impact per trade is
  σ x sqrt(6.5e-8), about 0.13 bp of the traded notional for a coin with 5% daily volatility.
- "Filled" means the coin lacked 20 days of statistics and got the conservative fill (90th percentile σ, 10th
  percentile V).

## Net bp/day with impact (Y = 1), at tier costs 1x / 2x / 3x

| Book | Capital | Discovery 2021-23 | Validation 2024-25 H1 | Validation impact bp/day (vs tier cost 1x) |
|---|---|---|---|---|
| A | none (tier only) | +11.19 / +8.20 / +5.21 | +13.60 / +8.00 / +2.40 | (5.60) |
| A | $10k | +11.10 / +8.11 / +5.13 | +13.41 / +7.81 / +2.21 | 0.19 |
| A | $1M | +10.32 / +7.33 / +4.34 | +11.67 / +6.07 / +0.48 | 1.93 |
| A | $10M | +8.43 / +5.44 / +2.45 | +7.50 / +1.90 / -3.69 | 6.10 |
| B | none | +3.90 / +3.35 / +2.81 | +6.99 / +5.77 / +4.54 | (1.23) |
| B | $10k | +3.89 / +3.34 / +2.79 | +6.96 / +5.74 / +4.51 | 0.03 |
| B | $1M | +3.78 / +3.23 / +2.68 | +6.69 / +5.46 / +4.23 | 0.31 |
| B | $10M | +3.51 / +2.96 / +2.41 | +6.02 / +4.79 / +3.56 | 0.98 |
| X2 | none | +15.47 / +11.85 / +8.24 | +19.68 / +12.75 / +5.82 | (6.93) |
| X2 | $10k | +15.34 / +11.73 / +8.11 | +19.40 / +12.47 / +5.55 | 0.28 |
| X2 | $1M | +14.20 / +10.59 / +6.97 | +16.90 / +9.97 / +3.04 | 2.79 |
| X2 | $10M | +11.47 / +7.85 / +4.24 | +10.87 / +3.94 / -2.99 | 8.81 |

NW t at 1x in validation:
- Book A falls from 1.89 (no impact) to 1.87 at $10k, 1.63 at $1M and 1.05 at $10M.
- Book X2 falls from 2.21 to 2.19, 1.90 and 1.23.

## Capacity (1x tier costs)

| Book | C50, Y = 1 (disc / val) | C0, Y = 1 (disc / val) | C50, Y = 0.5 (val) |
|---|---|---|---|
| A | $41M / $12M | $164M / $50M | $50M |
| B | $244M / $129M | $976M / $514M | $514M |
| X2 | $37M / $12M | $150M / $50M | $50M |

- C50 is where impact eats half the 1x net; C0 is where the net reaches zero. Both grow as 1/Y².
- **Validation capacity is a third of discovery's.** The books traded more in 2024-25 (turnover 0.76 vs 0.41 for A), so
  each dollar of capital moves more volume.

## Cost sensitivity
- **The tier model dominates impact below $1M.**
  - At $1M, impact adds 23-40% to the tier cost.
  - At $10M, it adds 72-127%.
- **At 3x tier cost**, A and X2 are already near zero in validation (+2.4, +5.8). Book B is the most robust to both
  costs and impact.

## Reading
- **For the owner:** stakes from $1k to $100k are not limited by impact on these books. The binding cost is the fee
  and spread (the tier model), not the size of the order.
- Capacity is not the reason to prefer one book. B has the most capacity but the smallest edge. A and X2 hold about
  $10M before impact takes half.
- This does not change any verdict. No book has passed gate 1 (unseen days); the forward lanes are the test.

## Not checked
- **MEXC volumes:** the archive has Binance only. R224's order-book snapshots measure MEXC directly, at $1k-$50k.
- **Metaorders:** same-direction hourly trades are not merged, so this understates impact.
- **Funding and borrowing costs** at size.
- **The holdout** (spent at program level).
