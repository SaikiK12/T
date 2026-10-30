# FINDINGS: venue_gap_v1 (R216): the forward replay is half stocks; the archive holdout is crypto but concentrated

PREREG sha 0ae50ac9. Run 2026-10-19 by `scripts/run_venue_gap.py`. Results in `results/`, including the TradFi symbol list
(`tradfi_symbols.json`) and the top contributors.

## Verdict: the reading-rule flag is raised
TradFi contracts carried **49% of book A's gross on the forward replay**; the threshold was 30%. From now on, MAP and
CLAIMS quote crypto-only numbers as the reference for the owner's venue. R198's and R200's frozen verdicts are
unchanged.

## 1. Forward replay, 2026-10-01..18, entry one bar late (as R214)

Net, 1x:

| Universe | Book A | Book B (top_vs_crowd) |
|---|---|---|
| All R200 symbols, Binance prices (= R214) | **+22.5%** (t 2.23) | **+9.7%** (t 1.74) |
| Crypto only, Binance | +8.7% (t 2.36) | -0.5% (t -0.43) |
| Crypto with a MEXC contract, Binance prices | +4.66% (t 1.37) | -0.10% |
| Same symbols on MEXC prices and funding (R215) | +4.67% | -0.10% |

Costs:
- A crypto-only: 1x/2x/3x +8.7/+7.8/+6.8%.
- A MEXC-mapped: +4.7/+3.8/+2.9%.
- B crypto-only: -0.5/-0.6/-0.7%.

How the A gap from +22.5% to +4.7% splits:
- Stock and commodity perps: -13.8 points. The top contributors are KORU, SOXL, SNXX, SNDK and SK Hynix, mostly Korean
  and semiconductor exposure.
- Crypto coins with no MEXC contract: -4.0 points. Most of it is one coin, 龙虾USDT, at +6.0 points of gross.
- MEXC's prices and funding against Binance's on the same coins: about 0.0 points.

**Book B's forward replay profit comes entirely from TradFi contracts.**

## 2. Archive, zero delay as R198 (TradFi perps exist from 2025-12)

| Book | Window | All (bp/day, t) | Crypto only | TradFi share of gross |
|---|---|---|---|---|
| A | in-sample 2021-01..2025-06 | +12.10, t 3.36 | identical | 0 |
| A | holdout 2025-07..2026-09 | +23.11, t 1.24 | +22.33, t 1.25 | -1.2% |
| B | in-sample | +4.92, t 2.64 | identical | 0 |
| B | holdout | +19.62, t 2.73 | **+18.25, t 2.74** | +3.0% |

Crypto-only holdout at 2x/3x: A +17.3/+12.3, B +17.4/+16.5 bp/day.

So the holdout evidence for top_vs_crowd is crypto evidence. **It is concentrated, though.**
- Two coins carry most of the holdout gross. In book A, BEAT is +0.45 and LAB +0.44 of a total gross of about 1.30,
  roughly 68%.
- In book B, LAB is +0.25 and BEAT +0.15 of about 0.94, roughly 42%.
- Both were shorted while top traders were short against the crowd, and both then fell.
- The in-sample contributors are spread out: the largest single coin is under 10% of gross.

## Notes and caveats
- The frozen TradFi definition includes underlyingType INDEX. That counts DEFIUSDT, a crypto index perp, as TradFi.
  It does not affect the replay, where DEFIUSDT is not eligible, and its archive share is inside the -1.2%.
- 18 replay days is a short sample: the split is about where this sample's profit came from, not about expected value.
- Trials 4; program trials after this lane: 9,471,718.

## What this changes
- The owner's venue is MEXC and crypto. The forward evidence that applies is the crypto, MEXC-mapped book A: +4.7%
  over 18 replayed days. R215 is that book on MEXC prices, so R215 is the forward test to watch, not R200's headline.
- R200's Binance universe includes stock perps. A book that shorts stocks against their crowd is a different strategy.
  It is untested in the archive, because the archive starts TradFi only in 2025-12.
- The concentration of the holdout in two coins means one or two squeezes or crashes can decide a 90-day forward
  result. Report per-coin contributions at every checkpoint.
