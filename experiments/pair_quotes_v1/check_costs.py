"""Post-outcome independent raw-order Decimal audit; never imports the cost kernel."""
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

LANE = Path(__file__).resolve().parent
D = lambda value: Decimal(str(value))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    identity = json.loads((LANE / "evidence_inputs.json").read_text())
    for name, expected in identity["sha256"].items():
        assert digest(LANE / name) == expected, name
    receipts = json.loads((LANE / "evidence/receipts.json").read_text())
    records = {r["name"]: r for r in receipts["records"]}

    def raw(name):
        r = records[name]
        body = gzip.decompress((LANE / "evidence" / r["body"]).read_bytes())
        assert hashlib.sha256(body).hexdigest() == r["sha256"]
        return json.loads(body, parse_float=Decimal)

    def cash(side, qty, descending):
        # Walk raw individual orders, without aggregating as the production
        # decoder does. Partial last-level fills keep identical BASE quantity.
        left, value = qty, D(0)
        for price, size in sorted(side, key=lambda x: x[0], reverse=descending):
            take = min(left, size)
            value += take * price
            left -= take
            if left == 0:
                return value
        raise AssertionError("insufficient raw depth")

    result = json.loads((LANE / "results.json").read_text())
    assert result["evidence_manifest_sha256"] == digest(LANE / "evidence_inputs.json")
    assert result["predictive_trials"] == 0
    errors, skew_ms, notionals = [], [], []
    checked = 0
    for row in result["observations"]:
        assert "error" not in row
        assert not row["execution_ready"] and not row["session_calendar_verified"]
        symbol, i = row["symbol"], row["observation"]
        mm = raw(symbol + "_mexc_meta")["data"]
        if isinstance(mm, list):
            mm, = [r for r in mm if r["symbol"] == symbol + "_USDT"]
        lm, = raw(symbol + "_lighter_meta")["order_book_details"]
        mb, lb = raw(f"{symbol}_mexc_book_{i}")["data"], raw(f"{symbol}_lighter_book_{i}")
        q = D(row["conditional_cost"]["quantity_base"])
        a, b = D(mm["contractSize"])*D(mm["volUnit"]), D(10)**(-lm["supported_size_decimals"])
        assert q % a == q % b == 0
        sides = []
        for name in ("asks", "bids"):
            side = sorted([(D(r[0]), D(r[1])*D(mm["contractSize"])) for r in mb[name]],
                          key=lambda x: x[0], reverse=name == "bids")[:mm["marketOrderMaxLevel"]]
            sides.append(cash(side, q, name == "bids"))
        for name in ("asks", "bids"):
            side = [(D(r["price"]), D(r["remaining_base_amount"])) for r in lb[name]]
            sides.append(cash(side, q, name == "bids"))
        m_buy, m_sell, l_buy, l_sell = sides
        crossing = m_buy-m_sell+l_buy-l_sell
        reserve = (m_buy+m_sell)*D(".001") + (l_buy+l_sell)*D(".0004")
        for scenario in row["conditional_cost"]["scenarios"]:
            expected = (crossing + reserve)*D(scenario["multiple"])
            error = abs(expected-D(scenario["round_trip_cost_usd"]))
            assert error < D("1e-9"), (symbol, i, error)
            errors.append(error)
            checked += 1
        fair = raw(symbol + "_fair")["data"]
        obs = row["funding_notional_observation"]
        assert not obs["settlement_notional_verified"]
        for actual, expected in ((obs["mexc_fair_quote_usd"], q*D(fair["fairPrice"])),
                                 (obs["lighter_index_quote_usd"], q*D(lm["index_price"]))):
            assert abs(D(actual)-expected) < D("1e-9")
            notionals.append(actual)
        r1, r2 = (records[f"{symbol}_{v}_book_{i}"]["receipt"] for v in ("mexc", "lighter"))
        skew = abs(r1["received_mono_ns"] - r2["received_mono_ns"])/1e6
        assert skew <= 1000 and row["first_seen_pair_ok"]
        skew_ms.append(skew)
    out = {"scope": "post-outcome accounting/identity audit, not another predictive variant",
           "result_sha256": digest(LANE/"results.json"), "audit_code_sha256": digest(Path(__file__)),
           "observations": len(result["observations"]), "cost_scenarios_checked": checked,
           "fair_index_notionals_checked": len(notionals), "max_cost_error_usd": str(max(errors)),
           "max_pair_receive_skew_ms": max(skew_ms)}
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    path = LANE / "audit.json"
    if path.exists():
        assert path.read_text() == text
    else:
        path.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
