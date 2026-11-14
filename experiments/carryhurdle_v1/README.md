# carryhurdle_v1 (R483)

M478 and M481, gate 0. Do the lab's audited cross-venue carry books (R437, R438 daily nets) beat holding Ethena's
sUSDe, which is paid by the same perp funding, or lending USDC on Aave v3? The six forward books decide on engine v2
at 2x costs against sUSDe; Aave USDC, Aave USDT and the 4.13% bill are reported.

- `PREREG.md`: frozen question, conversion, alignment, decision rule and what was seen before the freeze.
- `raw/`: the three DefiLlama `/chart` bodies captured once on 2026-11-12T23:41:27Z (the free endpoint stopped on
  2026-11-13), imported after the freeze commit by `scripts/fetch_carryhurdle.py`, with `import_receipt.json`.
- `results/`: written once by `scripts/run_carryhurdle.py` (`table.csv`, `summary.json`), plus `run.log`.
- Tests: `tests/test_carryhurdle.py`.

The freeze commit precedes the data-import commit. The #7 CLAIM is posted by the orchestrator, not before the run.

Paper only. No order, no money, no key.
