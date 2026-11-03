# Validation

[Repository home](../README.md) · [Environment setup](../docs/guides/OPERATIONS.md#setup-inspection-and-explicit-execution)

Run checks from the repository root using the locked Python environment:

```sh
# Fast feedback; explicitly defers heavier simulation contracts.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 .venv/bin/python -m lab check --suite fast

# Full Python gate before a code commit.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 .venv/bin/python -m lab check --suite full

# The same original unittest discovery entry point.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -t .

# Canonical metadata and preregistration integrity.
.venv/bin/python -m lab integrity
```

For a targeted check, use its module name, for example
`python -m unittest tests.test_repository_index`. Targeted/fast checks provide
feedback; the full commit gate remains required.

Rust build/binding commands and operator actions are in the
[operator guide](../docs/guides/OPERATIONS.md). CI also runs locked Rust tests.
Optional browser/archive checks report explicit skips when their dependencies
or pinned inputs are absent.

Tests should verify meaningful behavior with invented fixtures or declared
inputs. A passing engineering test does not establish strategy profitability,
source completeness or prospective on-time evidence. Historical frozen tests
stay unchanged with their lane; new behavior receives new coverage.
