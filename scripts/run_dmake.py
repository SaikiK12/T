"""R522 dmake_v1: make on Deribit's thin new perps, hedge on Hyperliquid. A historical simulation from Deribit's full
trade history, as set out in experiments/dmake_v1/PREREG.md.

Per coin, from its creation + 3 days to the end:
- **Quotes.** At each trade time t, a bid at I(t - LAT) x (1 - k) and an ask at I(t - LAT) x (1 + k). I is the index
  price carried by the last trade at or before t - LAT, so the quote never uses information newer than LAT seconds.
- **Fill (conservative).** A taker sell at a price strictly below the bid fills the bid. A taker buy strictly above
  the ask fills the ask. At most one fill per side per coin per COOL seconds. Size: one unit of $500.
- **Hedge.** At once on Hyperliquid at the index of the fill's trade: I_fill x (1 - h) for a bought unit, or
  I_fill x (1 + h) for a sold one. h = Hyperliquid's taker fee plus half-spread.
- **Edge of a fill, in bp of notional.**
  - Bought: (I_fill (1 - h) - bid) / bid - maker fee.
  - Sold: (ask - I_fill (1 + h)) / ask - maker fee.
- **Inventory.** At most CAP units long or short per coin; a side stops quoting at its cap. Units left at the end are
  closed at the last index, paying the taker fee on Deribit and h on Hyperliquid.
- **Not counted:** funding on inventory, the Deribit-Hyperliquid basis, and venue points.

usage: python scripts/run_dmake.py run
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "dmake_v1"
DATA = ROOT / "data" / "deribit_trades"
K_PRIMARY = 0.0015
K_SECONDARY = (0.0005, 0.0010, 0.0025, 0.0040)
LAT, COOL, CAP, UNIT = 2_000, 60_000, 10, 500.0
MAKER, TAKER, H = 0.00015, 0.00035, 0.00065            # Deribit maker / taker fee; Hyperliquid 4.5 bp + 2 bp half-spread
WARM = 3 * 86_400_000


def simulate(tr, k, maker=MAKER, h=H, taker=TAKER):
    """Fills of one coin: DataFrame(t, side, edge_bp). tr: timestamp, price, direction, index_price (sorted)."""
    t = tr.timestamp.to_numpy(np.int64)
    px = tr.price.to_numpy(float)
    idx = tr.index_price.to_numpy(float)
    buy = (tr.direction == "buy").to_numpy()
    if not len(t):
        return pd.DataFrame(columns=["t", "side", "edge_bp"])
    start = t[0] + WARM
    j = np.searchsorted(t, t - LAT, side="right") - 1      # last trade at or before t - LAT
    rows, inv, last = [], 0, {"bid": -10**18, "ask": -10**18}
    for i in range(len(t)):
        if t[i] < start or j[i] < 0:
            continue
        ref = idx[j[i]]
        if not (ref > 0 and idx[i] > 0):
            continue
        if not buy[i] and inv < CAP and t[i] - last["bid"] >= COOL:          # a taker sell hits our bid
            bid = ref * (1 - k)
            if px[i] < bid:
                rows.append((t[i], 1, ((idx[i] * (1 - h) - bid) / bid - maker) * 1e4))
                inv += 1
                last["bid"] = t[i]
        elif buy[i] and inv > -CAP and t[i] - last["ask"] >= COOL:          # a taker buy lifts our ask
            ask = ref * (1 + k)
            if px[i] > ask:
                rows.append((t[i], -1, ((ask - idx[i] * (1 + h)) / ask - maker) * 1e4))
                inv -= 1
                last["ask"] = t[i]
    out = pd.DataFrame(rows, columns=["t", "side", "edge_bp"])
    if inv:                                                     # close what is left at the last index, as a taker
        out = pd.concat([out, pd.DataFrame([{"t": int(t[-1]), "side": 0,
                                             "edge_bp": -abs(inv) * (taker + h) * 1e4}])], ignore_index=True)
    return out


def daily(fills):
    """Per UTC day: dollars and fill count over all coins (one unit = $500)."""
    if not len(fills):
        return pd.DataFrame(columns=["day", "usd", "n"])
    d = pd.to_datetime(fills.t, unit="ms").dt.floor("D")
    g = fills.assign(day=d, usd=fills.edge_bp * UNIT / 1e4).groupby("day")
    return pd.DataFrame({"usd": g.usd.sum(), "n": g.size()}).reset_index()


def summarize(fills, coins):
    dd = daily(fills)
    x = dd.usd.to_numpy(float)
    rep = {"fills": int((fills.side != 0).sum()), "coins_with_fills": int(fills.coin.nunique()) if len(fills) else 0,
           "days": int(len(dd))}
    real = fills[fills.side != 0]
    if len(real):
        rep.update({"mean_edge_bp": float(real.edge_bp.mean()), "median_edge_bp": float(real.edge_bp.median()),
                    "share_positive": float((real.edge_bp > 0).mean()),
                    "usd_total": float(x.sum()), "usd_per_day": float(x.mean()),
                    "fills_per_coin_day": float(len(real) / max(1, len(dd)) / max(1, coins))})
    if len(x) >= 10:
        rep["nw_t_daily_usd"] = float(newey_west_t(x, 5)[2])
        h_ = len(x) // 2
        rep["halves_usd_per_day"] = [float(x[:h_].mean()), float(x[h_:].mean())]
        by = real.groupby("coin").edge_bp.sum().sort_values(ascending=False)
        top = by.index[:2].tolist()
        rest = fills[~fills.coin.isin(top)]
        rep["l2co_dropped"], rep["l2co_usd_per_day"] = top, float(daily(rest).usd.mean()) if len(rest) else 0.0
    return rep


def decide(prim, prim2x):
    if prim.get("days", 0) < 30 or "nw_t_daily_usd" not in prim:
        return "UNREADABLE", {}
    c = {"t_ge_3": prim["nw_t_daily_usd"] >= 3.0, "positive_at_2x_cost": prim2x.get("usd_per_day", -1) > 0,
         "l2co_pos": prim["l2co_usd_per_day"] > 0, "both_halves_pos": min(prim["halves_usd_per_day"]) > 0}
    c = {k: bool(v) for k, v in c.items()}
    return ("PASS" if all(c.values()) else "FAIL"), c


def run_all(data=DATA, lane=LANE):
    from lab.prereg import verify
    from scripts.run_xfund_bfx import check_inputs
    import hashlib
    verify(lane / "PREREG.md")
    check_inputs(lane / "PREREG.md")
    man = json.loads((data / "manifest.json").read_text())["files"]
    bad = [p for p, h_ in man.items() if hashlib.sha256((data / p).read_bytes()).hexdigest() != h_]
    if bad:
        raise SystemExit(f"{len(bad)} trade files differ from the manifest")
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    files = sorted(data.glob("*.parquet"))
    tables = {p.stem: pd.read_parquet(p, columns=["timestamp", "price", "direction", "index_price"]) for p in files}
    rep = {"coins": len(tables), "files_verified": len(man)}

    def book(k, maker=MAKER, h=H, taker=TAKER):
        parts = [simulate(tb, k, maker, h, taker).assign(coin=c) for c, tb in tables.items()]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["t", "side", "edge_bp", "coin"])

    prim = book(K_PRIMARY)
    rep["primary_k15"] = summarize(prim, len(tables))
    rep["primary_k15_2x_cost"] = summarize(book(K_PRIMARY, 2 * MAKER, 2 * H, 2 * TAKER), len(tables))
    rep["primary_k15_3x_cost"] = summarize(book(K_PRIMARY, 3 * MAKER, 3 * H, 3 * TAKER), len(tables))
    rep["verdict"], rep["checks"] = decide(rep["primary_k15"], rep["primary_k15_2x_cost"])
    for k in K_SECONDARY:
        rep[f"secondary_k{round(k * 1e4)}"] = summarize(book(k), len(tables))
    res.mkdir(parents=True, exist_ok=True)
    prim.to_csv(res / "fills_k15.csv", index=False)
    daily(prim).to_csv(res / "daily_k15.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"], **rep["primary_k15"]}, default=str))
    return rep


if __name__ == "__main__":
    if sys.argv[1:] != ["run"]:
        raise SystemExit("usage: python scripts/run_dmake.py run")
    run_all()
