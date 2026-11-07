"""Recorded Lighter maker/taker role qualification through signed base-position identities."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN


HYPOTHESES = ("true_is_maker_ask", "true_is_taker_ask")
QUANTIZATION_TOLERANCE_LOTS = Decimal("0.000001")


def _int(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("noninteger " + field)
    return value


def _lots(value, decimals):
    """Recover declared integer lots; the tolerance applies only to stored-float noise."""
    if isinstance(value, bool):
        raise ValueError("boolean position or quantity")
    try:
        scaled = Decimal(str(value)) * (10 ** decimals)
        if not scaled.is_finite():
            raise ValueError("nonfinite position or quantity")
        rounded = scaled.to_integral_value(rounding=ROUND_HALF_EVEN)
        if abs(scaled - rounded) > QUANTIZATION_TOLERANCE_LOTS:
            raise ValueError("position or quantity off declared lot grid")
        return int(rounded)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid position or quantity") from exc


def canonicalize(rows, decimals):
    """Validate every source row, retaining liquidation rows as continuity barriers."""
    if not isinstance(decimals, int) or isinstance(decimals, bool) or not 0 <= decimals <= 12:
        raise ValueError("invalid size precision")
    output = []
    for source in rows:
        row = {k: _int(source[k], k) for k in
               ("trade_id", "t", "T", "tx_us", "ask_acct", "bid_acct", "maker_ask", "liq")}
        if (any(row[k] < 0 for k in ("trade_id", "t", "T", "tx_us", "ask_acct", "bid_acct"))
                or row["maker_ask"] not in (0, 1) or row["liq"] not in (0, 1)):
            raise ValueError("missing or invalid identity/clock/boolean")
        if row["ask_acct"] == row["bid_acct"]:
            raise ValueError("self-trade cannot identify two account roles")
        row.update(qty_lots=_lots(source["sz"], decimals),
                   taker_before_lots=_lots(source["tpos"], decimals),
                   maker_before_lots=_lots(source["mpos"], decimals))
        if row["qty_lots"] <= 0:
            raise ValueError("nonpositive base quantity")
        output.append(row)
    output.sort(key=lambda x: (x["tx_us"], x["trade_id"]))
    ids = [x["trade_id"] for x in output]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate trade id")
    if any(b <= a for a, b in zip(ids, ids[1:])):
        raise ValueError("trade-id order conflicts with transaction-clock order")
    if any(b["T"] < a["T"] for a, b in zip(output, output[1:])):
        raise ValueError("source timestamp reverses under fixed ordering")
    return output


def evaluate(rows, decimals, *, min_transitions=8, min_accounts=2, min_side_transitions=2):
    """Test both named conventions once; no price field or financial outcome is consumed."""
    rows = canonicalize(rows, decimals)
    hypotheses = {}
    for hypothesis in HYPOTHESES:
        previous = {}
        transitions = []
        barriers = 0
        for row in rows:
            if row["liq"]:
                previous.clear()
                barriers += 1
                continue
            maker_is_ask = bool(row["maker_ask"]) == (hypothesis == "true_is_maker_ask")
            ask_before = row["maker_before_lots"] if maker_is_ask else row["taker_before_lots"]
            bid_before = row["taker_before_lots"] if maker_is_ask else row["maker_before_lots"]
            for side, before in (("ask", ask_before), ("bid", bid_before)):
                account = row[side + "_acct"]
                if account in previous:
                    old = previous[account]
                    expected = old["before_lots"] + old["delta_lots"]
                    transitions.append(dict(account=account, previous_trade_id=old["trade_id"],
                                            next_trade_id=row["trade_id"], previous_side=old["side"],
                                            next_side=side, previous_before_lots=old["before_lots"],
                                            previous_delta_lots=old["delta_lots"],
                                            next_before_lots=before, expected_next_before_lots=expected,
                                            residual_lots=before - expected, matches=before == expected))
                previous[account] = dict(trade_id=row["trade_id"], side=side, before_lots=before,
                                         delta_lots=(-1 if side == "ask" else 1) * row["qty_lots"])
        accounts = len({x["account"] for x in transitions})
        side_counts = {side: sum(x["previous_side"] == side for x in transitions) for side in ("ask", "bid")}
        matches = sum(x["matches"] for x in transitions)
        coverage = (len(transitions) >= min_transitions and accounts >= min_accounts
                    and min(side_counts.values()) >= min_side_transitions)
        verdict = ("INCONCLUSIVE_COVERAGE" if not coverage else
                   "SAMPLED_POSITION_CONSISTENT" if matches == len(transitions) else "POSITION_IDENTITY_MISMATCH")
        hypotheses[hypothesis] = dict(verdict=verdict, transitions=len(transitions), accounts=accounts,
                                      previous_side_counts=side_counts, exact_matches=matches,
                                      mismatches=len(transitions) - matches, liquidation_barriers=barriers,
                                      identities=transitions)
    passing = [name for name, x in hypotheses.items() if x["verdict"] == "SAMPLED_POSITION_CONSISTENT"]
    verdict = "INCONCLUSIVE_COVERAGE"
    if len(passing) == 2:
        verdict = "INCONCLUSIVE_NOT_DISCRIMINATING"
    elif len(passing) == 1:
        other = next(name for name in HYPOTHESES if name not in passing)
        verdict = ("SAMPLED_ROLE_CONTRACT_PASS" if hypotheses[other]["verdict"] == "POSITION_IDENTITY_MISMATCH"
                   else "INCONCLUSIVE_NOT_DISCRIMINATING")
    elif all(x["verdict"] != "INCONCLUSIVE_COVERAGE" for x in hypotheses.values()):
        verdict = "UNQUALIFIED_POSITION_CONTRACT"
    return dict(verdict=verdict, supported_hypothesis=passing[0] if verdict == "SAMPLED_ROLE_CONTRACT_PASS" else None,
                source_rows=len(rows), ordinary_rows=sum(not r["liq"] for r in rows), hypotheses=hypotheses,
                complete_feed_certified=False, historical_grid_certified=False,
                public_api_contract_globally_certified=False, actual_fills=False, pnl=None)
