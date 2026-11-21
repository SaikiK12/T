# PREREG: deribitgap_v1 (R519). The funding-design gap between Deribit's linear perps and Hyperliquid, held statically

Freeze with `lab.prereg.freeze()` before the Deribit data are fetched. Never edited afterwards.

- **Registry id:** R519
- **Owner (single writer):** the Claude session that froze it. `scripts/fetch_deribit_perps.py` is the only writer
  of `data/deribit_perps/`, and `scripts/run_deribit_gap.py` the only writer of `experiments/deribitgap_v1/results/`.
- **Date registered (UTC):** 2026-11-21

**Methods:** M560 (new: R507/R508's design gap with Deribit as the floorless venue). Carry, candidate C13.
- **Paper only:** public data; nothing can place an order.

## Why
- **The owner, 2026-11-21:** "il nous faut une faille."
- **The faille this lab has found is a funding-design gap.**
  - A venue with no interest term against one whose longs pay a floor.
  - Kraken + Hyperliquid (R508) and Binance + Bitfinex (R507) passed. Kraken + Aster replicated (R511).
  - Kraken's books are thin, so their capacity is small.
- **Deribit's rule** (read 2026-11-21 through search summaries of Deribit's "Funding Specifications" and "Inverse
  Perpetual" support pages; the pages themselves sit behind a JavaScript check that was not bypassed):
  - funding = max(0.025%, P) + min(-0.025%, P) per 8 h, with P the mark's premium over the index;
  - so it is zero inside a ±0.025% dead zone, with no interest term.
- **Hyperliquid's rule:** premium plus a clamp toward 0.01%/8 h. When the premium is small, its longs pay 10.95%/yr.
- **So on BTC, ETH, SOL and other liquid coins,** long Deribit against short Hyperliquid should collect about the
  floor, with capacity far above Kraken's.
- **Supply.**
  - Deribit lists 15 linear USDC perps from 2022: BTC, ETH, SOL, XRP, AVAX, ADA, DOT, ALGO, BCH, DOGE, LINK, LTC, NEAR,
    TRX and UNI.
  - Then BNB (2024), PAXG and TRUMP (2024-25), HYPE (2026-06), and about 130 more in 2026-08..11.
  - The supply is continuous holding, not events.
- **Reach.** Third-party lists name France as served by Deribit (not checked against Deribit's own policy).
  Hyperliquid needs only a wallet.

## Break-even, written before the freeze (`CLAUDE.md` step 4)
- **The gap.** About 11%/yr on notional when both premia are small, which is about 5.5%/yr on two-leg capital
  unlevered.
- **The static hold's cost.** One entry and one exit: four legs at 7 bp, 0.28% per pair over a hold of months.
- **R275's rule** would churn at half its threshold, and churn ate R518's gap. So the primary holds.

## Question
Does a static design-gap book (long the venue paying less, chosen at entry, then held) earn a positive net return at
R275's costs on Deribit's linear USDC perps against Hyperliquid, 2023-05-01..2026-11-17?

## Data
- **Deribit:** `python scripts/fetch_deribit_perps.py --start 2022-03-01 --end 2026-11-19 --out data/deribit_perps`,
  once after this freeze. Public API: funding history per hour (`interest_1h`) and daily candles.
  - The run verifies its `manifest.json`.
- **Hyperliquid:** `data/hyperliquid` funding and daily candles (rebuilt 2026-11-18). All 470 files are pinned in
  `hl_manifest.json`.
- **Universe:** every live Deribit linear perp whose base is on Hyperliquid. HL's k-coins (kPEPE) match Deribit's
  1000-prefixed names.
- **Survivorship:** live Deribit listings only; Deribit returned no expired perpetuals on 2026-11-21.

## Rule (`scripts/run_deribit_gap.py`)
- **Primary, `StaticBook`** (`lab.xfund_v2`'s engine and accounting):
  - lookback 30 days, entry at a spread of at least 0 (the paying side shorted), 20 slots, widest first;
  - correlation guard 30 days >= 0.9 on 20 observations;
  - **no exit on the spread.** Exits only when a leg stops trading, or on a 20% ratio blowout.
- **Secondary (reported):** R275's book unchanged (L14d th5% K20) on the same pair.
- **Costs:** 7 / 14 / 21 bp a leg. Deribit's taker fee is 3.5 bp, Hyperliquid's 4.5 bp.

## Decision: R391's rule on book days (R516's `report`, R507's `decide`)
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided NW p (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean is above 0;
  - the 10% trimmed mean is above 0;
  - the mean without the two best coins is above 0.
- **FAIL:** otherwise.
- **Also reported:**
  - calendar %/yr against cash (about 4%/yr);
  - by year;
  - funding and price shares;
  - the secondary book.
- **What a PASS earns:** a forward paper lane on Deribit + Hyperliquid, as a new id.

## What the author has seen
- **On 2026-11-21 the session read three hourly BTC-PERPETUAL (inverse) funding rows** from Deribit's API to learn
  the format: 2026-10-26, about 0.005-0.008%/8 h.
- **It also listed Deribit's instruments:** names, creation dates and fees. No linear perp's funding or price was read.
- **Hyperliquid funding** was read by many carry lanes (R275, R439, R508, R511, R516 and others). Never against
  Deribit.

## Trials
- **This round:** 2 (the primary and the reported R275 book).
- **Program trials:** 9,785,761 before, 9,785,763 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/fetch_deribit_perps.py` | cafda9edec3fd8ac0f7a1011819cf41ec8a7a60bd8b3b246360896f105718a3b |
| `scripts/run_deribit_gap.py` | b8a0bc53d821c2cf88be7e11be5c401fcf99230de5e413c5aab28d79f2d34732 |
| `tests/test_deribit_gap.py` | 8385ece329ba85eaf3c641f22fd1ff1c9b752b48c44793b472269a91c4863824 |
| `scripts/run_xfund_listing.py` | c0d601be3a53b9a6dd1c81f84e645a7aec2416d1845f99db0df6ba0ae759c2c2 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/xfund_v2.py` | fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `experiments/deribitgap_v1/hl_manifest.json` | 5f3343484b3e08c1e726c14284845b62e6ad519e48209952bffb959b58af4c3a |
