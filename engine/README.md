# qx: the lab's fast engine (Rust)

qx runs a family of strategies from one TOML spec and decides the family together, so one registry row carries every
variant's trial count.

For a **new qx lane**, use the verified route after freezing its PREREG and direct inputs:

```sh
python scripts/build_engine.py   # print the source-matched build plan
python scripts/build_engine.py --execute --state-dir /tmp/qx-build-state --run-id unique-build-id
python scripts/qx_run_verified.py experiments/<lane> [--register]
```

The build receipt binds the executable to the Rust sources and toolchain. The verified runner checks that receipt,
the frozen input hashes, and provenance manifests for each data folder before and after execution; it also takes a
per-lane writer lock and retains an immutable calculation receipt. With `--register`, it writes an immutable
registration attempt before appending the registry row, then a separate outcome linked to that calculation receipt.
If the process ends between those writes, a missing outcome means registration needs reconciliation; the calculation
receipt's `SUCCESS` status alone confirms only the calculation. The build state directory must be outside the
repository, and each `--run-id` must be new. The binary is not archived, and the build is not hermetic.

**Historical lanes only:** a frozen PREREG that names `scripts/qx_run.py` keeps using that runner; do not migrate or
rewrite its recorded command. `scripts/qx_run.py experiments/<lane>` verifies the historical lane's own frozen
inputs and produces its summary/registry record as specified by that lane.

```
cargo build --locked --release --manifest-path engine/Cargo.toml
QX_DATA=data engine/target/release/qx events <spec.toml>   # event family
QX_DATA=data engine/target/release/qx spread <spec.toml>   # cross-venue funding carry family
QX_DATA=data engine/target/release/qx factors <spec.toml>  # factor report over a factor family
cargo test --locked --release --manifest-path engine/Cargo.toml     # before every commit that touches engine/
```

The three direct `qx` invocations above are low-level diagnostics only. They bypass lane-level PREREG checks and run
receipts, so do not use them to produce a registered lane result.

| Subcommand | Source | What a strategy is | Decision | Lanes |
|---|---|---|---|---|
| `events` | `src/events.rs` | event kind x direction x horizon x line (x cover), priced on hourly bars as the Python lab does (`scripts/run_delist.py`) | max-t cluster bootstrap, halves, 2025+, matched same-hour null, 2x | R271, R273, R274; `specs/parity_r269.toml` reproduces R269 |
| `factors` | `src/factors.rs` | factor x horizon over a long table of factor values (t, sym, one column per factor), alphalens / Qlib style: IC, rank IC, IR, quantile returns, long-short, turnover, net at the rebalancing horizon | moving-block bootstrap max \|t\| of rank IC over the family | none yet |
| `spread` | `src/spread.rs` | venue set x lookback x entry threshold x slots: a daily book long the lower-funding venue and short the higher one, per coin | moving-block bootstrap max-t over days, NW t, halves, 2025+, trimmed mean, hurdle, 2x | R275 |

Shared code:
- `src/data.rs`: the hourly axis, parquet reading, legs and covers.
- `src/stats.rs`: cluster statistics.
- `src/reserved.rs`: the reserved-sample check every subcommand runs before reading data.

The rules each subcommand implements are in the header comment of its source file. Each lane's PREREG states them in
full and freezes the source hashes.

Data come from `QX_DATA` (default `data/`). Rows before a spec's `start` are dropped as they are read.

**Reserved samples (`docs/GATES.md`).** A spec whose `start` is before 2021-01-01, or that names a path with a
`reserved` folder (Gate, KuCoin, dYdX long tails), is refused unless it sets `reserved_prereg` to a frozen batch PREREG.
- That PREREG must hold the token for each sample it reads: `RESERVED-2020-READ`, `RESERVED-GATE-READ`,
  `RESERVED-VENUE-READ`.
- Its PREREG.sha256 sidecar must match its bytes; the engine computes the SHA-256 itself.
- Before 2026-10-21 only `events` refused 2020 starts. `spread` and `factors` relied on their specs; no frozen spec
  started before 2021.
