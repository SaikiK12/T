"""Frozen R417 independent Fraction cash/depth checker; no kernel import."""
from fractions import Fraction as F
from math import gcd, lcm
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANE = ROOT / "experiments/carry_execution_v1"
PARENT = ROOT / "experiments/pair_quotes_v1/evidence"


def close(actual, expected):
    if abs(F(str(actual)) - expected) > F(1, 10**12):
        raise AssertionError((actual, str(expected)))


def main():
    report_path = LANE / "results/report.json"
    report = json.loads(report_path.read_text())
    spec = json.loads((LANE / "cases.json").read_text())
    for name, sha in report["inputs"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name
    receipts = {r["name"]: r for r in json.loads((PARENT / "receipts.json").read_text())["records"]}

    def raw(name):
        record = receipts[name]
        body = gzip.decompress((PARENT / record["body"]).read_bytes())
        assert hashlib.sha256(body).hexdigest() == record["sha256"]
        return json.loads(body, parse_float=str)

    mm = raw("BTC_mexc_meta")["data"]
    lm, = raw("BTC_lighter_meta")["order_book_details"]
    depth_checks, cash_checks, unknown = 0, 0, 0
    for row in report["snapshot_sweeps"]:
        i, m = row["observation"], F(row["cost_multiple"])
        mb, lb = raw(f"BTC_mexc_book_{i}")["data"], raw(f"BTC_lighter_book_{i}")
        sides = []
        for venue, payload in (("mexc", mb), ("lighter", lb)):
            output = {}
            for side in ("bids", "asks"):
                if venue == "mexc":
                    raw_levels = [(F(str(p)), F(str(q)) * F(str(mm["contractSize"]))) for p, q, _ in payload[side]]
                else:
                    raw_levels = [(F(str(x["price"])), F(str(x["remaining_base_amount"]))) for x in payload[side]]
                agg = {}
                for p, q in raw_levels:
                    agg[p] = agg.get(p, F(0)) + q
                levels = sorted(agg.items(), reverse=side == "bids")
                output[side] = levels[:mm["marketOrderMaxLevel"]] if venue == "mexc" else levels
            output["mid"] = (output["bids"][0][0] + output["asks"][0][0]) / 2
            sides.append(output)
        q = F(row["quantity"])
        lots = (F(str(mm["contractSize"])) * F(str(mm["volUnit"])), F(10) ** -lm["supported_size_decimals"])
        for step in lots:
            assert (q / step).denominator == 1
        assert q * max(x["mid"] for x in sides) <= F(row["target_per_leg"])
        step = F(lcm(lots[0].numerator, lots[1].numerator), gcd(lots[0].denominator, lots[1].denominator))
        assert (q + step) * max(x["mid"] for x in sides) > F(row["target_per_leg"])
        if row["state"] != "CONDITIONAL_SNAPSHOT":
            assert not row["directions"]
            unknown += 1
            continue
        for direction in row["directions"]:
            costs, fees = [], []
            for name, key, side in (("buy", direction["buyer"], "asks"), ("sell", direction["seller"], "bids")):
                left, quote = q, F(0)
                mid = sides[key]["mid"]
                for price, size in sides[key][side]:
                    take = min(left, size)
                    quote += take * (mid + m * (price - mid))
                    left -= take
                    if not left:
                        break
                fill = q - left
                cost = quote - fill * mid if name == "buy" else fill * mid - quote
                fee = quote * F(spec["snapshot_fee_scenarios"][key]) * m
                actual = direction[name]
                close(actual["quote"], quote)
                close(actual["filled"], fill)
                close(actual["book_cost"], cost)
                close(actual["fee"], fee)
                assert actual["complete"] == (left == 0)
                costs.append(cost)
                fees.append(fee)
                depth_checks += 4
            expected_complete = direction["buy"]["complete"] and direction["sell"]["complete"]
            if expected_complete:
                close(direction["complete_entry_cost"], sum(costs) + sum(fees))
                depth_checks += 1
            else:
                assert direction["complete_entry_cost"] is None
                unknown += 1
    cases = {c["name"]: c for c in spec["synthetic_cases"]}
    for world in report["synthetic_stress"]:
        case = cases[world["case"]]
        n, m = F(world["notional_per_leg"]), F(world["cost_multiple"])
        assert F(world["account_capital"]) == F(world["initial_capital"]) == 2 * n
        q = n / 100
        close(world["initial_quantity"], q)
        state = {}
        for k, sign in (("long", 1), ("short", -1)):
            entry = F(100) + sign * m / 20
            fee = q * entry * F(case["legs"][k]["fee_rate"]) * m
            state[k] = dict(q=sign * q, entry=entry, cash=n - fee, realized=F(0), fees=fee)
        for row, event in zip(world["rows"], case["events"], strict=True):
            total = F(0)
            for k, old in state.items():
                w, mark = row["wallets"][k], F(event["marks"][k])
                current = F(w["quantity"])
                assert abs(current) <= abs(old["q"])
                if not old["q"]:
                    assert not current
                closed = old["q"] - current
                if closed:
                    forced = event.get("forced", {}).get(k)
                    price = F(forced["price"]) if forced else mark - (1 if closed > 0 else -1) * m / 20
                    pnl = closed * (price - old["entry"])
                    rate = F(forced["fee_rate"]) if forced else F(case["legs"][k]["fee_rate"])
                    fee = abs(closed) * price * rate * m
                    if any(a.startswith(k + "_LIQUIDATED") for a in row["actions"]):
                        fee += abs(closed) * price * F(case["legs"][k]["liquidation_fee"]) * m
                    old["cash"] += pnl - fee
                    old["realized"] += pnl
                    old["fees"] += fee
                old["q"] = current
                close(w["cash"], old["cash"])
                close(w["realized"], old["realized"])
                close(w["fees"], old["fees"])
                close(w["funding"], F(0))  # all frozen toy paths explicitly use zero
                equity = old["cash"] + current * (mark - old["entry"])
                close(w["equity"], equity)
                total += equity
                cash_checks += 5
            close(row["equity"], total)
            close(row["net"], total - 2 * n)
            cash_checks += 2
            if event["label"] == "before_recovery":
                close(world["loss_before_recovery"], total - 2 * n)
                cash_checks += 1
        close(world["final_net"], sum(x["cash"] for x in state.values()) - 2 * n)
        assert all(not x["q"] for x in state.values())
        if case["name"] == "one_leg_liquidation":
            assert "TRANSFER_BLOCKED_OUTAGE" in world["rows"][0]["actions"]
            assert F(world["rows"][0]["wallets"]["short"]["cash"]) < 0
    result = dict(scope="independent exact-arithmetic check, not an independent market reconstruction",
                  report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                  depth_equalities=depth_checks, cash_equalities=cash_checks, retained_unknowns=unknown)
    path = LANE / "results/check.json"
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if path.exists():
        assert path.read_text() == text
    else:
        path.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
