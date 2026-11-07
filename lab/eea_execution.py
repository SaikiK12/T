"""Conditional CDE/Kraken displayed-depth costs; never fills, funding or a return."""
from decimal import Decimal

from lab.carry_execution import Book, number, pair_sweep


def normalize(body, venue, cde_size_unit, contract_size):
    """Keep two unverified CDE size conventions explicit, without selecting one."""
    if venue not in ("cde", "kraken") or cde_size_unit not in ("contracts", "base"):
        raise ValueError("closed venue/unit scenario required")
    scale = number(contract_size, positive=True) if venue == "cde" and cde_size_unit == "contracts" else Decimal(1)
    raw = body["pricebook"] if venue == "cde" else body["orderBook"]
    out = {}
    for side in ("bids", "asks"):
        levels = {}
        for row in raw[side]:
            p, q = (row["price"], row["size"]) if venue == "cde" else row
            p, q = number(p, positive=True), number(q, nonnegative=True) * scale
            if q:
                levels[p] = levels.get(p, Decimal(0)) + q
        out[side] = tuple(sorted(levels.items(), reverse=side == "bids"))
    return Book(**out)


def execution_case(cde, kraken, *, target, contract_size, kraken_lot,
                   cde_notional_fee, cde_contract_fee, kraken_fee, multiple):
    """Target MID notional per leg; initial segregated cash is 2*target.

    A synthetic immediate round trip consumes each side once at its snapshot.
    Each direction's entry drag uses its own venue mid, so a basis difference
    is never booked as a profit. Partial fills keep unmatched inventory and
    block an all-in pair/round-trip cost. Cost multiples are scenarios.
    """
    lot = number(contract_size, positive=True)
    fixed = number(cde_contract_fee, nonnegative=True)
    kfee = number(kraken_fee, nonnegative=True)
    cfee = number(cde_notional_fee, nonnegative=True)
    if multiple not in (1, 2, 3) or isinstance(multiple, bool):
        raise ValueError("1x/2x/3x required")
    # Public CDE metadata requires whole native contracts. A convention that
    # implies fractional contracts cannot silently be rounded into liquidity.
    for side in (cde.bids, cde.asks):
        if any(q % lot for _, q in side):
            raise ValueError("CDE unit scenario implies fractional displayed contracts")
    result = pair_sweep(target, (cde, kraken), (lot, kraken_lot), (lot, kraken_lot),
                        (cfee, kfee), multiple=multiple)
    result.update(target_per_leg=number(target, positive=True),
                  initial_segregated_cash=2 * number(target, positive=True),
                  cost_multiple=multiple, actual_fills=False, pnl=None,
                  funding_cash=None, margin_admitted=False)
    for direction in result["directions"]:
        fixed_total = Decimal(0)
        for name, venue in (("buy", direction["buyer"]), ("sell", direction["seller"])):
            fill = direction[name]
            contracts = fill["filled"] / lot if venue == 0 else None
            if contracts is not None and contracts != contracts.to_integral_value():
                raise ValueError("partial CDE fill is not a whole contract")
            extra = contracts * fixed * multiple if venue == 0 else Decimal(0)
            fill.update(native_cde_contracts=contracts, fee_percent=fill["fee"],
                        fee_fixed=extra, fee=fill["fee"] + extra)
            fixed_total += extra
        direction["fee"] += fixed_total
        direction["complete_entry_cost"] = (direction["book_cost"] + direction["fee"]
                                              if direction["state"] == "SHOWN_DEPTH" else None)
    complete = bool(result["directions"]) and all(d["state"] == "SHOWN_DEPTH" for d in result["directions"])
    friction = sum((d["complete_entry_cost"] for d in result["directions"]), Decimal(0)) if complete else None
    result.update(round_trip_complete=complete, same_snapshot_round_trip_cost=friction,
                  round_trip_bps_on_initial_cash=(friction / result["initial_segregated_cash"] * 10000
                                                  if friction is not None else None),
                  round_trip_bps_on_max_mid_leg=(friction / (result["quantity"] * max(cde.mid, kraken.mid)) * 10000
                                                if friction is not None else None))
    return result
