"""R367 hftlead_v1 runner, frozen in experiments/hftlead_v1/PREREG.md: does the Binance USDT or Bybit mid, when it has
moved away from the Binance USDC mid, make a one-second passive quote on the USDC perp worth posting?

Reads the daily files of scripts/record_hft.py (100 ms buckets, local-receive clock) for the whole UTC days from
FIRST_DAY, scores the sixteen rules of scripts/hftlead_rule.py once, and writes experiments/hftlead_v1/results/.

usage: python scripts/run_hftlead.py              the frozen run (verifies the PREREG and every input it lists)
       python scripts/run_hftlead.py --plumbing   coverage and row counts only; no quote, fill or markout is computed
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import hftlead_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "hftlead_v1"
REGISTRY = "R367"
DATA = ROOT / "data" / "hft"
FIRST_DAY = "2026-10-29"           # the first whole UTC day after the recorder's start (2026-10-28 19:10 UTC)
LAST_DAY = "2026-11-08"            # the window never extends past this day
SEED = 367
PLACEBOS = 10
PLACEBO_SHIFT = (3_600, 72_000)    # buckets: a circular shift of the signal by 6 minutes to 2 hours
KINDS = ("strict", "touch")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def frozen_inputs(prereg_path, root=ROOT):
    """Every file in the PREREG's inputs block must still hash to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    shas = {}
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
        shas[rel] = got
    return shas


def days_between(first, last):
    a, b = dt.date.fromisoformat(first), dt.date.fromisoformat(last)
    return [(a + dt.timedelta(d)).isoformat() for d in range((b - a).days + 1)]


def day_ms(day):
    return pd.Timestamp(day, tz="UTC").value // 10**6


def finished_days(data=DATA, first=FIRST_DAY, last=LAST_DAY, today=None):
    """Days from `first` whose daily book and trade files both exist (a day the recorder has merged), up to `last` and
    never the current UTC day. Gaps are allowed: a missing day is simply not usable."""
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    return [d for d in days_between(first, last)
            if d < today and (data / "book" / f"{d}.parquet").exists() and (data / "trades" / f"{d}.parquet").exists()]


def read_rows(data, day, coin):
    """The columns the rule needs for one coin and day: book (t, v, s, bid, ask) and trades (t, v, s, ls, hb), only the
    series of the rule (Binance USDT and USDC, Bybit USDT). Sizes are never read."""
    syms = [coin + "USDT", coin + "USDC"]
    book = pd.read_parquet(data / "book" / f"{day}.parquet", columns=["t", "v", "s", "bid", "ask"],
                           filters=[("s", "in", syms)])
    trades = pd.read_parquet(data / "trades" / f"{day}.parquet", columns=["t", "v", "s", "ls", "hb"],
                             filters=[("s", "in", [coin + "USDC"])])
    keep = (book.v == "binance") | ((book.v == "bybit") & (book.s == coin + "USDT"))
    return book[keep], trades[trades.v == "binance"]


def build(data, coin, grid_days):
    """The coin's grids over the consecutive days `grid_days` (a day without files is a block of NaN): the USDC bid,
    ask and mid, the Binance USDT and Bybit mids, and the USDC trade extremes."""
    first_ms = day_ms(grid_days[0])
    n = len(grid_days) * rule.DAY_BUCKETS
    parts = {"book": [], "trades": []}
    rows = {}
    for d in grid_days:
        if not ((data / "book" / f"{d}.parquet").exists() and (data / "trades" / f"{d}.parquet").exists()):
            continue
        b, t = read_rows(data, d, coin)
        parts["book"].append(b)
        parts["trades"].append(t)
        rows[d] = (len(b), len(t))
    book = pd.concat(parts["book"] or [pd.DataFrame(columns=["t", "v", "s", "bid", "ask"])], ignore_index=True)
    trades = pd.concat(parts["trades"] or [pd.DataFrame(columns=["t", "ls", "hb"])], ignore_index=True)

    def series(v, s):
        r = book[(book.v == v) & (book.s == s)]
        return rule.ffill_mid(rule.to_index(r.t.to_numpy(), first_ms), r.bid.to_numpy(), r.ask.to_numpy(), n)

    mid_c, bid_c, ask_c = series("binance", coin + "USDC")
    mid_u = series("binance", coin + "USDT")[0]
    mid_b = series("bybit", coin + "USDT")[0]
    ls, hb = rule.trade_extremes(rule.to_index(trades.t.to_numpy(), first_ms), trades.ls.to_numpy(),
                                 trades.hb.to_numpy(), n)
    return {"mid_c": mid_c, "bid_c": bid_c, "ask_c": ask_c, "mid_u": mid_u, "mid_b": mid_b, "ls": ls, "hb": hb,
            "n": n, "rows": rows}


def coverage(g, grid_days):
    """Per day, the share of buckets with a USDC, Binance USDT and Bybit mid, and the days' trade-bucket counts."""
    ok = np.isfinite(g["mid_c"]) & np.isfinite(g["mid_u"]) & np.isfinite(g["mid_b"])
    D = rule.DAY_BUCKETS
    return {d: (float(ok[i * D:(i + 1) * D].mean()), int(np.isfinite(g["ls"][i * D:(i + 1) * D]).sum()
                                                          + np.isfinite(g["hb"][i * D:(i + 1) * D]).sum()))
            for i, d in enumerate(grid_days)}


def summary_rows(blocks, vals):
    mean, se, t, n, h = rule.block_stat(blocks, vals)
    return {"mean": mean, "se": se, "t": t, "n": n, "blocks": h, "p": rule.p_one_sided(t, h)}


def candidates(x, th, quotable):
    return np.flatnonzero(quotable & np.isfinite(x) & np.isfinite(th) & (np.abs(x) >= th) & (x != 0))


def stale_marks(x, out, ks, kind, fills):
    """Kept quotes that filled but whose markout bucket had no fresh USDC mid."""
    j = np.where(x[ks] > 0, out[f"bid_{kind}_j"][ks], out[f"ask_{kind}_j"][ks])
    return int((j >= 0).sum() - fills)


def score_coin(g, coin, decision_days, grid_days, rng):
    """All rules, controls, placebos and the gross lead diagnostic of one coin."""
    n, D, H = g["n"], rule.DAY_BUCKETS, rule.HOUR_BUCKETS
    day_ix = {d: i for i, d in enumerate(grid_days)}
    dec = np.zeros(n, dtype=bool)
    for d in decision_days:
        dec[day_ix[d] * D:(day_ix[d] + 1) * D] = True
    quotable = dec & np.isfinite(g["bid_c"]) & np.isfinite(g["ask_c"])
    rules, controls, placebos, daily, lead = [], [], [], [], []
    sig = {v: rule.signal(g["mid_u" if v == "binance_usdt" else "mid_b"], g["mid_c"]) for v in rule.LEADS}
    thr = {(v, q): rule.thresholds(sig[v], q) for v in rule.LEADS for q in rule.PCTS}
    for lag in rule.LAGS:
        out = rule.outcomes(g["bid_c"], g["ask_c"], g["mid_c"], g["ls"], g["hb"], lag)
        valid = np.flatnonzero(quotable)
        for side in ("bid", "ask"):
            for kind in KINDS:
                _, kf, _, m = rule.control_fills(valid, side, out, lag, kind)
                controls.append({"coin": coin, "lag_ms": lag * 100, "side": side, "kind": kind,
                                 "decisions": len(valid), **summary_rows(kf // H, m)})
        move = np.full(n, np.nan)                           # the USDC mid from the order being live to one second on
        a, b = lag, lag + rule.MARK
        move[:n - b] = 1e4 * (g["mid_c"][b:] / g["mid_c"][a:n - b + a] - 1)
        for v in rule.LEADS:
            x = sig[v]
            for q in rule.PCTS:
                th = thr[(v, q)]
                name = f"{coin}|{v}|L{lag * 100}|p{q}"
                cand = candidates(x, th, quotable)
                row = {"rule": name, "coin": coin, "lead": v, "lag_ms": lag * 100, "pct": q, "candidates": len(cand)}
                for kind in KINDS:
                    ks, kf, _, m = rule.rule_fills(cand, x, out, lag, kind)
                    row.update({f"{kind}_{k}": val for k, val in summary_rows(kf // H, m).items()})
                    row[f"{kind}_decisions"] = len(ks)
                    row[f"{kind}_stale_marks"] = stale_marks(x, out, ks, kind, len(m))
                    if kind != "strict":
                        continue
                    for d in decision_days:
                        sel = (kf // D) == day_ix[d]
                        daily.append({"rule": name, "day": d, "n": int(sel.sum()),
                                      "mean": float(m[sel].mean()) if sel.any() else float("nan")})
                    shifted = []
                    for _ in range(PLACEBOS):
                        sh = int(rng.integers(*PLACEBO_SHIFT))
                        xs, ths = np.roll(x, sh), np.roll(th, sh)
                        ms = rule.rule_fills(candidates(xs, ths, quotable), xs, out, lag, "strict")[3]
                        shifted.append(float(ms.mean()) if len(ms) else float("nan"))
                    shifted = np.asarray(shifted)
                    placebos.append({"rule": name, "actual": row["strict_mean"],
                                     "placebo_mean": float(np.nanmean(shifted)),
                                     "placebo_sd": float(np.nanstd(shifted, ddof=1)),
                                     "placebos": int(np.isfinite(shifted).sum())})
                    gm = np.sign(x[cand]) * move[cand]
                    ok = np.isfinite(gm)
                    lead.append({"rule": name, **summary_rows(cand[ok] // H, gm[ok])})
                rules.append(row)
    return rules, controls, placebos, daily, lead


def run(plumbing=False, data=DATA, lane=LANE, check=True, today=None, first=FIRST_DAY, last=LAST_DAY):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
    avail = finished_days(data, first, last, today)
    if not avail:
        log("no finished day yet: run scripts/record_hft.py ensure after 00:30 UTC")
        return None
    grid_days = days_between((dt.date.fromisoformat(avail[0]) - dt.timedelta(1)).isoformat(), avail[-1])
    cov = {}
    grids = {}
    for coin in rule.COINS:
        grids[coin] = build(data, coin, grid_days)
        for d, (share, trade_buckets) in coverage(grids[coin], grid_days).items():
            cov[(coin, d)] = (share, trade_buckets)
        log(f"{coin}: built {len(grid_days)} days, rows per day {grids[coin]['rows']}")
    usable = [d for d in avail
              if all(cov[(c, d)][0] >= rule.MIN_DAY_COVERAGE and cov[(c, d)][1] > 0 for c in rule.COINS)]
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"coin": c, "day": d, "coverage": s, "trade_buckets": tb, "usable": d in usable}
                  for (c, d), (s, tb) in sorted(cov.items(), key=lambda kv: (kv[0][0], kv[0][1]))]).to_csv(
        res / "coverage.csv", index=False)
    log(f"finished days {avail}; usable {usable}")
    if plumbing or len(usable) < rule.MIN_DAYS:
        state, text = ("PLUMBING", "counts only") if plumbing else rule.verdict([], len(usable))
        if not plumbing:
            (res / "summary.json").write_text(json.dumps({"registry": REGISTRY, "state": state, "text": text,
                                                          "usable_days": usable}, indent=1) + "\n")
        log(state, text)
        return state
    rng = np.random.default_rng(SEED)
    allr, allc, allp, alld, alll = [], [], [], [], []
    for coin in rule.COINS:
        r, c, p, d, ld = score_coin(grids[coin], coin, usable, grid_days, rng)
        allr += r
        allc += c
        allp += p
        alld += d
        alll += ld
        log(f"{coin}: scored {len(r)} rules")
    p = np.array([r["strict_p"] for r in allr])
    adj = rule.holm(p)
    for r, a in zip(allr, adj):
        r["p_holm"] = float(a)
        r["mean_strict"], r["n_strict"], r["mean_touch"] = r["strict_mean"], r["strict_n"], r["touch_mean"]
        for k in rule.COST_MULTS:
            r[f"strict_net_{k}x"] = r["strict_mean"] - k * rule.UNIT_COST_BP
    state, text = rule.verdict(allr, len(usable))
    pd.DataFrame(allr).to_csv(res / "rules.csv", index=False)
    pd.DataFrame(allc).to_csv(res / "controls.csv", index=False)
    pd.DataFrame(allp).to_csv(res / "placebos.csv", index=False)
    pd.DataFrame(alld).to_csv(res / "daily.csv", index=False)
    pd.DataFrame(alll).to_csv(res / "lead_gross.csv", index=False)
    files = [{"path": str(f.relative_to(data)), "sha256": prereg.sha256_file(f)}
             for d in grid_days for kind in ("book", "trades") if (f := data / kind / f"{d}.parquet").exists()]
    pd.DataFrame(files).to_csv(res / "data_files.csv", index=False)
    (res / "summary.json").write_text(json.dumps({"registry": REGISTRY, "state": state, "text": text,
                                                  "usable_days": usable, "rules": rule.TRIALS,
                                                  "cost_unit_bp": rule.UNIT_COST_BP}, indent=1) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    run(plumbing=a.plumbing)
