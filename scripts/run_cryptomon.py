"""R471 cryptomon_v1, frozen in experiments/cryptomon_v1/PREREG.md: does a Bitcoin-linked US stock keep moving after
Monday's open in the direction of Bitcoin's weekend move (or give it back)? Gate 0 on public daily history.

For every session S that follows a market closure of at least three calendar days (Mondays, and Tuesdays after a
Monday holiday), with P the previous session:
- W  = Bitcoin's return from P 16:00 New York to S 09:00 New York (hourly opens of Binance's BTCUSDT perp);
- G  = each stock's gap, open(S) / close(P) - 1, and D = its session move, close(S) / open(S) - 1;
- the decision series is D_bar, the mean D of the decision names trading at S.

A (sessions to 2023-12-31) decides and fixes the direction; B (2024-01-01 .. 2026-11-11) confirms. Paper only.

usage: python scripts/run_cryptomon.py      the frozen run (verifies the PREREG, every input it lists and the data)
"""
import json
import math
import sys
import time
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "cryptomon_v1"
DATA = ROOT / "data" / "cryptomon"
REGISTRY = "R471"
NY = ZoneInfo("America/New_York")
H = 3_600_000
DECIDE = {"MSTR": "2020-09-01", "COIN": "2021-04-15", "MARA": "2021-01-01", "RIOT": "2021-01-01"}
REPORT = {"HOOD": "2021-07-30", "IREN": "2021-11-18", "QQQ": "2020-09-01"}
CALENDAR = "QQQ"                  # the session calendar
MIN_GAP_DAYS = 3                  # calendar days from P to S
THETA = 0.03                      # |W| for an event
UNIT_BP = 5.8                     # one round trip: trade.xyz growth mode 2 x 0.9 bp + 4 bp slippage (R462's unit)
SPLIT_GUARD = 0.5                 # |G| above this is a data break, dropped
SPANS = {"A": (date(2020, 9, 1), date(2023, 12, 31)), "B": (date(2024, 1, 1), date(2026, 11, 11))}
MIN_EVENTS = {"A": 30, "B": 15}
T_PASS = 2.0
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def verify_data(data):
    man = json.loads((data / "yahoo" / "manifest.json").read_text())
    for rel, meta in man["files"].items():
        if prereg.sha256_file(data / "yahoo" / rel) != meta["sha256"]:
            raise SystemExit(f"manifest mismatch: yahoo/{rel}")
    bman = json.loads((data / "binance" / "klines_1h" / "manifest.json").read_text())
    p = data / "binance" / "klines_1h" / "BTCUSDT.parquet"
    if prereg.sha256_file(p) != bman["symbols"]["BTCUSDT"]["sha256"]:
        raise SystemExit("manifest mismatch: BTCUSDT.parquet")
    return len(man["files"]) + 1


def ny_ms(day, hour):
    """Epoch ms of `hour`:00 New York time on the date `day` (YYYY-MM-DD)."""
    return int(pd.Timestamp(f"{day} {hour:02d}:00", tz=NY).tz_convert("UTC").timestamp() * 1000)


def load(data):
    stocks = {t: pd.read_parquet(data / "yahoo" / f"{t}.parquet") for t in list(DECIDE) + list(REPORT)}
    btc = pd.read_parquet(data / "binance" / "klines_1h" / "BTCUSDT.parquet")[["t", "open"]]
    return stocks, btc


def events(stocks, btc):
    """One row per (session S, ticker) after a closure of at least MIN_GAP_DAYS, with W, G and D."""
    btc_open = dict(zip(btc["t"].astype("int64"), btc["open"].astype(float)))
    days = sorted(stocks[CALENDAR]["date"])
    px = {t: {d: (float(o), float(c)) for d, o, c in zip(df["date"], df["open"], df["close"])}
          for t, df in stocks.items()}
    starts = {**DECIDE, **REPORT}
    rows = []
    for p, s in zip(days[:-1], days[1:]):
        if (date.fromisoformat(s) - date.fromisoformat(p)).days < MIN_GAP_DAYS:
            continue
        b0, b1 = btc_open.get(ny_ms(p, 16)), btc_open.get(ny_ms(s, 9))
        if not b0 or not b1:
            continue
        w = b1 / b0 - 1
        for t in stocks:
            if p < starts[t] or p not in px[t] or s not in px[t]:
                continue
            cp, (os_, cs) = px[t][p][1], px[t][s]
            if not (cp > 0 and os_ > 0 and cs > 0):
                continue
            g = os_ / cp - 1
            if abs(g) > SPLIT_GUARD:
                continue
            rows.append({"P": p, "S": s, "ticker": t, "W": w, "G": g, "D": cs / os_ - 1})
    return pd.DataFrame(rows)


def per_session(ev, names):
    sub = ev[ev["ticker"].isin(names)]
    g = sub.groupby("S").agg(W=("W", "first"), G=("G", "mean"), D=("D", "mean"), n=("ticker", "size"))
    return g.reset_index()


def ols(x, y):
    """Slope, HC1 standard error and t of y on x with an intercept."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 3 or np.var(x) == 0:
        return {"n": n, "slope": math.nan, "se": math.nan, "t": math.nan}
    xc = x - x.mean()
    b = float((xc * (y - y.mean())).sum() / (xc ** 2).sum())
    e = (y - y.mean()) - b * xc
    se = float(math.sqrt((xc ** 2 * e ** 2).sum() / (xc ** 2).sum() ** 2 * n / (n - 2)))
    return {"n": n, "slope": b, "se": se, "t": b / se if se > 0 else math.nan}


def mean_t(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return {"n": n, "mean_bp": math.nan, "sd_bp": math.nan, "t": math.nan}
    m, sd = float(x.mean()), float(x.std(ddof=1))
    return {"n": n, "mean_bp": m * 1e4, "sd_bp": sd * 1e4, "t": m / (sd / math.sqrt(n)) if sd > 0 else math.nan}


def in_span(df, span):
    lo, hi = span
    return df[(df["S"] >= lo.isoformat()) & (df["S"] <= hi.isoformat())]


def sample_stats(sess, ev, span, direction):
    s = in_span(sess, span)
    e = s[s["W"].abs() >= THETA]
    signed = np.sign(e["W"]) * e["D"]
    out = {"sessions": int(len(s)), "events": int(len(e)), "slope_D": ols(s["W"], s["D"]),
           "slope_G": ols(s["W"], s["G"]), "slope_D_neg": ols(s[s["W"] < 0]["W"], s[s["W"] < 0]["D"]),
           "slope_D_pos": ols(s[s["W"] > 0]["W"], s[s["W"] > 0]["D"]),
           "event_follow": mean_t(signed), "event_neg": mean_t(e[e["W"] < 0]["D"]),
           "event_pos": mean_t(e[e["W"] > 0]["D"])}
    if direction:
        net = direction * signed
        out["trade"] = {f"{k}x": mean_t(net - k * UNIT_BP / 1e4) for k in (1, 2, 3)}
        out["trade"]["gross"] = mean_t(net)
    se = in_span(ev, span)
    se = se[se["W"].abs() >= THETA]
    out["per_ticker"] = {t: mean_t(np.sign(g["W"]) * g["D"]) for t, g in se.groupby("ticker")}
    return out


def verdict(a, b):
    if a["events"] < MIN_EVENTS["A"] or b["events"] < MIN_EVENTS["B"]:
        return "INCONCLUSIVE", f"events A {a['events']}, B {b['events']} below {MIN_EVENTS}"
    sl = a["slope_D"]
    d = 1 if sl["slope"] > 0 else -1
    a_net = a["trade"]["gross"]["mean_bp"]
    a_ok = abs(sl["t"]) >= T_PASS and a_net > 2 * UNIT_BP
    b_net = b["trade"]["gross"]["mean_bp"]
    side = "follow" if d > 0 else "fade"
    text = (f"A slope {sl['slope']:+.3f} (t {sl['t']:.2f}), {side} events {a_net:+.1f} bp gross (n {a['events']}); "
            f"B {b_net:+.1f} bp (n {b['events']}, t {b['trade']['gross']['t']:.2f})")
    if not a_ok:
        return "NULL", text
    return ("PASS" if b_net > UNIT_BP else "PARTIAL"), text


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
        log(f"data files verified: {verify_data(data)}")
    stocks, btc = load(data)
    ev = events(stocks, btc)
    sess = per_session(ev, list(DECIDE))
    a0 = sample_stats(sess, ev[ev["ticker"].isin(list(DECIDE))], SPANS["A"], 0)
    d = 1 if a0["slope_D"]["slope"] > 0 else -1
    st = {k: sample_stats(sess, ev[ev["ticker"].isin(list(DECIDE))], v, d) for k, v in SPANS.items()}
    state, text = verdict(st["A"], st["B"])
    rep = {}
    for t in REPORT:
        s1 = per_session(ev, [t])
        rep[t] = {k: sample_stats(s1, ev[ev["ticker"] == t], v, d) for k, v in SPANS.items()}
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    ev.to_csv(res / "events.csv", index=False)
    sess.to_csv(res / "sessions.csv", index=False)
    summary = {"registry": REGISTRY, "state": state, "text": text, "direction": d, "unit_bp": UNIT_BP,
               "samples": st, "reported": rep}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    run()
