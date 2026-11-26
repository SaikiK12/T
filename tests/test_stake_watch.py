"""Offline tests for scripts/stake_watch.py (register T1)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("sw", Path(__file__).resolve().parent.parent / "scripts" / "stake_watch.py")
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)


def test_hl_delisted_and_absent():
    meta = {"universe": [{"name": "BTC"}, {"name": "JELLY", "isDelisted": True}]}
    assert sw.hl_delisted(meta, ["BTC", "JELLY", "GONE"]) == ["JELLY", "GONE"]


def test_hl_bad_fills():
    fills = [{"coin": "SYRUP", "dir": "Open Short", "px": "1", "sz": "5", "time": 1},
             {"coin": "SYRUP", "dir": "Auto-Deleveraging", "px": "1.2", "sz": "5", "time": 2},
             {"coin": "CAKE", "dir": "Close Long", "liquidation": {"markPx": "2"}, "px": "2", "sz": "3", "time": 3},
             {"coin": "OTHER", "dir": "Auto-Deleveraging", "px": "9", "sz": "1", "time": 4}]
    bad = sw.hl_bad_fills(fills, {"SYRUP", "CAKE"})
    assert [b["coin"] for b in bad] == ["SYRUP", "CAKE"]


def test_kraken_problems_and_page():
    ins = {"instruments": [{"symbol": "PF_A", "tradeable": True}, {"symbol": "PF_B", "tradeable": False},
                           {"symbol": "PF_C", "tradeable": True, "postOnly": True}]}
    assert sw.kraken_problems(ins, ["PF_A", "PF_B", "PF_C", "PF_D"]) == [("PF_B", "not tradeable"),
                                                                       ("PF_C", "post-only"), ("PF_D", "missing")]
    assert sw.kraken_named("Upcoming Delistings PF_ACEUSD 27-Nov", ["PF_ACEUSD", "PF_ACE"]) == ["PF_ACEUSD"]
