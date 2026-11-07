"""Fixed-quantity segregated CDE/Kraken proxy accounting, never certified cash or fills."""
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction as F


def number(value, *, positive=False):
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("explicit decimal inputs required")
    if isinstance(value, F):
        out = value
    else:
        try:
            d = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError("invalid decimal") from exc
        if not d.is_finite():
            raise ValueError("nonfinite decimal")
        out = F(d)
    if positive and out <= 0:
        raise ValueError("positive value required")
    return out


def text(value):
    with localcontext() as ctx:
        ctx.prec = 60
        return format(Decimal(value.numerator) / Decimal(value.denominator), ".12f")


def bar(row):
    out = {k: number(row[k], positive=True) for k in ("open", "high", "low", "close")}
    if not out["low"] <= min(out["open"], out["close"]) <= max(out["open"], out["close"]) <= out["high"]:
        raise ValueError("invalid OHLC envelope")
    return out


def friction(report, coin):
    """Worst already-measured fraction by venue/side, fixed5k initial leg only."""
    slips = {v: {s: F(0) for s in ("buy", "sell")} for v in ("cde", "kraken")}
    seen = set()
    for r in report["scenarios"]:
        if r["coin"] != coin or r["target_per_leg"] != "5000" or r["cost_multiple"] != 1:
            continue
        if not r["round_trip_complete"]:
            raise ValueError("incomplete parent cost scenario")
        key = (r["cde_size_unit"], r["phase"])
        if key in seen:
            raise ValueError("duplicate parent cost scenario")
        seen.add(key)
        for d in r["directions"]:
            for side, venue_index in (("buy", d["buyer"]), ("sell", d["seller"])):
                fill = d[side]
                if not fill["complete"] or number(fill["filled"]) != number(r["quantity"]):
                    raise ValueError("incomplete parent fill")
                cost, quote = number(fill["book_cost"]), number(fill["quote"], positive=True)
                mid_notional = quote - cost if side == "buy" else quote + cost
                if cost < 0 or mid_notional <= 0 or venue_index not in (0, 1):
                    raise ValueError("invalid parent price drag")
                venue = "cde" if venue_index == 0 else "kraken"
                slips[venue][side] = max(slips[venue][side], cost / mid_notional)
    if seen != {(unit, phase) for unit in ("contracts", "base") for phase in ("initial", "delayed")}:
        raise ValueError("parent unit/phase coverage missing")
    return slips


def fixed_quantity(capital, lot, cde_entry, kraken_entry, slips, fees):
    """One quantity at3x worst entry costs, common to directions and cost sensitivities."""
    wallet, lot = number(capital, positive=True) / 2, number(lot, positive=True)
    prices = {"cde": number(cde_entry, positive=True), "kraken": number(kraken_entry, positive=True)}
    if any(not 0 <= number(fees[v]) < F(1, 3) for v in ("cde", "kraken")) or number(fees["cde_per_contract"]) < 0:
        raise ValueError("invalid fee schedule")
    if any(not 0 <= x < F(1, 3) for row in slips.values() for x in row.values()):
        raise ValueError("invalid execution drag")
    needs = []
    for venue, price in prices.items():
        execution = price * (1 + 3 * max(slips[venue].values()))
        fixed = 3 * number(fees["cde_per_contract"]) if venue == "cde" else F(0)
        needs.append(lot * execution * (1 + 3 * number(fees[venue])) + fixed)
    contracts = wallet // max(needs)
    if contracts < 1:
        raise ValueError("insufficient fully-funded common lot")
    return contracts * lot


def replay(*, cde_bars, kraken_marks, cde_rates, kraken_rates, start, end,
           allowed_missing_cde_bars, capital, lot, slips, fees, multiple, direction):
    """Conditional price proxies only. Positive funding is unavailable until exit.

    direction+1 = short CDE/long Kraken. CDE funding cash at t uses its published
    rate at t; Kraken's absolute rate at t-1h covers that preceding hour.
    Last completed CDE trade-bar low/high is an ASSUMED cash-price envelope,
    not a proven bound on exchange funding marks. A gap never becomes a zero
    rate or an interpolated candle. At most one missing prior bar is admitted.
    """
    if direction not in (-1, 1) or multiple not in (1, 2, 3) or end <= start or (end - start) % 3600:
        raise ValueError("fixed direction/cost/hour window required")
    capital, lot = number(capital, positive=True), number(lot, positive=True)
    times = list(range(start + 3600, end + 1, 3600))
    expected = set(range(start - 3600, end + 1, 3600))
    actual_missing = expected - cde_bars.keys()
    if actual_missing != set(allowed_missing_cde_bars) or start not in cde_bars or end not in cde_bars:
        raise ValueError("CDE coverage differs from frozen missing-hour declaration")
    if any(t not in kraken_marks for t in range(start, end + 1, 3600)):
        raise ValueError("missing Kraken mark")
    if any(t not in cde_rates or t - 3600 not in kraken_rates for t in times):
        raise ValueError("missing funding: never fill zero")
    cb = {t: bar(cde_bars[t]) for t in sorted(expected & cde_bars.keys())}
    kb = {t: bar(kraken_marks[t]) for t in range(start, end + 1, 3600)}
    rates = {t: number(cde_rates[t]) for t in times}
    absolute = {t: number(kraken_rates[t]) for t in range(start, end, 3600)}
    reference_entry = {"cde": cb[start]["open"], "kraken": kb[start]["open"]}
    reference_exit = {"cde": cb[end]["open"], "kraken": kb[end]["open"]}
    q = fixed_quantity(capital, lot, reference_entry["cde"], reference_entry["kraken"], slips, fees)
    position = {"cde": -direction, "kraken": direction}
    entry, exit_price, entry_fee, exit_fee = {}, {}, {}, {}
    for venue, pos in position.items():
        entry_side, exit_side = ("buy", "sell") if pos > 0 else ("sell", "buy")
        entry[venue] = reference_entry[venue] * (1 + pos * multiple * slips[venue][entry_side])
        exit_price[venue] = reference_exit[venue] * (1 - pos * multiple * slips[venue][exit_side])
        if min(entry[venue], exit_price[venue]) <= 0:
            raise ValueError("nonpositive execution proxy")
        fixed = q / lot * number(fees["cde_per_contract"]) if venue == "cde" else F(0)
        entry_fee[venue] = multiple * (q * entry[venue] * number(fees[venue]) + fixed)
        exit_fee[venue] = multiple * (q * exit_price[venue] * number(fees[venue]) + fixed)
    funding = {v: {k: F(0) for k in ("low", "center", "high")} for v in position}
    unavailable_credits = {v: F(0) for v in position}
    negative_cash = {v: F(0) for v in position}
    minimum_wallet = {v: capital / 2 - entry_fee[v] + position[v] * q * (reference_entry[v] - entry[v]) for v in position}
    path, stale_references, comparisons = [], [], 0
    for t in times:
        candidates = [u for u in cb if u < t]
        src = max(candidates)
        if t - src not in (3600, 7200):
            raise ValueError("unqualified stale CDE trade proxy")
        if t - src == 7200:
            stale_references.append(dict(payment_time=t, prior_bar=src))
        ref = cb[src]
        cf = sorted((direction * q * rates[t] * ref["low"], direction * q * rates[t] * ref["high"]))
        flows = {"cde": dict(low=cf[0], center=direction * q * rates[t] * ref["close"], high=cf[1]),
                 "kraken": {k: -direction * q * absolute[t - 3600] for k in ("low", "center", "high")}}
        marks = {"cde": ref["close"], "kraken": kb[t]["open"]}
        spendable, proxy_equity = {}, {}
        for venue, pos in position.items():
            for key in funding[venue]:
                funding[venue][key] += flows[venue][key]
            negative_cash[venue] += min(F(0), flows[venue]["low"])
            unavailable_credits[venue] += max(F(0), flows[venue]["center"])
            mtm = pos * q * (marks[venue] - entry[venue])
            spendable[venue] = capital / 2 - entry_fee[venue] + mtm + negative_cash[venue]
            minimum_wallet[venue] = min(minimum_wallet[venue], spendable[venue])
            proxy_equity[venue] = capital / 2 - entry_fee[venue] + mtm + funding[venue]["center"]
            comparisons += 1
        point = dict(time=t, cde_reference_bar=src, **{v: text(spendable[v]) for v in position},
                     total_center_equity=text(sum(proxy_equity.values())))
        path.append(point)
        if min(spendable.values()) <= 0:
            return dict(state="CONDITIONAL_CAPITAL_DEFICIT", quantity=text(q), multiple=multiple,
                        direction=direction, stop=point, terminal_net=None, recovery_pnl_counted=False,
                        minimum_wallet={v: text(x) for v, x in minimum_wallet.items()}, path=path,
                        conditional_price_envelope=True, actual_margin_or_funding_cash_certified=False)
    trading = {v: position[v] * q * (exit_price[v] - entry[v]) for v in position}
    fee_total = sum(entry_fee.values()) + sum(exit_fee.values())
    net = {k: sum(trading.values()) + sum(funding[v][k] for v in position) - fee_total
           for k in ("low", "center", "high")}
    wallets = {v: capital / 2 + trading[v] + funding[v]["center"] - entry_fee[v] - exit_fee[v]
               for v in position}
    if sum(wallets.values()) - capital != net["center"]:
        raise AssertionError("separate-wallet terminal identity failed")
    gross_basis = sum(position[v] * q * (reference_exit[v] - reference_entry[v]) for v in position)
    slippage = gross_basis - sum(trading.values())
    if slippage < 0 or not net["low"] <= net["center"] <= net["high"]:
        raise AssertionError("invalid cost/envelope accounting")
    return dict(state="CONDITIONAL_PROXY_SCREEN", quantity=text(q), multiple=multiple, direction=direction,
                capital=text(capital), reference_entry={v: text(x) for v, x in reference_entry.items()},
                reference_exit={v: text(x) for v, x in reference_exit.items()},
                execution_entry={v: text(x) for v, x in entry.items()}, execution_exit={v: text(x) for v, x in exit_price.items()},
                entry_fee={v: text(x) for v, x in entry_fee.items()}, exit_fee={v: text(x) for v, x in exit_fee.items()},
                funding={v: {k: text(x) for k, x in row.items()} for v, row in funding.items()},
                gross_basis_pnl=text(gross_basis), execution_drag=text(slippage), fees=text(fee_total),
                terminal_net={k: text(x) for k, x in net.items()},
                net_pct_on_total_cash={k: text(100 * x / capital) for k, x in net.items()},
                terminal_wallets={v: text(x) for v, x in wallets.items()},
                minimum_wallet={v: text(x) for v, x in minimum_wallet.items()},
                withheld_positive_funding={v: text(x) for v, x in unavailable_credits.items()},
                hourly_wallet_checks=comparisons, stale_trade_proxy_references=stale_references, path=path,
                conditional_price_envelope=True, envelope_is_verified_mark_bound=False,
                actual_margin_or_funding_cash_certified=False, actual_fills=False,
                cost_source="Current CFSE/Kraken fees and R421 recorded5k-depth friction, hypothetical historically")
