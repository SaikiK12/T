"""Constants every lane shares. Values are the ones the hypermine lane (R182) used.

Changing one is a new program version, not an edit: bump PROGRAM_VERSION and re-register every lane that depends on it.
"""
from datetime import date

PROGRAM_VERSION = 1

DISCOVERY_END = date(2024, 1, 1)    # discovery: day < 2024-01-01
VALIDATION_END = date(2025, 6, 30)  # validation: 2024-01-01 .. 2025-06-30 inclusive; holdout: day >= 2025-07-01

HORIZONS = (1, 3, 7, 14, 30)  # days
COST = 0.002                  # flat per trade, as hypermine COST; see docs/AUDIT.md on liquidity-blind cost
SEED = 20261012

GATES = {"disc": (120, 3.5), "val": (60, 2.0), "hold": (40, 2.0)}  # (min observations, min Newey-West t)
N_NULL = 60                  # shifted replicas per search
NULL_SHIFT_MARGIN = 180      # a null shift lies in [margin, n_days - margin)
FW_P_CANDIDATE = 0.05        # CANDIDATE = holdout gate passed and family-wise p below this

GO_REAL = {"min_scored": 20, "min_mean": 0.0, "min_hit": 0.55, "worst_event": -0.40}  # returns unlevered


def split_of(day: date) -> str:
    if day < DISCOVERY_END:
        return "disc"
    if day <= VALIDATION_END:
        return "val"
    return "hold"
