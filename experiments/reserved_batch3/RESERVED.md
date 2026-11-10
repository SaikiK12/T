# Reserved-read declaration: batch 3 (R392)

This file is the `reserved_prereg` named by `experiments/reserved_batch3/spec.toml`. It is frozen with
`lab.prereg.freeze()` before `PREREG.md`, and `PREREG.md` lists its sha256 in its inputs block. A file cannot hold its
own hash, so the declaration lives here. The batch's question, rules and decision live in `PREREG.md`.

RESERVED-GATE-READ

- **Sample read through this file:** the Gate long tail in `data/gate_hist/reserved/` (read 2 of 4 of the Gate
  sample; batch 1, R286, was read 1).
- **Which rows:** only the 31 contracts in `experiments/reserved_batch3/symbols.csv`, their 1 h candlesticks and
  funding settlements from 2021-01-01 to 2026-09-30.
- **Not read through this file:**
  - no Gate row before 2021-01-01 (the engine's 14-day lookback is inside the window);
  - no other Gate contract (713 long-tail contracts have no MEXC partner and are not in the table);
  - no MEXC-only reserved contract (the six long-tail bases AGI, FLR, PEAQ, RHEA, VELO and XDC have no row);
  - no KuCoin, dYdX or Lighter `reserved/` folder.
- **The 2020 sample** (Binance bars and funding before 2021-01-01) is read by the same batch through
  `lab.panel.check_reserved` against `PREREG.md`, which declares RESERVED-2020-READ. The engine does not read it.
- **One read only.** The run is done once with `scripts/run_reserved_batch3.py --run`, which calls
  `scripts/qx_run_verified.py`, and nothing is retried after data is read.
