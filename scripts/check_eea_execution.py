"""Independent Fraction check of R421; does not import either execution kernel."""
from fractions import Fraction as F
import gzip
import hashlib
import json
from math import lcm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "experiments/eea_execution_v1"


def read(path):
    return json.loads(path.read_text(), parse_float=str)


def main():
    sha = hashlib.sha256((LANE / "PREREG.md").read_bytes()).hexdigest()
    if (LANE / "PREREG.sha256").read_text().strip() != sha:
        raise ValueError("preregistration changed")
    for p, wanted in read(LANE / "inputs.json")["sha256"].items():
        if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != wanted:
            raise ValueError("frozen input changed")
    report_path = LANE / "results/report.json"
    report, cfg = read(report_path), read(LANE / "cases.json")
    if report["prereg_sha256"] != sha or len(report["scenarios"]) != 144:
        raise ValueError("report freeze/cardinality mismatch")
    source = LANE / "source/packets/20261107T04"
    bodies = {p.name.removesuffix(".body.gz"): json.loads(gzip.decompress(p.read_bytes()), parse_float=str)
              for p in source.glob("*.body.gz")}
    equalities = 0

    def equal(actual, expected):
        nonlocal equalities
        if actual is None or abs(F(actual) - expected) > F(1, 10**12):
            raise ValueError("independent rational cost mismatch")
        equalities += 1

    def book(body, venue, unit, lot):
        raw = body["pricebook"] if venue == 0 else body["orderBook"]
        out = {}
        for side in ("bids", "asks"):
            merged = {}
            for x in raw[side]:
                price, qty = (x["price"], x["size"]) if venue == 0 else x
                p, q = F(price), F(qty) * (lot if venue == 0 and unit == "contracts" else 1)
                if p <= 0 or q < 0:
                    raise ValueError("bad reference book")
                if q:
                    merged[p] = merged.get(p, F(0)) + q
            out[side] = sorted(merged.items(), reverse=side == "bids")
        if not out["bids"] or not out["asks"] or out["bids"][0][0] >= out["asks"][0][0]:
            return None
        out["mid"] = (out["bids"][0][0] + out["asks"][0][0]) / 2
        return out

    for row in report["scenarios"]:
        coin, unit, phase, n, m = (row[k] for k in ("coin", "cde_size_unit", "phase", "target_per_leg", "cost_multiple"))
        n = F(n)
        spec = cfg["instruments"][coin]
        c_lot = F(spec["contract_size"])
        instrument = next(x for x in bodies["kraken_metadata"]["instruments"] if x["symbol"] == spec["kraken"])
        k_lot = F(1, 10 ** instrument["contractValueTradePrecision"])
        suffix = "_delayed" if phase == "delayed" else ""
        try:
            books = [book(bodies[coin + "_cde_book" + suffix], 0, unit, c_lot),
                     book(bodies[coin + "_kraken_book" + suffix], 1, unit, c_lot)]
        except ValueError:
            books = [None, None]
        if any(b is None for b in books):
            if row["state"] != "UNQUALIFIED_SOURCE":
                raise ValueError("empty/crossed book not rejected")
            equalities += 1
            continue
        if any(q % c_lot for side in ("bids", "asks") for _, q in books[0][side]):
            if row["state"] != "UNQUALIFIED_UNIT":
                raise ValueError("fractional CDE contract not rejected")
            equalities += 1
            continue
        denominator = lcm(c_lot.denominator, k_lot.denominator)
        step = F(lcm(c_lot.numerator * (denominator // c_lot.denominator),
                     k_lot.numerator * (denominator // k_lot.denominator)), denominator)
        mid = max(b["mid"] for b in books)
        q = (n / (mid * step)).__floor__() * step
        equal(row["quantity"], q)
        equal(row["common_lot"], step)
        equal(row["initial_segregated_cash"], 2 * n)
        if not q or q < max(c_lot, k_lot):
            if row["state"] != "BLOCKED_MINIMUM" or row["same_snapshot_round_trip_cost"] is not None:
                raise ValueError("minimum-order mismatch")
            continue
        costs, complete = [], True
        for actual in row["directions"]:
            fills = []
            for name, venue in (("buy", actual["buyer"]), ("sell", actual["seller"])):
                b, left, quote = books[venue], q, F(0)
                for p, available in b["asks"] if name == "buy" else b["bids"]:
                    take = min(left, available)
                    quote += take * (b["mid"] + m * (p - b["mid"]))
                    left -= take
                    if not left:
                        break
                filled = q - left
                drag = quote - filled * b["mid"] if name == "buy" else filled * b["mid"] - quote
                rate = F(cfg["fees"]["cde_notional_fee" if venue == 0 else "kraken_fee"])
                fixed = filled / c_lot * F(cfg["fees"]["cde_contract_fee"]) * m if venue == 0 else F(0)
                fee = quote * rate * m + fixed
                fill = actual[name]
                for k, v in (("filled", filled), ("quote", quote), ("book_cost", drag),
                             ("fee_percent", quote * rate * m), ("fee_fixed", fixed), ("fee", fee)):
                    equal(fill[k], v)
                fills.append((filled, drag, fee))
                complete &= filled == q
            equal(actual["unmatched_base"], fills[0][0] - fills[1][0])
            equal(actual["book_cost"], sum(x[1] for x in fills))
            equal(actual["fee"], sum(x[2] for x in fills))
            if all(x[0] == q for x in fills):
                cost = sum(x[1] + x[2] for x in fills)
                equal(actual["complete_entry_cost"], cost)
                costs.append(cost)
            elif actual["complete_entry_cost"] is not None:
                raise ValueError("partial pair given a complete cost")
        if bool(row["round_trip_complete"]) != complete:
            raise ValueError("round-trip completeness mismatch")
        if complete:
            cost = sum(costs)
            equal(row["same_snapshot_round_trip_cost"], cost)
            equal(row["round_trip_bps_on_initial_cash"], cost / (2 * n) * 10000)
            equal(row["round_trip_bps_on_max_mid_leg"], cost / (q * mid) * 10000)
        elif row["same_snapshot_round_trip_cost"] is not None:
            raise ValueError("absent depth extrapolated into a round trip")
    check = dict(round="R421", verdict="ACCOUNTING_PASS", equalities=equalities,
                 checker="independent Fraction sweeps and contract fees; no implementation imports",
                 report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(), tolerance_usd="1e-12",
                 financial_return_admitted=False)
    with (LANE / "results/check.json").open("x") as f:
        f.write(json.dumps(check, indent=2) + "\n")
    print(json.dumps(check))


if __name__ == "__main__":
    main()
