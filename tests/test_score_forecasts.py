"""Offline tests for scripts/score_forecasts.py (register Q25)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("sf", Path(__file__).resolve().parent.parent / "scripts" / "score_forecasts.py")
sf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sf)


def row(rid, kind, fid, p="", outcome=""):
    return {"row_id": rid, "kind": kind, "forecast_id": fid, "written_utc": "", "event": "", "p": p, "source": "",
            "outcome": outcome, "note": ""}


def test_brier_and_reference():
    rows = [row("1", "forecast", "a", "0.8"), row("2", "forecast", "b", "0.2"), row("3", "resolve", "a", outcome="1"),
            row("4", "resolve", "b", outcome="1"), row("5", "forecast", "c", "0.5")]
    assert sf.check(rows) == []
    s = sf.score(sf.pairs(rows))
    assert s["n"] == 2 and abs(s["brier"] - (0.04 + 0.64) / 2) < 1e-12
    assert s["hit_rate"] == 1.0 and s["brier_base_rate"] == 0.0


def test_check_catches_bad_rows():
    rows = [row("1", "forecast", "a", "1.3"), row("1", "resolve", "z", outcome="1"), row("3", "resolve", "a", outcome="2")]
    errs = " ".join(sf.check(rows))
    assert "not in [0, 1]" in errs and "duplicate row_id" in errs and "no earlier forecast" in errs and "0 or 1" in errs
