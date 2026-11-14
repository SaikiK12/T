"""Independent Decimal cash/inventory and liquidation identities on R426 outputs."""
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "experiments/maker_pilot_v1"


def check(report):
    comparisons = 0
    tol = D("0.00000001")
    for r in report["cases"]:
        if "fills" not in r:
            if r["pnl"] is not None:
                raise AssertionError("unknown source became profit")
            continue
        cash = sum((-D(f["side"]) * D(f["quantity"]) * D(f["price"]) for f in r["fills"]), D(0))
        qty = sum((D(f["side"]) * D(f["quantity"]) for f in r["fills"]), D(0))
        fees = sum((D(f["maker_fee"]) for f in r["fills"]), D(0))
        if max(abs(cash - D(r["quote_currency_cashflow"])), abs(qty - D(r["terminal_inventory"])), abs(fees - D(r["maker_fees"]))) > tol:
            raise AssertionError("signed cash/inventory/fee identity")
        comparisons += 3
        if r["pnl"] is not None:
            want = D(r["mid_mark_before_funding"]) - D(r["terminal_exit_drag"]) - D(r["terminal_taker_fee"])
            if abs(want - D(r["pnl"])) > tol:
                raise AssertionError("liquidation cost identity")
            comparisons += 1
        if "stop" in r and (r["pnl"] is not None or r["recovery_counted"]):
            raise AssertionError("resurrection after stop")
    return dict(result="ACCOUNTING_PASS", decimal_identities=comparisons,
                display_tolerance_quote_currency=str(tol), actual_fills_or_funding_cash_certified=False)


if __name__ == "__main__":
    path = LANE / "results/report.json"
    result = check(json.loads(path.read_text()))
    result["report_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with (LANE / "results/independent_accounting.json").open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
