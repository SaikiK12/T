# Reserved-read declaration: batch 2 (R391)

This file is the `reserved_prereg` named by `experiments/reserved_batch2/spec.toml`. It is frozen with
`lab.prereg.freeze()` before `PREREG.md`, and `PREREG.md` lists its sha256 in its inputs block. A file cannot hold its
own hash, so the declaration lives here. The batch's question, rule and decision live in `PREREG.md`.

RESERVED-VENUE-READ

- **Samples read:**
  - the KuCoin long tail in `data/kucoin_hist/reserved/` (read 1 of 4);
  - the dYdX long tail in `data/dydx_hist/reserved/` (read 1 of 4);
  - the Lighter long tail in `data/lighter_hist/reserved/` (read 1 of 4). Lighter's `reserved/` folder is built by
    `scripts/fetch_venue_history.py` under the same rule as KuCoin's and dYdX's, and the engine guards it with the same
    token.
- **Which rows:** only the contracts in `experiments/reserved_batch2/symbols.csv`, from 2021-01-01 to 2026-10-19.
- **Samples not read:**
  - no row before 2021-01-01, so no 2020 sample;
  - no Gate folder;
  - no MEXC-only reserved contract.
- **One read only.** The run is done once with `scripts/qx_run_verified.py`, and nothing is retried after data is read.
