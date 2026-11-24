"""Tests for scripts/check_wknd_depth.py: New York windows and the capacity rule."""
import importlib.util
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location(
    "check_wknd_depth", Path(__file__).resolve().parents[1] / "scripts" / "check_wknd_depth.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NY = ZoneInfo("America/New_York")


def ms(y, mo, d, h, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=NY).timestamp() * 1000)


def test_windows_follow_new_york_time():
    assert m.window(ms(2026, 11, 22, 19, 0)) == "SunE"      # Sunday 19:00 ET (00:00 UTC Monday)
    assert m.window(ms(2026, 11, 22, 22, 10)) == "SunX"
    assert m.window(ms(2026, 11, 21, 12, 0)) == "WKND"      # Saturday
    assert m.window(ms(2026, 11, 20, 20, 30)) == "WKND"     # Friday after 20:00
    assert m.window(ms(2026, 11, 20, 19, 0)) is None        # Friday post-market, not counted
    assert m.window(ms(2026, 11, 23, 10, 0)) == "RTH"
    assert m.window(ms(2026, 11, 23, 3, 0)) is None         # weekday overnight
    assert m.window(ms(2026, 7, 19, 19, 0)) == "SunE"       # summer time too


def test_round_trip_blank_is_unfilled():
    assert m.round_trip({"buy_1000_bp": "3", "sell_1000_bp": "2.5"}, "1000") == 5.5
    assert m.round_trip({"buy_1000_bp": "", "sell_1000_bp": "2"}, "1000") == float("inf")


def test_capacity_takes_largest_size_within_budget():
    costs = defaultdict(lambda: defaultdict(list))
    costs[("SunE", "A")]["1k"] = [4, 6]
    costs[("SunE", "A")]["10k"] = [9, 11]
    costs[("SunE", "B")]["1k"] = [12]
    costs[("SunE", "B")]["10k"] = [float("inf")]
    cap = m.capacity(costs, {"1k": 1e3, "10k": 1e4}, "SunE", 10.0)
    assert cap == {"A": 1e4, "B": 0.0}
