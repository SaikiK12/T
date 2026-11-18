# Deviations: xfund_bfx_v1 (R507)

## 2026-11-18 04:40 UTC: discovery re-adds five non-crypto pairs; the run follows the PREREG's universe
Written during the fetch, before any in-window Bitfinex price or funding was read or summarised.

**What happened.**
- The PREREG's universe is the crypto USDt pairs. It excludes index, FX, metal, oil and volatility contracts
  (`fetch_bitfinex_history.is_crypto`).
- The frozen discovery step (`run_xfund_bfx.fetch`) probes a Bitfinex code for every Binance coin name. It does not
  apply `is_crypto`. Binance's archive holds BTCDOM, XAG, XAUT, XPD and XPT perps. Bitfinex lists the same codes
  today, so discovery found them and added them to `pairs_all.csv`.
- **The discovery result** (`data/bitfinex_hist/discovery.csv`): 880 codes probed, 17 found.
  - 12 are delisted crypto pairs: ANC, EOS, FTM, KNC, LUNA, MATIC, MKR, OMG, STG, WAVES, WLD and XMR.
  - 5 are the non-crypto pairs above. They are not delisted.

**What is done.**
- The PREREG's text governs. Its code cannot change, so the data step aligns the run with the text:
  - the fetch runs as frozen, these five pairs included;
  - after the last fetch and before `run`, the five receipts (`receipts/{BTCDOM,XAG,XAUT,XPD,XPT}.json`) move to
    `data/bitfinex_hist/excluded/receipts/`. Nothing is deleted.
  - `run` builds its symbol table from `receipts/`, so they are out of the universe.
- **Reported, not decided on:** the primary book with the five included, from a copy of the receipts in a scratch
  folder, after the frozen read.

**Why not keep them.** Gold, silver, platinum, palladium and a dominance index carry funding of a different kind
(TradFi hours, index construction). The PREREG excluded them before any data, and its stated question is about crypto
perps.
