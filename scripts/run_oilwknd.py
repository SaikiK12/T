"""oilwknd_fwd (R459): R432's one lead, a fade of the oil perps' weekend move held through the CME Sunday reopen to
the Monday cash open, tested forward on fresh weekends on Lighter (WTI and BRENTOIL; Standard account, no fee), at
Lighter's own one-minute prices, hourly funding and recorded book cost. As set out in experiments/oilwknd_fwd/PREREG.md.

Per weekend, in New York time (DST-aware): F = Friday 17:00, S = Sunday 18:00 (CME reopen), C = Monday 09:30.
- W = 1e4 ln(P(S - 5 min) / P(F)), P(tau) = close of the last one-minute bar that opened in [tau - 60 min, tau).
- A trade when |W| >= 100 bp: fade (short after a rise, long after a fall).
  - Entry: the open of the first bar that opened in [S - 4 min, S - 1 min] (before the reopen).
  - Exit: the open of the first bar that opened in [C, C + 5 min]; the S + 60 min exit is reported only.
- Funding: Lighter's hourly settlements after the entry minute and not after the exit minute (positive: longs pay).
- Cost of a fill: 0 fee plus the $1k market-order cost on the side traded in the nearest lighter/books snapshot within
  90 minutes (scripts/record_lighter_costs.py), else 10 bp, counted.
- A weekend touching an NYSE holiday (Friday or Monday) is skipped. A weekend is scored once, at the first run at
  least 3 hours after C; a fetch error leaves it for the next run; a missing price makes the asset's weekend unpriced.
Writes journal/trades.csv (append-only, one row per asset and weekend) and journal/status.json.
Paper only: public endpoints, no key, no order.

usage: python scripts/run_oilwknd.py --snapshots DIR [--status]
"""
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.sessions import NYSEHolidays  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ud = _load("run_usopen_dex")         # R457: Lighter one-minute bars and funding, close_before, funding_sum, fill_cost

LANE = ROOT / "experiments" / "oilwknd_fwd"
J = LANE / "journal"
NY = "America/New_York"
MIN, H = 60_000, 3_600_000
# ---- the frozen rule (PREREG "Rule"); tests/test_run_oilwknd.py checks these against the PREREG text
FIRST_FRIDAY = "2026-11-13"
ASSETS = ("WTI", "BRENTOIL")
THETA_BP = 100.0                     # |W| at or above this trades
ENTRY_LAG_MIN, ENTRY_WINDOW_MIN = 4, 3      # entry bar opened in [S - 4 min, S - 1 min]
EXIT_WINDOW_MIN = 5                  # exit bar opened in [X, X + 5 min]
FALLBACK = 10e-4                     # cost of a fill with no usable snapshot (R457's)
SCORE_AFTER = 3 * H
FUTILITY_N, FINAL_N = 15, 40         # traded weekends
ALPHA, N_BOOT, SEED, TOP_K = 0.05, 10_000, 459, 3
COLS = ["friday", "asset", "status", "w_bp", "side", "entry_t", "entry_px", "exit_t", "exit_px", "price", "funding",
        "gross", "cost_1x", "fallback_fills", "net_1x", "net_2x", "net_3x", "x60_px", "gross_x60", "net_x60_1x"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- pure parts
def ny_ms(day, hh, mm=0):
    """Epoch ms of a New York wall-clock time on a calendar day (DST-aware)."""
    ts = pd.Timestamp(f"{pd.Timestamp(day).date()} {hh:02d}:{mm:02d}", tz=NY)
    return int(ts.tz_convert("UTC").value // 10**6)


def weekend(friday):
    """Anchor times (epoch ms) of the weekend that starts on `friday`, and whether an NYSE holiday touches it."""
    f = pd.Timestamp(friday)
    mon = f + pd.Timedelta(days=3)
    hol = set(NYSEHolidays().holidays(f - pd.Timedelta(days=1), mon + pd.Timedelta(days=1)).date)
    S = ny_ms(f + pd.Timedelta(days=2), 18)
    return {"friday": str(f.date()), "F": ny_ms(f, 17), "S": S, "E": S - 5 * MIN, "C": ny_ms(mon, 9, 30),
            "x60": S + 60 * MIN, "holiday": bool(f.date() in hol or mon.date() in hol)}


def fridays(first, now_ms):
    """Fridays from `first` whose weekend is due (now at least SCORE_AFTER after its Monday cash open)."""
    out = []
    for f in pd.date_range(first, pd.Timestamp(now_ms, unit="ms") + pd.Timedelta(days=1), freq="W-FRI"):
        w = weekend(f)
        if now_ms >= w["C"] + SCORE_AFTER:
            out.append(w)
    return out


def first_open(bars, t0, t1):
    """Open of the first one-minute bar that opened in [t0, t1], or None."""
    w = bars[(bars.t >= t0) & (bars.t <= t1) & (bars.open > 0)]
    return float(w.open.iloc[0]) if len(w) else None


def score_asset(asset, w, bars, fund, books):
    """One asset's row for one weekend (status ok, no_trade or unpriced)."""
    row = dict.fromkeys(COLS)
    row.update(friday=w["friday"], asset=asset)
    pf, pe = ud.close_before(bars, w["F"]), ud.close_before(bars, w["E"])
    if pf is None or pe is None:
        row["status"] = "unpriced"
        return row
    W = 1e4 * np.log(pe / pf)
    row["w_bp"] = float(W)
    if abs(W) < THETA_BP:
        row["status"] = "no_trade"
        return row
    side = -1 if W > 0 else 1                                   # fade
    e_t0 = w["S"] - ENTRY_LAG_MIN * MIN
    ein = first_open(bars, e_t0, e_t0 + ENTRY_WINDOW_MIN * MIN)
    eout = first_open(bars, w["C"], w["C"] + EXIT_WINDOW_MIN * MIN)
    if ein is None or eout is None:
        row["status"] = "unpriced"
        return row
    ent = int(bars[(bars.t >= e_t0) & (bars.open > 0)].t.iloc[0])
    ext = int(bars[(bars.t >= w["C"]) & (bars.open > 0)].t.iloc[0])
    price = side * (eout / ein - 1)
    funding = -side * ud.funding_sum(fund, ent, ext)
    fills, fb = [], 0
    for t, col in ((ent, "buy_1k_bp" if side > 0 else "sell_1k_bp"), (ext, "sell_1k_bp" if side > 0 else "buy_1k_bp")):
        c = ud.fill_cost(books, "symbol", asset, t, col)
        if c is None:
            c, fb = FALLBACK, fb + 1
        fills.append(c)
    cost = float(sum(fills))
    gross = price + funding
    x60 = first_open(bars, w["x60"], w["x60"] + EXIT_WINDOW_MIN * MIN)
    row.update(status="ok", side=side, entry_t=ent, entry_px=ein, exit_t=ext, exit_px=eout, price=price,
               funding=funding, gross=gross, cost_1x=cost, fallback_fills=fb, net_1x=gross - cost,
               net_2x=gross - 2 * cost, net_3x=gross - 3 * cost, x60_px=x60)
    if x60 is not None:                       # reported only: the same entry, out at S + 60 min, no funding crossed
        c60 = ud.fill_cost(books, "symbol", asset, w["x60"], "sell_1k_bp" if side > 0 else "buy_1k_bp")
        row["gross_x60"] = side * (x60 / ein - 1)
        row["net_x60_1x"] = row["gross_x60"] - fills[0] - (FALLBACK if c60 is None else c60)
    return row


def weekend_nets(tr, col="net_1x"):
    """One value per traded weekend (the mean over its assets with status ok), in calendar order."""
    ok = tr[tr.status == "ok"]
    return ok.groupby("friday")[col].mean().sort_index() if len(ok) else pd.Series(dtype=float)


def boot_p(x, n_boot=N_BOOT, seed=SEED):
    """One-sided p: the share of resampled means (whole weekends, with replacement) at or below 0."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(1)
    return float((m <= 0).mean())


def decision(tr):
    x1, x2 = weekend_nets(tr, "net_1x"), weekend_nets(tr, "net_2x")
    n = len(x1)
    s = {"traded_weekends": n}
    for k in (1, 2, 3):
        x = weekend_nets(tr, f"net_{k}x")
        s[f"mean_{k}x_bp"] = float(x.mean() * 1e4) if n else None
    if n >= FUTILITY_N and x1.iloc[:FUTILITY_N].mean() <= 0:
        s["decision"] = f"NULL (futility at {FUTILITY_N} traded weekends)"
    elif n >= FINAL_N:
        a, b = x1.iloc[:FINAL_N].to_numpy(float), x2.iloc[:FINAL_N].to_numpy(float)
        p = boot_p(a)
        trim = np.sort(a)[:-TOP_K].mean()
        ok = a.mean() > 0 and p < ALPHA and b.mean() > 0 and trim > 0
        s.update(p=p, mean_without_best3_bp=float(trim * 1e4))
        s["decision"] = ("PASS" if ok else "NULL") + f" at {FINAL_N} traded weekends (p {p:.4f})"
    else:
        s["decision"] = f"pending ({n} traded weekends of {FUTILITY_N} for the futility read, {FINAL_N} final)"
    return s


# ---------------------------------------------------------------- forward
def read_csv(p):
    return pd.read_csv(p) if Path(p).exists() and Path(p).stat().st_size else pd.DataFrame(columns=COLS)


def weekend_bars(venue, asset, w):
    """The one-minute bars the rule reads, in three short requests: Lighter's candles return at most 500 bars, the
    last ones of the range asked (checked 2026-11-11)."""
    parts = [venue.minutes(asset, w["F"] - 61 * MIN, w["F"]),
             venue.minutes(asset, w["E"] - 61 * MIN, w["x60"] + (EXIT_WINDOW_MIN + 1) * MIN),
             venue.minutes(asset, w["C"], w["C"] + (EXIT_WINDOW_MIN + 1) * MIN)]
    parts = [p for p in parts if p is not None and len(p)]
    if not parts:
        return pd.DataFrame(columns=["t", "open", "close"])
    return pd.concat(parts, ignore_index=True).drop_duplicates("t").sort_values("t").reset_index(drop=True)


def read_books(snap_dir, days):
    files = [Path(snap_dir) / "lighter" / "books" / f"{d}.csv" for d in days]
    got = [pd.read_csv(p) for p in files if p.exists()]
    return pd.concat(got, ignore_index=True) if got else pd.DataFrame(columns=["ts", "symbol"])


def forward(snap_dir, status_only=False, now_ms=None, venue=None):
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    venue = venue or ud.Lighter()
    tr = read_csv(J / "trades.csv")
    done = set(zip(tr.friday.astype(str), tr.asset)) if len(tr) else set()
    rows = []
    for w in ([] if status_only else fridays(FIRST_FRIDAY, now_ms)):
        todo = [a for a in ASSETS if (w["friday"], a) not in done]
        if not todo:
            continue
        if w["holiday"]:
            rows += [dict(dict.fromkeys(COLS), friday=w["friday"], asset=a, status="holiday") for a in todo]
            continue
        days = sorted({pd.Timestamp(t, unit="ms").strftime("%Y-%m-%d") for t in (w["S"] - H, w["S"] + H,
                                                                                 w["C"] - 2 * H, w["C"] + 2 * H)})
        books = read_books(snap_dir, days)
        for a in todo:
            try:
                bars = weekend_bars(venue, a, w)
                fund = venue.funding(a, w["S"] - 2 * H, w["C"] + 2 * H)
            except Exception as e:                  # noqa: BLE001 - a fetch error is retried at the next run
                log(w["friday"], a, "fetch failed, retried next run:", type(e).__name__, str(e)[:80])
                continue
            rows.append(score_asset(a, w, bars, fund, books))
    J.mkdir(parents=True, exist_ok=True)
    if rows:
        p = J / "trades.csv"
        pd.DataFrame(rows, columns=COLS).to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
        tr = read_csv(p)
    st = decision(tr)
    st["rows"] = int(len(tr))
    st["by_status"] = {k: int(v) for k, v in tr.status.value_counts().items()} if len(tr) else {}
    st["fallback_fills"] = int(pd.to_numeric(tr.fallback_fills, errors="coerce").fillna(0).sum()) if len(tr) else 0
    x60 = pd.to_numeric(tr[tr.status == "ok"].net_x60_1x, errors="coerce").dropna() if len(tr) else []
    st["x60_mean_1x_bp_per_trade"] = float(np.mean(x60) * 1e4) if len(x60) else None
    (J / "status.json").write_text(json.dumps(st, indent=1, default=float) + "\n")
    return st


def check_inputs(prereg_path):
    text = Path(prereg_path).read_text()
    lines = text.split("```inputs\n", 1)[1].split("```", 1)[0].splitlines()
    for line in lines:
        sha, rel = line.split()
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != sha:
            raise SystemExit(f"input changed since the freeze: {rel}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, help="checkout of the data branch claude/xyz-books-data")
    ap.add_argument("--status", action="store_true", help="rewrite status.json from the journal, no fetch")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs(LANE / "PREREG.md")
    log(forward(a.snapshots, a.status))


if __name__ == "__main__":
    main()
