"""R427 independent Fraction/account-history check of the unchanged one-run role report."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_lighter_trade_contract import COLUMNS, LANE, verify  # noqa: E402


def lot_integer(value, precision):
    if isinstance(value, bool):
        raise ValueError("boolean quantity")
    number = Fraction(str(value)) * 10 ** precision
    nearest = round(number)
    if abs(number - nearest) > Fraction(1, 1_000_000):
        raise ValueError("unqualified fractional lot")
    return nearest


def identities(rows, precision, hypothesis):
    """Build each account's full occurrence list, then difference adjacent states."""
    accounts = {}
    segment = 0
    ordered = sorted(rows, key=lambda x: (x["tx_us"], x["trade_id"]))
    for row in ordered:
        if row["liq"]:
            segment += 1
            continue
        quantity = lot_integer(row["sz"], precision)
        side_for_maker = "ask" if row["maker_ask"] == (hypothesis == "true_is_maker_ask") else "bid"
        for side, sign in (("ask", -1), ("bid", 1)):
            before = lot_integer(row["mpos"] if side == side_for_maker else row["tpos"], precision)
            account = row[side + "_acct"]
            accounts.setdefault((segment, account), []).append((row["trade_id"], before, sign * quantity, side))
    output = []
    for (_, account), history in accounts.items():
        for old, new in zip(history, history[1:]):
            expected = old[1] + old[2]
            output.append(dict(account=account, previous_trade_id=old[0], next_trade_id=new[0],
                               previous_side=old[3], next_side=new[3], previous_before_lots=old[1],
                               previous_delta_lots=old[2], next_before_lots=new[1],
                               expected_next_before_lots=expected, residual_lots=new[1] - expected,
                               matches=new[1] == expected))
    return sorted(output, key=lambda x: (x["next_trade_id"], x["next_side"]))


def main():
    frozen = verify()
    import pyarrow.parquet as pq
    report_path = LANE / "results/report.json"
    report = json.loads(report_path.read_text())
    cfg = json.loads((LANE / "cases.json").read_text())
    checked = 0
    for market, case in cfg["markets"].items():
        rows = pq.read_table(ROOT / case["file"], columns=COLUMNS).to_pylist()
        assert len(rows) == case["expected_rows"]
        native = report["markets"][market]
        for hypothesis in ("true_is_maker_ask", "true_is_taker_ask"):
            expected = identities(rows, case["size_decimals"], hypothesis)
            actual = native["hypotheses"][hypothesis]
            assert expected == sorted(actual["identities"], key=lambda x: (x["next_trade_id"], x["next_side"])), market
            assert len(expected) == actual["transitions"]
            assert sum(x["matches"] for x in expected) == actual["exact_matches"]
            assert len({x["account"] for x in expected}) == actual["accounts"]
            counts = {s: sum(x["previous_side"] == s for x in expected) for s in ("ask", "bid")}
            assert counts == actual["previous_side_counts"]
            coverage = (len(expected) >= cfg["coverage"]["min_transitions"]
                        and actual["accounts"] >= cfg["coverage"]["min_accounts"]
                        and min(counts.values()) >= cfg["coverage"]["min_side_transitions"])
            verdict = ("INCONCLUSIVE_COVERAGE" if not coverage else "SAMPLED_POSITION_CONSISTENT"
                       if all(x["matches"] for x in expected) else "POSITION_IDENTITY_MISMATCH")
            assert actual["verdict"] == verdict
            checked += len(expected)
    verify()
    result = dict(round="R427", prereg_sha256=frozen, independent_arithmetic="Fraction/integer lots",
                  report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                  markets=len(cfg["markets"]), hypotheses_per_market=2,
                  checked_transition_identities=checked, all_checks_passed=True,
                  source_convention_pass_is_not_profit=True, costs={"1x": "N/A", "2x": "N/A", "3x": "N/A"})
    with (LANE / "results/independent_accounting.json").open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
