"""Offline tests for scripts/record_variational.py."""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "record_variational", Path(__file__).resolve().parents[1] / "scripts" / "record_variational.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

STATS = {"listings": [
    {"ticker": "NVDA-PERP", "contract_type": "perpetual", "mark_price": "144.3", "volume_24h": "15863215",
     "base_spread_bps": "6.1", "open_interest": {"long_open_interest": "1", "short_open_interest": "2"},
     "funding": {"last": {"rate": "0.0001"}},
     "quotes": {"updated_at": "2026-11-25T17:30:59Z", "base": {"bid": "144.33", "ask": "144.42"},
                "size_1k": {"bid": "144.33", "ask": "144.42"}, "size_100k": {"bid": "144.29", "ask": "144.47"}}},
    {"ticker": "XAU-SWAP", "contract_type": "swap", "mark_price": "2400", "quotes": None, "funding": None}]}


def test_rows_of_flattens_quotes_and_tolerates_missing_fields():
    r = m.rows_of(STATS, 1)
    assert len(r) == 2
    assert r[0]["bid_100k"] == "144.29" and r[0]["ask_1m"] is None
    assert json.loads(r[0]["funding_last"]) == {"rate": "0.0001"}
    assert r[1]["base_bid"] is None and r[1]["funding_last"] == ""


def test_merge_is_idempotent(tmp_path):
    p = tmp_path / "d.csv"
    rows = m.rows_of(STATS, 1)
    assert m.merge_rows(p, rows) == 2
    assert m.merge_rows(p, rows) == 0
    assert m.merge_rows(p, m.rows_of(STATS, 2)) == 2
