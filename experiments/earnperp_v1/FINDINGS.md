# FINDINGS: earnperp_v1 (R461), 24/7 stock perps after an out-of-hours earnings release

**Verdict: NULL.**
- After an after-close (amc) earnings filing, the perp's first move neither continues nor reverses on average:
  - by the next cash open + 30 min (D2): +0.9 bp, Holm p 1.0;
  - by the next cash close (D1): +22 bp, Holm p 1.0.
- Both decision cells lose money at 1x cost.
- The cells are underpowered. Continuations are far noisier than the PREREG's power guess: sd 672 bp, not 400. D1's
  MDE80 is 127 bp, twice the 60 bp 2x cost. So this is **"NULL, underpowered for a cost-sized effect"**. A large
  amc continuation or reversal is ruled out; a 30-60 bp one is not.

Run: `python scripts/run_earnperp.py`, 2026-11-11, after the freeze (PREREG sha256 `e9c946bc`, commit `ce39759e`).
- The PREREG verified and its 11 inputs matched.
- 442 bar files matched their manifests (`results/run.log`):
  - sample A against `docs/provenance/mexc_tradfi.json`;
  - sample B against `data/mexc_stock_post/manifest.json`.
- **Sample B** was fetched after the freeze by the frozen `scripts/fetch_mexc_stock_1h.py`:
  - 187 symbols and 113,049 hourly bars, 2026-10-14 to 2026-11-11 00:00 UTC;
  - 14 symbols returned no bars;
  - provenance in `docs/provenance/mexc_stock_post.json`.
- Output: `results/cells.csv` (32 cells), `results/events.csv` (one row per event), `results/summary.json`.

## Decision cells
bp per event, unhedged, `all` subset, sample A decides.

| cell | n A | days A | mean A | sd A | hit A | p A | Holm p | MDE80 A | n B | days B | mean B | net 1x / 2x / 3x (A) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 amc, next close | 219 | 90 | +22.2 | 672 | 51% | 0.64 | 1.0 | 127 | 92 | 11 | +58.8 | -7.8 / -37.8 / -67.8 |
| D2 amc, next open + 30 min | 219 | 90 | +0.9 | 544 | 49% | 0.98 | 1.0 | 103 | 92 | 11 | -11.4 | -29.1 / -59.1 / -89.1 |

- 219 of the 227 usable amc filings in A had both reference and entry prices. The rest were dropped and counted.
- Sample B's 92 amc events fall on only 11 next-session days. It confirms nothing on its own.
- Hedging with the SPX500 perp changes nothing: D1 +13 bp, D2 -8 bp.

## Diagnostics (not decided on; 30 more cells)
These cells do not reopen M513 (PREREG stop rules). With 32 cells, about 1.6 would reach p <= 0.05 by chance.

- **Before-open (bmo) filings, held to the cash close:**
  - A +80 bp (n 129, 72 days, raw p 0.03, hit 56%); B +70 bp (n 77, p 0.23).
  - Hedged: A +65 bp, B +83 bp.
  - Net in A: +49.7 / +19.7 / -10.3 bp at 1x / 2x / 3x.
  - The continuation holds for both up moves (A +94 bp) and down moves (A +64 bp).
  - It is the only cell of 32 with raw p <= 0.05, and it is weak: 0.03 x 32 cells is about 1.
- **The `big` subset** (the top third of |first move|, cut on A) continues by the close in both sessions:
  - amc +101 bp (n 73, p 0.20); B +124 bp (n 21).
  - bmo +163 bp (n 43, p 0.08); B +147 bp (n 24).
  - The `big` cut uses A's whole distribution, so it is a look-ahead diagnostic.
- **To the next open (x1),** every `all` cell sits within ±35 bp, with p >= 0.27.
- **Q3 2026 (sample B) reactions** leaned down: median first move after amc filings -133 bp; A's was -38 bp.

**Reading against the program.**
- The registry holds 9,785,069 trials. Nothing here is evidence of an edge.
- The bmo-to-close continuation agrees in sign and size in A and B. It is a lead only, in line with the first day
  of post-earnings drift.
- Any test of it must be a **new prospective lane on fresh filings.** The next season starts mid-January 2027.

## Costs (1x, 2x, 3x)
- **The unit is 30 bp per round trip of price:**
  - xyz HIP-3 taker, 9 bp each way;
  - 10 bp of off-hours spread and slippage (assumed, not measured);
  - 2 bp of funding.
- **Decision cells:**
  - D1: -7.8 / -37.8 / -67.8 bp.
  - D2: -29.1 / -59.1 / -89.1 bp.
- **Break-even cost** (the |mean|): D1 22 bp, D2 1 bp. Both are below a single xyz round trip.

## What this closes and what it does not
- **Closed:** M513 in this form. That covers amc 8-K Item 2.02 filings and a first move measured from the cash close
  to one hour after the filing hour, followed to the next open + 30 min or the next close, on MEXC hourly prices,
  2025-07 to 2026-11. No retuning follows.
- **Not tested:**
  - holds beyond the next close (multi-day post-earnings drift, M222);
  - entries later than the first hour;
  - minute bars;
  - foreign issuers (6-K);
  - an earnings-surprise measure (no free consensus);
  - prices on Hyperliquid xyz or Lighter themselves. These venues list far fewer stocks than MEXC's 405, so the
    tradable set is smaller.
- **Not checked:**
  - the 10 bp off-hours slippage;
  - xyz funding around earnings;
  - survivorship: perps delisted before 2026-10-22 are absent.

## Registry
R461, DONE, NULL, 32 trials. Program trials: 9,785,037 before, 9,785,069 after.
