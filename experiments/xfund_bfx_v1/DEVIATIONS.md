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

## 2026-11-18 04:45 UTC: the fetch runs as three parallel workers (execution only)
- **Why.** The sequential fetch managed about 28 status requests a minute: 1.2 s per reply plus the frozen 0.9 s pause.
  That projected to about 20 hours, with container restarts about every 30 minutes. Bitfinex allows 90 a minute.
- **What changed.** `run_xfund_bfx.py fetch` ran the frozen discovery to completion (`pairs_all.csv`: 59 listed and 17
  found pairs). Its sequential fetch was then stopped after AAVE (receipt written) and part of ADA. The fetch now
  runs as three processes, `fetch_worker.py k 3` for k = 0, 1, 2:
  - each calls the frozen `fetch_bitfinex_history.fetch` with the frozen window, pace and `pairs_all.csv`;
  - each takes the subset `k::3` of the pairs that still have no receipt, so no pair has two writers;
  - after a container restart, all three are relaunched together, never alongside an old one.
- **What did not change.** Requests, reductions, files and receipts are those of the frozen code. A pair's
  half-finished progress file is resumed by whichever worker gets it.
- The combined rate is about 84 requests a minute. A rate-limit reply makes the frozen code wait 60 s.
