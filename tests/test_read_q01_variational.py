"""Offline tests for scripts/read_q01_variational.py (register Q01, event F034)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("q", Path(__file__).resolve().parent.parent / "scripts" / "read_q01_variational.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def test_ny_hours_follow_dst():
    assert q.ny_ms("2026-11-27", 16) == 1795813200000      # 21:00 UTC (EST)
    assert q.ny_ms("2026-07-03", 16) - q.ny_ms("2026-07-03", 15) == 3600000


def test_read_frozen_and_xyz_gap():
    fri, sun = q.ny_ms("2026-11-27", 16), q.ny_ms("2026-11-29", 18)
    var = [{"ts": fri, "ticker": "AAPL-PERP", "mark_price": "100", "bid_1k": "", "ask_1k": ""},
           {"ts": sun + 60000, "ticker": "AAPL-PERP", "mark_price": "100", "bid_1k": "100.0", "ask_1k": "100.2"},
           {"ts": fri, "ticker": "TSLA-PERP", "mark_price": "200", "bid_1k": "", "ask_1k": ""},
           {"ts": sun, "ticker": "TSLA-PERP", "mark_price": "200", "bid_1k": "204", "ask_1k": "206"},
           {"ts": sun, "ticker": "NVDA-PERP", "mark_price": "50", "bid_1k": "50", "ask_1k": "50"}]
    books = [{"dex": "xyz", "coin": "xyz:AAPL", "ts": sun, "bid": "101", "ask": "101.2"},
             {"dex": "xyz", "coin": "xyz:TSLA", "ts": sun - 3 * 3600 * 1000, "bid": "1", "ask": "1"}]
    r = q.read(var, books, ["AAPL", "TSLA", "NVDA"], "2026-11-27")
    assert r["matched"] == 2                                  # NVDA has no Friday reference
    devs = sorted(p["frozen_dev_bp"] for p in r["per"])
    assert abs(devs[0] - 10.0) < 1e-6 and abs(devs[1] - 250.0) < 1e-6
    assert r["f034_event"] is False                           # median 130 bp
    assert r["with_xyz"] == 1                                 # the TSLA book is outside the 90-minute window
    assert abs(r["median_xyz_gap_bp"] - abs(100.1 / 101.1 - 1) * 1e4) < 1e-6
