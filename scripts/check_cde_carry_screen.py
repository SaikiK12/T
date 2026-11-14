"""Independent Decimal identities on R424 serialized accounts, not a second strategy run."""
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "experiments/cde_carry_screen_v1"


def check(report):
    comparisons, deficits = 0, 0
    quantity = {}
    tolerance = D("0.00000001")  # USD display-rounding only, fixed before measurement.
    with localcontext() as ctx:
        ctx.prec = 60
        for r in report["scenarios"]:
            key = r["coin"]
            if key in quantity and quantity[key] != r["quantity"]:
                raise AssertionError("changed quantity across costs/directions")
            quantity[key] = r["quantity"]
            if r["state"] == "CONDITIONAL_CAPITAL_DEFICIT":
                if r["terminal_net"] is not None or r["recovery_pnl_counted"]:
                    raise AssertionError("invented recovery after deficit")
                deficits += 1
                continue
            q, capital = D(r["quantity"]), D(r["capital"])
            pos = {"cde": -r["direction"], "kraken": r["direction"]}
            trading = sum(pos[v] * q * (D(r["execution_exit"][v]) - D(r["execution_entry"][v])) for v in pos)
            fees = sum(D(r[s][v]) for v in pos for s in ("entry_fee", "exit_fee"))
            for label in ("low", "center", "high"):
                funding = sum(D(r["funding"][v][label]) for v in pos)
                wanted = trading + funding - fees
                if abs(wanted - D(r["terminal_net"][label])) > tolerance:
                    raise AssertionError("execution/cash identity")
                if abs(100 * wanted / capital - D(r["net_pct_on_total_cash"][label])) > tolerance:
                    raise AssertionError("wrong total-capital denominator")
                comparisons += 2
            from_components = D(r["gross_basis_pnl"]) - D(r["execution_drag"]) - fees + sum(D(r["funding"][v]["center"]) for v in pos)
            from_wallets = sum(D(x) for x in r["terminal_wallets"].values()) - capital
            if max(abs(from_components - D(r["terminal_net"]["center"])), abs(from_wallets - D(r["terminal_net"]["center"]))) > tolerance:
                raise AssertionError("basis/wallet identity")
            comparisons += 2
    return dict(result="ACCOUNTING_PASS", decimal_identities=comparisons,
                stopped_capital_deficits=deficits, scenarios=len(report["scenarios"]),
                tolerance_usd=str(tolerance), display_precision=12,
                meaning="Arithmetic identities only; price proxies, funding cash and execution realism remain conditional")


if __name__ == "__main__":
    path = LANE / "results/report.json"
    result = check(json.loads(path.read_text()))
    result["report_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with (LANE / "results/independent_accounting.json").open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
