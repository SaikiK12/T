"""Offline tests for scripts/measure_daily_vrp.py (register O3b)."""
import importlib.util
import math
from pathlib import Path

import pandas as pd

spec = importlib.util.spec_from_file_location("mdv", Path(__file__).resolve().parent.parent / "scripts" / "measure_daily_vrp.py")
mdv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mdv)


def test_straddle_premium():
    assert abs(mdv.straddle_bp(30, 24) - 0.7979 * 0.30 * math.sqrt(24 / 8760) * 1e4) < 1e-9


def test_implied_filters_expiry_hour_band_and_size():
    D = pd.Timestamp("2026-01-04", tz="UTC")  # a Sunday
    ms = lambda ts: int(ts.timestamp() * 1000)  # noqa: E731
    exp = ms(D + pd.Timedelta(hours=32))
    rows = [
        {"t": ms(D + pd.Timedelta(hours=8)), "expiry_ms": exp, "strike": 100.0, "index_price": 100.0, "buy": 3, "sell": 0, "iv": 40.0},
        {"t": ms(D + pd.Timedelta(hours=9)), "expiry_ms": exp, "strike": 101.0, "index_price": 100.0, "buy": 0, "sell": 3, "iv": 50.0},
        {"t": ms(D + pd.Timedelta(hours=9)), "expiry_ms": exp, "strike": 110.0, "index_price": 100.0, "buy": 9, "sell": 0, "iv": 99.0},
        {"t": ms(D + pd.Timedelta(hours=11)), "expiry_ms": exp, "strike": 100.0, "index_price": 100.0, "buy": 9, "sell": 0, "iv": 99.0},
        {"t": ms(D + pd.Timedelta(hours=8)), "expiry_ms": exp + 86400000, "strike": 100.0, "index_price": 100.0, "buy": 9, "sell": 0, "iv": 99.0},
    ]
    g = mdv.implied_by_day(pd.DataFrame(rows))
    assert list(g.index) == [D]
    assert abs(g.loc[D, "iv"] - 45.0) < 1e-9 and g.loc[D, "btc"] == 6


def test_moves_use_close_of_previous_bar():
    idx = pd.date_range(mdv.START, periods=60, freq="h")
    closes = pd.Series(100.0, index=idx)
    closes[mdv.START + pd.Timedelta(hours=31)] = 101.0   # bar opening D+1 07:00 -> P(D+1 08:00)
    m = mdv.moves(closes)
    assert abs(m.loc[mdv.START, "move"] - math.log(1.01) * 1e4) < 1e-9


def test_md_table():
    t = mdv.md(pd.DataFrame({"a": ["x"], "b": [1.234]}))
    assert t.splitlines()[0] == "| a | b |" and t.splitlines()[2] == "| x | 1.23 |"
