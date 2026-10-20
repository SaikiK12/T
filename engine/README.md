# qx: the lab's fast engine (Rust)

qx runs a family of strategies from one TOML spec and decides the family together, so one registry row carries every
variant's trial count. A lane runs it through `scripts/qx_run.py experiments/<lane>`, which:
1. verifies the frozen PREREG;
2. checks every input hash;
3. runs qx;
4. writes `results/SUMMARY.md`;
5. with `--register`, appends the registry row.

```
cargo build --release --manifest-path engine/Cargo.toml
QX_DATA=data engine/target/release/qx events <spec.toml>   # event family
QX_DATA=data engine/target/release/qx spread <spec.toml>   # cross-venue funding carry family
cargo test --release --manifest-path engine/Cargo.toml     # before every commit that touches engine/
```

| Subcommand | Source | What a strategy is | Decision | Lanes |
|---|---|---|---|---|
| `events` | `src/events.rs` | event kind x direction x horizon x line (x cover), priced on hourly bars as the Python lab does (`scripts/run_delist.py`) | max-t cluster bootstrap, halves, 2025+, matched same-hour null, 2x | R271, R273, R274; `specs/parity_r269.toml` reproduces R269 |
| `spread` | `src/spread.rs` | venue set x lookback x entry threshold x slots: a daily book long the lower-funding venue and short the higher one, per coin | moving-block bootstrap max-t over days, NW t, halves, 2025+, trimmed mean, hurdle, 2x | R275 |

Shared code:
- `src/data.rs`: the hourly axis, parquet reading, legs and covers.
- `src/stats.rs`: cluster statistics.

The rules each subcommand implements are in the header comment of its source file. Each lane's PREREG states them in
full and freezes the source hashes.

Data come from `QX_DATA` (default `data/`). Rows before a spec's `start` are dropped as they are read, so the
reserved 2020 sample is never used (`docs/GATES.md`).
