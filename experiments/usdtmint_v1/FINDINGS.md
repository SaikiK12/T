# FINDINGS: usdtmint_v1 (R460), BTC after Tether USDT mints

**Verdict: NULL.**
- Neither decision cell beats the circular-shift placebo.
  - D1 (BTC, 24 h): Holm p 0.40. D2 (BTC, 4 h): Holm p 0.44.
  - D1 loses money at 2x cost, and its excess is negative in the holdout.
- The 24-hour cell can only detect about 65 bp (MDE80), well above the 20 bp 2x cost. So the result is
  **"NULL, underpowered for an effect of the cost's size"**: there is no sign of a large post-mint rise, and a small one
  cannot be ruled out.

Run: `python scripts/run_usdtmint.py`, 2026-11-11, after the freeze (PREREG sha256 `3ee286ea`, commit `01e53780`).
PREREG verified, its 12 inputs matched, and the bar and funding parquet files matched their manifests (`run.log`).
Output: `results/cells.csv` (30 cells), `results/trades.csv`, `results/summary.json`.

## Decision cells
All figures in bp per trade, long BTC.

| cell | n | mean | placebo mean | excess | p | Holm p | excess disc / val / hold | funding | net 1x / 2x / 3x |
|---|---|---|---|---|---|---|---|---|---|
| D1 BTC all 24 h | 201 | +23.1 | +6.2 | +16.9 | 0.20 | 0.40 | +5.7 / +57.5 / **-13.1** | 6.5 | +6.6 / **-3.4** / -13.4 |
| D2 BTC all 4 h | 223 | +2.0 | +0.7 | +1.3 | 0.44 | 0.44 | -4.9 / +12.7 / -0.1 | 1.5 | -9.6 / -19.6 / -29.6 |

- **D1:** the mean (+23 bp) is the break-even round-trip cost before funding. After 6.5 bp of funding, D1 clears 1x
  (10 bp) and fails 2x. Its sd is 331 bp (t 0.99, hit rate 55%).
- **D2:** at 4 hours the mean is +2 bp, below every cost level.
- **Splits:** the validation period (2024-01 .. 2025-06) carries the whole positive excess. The holdout
  (2025-07 .. 2026-09, 41 trades) is negative.

## Diagnostics (not decided on; 28 cells)
- **Tron against Ethereum mints.**
  - BTC after Tron mints is flat to negative: 24 h mean -9 bp (p 0.72); 4 h -14 bp (p 0.91).
  - BTC after Ethereum mints is +64 bp over 24 h (p 0.02, n 96), but the holdout excess is -44 bp. The per-split
    figures (+126 / +55 / -44) fall over time.
- **ETH as the asset.**
  - ETH after all mints: +58 bp over 24 h (raw p 0.03, net 2x +30 bp). Its holdout excess is -5 bp, and validation
    (+127) carries it.
  - Its 1-hour and 4-hour cells are near zero.
- **After a down day** (Griffin and Shams' setting): BTC 24 h +35 bp (p 0.17, n 83), holdout -41 bp. ETH: p 0.22.
- **At least $1B per mint:** weaker than all mints in every BTC cell (24 h +11 bp, p 0.38).
- **Multiplicity:** 30 cells at one-sided p <= 0.05 would give about 1.5 false hits under the null. Two cells come
  out at p <= 0.05 (BTC Ethereum-chain 24 h 0.02; ETH all 24 h 0.03), and in both the holdout goes the wrong way.
  Read against the program's 9,785,037 trials, none of this is evidence.

## Costs (1x, 2x, 3x)
- The unit is 10 bp per round trip: Hyperliquid tier-0 taker, 4.5 bp each way, plus 1 bp slippage (assumed).
- Funding is charged at Binance's rates on top: 6.5 bp per 24-hour BTC trade, 1.5 bp per 4-hour trade.
- **D1:** +6.6 / -3.4 / -13.4. **D2:** -9.6 / -19.6 / -29.6.
- Cost is not what fails the lane. The placebo test does, and so does the holdout's sign.

## What this closes and what it does not
- **Closed:** M512 for BTC in 2021-2026 at a 2-minute lag, holding 4 or 24 hours. No retuning follows. The ETH and
  Ethereum-chain cells are diagnostics; they do not reopen it (PREREG stop rules).
- **Not tested:**
  - mints on other chains (Solana, TON and others);
  - the 2017-2018 period of the Griffin and Shams paper (not read);
  - redemptions (burns);
  - USDC and other stablecoins;
  - horizons beyond 24 hours;
  - a short or contrarian rule.
- **Not checked:** Hyperliquid's own fills and funding at these instants (Binance stands in); the 1 bp slippage.

## Registry
R460, DONE, NULL, 30 trials. Program trials: 9,785,007 before, 9,785,037 after.
