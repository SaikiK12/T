# R372: executable code for the common-parent ORB pilot

This lane implements an independent OR30/VWAP/volume comparison, not a copy of
TradeX or Fractal. [PREREG](PREREG.md) fixes the exact rule, data and accounting
limits. The registration snapshot is append-only; [FINDINGS](FINDINGS.md) and
run receipts report actual completion and native verdict separately.

From the repository root, with the project test environment:

```sh
python -m unittest tests.test_orb_family tests.test_run_orb_family
python scripts/run_orb_family.py --lane experiments/orb_index_v1 --run-id reproduction_001
```

The market command requires the exact sealed raw files under
`data/orb_index_pilot/`; these remain outside Git. Their request URLs, sizes and
SHA-256 values are in [the provenance manifest](../../docs/provenance/orb_index_pilot.json).
The runner refuses absent/changed/extra files, changed code/policy, missing
registration, existing output and concurrent writers. It does not silently
download, reconstruct missing data or select another window. A future fetch
may return revised or expired minute history and is not a byte-identical input.

The independent implementation lives in [orb_family.py](../../lab/orb_family.py).
Invented adversarial tests cover feature causality, fixed parent tickets,
funding units/boundaries, gap exits, lots, calendars, capital continuity,
unknown-outcome propagation and frozen-entry verification. Passing those tests
is separate from profitable market evidence. Raw receipt hashes do not prove
first-seen publication, actual quotes/fills or historical contract parameters.
