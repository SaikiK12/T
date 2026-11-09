# PREREG: okxcarry_v1, cash-and-carry on OKX Europe X-Perps (BTC, ETH), gate 0

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R430
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); no runtime file of R420/R429 is written
- **Date registered (UTC):** 2026-11-09
- **Method:** M484 (France-eligible carry). The owner asked on 2026-11-09 for the open work to be finished.

## Question
Over every funding print OKX Europe's public API still served on 2026-11-09, would a static short X-Perp / long
spot carry on BTC or on ETH have beaten the 3-month T-bill by at least 2%/yr on capital, net of the venue's
regular taker fees? That is, is the route worth a forward paper lane?

## Universe
- **The two traded instruments:** `BTC-USD_UM_XPERP-310404` and `ETH-USD_UM_XPERP-310404`.
  - OKX EEA crypto X-Perps: linear, settled in USD, expiry 2031-04-04, funding every 8 h, formula `withRate`.
  - Each is the coin's only crypto X-Perp in the snapshot. The runner refuses if there is not exactly one.
- **Reported only, never decided:** all 167 crypto X-Perps listed on 2026-11-09 (`instCategory` 1).
  - This cross-section is current listings only: delisted X-Perps are absent.

## Data
All three data files come from `scripts/fetch_okx_xperp.py`: public `eea.okx.com/api/v5` endpoints, no key,
User-Agent `lab-research/1.0`. The runs were on 2026-11-06 and on 2026-11-09 at 17:39 UTC, merged on
(instId, time). They are copied to the gitignored folder `data/okx_xperp/snap_20261109/`.
- **`funding.parquet`:** `public/funding-rate-history`, every print the API serves (about 3 months).
  - BTC and ETH: 286 prints each, 2026-08-06 16:00 to 2026-11-09 16:00 UTC, every 8 h with no gap.
  - `realizedRate` is present on every one.
- **`mark_1d.parquet`:** `market/history-mark-price-candles`, bar 1D (OKX daily bars open at 16:00 UTC).
- **`index_1d.parquet`:** `market/history-index-candles` for BTC-USD and ETH-USD, bar 1D.
- **T-bill:** `experiments/okxcarry_v1/inputs/tbill_dtb3_20261103.csv`.
  - A copy of `experiments/lockcarry_fwd2/journal/tbill.csv` (FRED DTB3, per cent, rows to 2026-11-03).
  - DTB3 is a bank-discount quote, used as the lab's hurdle, not as a paid cash return (R429's note).

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| funding income F = Σ rate | realizedRate (fundingRate if missing) | OKX EEA, X-Perp, fraction of notional per print | prints in (T0, T1] | venue history, read 2026-11-06/09 | ex post: carry is held, not timed | current listing, forward-captured history | no fill; a missing realizedRate falls back to fundingRate and is counted |
| basis P&L B = I1/I0 − M1/M0 | mark and index 1D closes | OKX EEA mark price and OKX index, USD | closes at T0 and T1 | venue history | ex post | same | a missing bar stops the run |
| T-bill hurdle | DTB3 per cent | FRED via R406's journal copy | each window day, latest value at least 2 days old | FRED | yes (2-day lag) | latest vintage | as-of fill |

Classification: forward-captured venue history for the traded pair; latest-vintage T-bill. No decision inside the
window depends on data the position could not have had. The carry is static: entered at T0 and exited at T1.

## Rule
- **Window:**
  - T0 = 2026-08-06 16:00 UTC, the close of the OKX 1D bar that opens 2026-08-05 16:00.
  - T1 = 2026-11-09 16:00 UTC, the close of the bar that opens 2026-11-08 16:00.
  - That is 95 days and 285 prints in (T0, T1].
- **Position:** at T0, short notional N of the X-Perp and buy N of spot. The OKX index stands in for spot, so the
  spot is held at an EU CASP. Constant notional.
- **Funding:** the short receives N × realizedRate at each print in (T0, T1]. A negative rate is paid.
- **Basis P&L:** N × (I1/I0 − M1/M0), with M the X-Perp mark close and I the index close.
- **Costs:**
  - One round trip of both legs, as a fraction of N: 1x = 0.30%. This is 2 × (0.05% X-Perp taker + 0.10% spot
    taker), OKX EEA regular fees as recorded in M484's note.
  - 2x = 0.60%, 3x = 0.90%. The spread is not modelled; the 2x and 3x multiples cover it.
- **Capital:** K = N × (1 + 1/L): the spot is fully paid, and the X-Perp margin is N/L. The primary is L = 2;
  L = 1 and L = 3 are reported.
- **Annual return on capital:** (F + B − m × 0.30%) / (1 + 1/L) × 365 / 95. Simple, not compounded.
- **Hurdle:** the mean, over the 95 window days, of the latest DTB3 value dated at least 2 days earlier.

## Decision (per coin)
**FORWARD_WORTHY** needs all five; otherwise **NULL**.
1. Excess of the 1x, L = 2 annual return over the T-bill ≥ +2.0 points.
2. Excess at 2x, L = 2 > 0.
3. The mean realized rate is > 0 in each third of the 285 prints (95 each, split in time order).
4. At most 20% of the prints are negative.
5. The largest daily mark high in the window is < 40% above the entry mark, so an L = 2 short needs no top-up.

- **Lane verdict:** FORWARD_WORTHY if either coin is.
- **Trials:** 2 (BTC, ETH).
- **Reported, not decided:**
  - 3x costs and L = 1 and L = 3;
  - funding versus basis;
  - the share of prints at exactly the 0.01% interest baseline;
  - a fixed coin quantity instead of fixed notional;
  - the NW t (lag 10) of daily funding sums;
  - the carry account's daily path and its worst drawdown (L = 2, 1x);
  - the cross-section of all crypto X-Perps' annual realized funding (quantiles and the CSV).

## Gates
Gate 0 only: one historical window, no holdout. A FORWARD_WORTHY verdict earns a forward paper lane, nothing else.

## Null
No shuffled null. The question is a level against a hurdle, not a signal. Persistence is checked by the thirds and
the negative share, and stated as a limit.

## Multiplicity
- 2 trials, one decision group: the static X-Perp carry on BTC and ETH. No variant was generated or dropped before
  this freeze.
- Program trials so far: 9,784,361. After this lane: 9,784,363. The raw program sum is bookkeeping, not a correction.

## Evidence lineage and admission
- **Canonical method:** M484. No parent round on OKX.
- **Related France-eligible carry screens by Codex:**
  - R418: Kraken EEA spot/perp, DOES_NOT_CLEAR_FROZEN_SCREEN.
  - R424: CDE versus Kraken two-perp, negative net proxy.
  - Neither used OKX data.
- **Gates:** current `docs/GATES.md` sha256 e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. This
  lane meets none of the admission requirements beyond gate 0 and stays exploratory.
- **Selection control:** none across families.

## What was seen before this freeze
- Instrument metadata for the 167 crypto X-Perps, including contract value, expiry, settlement currency and maximum
  leverage.
- The 2026-11-06 response of `public/funding-rate`: the formula `withRate`, an interest rate of 0.0001 per 8 h and the
  cap. From that, a back-of-envelope "about 10.95%/yr if every print sat at the baseline" was written to the owner as
  an unmeasured estimate.
- Row counts, timestamps, gaps, method and formula tallies, and the presence of `realizedRate` (`plumbing.log`).
- No statistic of the realized funding series, the basis or any return has been computed.

## Stop rules
- The runner runs once after this freeze, the registry row and a pushed commit.
- No re-run with another window, cost, leverage, bar or coin.
- A different idea, such as alts from the cross-section or a timed entry, is a new lane.

## Limits (stated now)
- **History:** 95 days of history in one regime. Funding regimes change; only a forward lane can show persistence.
- **Prices:** mark and index closes stand in for fills. No order book was recorded, and the X-Perp book depth on
  OKX EEA is unmeasured.
- **Constant notional:** rebalancing costs are ignored. The fixed-quantity variant is reported.
- **Spot venue:** spot is assumed at index price at an EU CASP, so transfer and custody costs are ignored.
- **France access:** OKX EEA X-Perps under MiFID come from the 2026-11-06 report and the venue's documents. This is
  not checked against the AMF/ESMA registers and is not legal advice.
- **Data access:** Codex's runtime host got HTTP 403 from eea.okx.com (M484 note); this container did not. A forward
  lane needs a host that can reach the venue.

## Inputs frozen with this file
```inputs
9c60256cca0516ec8ade2f3d8568b372339c033841112a8616acca4a49915d33  scripts/run_okxcarry.py
42b3287b2bcbbafb1164da850ab0ad21381e3e0d1b3d5fa5e461570df7dce656  tests/test_run_okxcarry.py
bac8b194045c694a897b2fad94cf7303a6b65075987aa3e8d5c1e231fd1e6c84  scripts/fetch_okx_xperp.py
d39df46e17975b9790edfe01388745eac340ba5258f76d09d6a09d4aea1a4b71  data/okx_xperp/snap_20261109/funding.parquet
1b2760e32cfd0d1d7a4567936930a975fff76b945f1145a32edcd17acae8ba10  data/okx_xperp/snap_20261109/mark_1d.parquet
f42ab5c65974abe2dca2349d1b534e1bc4f0c3b4e71195e3e86b256ab1beabe9  data/okx_xperp/snap_20261109/index_1d.parquet
f691f590b957324c9fbcd0ec93858c15de6f4d44d57c5f963ccb5141f3a70345  experiments/okxcarry_v1/inputs/tbill_dtb3_20261103.csv
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
```
