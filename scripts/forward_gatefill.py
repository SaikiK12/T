"""gatefill_fwd (R498): forward paper measurement of a resting order on Gate's wide leg of R390's C14 carry book, hedged
on Binance, against crossing both legs at once (M546, lever 2 of research/intake/fee_map_20261116.md).

R497 found that a resting order at Gate's touch costs at most half of a taker if every trade at the touch fills it.
This lane measures what R497 assumed: the queue ahead at placement, fills only by trade-through or by volume beyond that
queue, the time to fill, and the chase when the price leaves.

Each tick (every 2 hours on GitHub Actions):
1. **Settle** paper orders placed at least 70 minutes earlier, from Gate's public trade tape and Binance's public
   aggTrades (both readable after the fact).
2. **Place** new paper orders on the Gate contract of every position R390's book A holds now. For each contract: a bid
   and an ask, of $1k and $5k:
   - at the touch, behind the displayed size at that price;
   - one tick inside the spread, first in its queue, when the spread is at least 2 ticks.
   Only the book at placement has to be read live. It is recorded in the journal before any trade after it is read.

Paper only: public endpoints, no key, no account, no order. The journal is append-only.

    python scripts/forward_gatefill.py          # one tick (verifies the frozen PREREG first)
"""
import argparse
import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_gatemaker as gm  # noqa: E402  (R497's frozen tape pager, mid proxy and HTTP client)

LANE = ROOT / "experiments" / "gatefill_fwd"
JOURNAL = LANE / "journal"
TICKETS = ROOT / "experiments" / "xfund_bg_fwd" / "journal" / "tickets.csv"
SYMBOLS = ROOT / "experiments" / "xfund_v1" / "symbols.csv"
GATE = gm.GATE
BN = "https://www.binance.com/fapi/v1"

SIZES = (1_000, 5_000)
HORIZONS_S = (900, 3600)              # 15 min reported, 60 min decides
PRIMARY_USD, PRIMARY_H = 5_000, 3600
HEDGE_LAG_S = 5                       # the Binance hedge is taken 5 s after each Gate fill
SETTLE_AFTER_S = 3600 + gm.MARGIN_S + 300
GATE_TAKER_FEE_BP = 7.5               # Gate's listed taker fee (contract field), as in R497
BN_TAKER_FEE_BP = 5.0                 # Binance base taker fee
MAKER_FEE_BP = 2.0                    # decided; 4 bp and the contract's listed rate are reported beside
MAKER_FEE_HIGH_BP = 4.0
GATE_DEPTH, BN_DEPTH = 100, 100
BN_PAGE, BN_MAX_PAGES, BN_PACE_S = 1000, 40, 0.6
END = datetime(2026, 12, 1, tzinfo=timezone.utc)      # no order is placed at or after END
GIVE_UP_S = 5 * 86400                 # an order still unsettled 5 days after placement is closed as invalid
MIN_ORDERS, MIN_DAYS, MIN_T = 300, 10, 2.0

ORDER_FIELDS = ["id", "tick", "t0", "coin", "contract", "bsym", "r390_gate_side", "side", "usd", "placement",
                "primary", "price", "tick_size", "spread_ticks", "queue_ahead", "qty", "quanto", "mid_g0", "mid_b0",
                "gate_taker_bp", "bn_taker_bp", "maker_fee_listed_bp"]
SETTLED_FIELDS = ["id", "horizon_s", "settled_at", "valid", "reason", "fill_frac", "first_fill_s", "full_fill_s",
                  "through", "gate_part_bp", "hedge_part_bp", "chase_part_bp", "maker_pair_bp", "maker_pair_high_bp",
                  "maker_pair_listed_bp", "taker_pair_bp", "saving_bp", "saving_high_bp", "saving_listed_bp"]


def log(msg):
    print(f"{datetime.now(timezone.utc):%H:%M:%S} {msg}", flush=True)


# ---------------------------------------------------------------------------------------------------------------- inputs
def open_book(rows, book="A"):
    """R390's open positions from its tickets journal: {binance symbol: +1 if Gate is the long leg, -1 if short}."""
    held = {}
    for r in rows:
        if r["book"] != book:
            continue
        if r["action"] in ("enter", "inherit"):
            held[r["coin"]] = 1 if r["long"] == "gate" else -1 if r["short"] == "gate" else 0
        elif r["action"] in ("exit", "drop"):
            held.pop(r["coin"], None)
    return {k: v for k, v in held.items() if v}


def symbol_map(rows):
    """Binance symbol -> Gate contract, from experiments/xfund_v1/symbols.csv."""
    return {r["binance"]: r["gate"] for r in rows if r.get("binance") and r.get("gate")}


def walk_bp(levels, usd, mid):
    """bp between mid and the average fill of a market order of `usd` notional through levels [(price, base)], best
    first; NaN when the shown book is too thin."""
    left, paid, qty = float(usd), 0.0, 0.0
    for p, q in levels:
        take = min(left, p * q)
        paid += take
        qty += take / p
        left -= take
        if left <= 1e-9:
            return abs(paid / qty / mid - 1) * 1e4
    return float("nan")


# ------------------------------------------------------------------------------------------------------------- placement
def place(tick, coin, contract, bsym, r390_side, gbook, gcon, bbook):
    """Paper orders for one contract at the Gate book's server time; [] when either book is empty or crossed."""
    quanto = float(gcon["quanto_multiplier"])
    tick_size = float(gcon["order_price_round"])
    gb = [(float(x["p"]), float(x["s"]) * quanto) for x in gbook.get("bids") or []]
    ga = [(float(x["p"]), float(x["s"]) * quanto) for x in gbook.get("asks") or []]
    bb = [(float(p), float(q)) for p, q in bbook.get("bids") or []]
    ba = [(float(p), float(q)) for p, q in bbook.get("asks") or []]
    if not gb or not ga or not bb or not ba or ga[0][0] <= gb[0][0] or ba[0][0] <= bb[0][0]:
        return []
    t0 = float(gbook["current"])
    mid_g0, mid_b0 = (gb[0][0] + ga[0][0]) / 2, (bb[0][0] + ba[0][0]) / 2
    spread_ticks = int(round((ga[0][0] - gb[0][0]) / tick_size))
    listed = float(gcon.get("maker_fee_rate") or 0) * 1e4
    rows = []
    for side in (1, -1):                       # +1: a resting bid (Gate buy, Binance sell hedge); -1: a resting ask
        best, best_base = (gb[0] if side > 0 else ga[0])
        gate_walk_levels = ga if side > 0 else gb
        bn_walk_levels = bb if side > 0 else ba
        for usd in SIZES:
            g_taker = walk_bp(gate_walk_levels, usd, mid_g0)
            b_taker = walk_bp(bn_walk_levels, usd, mid_b0)
            choices = [("touch", best, best_base / quanto)]
            if spread_ticks >= 2:
                choices.append(("inside", best + side * tick_size, 0.0))
            for placement, price, queue in choices:
                primary = placement == "inside" or spread_ticks < 2
                rows.append({
                    "id": f"{tick}|{contract}|{side:+d}|{usd}|{placement}", "tick": tick, "t0": round(t0, 3),
                    "coin": coin, "contract": contract, "bsym": bsym, "r390_gate_side": r390_side, "side": side,
                    "usd": usd, "placement": placement, "primary": primary, "price": price, "tick_size": tick_size,
                    "spread_ticks": spread_ticks, "queue_ahead": queue, "qty": usd / (quanto * price),
                    "quanto": quanto, "mid_g0": mid_g0, "mid_b0": mid_b0,
                    "gate_taker_bp": round(g_taker, 4) if g_taker == g_taker else "",
                    "bn_taker_bp": round(b_taker, 4) if b_taker == b_taker else "",
                    "maker_fee_listed_bp": listed})
    return rows


# ------------------------------------------------------------------------------------------------------------ settlement
def fills(tape, t0, side, price, queue, qty, horizon, tick_size):
    """Fills [(time, contracts)] of a resting order over (t0, t0 + horizon] from Gate's tape (size > 0: taker buy).

    A resting bid (side +1) is reached by taker sells: at its price they consume the queue displayed ahead of it at
    placement first, then fill it; any taker sell below its price means the level was emptied, so the rest fills at
    once. Asks mirror this. Cancellations ahead are not credited (a slower fill than reality), and orders that join
    the level after placement are behind it."""
    eps = tick_size / 2
    x = tape[(tape.t > t0) & (tape.t <= t0 + horizon)].sort_values(["t", "id"])
    x = x[(x["size"] < 0) if side > 0 else (x["size"] > 0)]
    out, ahead, left = [], float(queue), float(qty)
    for t, sz, p in zip(x.t.to_numpy(), x["size"].to_numpy(), x.price.to_numpy()):
        through = (p < price - eps) if side > 0 else (p > price + eps)
        at_level = abs(p - price) <= eps
        if through:
            out.append((float(t), left, True))
            return out
        if not at_level:
            continue
        v = abs(float(sz))
        use = min(ahead, v)
        ahead -= use
        v -= use
        if v > 0:
            q = min(left, v)
            out.append((float(t), q, False))
            left -= q
            if left <= 1e-12:
                return out
    return out


def bn_tape(get, sym, lo, hi, pace=BN_PACE_S, sleep=time.sleep, max_pages=BN_MAX_PAGES):
    """Binance aggTrades with lo <= time <= hi (seconds) as a frame (t, d, p), d = +1 for a taker buy; and whether the
    pages reached hi. It reads a time window to find the first trade, then pages forward by trade id."""
    lo_ms, hi_ms = int(lo * 1000), int(hi * 1000)
    rows, pages, w0, nxt, complete = [], 0, lo_ms, None, False
    while pages < max_pages:
        if nxt is None:
            if w0 > hi_ms:
                complete = True
                break
            w1 = min(w0 + 3_599_999, hi_ms)
            url = f"{BN}/aggTrades?symbol={sym}&startTime={w0}&endTime={w1}&limit={BN_PAGE}"
        else:
            url = f"{BN}/aggTrades?symbol={sym}&fromId={nxt}&limit={BN_PAGE}"
        sleep(pace)
        batch = get(url)
        pages += 1
        if not batch:
            if nxt is None:
                w0 = w1 + 1
                continue
            complete = True                      # paged past the newest trade
            break
        rows += [x for x in batch if lo_ms <= int(x["T"]) <= hi_ms]
        if int(batch[-1]["T"]) >= hi_ms or (nxt is not None and len(batch) < BN_PAGE):
            complete = True
            break
        nxt = int(batch[-1]["a"]) + 1
    f = pd.DataFrame({"t": [int(x["T"]) / 1000 for x in rows], "d": [-1 if x["m"] else 1 for x in rows],
                      "p": [float(x["p"]) for x in rows]})
    return f.sort_values("t", kind="stable").reset_index(drop=True), complete


def mid_fn(t, d, p):
    """R497's two-sided mid proxy over a sorted tape: the mean of the last taker-buy and last taker-sell prices at or
    before each query time, each at most 300 s old; NaN otherwise."""
    return gm.mid_series(np.asarray(t, float), np.asarray(d, float), np.asarray(p, float))


def settle_order(o, gtape, gate_mid, bn_mid, horizon, gate_complete, bn_complete, now):
    """One settled row for order `o` (a dict of journal fields with numbers parsed) at `horizon` seconds."""
    row = {"id": o["id"], "horizon_s": horizon, "settled_at": now, "valid": True, "reason": ""}
    for k in SETTLED_FIELDS[5:]:
        row[k] = ""
    bad = []
    if not gate_complete:
        bad.append("gate_tape_incomplete")
    if not bn_complete:
        bad.append("bn_tape_incomplete")
    if not (o["gate_taker_bp"] == o["gate_taker_bp"]) or not (o["bn_taker_bp"] == o["bn_taker_bp"]):
        bad.append("book_too_thin")
    side, t0, qty = o["side"], o["t0"], o["qty"]
    fl = fills(gtape, t0, side, o["price"], o["queue_ahead"], qty, horizon, o["tick_size"])
    w = [q / qty for _, q, _ in fl]
    filled = min(sum(w), 1.0)
    gate_part = sum(wi * side * (o["price"] - o["mid_g0"]) / o["mid_g0"] * 1e4 for wi in w)
    hedge_mids = bn_mid([t + HEDGE_LAG_S for t, _, _ in fl]) if fl else np.array([])
    hedge_part = sum(wi * side * (o["mid_b0"] - m) / o["mid_b0"] * 1e4 for wi, m in zip(w, hedge_mids))
    chase = 1.0 - filled
    chase_part = 0.0
    if chase > 1e-9:
        mg = float(gate_mid([t0 + horizon])[0])
        mb = float(bn_mid([t0 + horizon + HEDGE_LAG_S])[0])
        if mg != mg or mb != mb:
            bad.append("chase_mid_missing")
        chase_part = chase * (side * (mg - o["mid_g0"]) / o["mid_g0"] * 1e4 + o["gate_taker_bp"] + GATE_TAKER_FEE_BP
                              + side * (o["mid_b0"] - mb) / o["mid_b0"] * 1e4)
    if len(hedge_mids) and np.isnan(hedge_mids).any():
        bad.append("hedge_mid_missing")
    taker = o["gate_taker_bp"] + GATE_TAKER_FEE_BP + o["bn_taker_bp"] + BN_TAKER_FEE_BP
    base = gate_part + hedge_part + chase_part + o["bn_taker_bp"] + BN_TAKER_FEE_BP
    maker = {k: base + filled * fee for k, fee in
             (("maker_pair_bp", MAKER_FEE_BP), ("maker_pair_high_bp", MAKER_FEE_HIGH_BP),
              ("maker_pair_listed_bp", o["maker_fee_listed_bp"]))}
    row.update({"fill_frac": round(filled, 6),
                "first_fill_s": round(fl[0][0] - t0, 3) if fl else "",
                "full_fill_s": round(fl[-1][0] - t0, 3) if fl and filled >= 1 - 1e-9 else "",
                "through": any(th for _, _, th in fl),
                "gate_part_bp": round(gate_part, 4), "hedge_part_bp": round(hedge_part, 4),
                "chase_part_bp": round(chase_part, 4), "taker_pair_bp": round(taker, 4),
                **{k: round(v, 4) for k, v in maker.items()},
                "saving_bp": round(taker - maker["maker_pair_bp"], 4),
                "saving_high_bp": round(taker - maker["maker_pair_high_bp"], 4),
                "saving_listed_bp": round(taker - maker["maker_pair_listed_bp"], 4)})
    if bad:
        row["valid"], row["reason"] = False, ";".join(sorted(set(bad)))
    return row


def parse_order(r):
    o = dict(r)
    for k in ("t0", "price", "tick_size", "queue_ahead", "qty", "quanto", "mid_g0", "mid_b0", "maker_fee_listed_bp"):
        o[k] = float(r[k])
    for k in ("gate_taker_bp", "bn_taker_bp"):
        o[k] = float(r[k]) if r[k] not in ("", None) else float("nan")
    o["side"], o["usd"] = int(r["side"]), int(r["usd"])
    return o


def settle_group(get, orders, now, sleep=time.sleep):
    """Settled rows for orders of one contract placed at one t0: one Gate tape and one Binance tape serve them all."""
    o0 = orders[0]
    t0 = o0["t0"]
    start = datetime.fromtimestamp(t0, timezone.utc)
    tape, covered_from, _ = gm.fetch_window(get, o0["contract"], start, sleep=sleep)
    gate_complete = covered_from <= t0
    gmid = mid_fn(tape.t.to_numpy(), np.sign(tape["size"].to_numpy()), tape.price.to_numpy()) if len(tape) else \
        (lambda at: np.full(len(at), np.nan))
    btape, bn_complete = bn_tape(get, o0["bsym"], t0 - gm.MID_LOOKBACK_S, t0 + max(HORIZONS_S) + HEDGE_LAG_S + 1,
                                 sleep=sleep)
    bmid = mid_fn(btape.t, btape.d, btape.p) if len(btape) else (lambda at: np.full(len(at), np.nan))
    return [settle_order(o, tape, gmid, bmid, h, gate_complete, bn_complete, now) for o in orders for h in HORIZONS_S]


# --------------------------------------------------------------------------------------------------------------- verdict
def decide(orders, settled, now=None):
    """The frozen reading over valid settled $5k primary orders at 60 min, placed before END."""
    o = pd.DataFrame(orders)
    s = pd.DataFrame(settled)
    out = {"verdict": "INSUFFICIENT_DATA", "n": 0, "days": 0}
    if o.empty or s.empty:
        return out
    o = o.assign(t0=o.t0.astype(float), usd=o.usd.astype(int), primary=o.primary.astype(str) == "True")
    s = s.assign(horizon_s=s.horizon_s.astype(int), valid=s.valid.astype(str) == "True")
    x = s[(s.horizon_s == PRIMARY_H) & s.valid].merge(o, on="id")
    x = x[(x.usd == PRIMARY_USD) & x.primary & (x.t0 < END.timestamp())]
    pending = set(o[o.t0 < END.timestamp()].id) - set(s.id)
    out["pending_before_end"] = len(pending)
    out["final"] = bool(now is not None and now >= END.timestamp() and not pending)
    if x.empty:
        return out
    v = x.saving_bp.astype(float).to_numpy()
    days = pd.to_datetime(x.t0, unit="s", utc=True).dt.date.nunique()
    mean, med = float(v.mean()), float(np.median(v))
    g = x.tick.to_numpy()
    resid = pd.Series(v - mean).groupby(g).sum().to_numpy()
    G, n = len(resid), len(v)
    se = math.sqrt((resid ** 2).sum()) / n * math.sqrt(G / (G - 1)) if G > 1 else float("nan")
    t = mean / se if se and se == se and se > 0 else float("nan")
    tot = x.assign(v=v).groupby("contract").v.sum().sort_values(ascending=False)
    keep = ~x.contract.isin(tot.index[:2])
    l2co = float(v[keep.to_numpy()].mean()) if keep.any() else float("nan")
    out.update({"n": int(n), "days": int(days), "ticks": int(G), "contracts": int(x.contract.nunique()),
                "mean_saving_bp": round(mean, 3), "median_saving_bp": round(med, 3), "t_cluster_tick": round(t, 3),
                "l2co_mean_saving_bp": round(l2co, 3),
                "mean_saving_high_fee_bp": round(float(x.saving_high_bp.astype(float).mean()), 3),
                "mean_saving_listed_fee_bp": round(float(x.saving_listed_bp.astype(float).mean()), 3),
                "mean_maker_pair_bp": round(float(x.maker_pair_bp.astype(float).mean()), 3),
                "mean_taker_pair_bp": round(float(x.taker_pair_bp.astype(float).mean()), 3),
                "mean_fill_frac": round(float(x.fill_frac.astype(float).mean()), 4)})
    if n < MIN_ORDERS or days < MIN_DAYS:
        out["verdict"] = "INSUFFICIENT_DATA"
    elif mean > 0 and t >= MIN_T and med > 0 and l2co > 0:
        out["verdict"] = "MAKER_ROUTE"
    else:
        out["verdict"] = "NO_GAIN"
    return out


# ------------------------------------------------------------------------------------------------------------------ tick
def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def append_csv(path, fields, rows):
    if not rows:
        return
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fields, lineterminator="\n", extrasaction="raise")
        if new:
            w.writeheader()
        w.writerows(rows)


def tick(get=gm.http, now=None, sleep=time.sleep, journal=JOURNAL, tickets=TICKETS, symbols=SYMBOLS):
    now = time.time() if now is None else now
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    orders_path, settled_path = journal / "orders.csv", journal / "settled.csv"
    orders, settled = read_csv(orders_path), read_csv(settled_path)
    done = {r["id"] for r in settled}
    errors = []
    # 1. settle
    due = {}
    for r in orders:
        if r["id"] not in done and float(r["t0"]) + SETTLE_AFTER_S <= now:
            due.setdefault((r["contract"], r["t0"]), []).append(parse_order(r))
    new_settled = []
    for (contract, t0), group in sorted(due.items(), key=lambda kv: float(kv[0][1])):
        try:
            new_settled += settle_group(get, group, stamp, sleep=sleep)
        except Exception as e:  # noqa: BLE001  one contract's failure must not stop the others
            errors.append(f"settle {contract} {t0}: {type(e).__name__}: {str(e)[:120]}")
            if float(t0) + GIVE_UP_S <= now:
                for o in group:
                    for h in HORIZONS_S:
                        new_settled.append({**{k: "" for k in SETTLED_FIELDS}, "id": o["id"], "horizon_s": h,
                                            "settled_at": stamp, "valid": False, "reason": "settle_failed"})
    append_csv(settled_path, SETTLED_FIELDS, new_settled)
    # 2. place
    new_orders = []
    if now < END.timestamp():
        held = open_book(read_csv(tickets))
        smap = symbol_map(read_csv(symbols))
        try:
            gcons = {c["name"]: c for c in get(f"{GATE}/contracts")}
        except Exception as e:  # noqa: BLE001
            gcons = {}
            errors.append(f"contracts: {type(e).__name__}: {str(e)[:120]}")
        for coin, r390_side in sorted(held.items()):
            contract = smap.get(coin)
            if not contract or contract not in gcons:
                errors.append(f"place {coin}: no Gate contract")
                continue
            try:
                sleep(gm.PACE_S)
                gbook = get(f"{GATE}/order_book?contract={contract}&limit={GATE_DEPTH}&with_id=true")
                sleep(gm.PACE_S)
                bbook = get(f"{BN}/depth?symbol={coin}&limit={BN_DEPTH}")
                new_orders += place(stamp, coin, contract, coin, r390_side, gbook, gcons[contract], bbook)
            except Exception as e:  # noqa: BLE001
                errors.append(f"place {coin}: {type(e).__name__}: {str(e)[:120]}")
        append_csv(orders_path, ORDER_FIELDS, new_orders)
    # 3. status
    all_orders, all_settled = read_csv(orders_path), read_csv(settled_path)
    status = {"registry": "R498", "updated": stamp, "orders": len(all_orders),
              "settled_rows": len(all_settled), "placed_now": len(new_orders), "settled_now": len(new_settled),
              "errors_now": len(errors), "end": END.isoformat(), **decide(all_orders, all_settled, now)}
    journal.mkdir(parents=True, exist_ok=True)
    (journal / "status.json").write_text(json.dumps(status, indent=1) + "\n")
    append_csv(journal / "ticks.csv", ["tick", "placed", "settled", "errors", "first_error"],
               [{"tick": stamp, "placed": len(new_orders), "settled": len(new_settled), "errors": len(errors),
                 "first_error": errors[0] if errors else ""}])
    for e in errors:
        log(e)
    log(f"tick {stamp}: placed {len(new_orders)}, settled {len(new_settled)} rows, errors {len(errors)}; "
        f"verdict {status['verdict']} (n {status['n']})")
    return status


def main(argv=None):
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    digest = prereg.verify(LANE / "PREREG.md")
    inputs = gm.frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
    tick()
    return 0


if __name__ == "__main__":
    sys.exit(main())
