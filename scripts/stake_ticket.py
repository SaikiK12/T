"""Order ticket for a small stake on the design-gap lanes: what the owner would place, venue by venue, after a forward
PASS. Paper only: nothing here can place an order, move money or read a key. It reads public books.

For each lane (R509 Kraken + Hyperliquid, R520 Deribit + Hyperliquid, R524 Bitfinex + Binance):
- **Positions:** the lane's open pairs (book A), replayed from its journal tickets. No forward result is read.
- **Size:** the stake is split equally across lanes (R527's weights). Each slot's leg notional is
  capital x leverage / (2 K), K = 20, as in the paper book.
- **R526's live entry filters**, checked on live books:
  - agree: the legs' mids agree within 2% once the contract multiplier (the nearest power of 10) is divided out;
  - depth: both books are two-sided and a market order of the leg notional fills, at a cost in bp of mid.
  A pair that fails is listed as SKIP with the reason.
- **Margin:** each lane's capital is split across its two venues so that both cross-margin accounts are the same move
  from liquidation, measured as the move against every leg at once (`worst_move`). `lab/margin.py`'s uniform move
  nets an account's long and short legs, which reads near-infinite for a mixed account. Rebalance below 30%, cut both legs pro rata if a
  transfer cannot restore 25% (`docs/reviews/stake_dhl_20261123.md`).

The header reads DRY RUN unless `--passed RID` names a read that has PASSED on its date. This tool never runs a read.

usage: python scripts/stake_ticket.py [--capital 2000] [--leverage 2.5] [--lanes R509,R520,R524] [--passed RID]
                                      [--offline] [--out PATH]
"""
import argparse
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import kraken  # noqa: E402

K = 20
AGREE = 0.02
MM = {"BTC": 0.0125, "ETH": 0.02}       # Hyperliquid's (half the initial margin at max leverage), as stress_dhl
MM_ALT = 0.05                           # 10x alts; assumed on every venue (check each venue's schedule before money)
REBALANCE_AT, RESTORE_TO, CUT_AT = 0.30, 0.35, 0.25


def lanes():
    """rid -> (lane, book functions), imported lazily: each import registers its venues."""
    from scripts import forward_xfund_bfx as r524
    from scripts import forward_xfund_dhl as r520
    from scripts import forward_xfund_eea as r509
    return {"R509": (r509.LANE, kraken.BOOKS), "R520": (r520.LANE, r520.BOOKS), "R524": (r524.LANE, r524.BOOKS)}


def open_pairs(tickets, book="A"):
    """[(coin, long venue, short venue)] still open after the tickets, in entry order."""
    held = {}
    for r in tickets:
        if r["book"] != book:
            continue
        if r["action"] == "enter":
            held[r["coin"]] = (r["coin"], r["long"], r["short"])
        elif r["action"] in ("exit", "drop"):
            held.pop(r["coin"], None)
    return list(held.values())


def agree(mid_long, mid_short, tol=AGREE):
    """(ok, |log ratio| after dividing out the nearest power of 10)."""
    if not (mid_long and mid_short and mid_long > 0 and mid_short > 0):
        return False, math.inf
    r = math.log10(mid_long / mid_short)
    x = abs((r - round(r)) * math.log(10))
    return x <= math.log1p(tol), x


def mm_of(coin):
    base = coin.upper().removesuffix("USDT")
    return MM.get(base, MM_ALT)


def worst_move(equity, legs):
    """The move against every leg at once (longs down, shorts up) that brings the account to its maintenance:
    (equity - sum |N| mm) / sum |N| (1 + mm). Conservative, and well posed for an account with legs in both
    directions, where `margin.liq_move`'s uniform move nets them and reads near-infinite. math.inf with no legs."""
    gross = sum(abs(n) for n, _ in legs)
    if gross == 0:
        return math.inf
    gmm = sum(abs(n) * m for n, m in legs)
    return max(0.0, (equity - gmm) / (gross + gmm))


def split(capital, legs_a, legs_b):
    """Equities (venue a, venue b) that equalise both accounts' worst moves; legs are [(signed notional, mm)]."""
    if not legs_a and not legs_b:
        return capital / 2, capital / 2
    if not legs_a:
        return 0.0, capital
    if not legs_b:
        return capital, 0.0
    lo, hi = 0.0, capital
    for _ in range(100):
        e = (lo + hi) / 2
        lo, hi = (e, hi) if worst_move(e, legs_a) < worst_move(capital - e, legs_b) else (lo, e)
    return e, capital - e


MIN_HL_USD = 10.0                        # Hyperliquid's minimum order value
HEDGE_TOL = 0.05                         # legs' notionals may differ by at most 5% after lot rounding


def _retail_first(sched):
    """The most conservative first-tier retail (initial, maintenance) across Kraken's margin entities, or None."""
    tiers = [lv[0] for ent in (sched or {}).values() for who, lv in (ent or {}).items() if who == "retail" and lv]
    return (max(x["initialMargin"] for x in tiers), max(x["maintenanceMargin"] for x in tiers)) if tiers else None


def specs(venue, offline=False):
    """{symbol: {"step", "min_qty", "min_usd", "im", "mm", "src"}} from the venue's public instrument list.
    Missing fields fall back to the assumptions above, marked in "src"."""
    if offline:
        return {}
    out = {}
    try:
        if venue == "kraken":
            for i in kraken._json(f"{kraken.BASE}/derivatives/api/v3/instruments").get("instruments", []):
                s = str(i.get("symbol", ""))
                if not s.startswith("PF_"):
                    continue
                r = _retail_first(i.get("marginSchedules"))
                step = 10.0 ** -int(i.get("contractValueTradePrecision") or 0)
                out[s] = {"step": step, "min_qty": step, "min_usd": 0.0, "im": r[0] if r else 2 * MM_ALT,
                          "mm": r[1] if r else MM_ALT, "src": "kraken retail schedule" if r else "assumed"}
        elif venue == "hyperliquid":
            for u in (kraken._json(kraken.HL, {"type": "meta"}) or {}).get("universe", []):
                step, lev = 10.0 ** -int(u.get("szDecimals", 0)), float(u.get("maxLeverage") or 10)
                out[u["name"]] = {"step": step, "min_qty": step, "min_usd": MIN_HL_USD, "im": 1 / lev, "mm": 0.5 / lev,
                                  "src": "hyperliquid meta (mm = half of 1/max leverage)"}
        elif venue == "deribit":
            from lab import deribit
            for i in deribit._get("get_instruments", currency="USDC", kind="future") or []:
                name = str(i.get("instrument_name", ""))
                if name.endswith("_USDC-PERPETUAL"):
                    step = float(i.get("min_trade_amount") or i.get("contract_size") or 1)
                    out[name.removesuffix("_USDC-PERPETUAL")] = {"step": step, "min_qty": step, "min_usd": 0.0,
                                                                  "im": 2 * MM_ALT, "mm": MM_ALT,
                                                                  "src": "deribit lot; margin assumed"}
        elif venue == "bitfinex":
            from scripts import fetch_bitfinex_history as fb
            for k_, v in (fb.get(f"{fb.API}/conf/pub:info:pair:futures") or [[]])[0]:
                if k_.endswith("F0:USTF0"):
                    out[k_[:-len("F0:USTF0")]] = {"step": 1e-8, "min_qty": float(v[3]), "min_usd": 0.0,
                                                  "im": max(2 * MM_ALT, float(v[8] or 0)),
                                                  "mm": max(MM_ALT, float(v[9] or 0)),
                                                  "src": "bitfinex minimum; margin floored at the assumption"}
        elif venue == "binance":
            from lab import live
            for s in (live.get("fapi/v1/exchangeInfo") or {}).get("symbols", []):
                f = {x["filterType"]: x for x in s.get("filters", [])}
                lot = f.get("MARKET_LOT_SIZE") or f.get("LOT_SIZE") or {}
                out[s["symbol"]] = {"step": float(lot.get("stepSize") or 1e-8), "min_qty": float(lot.get("minQty") or 0),
                                    "min_usd": float((f.get("MIN_NOTIONAL") or {}).get("notional") or 0),
                                    "im": 2 * MM_ALT, "mm": MM_ALT, "src": "binance lot; margin assumed"}
    except Exception as e:      # noqa: BLE001 - no specs means "not checked", never a guess presented as checked
        print(f"# {venue} specs failed: {type(e).__name__}", file=sys.stderr)
    return out


def lot(qty, spec):
    """qty rounded down to the venue's step; 0 below its minimum quantity."""
    if not spec or qty is None:
        return qty
    q = math.floor(qty / spec["step"] + 1e-9) * spec["step"]
    return q if q >= spec["min_qty"] - 1e-12 else 0.0


def ticket_lane(rid, lane, books, capital, leverage, offline=False, spec_by_venue=None):
    _, tk, _ = lane.journal()
    pairs = open_pairs(tk)
    table = lane.table().set_index("key")
    n = capital * leverage / (2 * K)
    venues = list(lane.venues)
    sp = spec_by_venue if spec_by_venue is not None else {v: specs(v, offline) for v in venues}
    rows, legs, im_need = [], {v: [] for v in venues}, {v: 0.0 for v in venues}
    for coin, lo, hi in pairs:
        row = {"lane": rid, "coin": coin, "long": lo, "short": hi, "notional": n, "status": "OK", "why": ""}
        quotes = {}
        for v, side in ((lo, "buy"), (hi, "sell")):
            sym = table.loc[coin, v]
            row[f"sym_{side}"] = sym
            if offline:
                quotes[v] = (None, None, None)
                continue
            try:
                bids, asks = books[v](sym)
            except Exception as e:      # noqa: BLE001 - a failed book is a SKIP, never a guess
                bids, asks = [], []
                row["why"] += f"{v} book failed ({type(e).__name__}); "
            quotes[v] = kraken.side_fill(bids, asks, side, n)
        if offline:
            row.update(status="NOT CHECKED", why="offline")
        else:
            (m_l, p_l, c_l), (m_s, p_s, c_s) = quotes[lo], quotes[hi]
            ok, x = agree(m_l, m_s)
            row.update(mid_long=m_l, mid_short=m_s, cost_bp_long=c_l, cost_bp_short=c_s, disagree_pct=100 * x,
                       qty_long=n / m_l if m_l else None, qty_short=n / m_s if m_s else None)
            if m_l is None or m_s is None:
                row["status"], row["why"] = "SKIP", row["why"] + "a book is not two-sided"
            elif p_l is None or p_s is None:
                row["status"], row["why"] = "SKIP", row["why"] + f"a book cannot fill ${n:,.0f}"
            elif not ok:
                row["status"], row["why"] = "SKIP", row["why"] + f"legs disagree by {100 * x:.2f}%"
            if row["status"] == "OK" and sp:
                s_l, s_s = sp.get(lo, {}).get(row["sym_buy"]), sp.get(hi, {}).get(row["sym_sell"])
                row["qty_long"], row["qty_short"] = lot(row["qty_long"], s_l), lot(row["qty_short"], s_s)
                u_l, u_s = row["qty_long"] * m_l, row["qty_short"] * m_s
                row.update(usd_long=u_l, usd_short=u_s)
                if (s_l is None) or (s_s is None):
                    row["why"] += "a lot rule was not found (quantities unrounded); "
                if min(u_l, u_s) <= 0 or u_l < (s_l or {}).get("min_usd", 0) or u_s < (s_s or {}).get("min_usd", 0):
                    row["status"], row["why"] = "SKIP", row["why"] + "below a venue's minimum order"
                elif abs(u_l - u_s) > HEDGE_TOL * n:
                    row["status"], row["why"] = "SKIP", row["why"] + f"lots leave the hedge {abs(u_l - u_s) / n:.0%} off"
        if row["status"] != "SKIP":
            for v, sgn, key in ((lo, 1, "sym_buy"), (hi, -1, "sym_sell")):
                s = (sp.get(v) or {}).get(row[key]) if sp else None
                mm = max(mm_of(coin), s["mm"]) if s else mm_of(coin)
                legs[v].append((sgn * n, mm))
                im_need[v] += n * (s["im"] if s else 2 * mm)
        rows.append(row)
    ea, eb = split(capital, legs[venues[0]], legs[venues[1]])
    a_need, b_need = im_need[venues[0]], im_need[venues[1]]
    if ea < a_need <= capital - b_need:          # the initial margin binds: fund it first
        ea, eb = a_need, capital - a_need
    elif eb < b_need <= capital - a_need:
        ea, eb = capital - b_need, b_need
    acct = {}
    for v, e in zip(venues, (ea, eb)):
        lm = worst_move(e, legs[v])
        acct[v] = {"equity": e, "legs": len(legs[v]), "gross": sum(abs(x) for x, _ in legs[v]), "liq_move": lm,
                   "initial_margin": im_need[v], "short_of_initial": e + 1e-9 < im_need[v]}
    return rows, acct


def fmt(x, f="{:.6g}"):
    return "" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f.format(x)


def render(out, capital, leverage, passed, offline):
    head = (f"# Stake ticket, {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n\n"
            + (f"**After the PASS of {passed}.** The owner places every order; nothing here is sent.\n"
               if passed else "**DRY RUN: no forward read has passed.** Do not place these orders.\n")
            + f"\n- Capital ${capital:,.0f} at leverage {leverage:g} (total notional / capital), split equally across "
            f"{len(out)} lane(s); K = {K} slots a lane.\n"
            f"- Entry filters (R526): legs agree within {100 * AGREE:g}% (multiplier divided out); both books "
            "two-sided and deep enough for the leg.\n"
            f"- Margin: each venue's public retail schedule where it publishes one (Kraken; Hyperliquid's max leverage), "
            f"else BTC 1.25%, ETH 2%, others {100 * MM_ALT:g}% maintenance and twice that initial (Deribit, Binance, "
            "Bitfinex floors). Quantities are rounded down to each venue's lot.\n"
            + ("- **Offline:** books were not read; no check was made.\n" if offline else ""))
    parts = [head]
    for rid, (rows, acct) in out.items():
        parts.append(f"\n## {rid}\n\n| Coin | Buy on | Symbol | Qty | Sell on | Symbol | Qty | $ a leg | Cost bp "
                     "(buy/sell) | Disagree | Status |\n|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            parts.append(f"| {r['coin']} | {r['long']} | {r['sym_buy']} | {fmt(r.get('qty_long'))} | {r['short']} | "
                         f"{r['sym_sell']} | {fmt(r.get('qty_short'))} | {r['notional']:,.0f} | "
                         f"{fmt(r.get('cost_bp_long'), '{:.1f}')}/{fmt(r.get('cost_bp_short'), '{:.1f}')} | "
                         f"{fmt(r.get('disagree_pct'), '{:.2f}%')} | {r['status']}"
                         f"{' (' + r['why'].strip('; ') + ')' if r['why'] else ''} |\n")
        if not rows:
            parts.append("| (no open pair) | | | | | | | | | | |\n")
        parts.append("\n| Venue | Deposit $ | Initial margin $ | Legs | Gross notional $ | Move to liquidation |\n"
                     "|---|---|---|---|---|---|\n")
        for v, a in acct.items():
            lm = "none" if not math.isfinite(a["liq_move"]) else f"{100 * a['liq_move']:.0f}%"
            warn = " **(short of initial margin: lower the leverage)**" if a.get("short_of_initial") else ""
            parts.append(f"| {v} | {a['equity']:,.0f}{warn} | {a.get('initial_margin', 0):,.0f} | {a['legs']} | "
                         f"{a['gross']:,.0f} | {lm} |\n")
    parts.append(f"\n## Every day\n- Rebalance when a venue's move to liquidation falls under {100 * REBALANCE_AT:.0f}%: "
                 f"transfer to bring both to {100 * RESTORE_TO:.0f}%.\n- If a transfer cannot restore "
                 f"{100 * CUT_AT:.0f}%, cut both legs pro rata.\n- Follow the lane's own tickets for exits and entries; "
                 "apply the two entry filters to every new entry.\n")
    return "".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=2000.0)
    ap.add_argument("--leverage", type=float, default=2.5)
    ap.add_argument("--lanes", default="R509,R520,R524")
    ap.add_argument("--passed", default="", help="the read that PASSED on its date (R510, R521, R523 or R527)")
    ap.add_argument("--offline", action="store_true", help="do not read books (format check only)")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    if a.leverage > 2.5:
        raise SystemExit("leverage above 2.5 is outside the stake rule (docs/reviews/stake_dhl_20261123.md)")
    reg = lanes()
    rids = [x.strip() for x in a.lanes.split(",") if x.strip()]
    out = {rid: ticket_lane(rid, *reg[rid], a.capital / len(rids), a.leverage, a.offline) for rid in rids}
    text = render(out, a.capital, a.leverage, a.passed, a.offline)
    if a.out:
        Path(a.out).write_text(text)
    print(text)
    return out


if __name__ == "__main__":
    main()
