"""R351 minflow_alts_v1: R349's frozen pick, unchanged, on nine more coins whose 1-minute bars no lane has read (M426).

R349 (minflow_v1) chose `flow_fade_k5_h5` from 57 minute rules on BTC, ETH and SOL: when the last 5 minutes' signed
taker volume reaches its trailing-week 99.5th percentile, take the other side at the next minute's open and exit 5
minutes later. Here the same code, imported from R349's frozen runner, trades the 1-s tape's nine other coins (BNB,
XRP, TRX, AVAX, LINK, DOGE, SUI, ADA, LTC), each at its own Lighter $1k book walk measured in R348 (fee 0). One rule
and no selection: it replicates, or it does not, and the decision also asks whether it still pays since 2025-07.

usage: python scripts/run_minflow_alts.py    (verifies the frozen PREREG and every input hash first)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg, stats  # noqa: E402
import run_minflow as r349  # noqa: E402  R349's frozen runner, imported unchanged

LANE = ROOT / "experiments" / "minflow_alts_v1"
REGISTRY = "R351"
COINS = ("BNBUSDT", "XRPUSDT", "TRXUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "SUIUSDT", "ADAUSDT", "LTCUSDT")
DATA = ROOT / "data" / "klines_1m_tape"
PICK, HOLD = "flow_fade_k5", 5                    # R349's j*, flow_fade_k5_h5
WALK_BP = {"BNBUSDT": 0.81, "XRPUSDT": 0.77, "TRXUSDT": 1.59, "AVAXUSDT": 1.63, "LINKUSDT": 1.65, "DOGEUSDT": 1.95,
           "SUIUSDT": 2.00, "ADAUSDT": 2.72, "LTCUSDT": 4.10}   # R348 summary.json walk_cost_bp, 2 decimals
WEB_BP, API_BP = 3.0, 8.5                         # MEXC web and API a side, reported only (as R349)
ALL = ("2021-04-01", "2026-09-30")
HALVES = (("2021-04-01", "2023-12-31"), ("2024-01-01", "2026-09-30"))
RECENT = ("2025-07-01", "2026-09-30")
NW_LAG, T_BAR, MIN_POSITIVE_COINS = 10, 2.0, 6
TRIALS = 1
MIN, DAY, T0, T1 = r349.MIN, r349.DAY, r349.T0, r349.T1
N_DAYS = (T1 - T0) // DAY


def log(msg):
    line = f"{time.strftime('%H:%M:%S', time.gmtime())} {msg}"
    print(line, flush=True)
    with open(LANE / "run.log", "a") as f:
        f.write(line + "\n")


def check_costs(summary_path):
    """The frozen costs must be R348's measured walks rounded to 2 decimals."""
    walk = json.loads(Path(summary_path).read_text())["walk_cost_bp"]
    for c in COINS:
        got = round(walk[c.removesuffix("USDT")], 2)
        if got != WALK_BP[c]:
            raise ValueError(f"{c}: frozen cost {WALK_BP[c]} != R348's {got}")


def simulate(bars, tick, F, rate, delay=0, tick_mult=1.0):
    """R349's pick on one coin: its own signal code and trade code, unchanged. tick_mult 2 moves each price a full tick
    against the trade instead of half (reported only)."""
    sig = r349.coin_signals(bars)[PICK]
    return r349.trades(bars, tick * tick_mult, F, rate, sig, HOLD, delay)


def book(per_coin, mult=1.0, cost=None):
    """Daily net of the book: each of the nine coins holds a ninth of capital and trades it in sequence; a coin
    without bars (SUI before its listing) leaves its ninth idle."""
    x = np.zeros(N_DAYS)
    for coin, t in per_coin.items():
        if len(t):
            c = WALK_BP[coin] if cost is None else cost
            np.add.at(x, t.day.values, r349.net(t, c, mult) / len(COINS))
    return x


def sel(a, b):
    return r349.window(N_DAYS, a, b)


def decide(per_coin):
    """The frozen verdict: REPLICATES needs (1) NW t >= 2 at 1x over 2021-04..2026-09, (2) a positive 2x mean there,
    (3) a positive 1x mean in both halves and (4) positive gross per trade on at least 6 of the 9 coins over the whole
    window. LIVE needs REPLICATES and an NW t >= 2 at 1x over 2025-07..2026-09."""
    b1, b2 = book(per_coin, 1), book(per_coin, 2)
    a = sel(*ALL)
    _, mu, t_all = stats.newey_west_t(b1[a], NW_LAG)
    halves = [float(b1[sel(*h)].mean()) for h in HALVES]
    gross = {}
    for c, t in per_coin.items():
        tt = t[np.isin(t.day.values, np.flatnonzero(a))]
        gross[c] = float(tt.gross.mean() * 1e4) if len(tt) else float("nan")
    positive = sum(1 for g in gross.values() if g > 0)
    r = sel(*RECENT)
    _, mu_r, t_r = stats.newey_west_t(b1[r], NW_LAG)
    replicates = bool(t_all >= T_BAR and b2[a].mean() > 0 and min(halves) > 0 and positive >= MIN_POSITIVE_COINS)
    live = bool(replicates and t_r >= T_BAR)
    return {"verdict": "LIVE" if live else ("REPLICATES" if replicates else "NULL"),
            "all_net1_day_bp": float(mu * 1e4), "all_t1": float(t_all), "all_net2_day_bp": float(b2[a].mean() * 1e4),
            "halves_net1_day_bp": [h * 1e4 for h in halves], "gross_trade_bp_by_coin": gross,
            "coins_positive_gross": positive, "recent_net1_day_bp": float(mu_r * 1e4), "recent_t1": float(t_r),
            "replicates": replicates, "live": live}


def describe(per_coin, name, window_sel, late=None, full_tick=None):
    """One reported row for a window: trades, hit, gross and net per trade, daily net at 1x/2x/3x, web, API, NW t."""
    days = np.flatnonzero(window_sel)
    t = pd.concat([tt.assign(coin=c) for c, tt in per_coin.items()], ignore_index=True)
    t = t[np.isin(t.day.values, days)]
    b = {m: book(per_coin, m)[window_sel] for m in (1, 2, 3)}
    _, mu, tt = stats.newey_west_t(b[1], NW_LAG)
    cost = t.coin.map(WALK_BP).values / 1e4 if len(t) else np.zeros(0)
    row = {"window": name, "days": int(window_sel.sum()), "trades": int(len(t)),
           "trades_per_day": len(t) / max(1, int(window_sel.sum())),
           "hit": float((t.gross > 0).mean()) if len(t) else np.nan,
           "gross_trade_bp": float(t.gross.mean() * 1e4) if len(t) else np.nan,
           "net1_trade_bp": float((t.gross - t.fund - 2 * cost).mean() * 1e4) if len(t) else np.nan,
           "net1_day_bp": mu * 1e4, "net2_day_bp": float(b[2].mean() * 1e4), "net3_day_bp": float(b[3].mean() * 1e4),
           "web_day_bp": float(book(per_coin, cost=WEB_BP)[window_sel].mean() * 1e4),
           "api_day_bp": float(book(per_coin, cost=API_BP)[window_sel].mean() * 1e4), "nw_t1": tt,
           "breakeven_bp_side": float((t.gross - t.fund).mean() / 2 * 1e4) if len(t) else np.nan}
    if late is not None:
        row["late_net1_day_bp"] = float(book(late, 1)[window_sel].mean() * 1e4)
    if full_tick is not None:
        row["full_tick_net1_day_bp"] = float(book(full_tick, 1)[window_sel].mean() * 1e4)
    return row


def windows():
    out = {"all": sel(*ALL), "early": sel(*HALVES[0]), "late": sel(*HALVES[1]), "recent": sel(*RECENT)}
    for y in range(2021, 2027):
        out[str(y)] = sel(max(f"{y}-01-01", ALL[0]), min(f"{y}-12-31", ALL[1]))
    return out


def detail(per_coin):
    """Per coin and window: trades, gross and net per trade, t of the per-trade net; sides; the 10 best days' share."""
    rows = []
    for c, t in per_coin.items():
        for name, w in windows().items():
            tt = t[np.isin(t.day.values, np.flatnonzero(w))]
            if not len(tt):
                continue
            n1 = r349.net(tt, WALK_BP[c], 1)
            rows.append({"coin": c, "window": name, "trades": len(tt), "gross_trade_bp": tt.gross.mean() * 1e4,
                         "net1_trade_bp": n1.mean() * 1e4,
                         "t_trade": n1.mean() / (n1.std(ddof=1) / np.sqrt(len(n1))) if len(n1) > 1 else np.nan,
                         "long_net1_bp": n1[tt.side.values > 0].mean() * 1e4 if (tt.side > 0).any() else np.nan,
                         "short_net1_bp": n1[tt.side.values < 0].mean() * 1e4 if (tt.side < 0).any() else np.nan,
                         "walk_bp": WALK_BP[c]})
    b = book(per_coin, 1)[sel(*ALL)]
    top = np.sort(b)[::-1][:10]
    extra = {"all_best10_share": float(top.sum() / b.sum()) if b.sum() != 0 else np.nan,
             "all_without_best10_bp": float((b.sum() - top.sum()) / (len(b) - 10) * 1e4)}
    return pd.DataFrame(rows), extra


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = r349.frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    check_costs(ROOT / "experiments" / "tapelag_lighter_v2" / "results" / "summary.json")
    sims = {0: {}, 1: {}, "full": {}}
    for c in COINS:
        bars = r349.load_bars(DATA / f"{c}.parquet")
        F, rate = r349.load_funding(ROOT / "data" / "fundingRate" / f"{c}.parquet")
        tick = r349.month_ticks(bars)
        sims[0][c] = simulate(bars, tick, F, rate)
        sims[1][c] = simulate(bars, tick, F, rate, delay=1)
        sims["full"][c] = simulate(bars, tick, F, rate, tick_mult=2.0)
        log(f"{c}: {int(np.isfinite(bars['close']).sum())} bars, {len(sims[0][c])} trades")
    dec = decide(sims[0])
    rows = [describe(sims[0], name, w, late=sims[1], full_tick=sims["full"]) for name, w in windows().items()]
    per_coin, extra = detail(sims[0])
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(res / "windows.csv", index=False, float_format="%.6g")
    per_coin.to_csv(res / "coins.csv", index=False, float_format="%.6g")
    daily = pd.DataFrame({"day": pd.to_datetime(T0 + np.arange(N_DAYS, dtype=np.int64) * DAY, unit="ms").date,
                          "net1": book(sims[0], 1), "net2": book(sims[0], 2), "net3": book(sims[0], 3)})
    daily.to_csv(res / "daily.csv.gz", index=False, float_format="%.6g")
    pd.concat([t.assign(coin=c) for c, t in sims[0].items()]).to_csv(res / "trades.csv.gz", index=False)
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "pick": f"{PICK}_h{HOLD}",
               "decision": dec, "verdict": dec["verdict"], "extra": extra, "walk_bp": WALK_BP, "inputs": shas}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {dec['verdict']}; all 1x {dec['all_net1_day_bp']:.2f} bp/day t {dec['all_t1']:.2f}; halves "
        f"{dec['halves_net1_day_bp'][0]:.2f}/{dec['halves_net1_day_bp'][1]:.2f}; coins positive "
        f"{dec['coins_positive_gross']}/9; recent {dec['recent_net1_day_bp']:.2f} bp/day t {dec['recent_t1']:.2f}")


if __name__ == "__main__":
    main()
