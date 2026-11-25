"""Tests for scripts/check_wknd_power.py: the balanced book cancels a common move; the decision schedule."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location(
    "check_wknd_power", Path(__file__).resolve().parents[1] / "scripts" / "check_wknd_power.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _per(moves_after, w, f="2026-05-08"):
    """Rows as R462's build makes them: fade side s = -sign(W), c = s * move, g = c (no funding)."""
    rows = []
    for i, (wv, mv) in enumerate(zip(w, moves_after)):
        s = -1 if wv > 0 else 1
        rows.append({"coin": f"C{i}", "F": f, "sample": "A", "W": wv, "s": s, "g_x1": s * mv})
    return pd.DataFrame(rows)


def test_balanced_book_cancels_a_common_move():
    # Every market moves +30 bp after entry (a common move); relative weekend moves are +-100 bp.
    w = [100.0, 120.0, 0.0, -100.0, -120.0, 0.0]
    per = _per([30.0] * 6, w)
    b = m.balanced_weekends(per, "A", cost=0.0)
    assert len(b) == 1 and abs(b.gross.iloc[0]) < 1e-9
    raw = m.raw_weekends(per, "A", cost=0.0)
    assert raw.gross.iloc[0] == 0.0          # two fades lose 30, two gain 30


def test_balanced_book_earns_idiosyncratic_reversal():
    # Names that rose relative give back 20 bp, names that fell relative recover 20 bp, on top of a +50 common move.
    w = [100.0, 120.0, 0.0, -100.0, -120.0, 0.0]
    mv = [30.0, 30.0, 50.0, 70.0, 70.0, 50.0]
    b = m.balanced_weekends(_per(mv, w), "A", cost=5.0)
    assert abs(b.gross.iloc[0] - 20.0) < 1e-9 and abs(b.net.iloc[0] - 15.0) < 1e-9


def test_decide_futility_and_pass():
    rng = np.random.default_rng(0)
    assert m.decide(np.full(30, -1.0), 5.0, rng, 200) == "futile"
    good = np.r_[np.full(27, 30.0), [10.0, 12.0, 14.0]]
    assert m.decide(good, 5.0, rng, 200) == "pass20"
