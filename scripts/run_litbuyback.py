"""litbuyback_v1 (R486, M537): does Lighter's daily LIT buyback, as a share of LIT's own daily traded value, predict
LIT's next-week return on Lighter's LIT perp? Gate 0 on history, as set out in experiments/litbuyback_v1/PREREG.md.

Verifies the PREREG and its inputs block (the three exchangeMetrics bodies and this file), the pinned commit of the
data branch claude/okx-xperp-data and the lit/ tree hashes, then reads lit/ through `git cat-file` at that commit
(the main worktree is never switched). Nothing dated after the sample end 2026-11-10 is read: files are chosen by
their date name and every row is checked against the cut (later LIT prices sit inside R447's forward window).

usage: python scripts/run_litbuyback.py
"""
import hashlib
import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LANE = ROOT / "experiments" / "litbuyback_v1"
INTAKE = ROOT / "research" / "intake" / "hlp_llp_lit_20261113"
PIN = "0364bbc63ec3bc4d7cc135ff4b060cabf8127062"      # origin/claude/okx-xperp-data on 2026-11-13
TREES = {"lit": "1a377a6aaa39e065aa3a4ecac69329a3fabd4f65",
         "lit/perp_candles_1d": "6363224ed40d96438abff4b6f151375a7a2d4da2",
         "lit/spot_candles_1d": "d57125a278544aa6e919db70a57db84bb9a28323",
         "lit/perp_funding": "52362e744c3229230305808d1708db27757b6234"}
SAMPLE_END = "2026-11-10"          # last UTC day whose price, volume or funding may be read
FIRST_BUYBACK = "2025-12-30"
FIRST_PERP = "2026-01-02"
H = 7                              # target horizon and block length, days
LAST_T = "2026-11-03"              # t + H <= SAMPLE_END
MIN_SHIFT = 14                     # circular shifts k in [14, n - 14]
MED_WIN = 60                       # prior days of the 7-day mean signal behind the median
COST = {1: 0.002, 2: 0.004, 3: 0.006}   # round trip per entered block (10 bp a leg a side at 1x, as R447)
DAY = 86_400_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def day_label(t):
    return str(pd.Timestamp(int(t), unit="ms", tz="UTC").date())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- inputs
def check_inputs(prereg_path):
    """Every file in the PREREG's inputs block hashes to its frozen sha256."""
    text = Path(prereg_path).read_text()
    block = re.search(r"```inputs\n(.*?)```", text, re.S).group(1)
    n = 0
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = sha(ROOT / rel)
        if got != want:
            raise SystemExit(f"{rel}: sha256 {got} != frozen {want}")
        n += 1
    return n


def git(*args, inp=None):
    r = subprocess.run(["git", "-C", str(ROOT), *args], input=inp, capture_output=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.decode().strip()}")
    return r.stdout


def check_pin():
    for rel, want in TREES.items():
        got = git("rev-parse", f"{PIN}:{rel}").decode().strip()
        if got != want:
            raise SystemExit(f"{PIN[:12]}:{rel} tree {got} != frozen {want}")


class GitReader:
    """lit/ at the pinned commit, read with git ls-tree and git cat-file --batch."""

    def list(self, folder):
        return git("ls-tree", "--name-only", f"{PIN}:{folder}").decode().split()

    def read(self, paths):
        if not paths:
            return {}
        out = git("cat-file", "--batch", inp="".join(f"{PIN}:{p}\n" for p in paths).encode())
        res, pos = {}, 0
        for p in paths:
            nl = out.index(b"\n", pos)
            head = out[pos:nl].split()
            if len(head) != 3 or head[1] != b"blob":
                raise SystemExit(f"{p}: {out[pos:nl].decode()}")
            size = int(head[2])
            res[p] = out[nl + 1:nl + 1 + size].decode()
            pos = nl + 1 + size + 1
        return res


# ---------------------------------------------------------------- the sample-end cut
def dated_names(names, end=SAMPLE_END):
    """<YYYY-MM-DD>.csv names dated on or before end; anything else is refused or left unread."""
    keep = []
    for n in names:
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\.csv", n)
        if not m:
            raise ValueError(f"unexpected file {n!r}")
        if m.group(1) <= end:
            keep.append(n)
    return sorted(keep)


def enforce_cut(df, end=SAMPLE_END, col="ts"):
    """Refuse any row stamped at or after 00:00 UTC of the day after end."""
    if len(df) and (df[col].astype(np.int64) >= ms(end) + DAY).any():
        raise ValueError(f"row stamped after the sample end {end}")
    return df


def read_folder(reader, folder, end=SAMPLE_END):
    names = dated_names(reader.list(folder), end)
    bodies = reader.read([f"{folder}/{n}" for n in names])
    frames = []
    for n in names:
        f = pd.read_csv(io.StringIO(bodies[f"{folder}/{n}"]))
        if len(f) and {day_label(t) for t in f.ts} != {n[:-4]}:
            raise ValueError(f"{folder}/{n}: rows outside the file's day")
        frames.append(f)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["ts"])
    return enforce_cut(df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True), end)


def load_lit(reader, end=SAMPLE_END):
    """Perp close and quote volume, spot quote volume, and funding summed by UTC day (rate + when longs pay)."""
    perp = read_folder(reader, "lit/perp_candles_1d", end)
    spot = read_folder(reader, "lit/spot_candles_1d", end)
    fund = read_folder(reader, "lit/perp_funding", end)
    p = pd.DataFrame({"close": perp.close.astype(float).values, "qv": perp.quote_volume.astype(float).values},
                     index=[day_label(t) for t in perp.ts])
    s = pd.Series(spot.quote_volume.astype(float).values, index=[day_label(t) for t in spot.ts])
    fund = fund.assign(day=[day_label(t) for t in fund.ts])
    f = fund.groupby("day").agg(rate=("rate", "sum"), hours=("rate", "size"))
    return p, s, f


def load_buyback(path, end=SAMPLE_END):
    """exchangeMetrics points {timestamp (s, 00:00 UTC of the day), data} -> Series by UTC day, cut at end."""
    pts = json.loads(Path(path).read_text())["metrics"]
    s = pd.Series({day_label(int(p["timestamp"]) * 1000): float(p["data"]) for p in pts}, dtype=float).sort_index()
    return s[s.index <= end]


# ---------------------------------------------------------------- signal, target, statistics
def days(first, last):
    return [day_label(t) for t in range(ms(first), ms(last) + DAY, DAY)]


def share(buyback_usdc, perp_qv, spot_qv):
    """s_t = buyback USDC on day t / (perp + spot quote volume on day t); NaN if any part is missing."""
    idx = sorted(set(buyback_usdc.index) | set(perp_qv.index) | set(spot_qv.index))
    tv = perp_qv.reindex(idx) + spot_qv.reindex(idx)
    s = buyback_usdc.reindex(idx) / tv
    return s.where(tv > 0)


def fwd_return(close, h):
    """r_t = close(t+h) / close(t) - 1 by calendar day; NaN where either close is missing."""
    idx = days(close.index[0], close.index[-1])
    c = close.reindex(idx)
    return c.shift(-h) / c - 1


def ranks(x):
    return pd.Series(x).rank(method="average").to_numpy(float)


def spearman(x, y):
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def circular_null(x, y, min_shift=MIN_SHIFT):
    """Spearman rho of x against y, and the rhos of x circularly shifted by k for every k in [min_shift,
    n - min_shift]. p_two = share of |rho_k| >= |rho|; p_one = share of rho_k >= rho."""
    rx, ry = ranks(x), ranks(y)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    n = len(rx)
    ks = np.arange(min_shift, n - min_shift + 1)
    null = np.array([np.corrcoef(np.roll(rx, k), ry)[0, 1] for k in ks])
    return {"n": int(n), "rho": rho, "shifts": int(len(ks)),
            "p_two": float((np.abs(null) >= abs(rho)).mean()) if len(ks) else None,
            "p_one": float((null >= rho).mean()) if len(ks) else None,
            "null_mean": float(null.mean()) if len(ks) else None}


def paired(sig, tgt, first, last):
    """Days t in [first, last] where both are finite, as aligned arrays."""
    d = days(first, last)
    a, b = sig.reindex(d), tgt.reindex(d)
    ok = a.notna() & b.notna() & np.isfinite(a) & np.isfinite(b)
    return a[ok].to_numpy(float), b[ok].to_numpy(float), [x for x, k in zip(d, ok) if k]


def smoothed(s, first, last):
    """sbar_t = mean of s over t-6..t (all 7 present); med_t = median of sbar over t-60..t-1 (all 60 present)."""
    idx = days(first, last)
    x = s.reindex(idx)
    sbar = x.rolling(H, min_periods=H).mean()
    med = sbar.shift(1).rolling(MED_WIN, min_periods=MED_WIN).median()
    return sbar, med


def funding_paid(fund, b):
    """Funding paid by a long held from the close of b to the close of b+7: hours stamped on days b+1..b+7
    (R447's day convention), rate + when longs pay. Returns (sum, hours)."""
    d = days(day_label(ms(b) + DAY), day_label(ms(b) + H * DAY))
    f = fund.reindex(d)
    return float(f.rate.fillna(0).sum()), int(f.hours.fillna(0).sum())


def book(s, close, fund, first=FIRST_PERP, last=LAST_T, hist_first=None):
    """Non-overlapping blocks b = first + 7j <= last. Long the perp for 7 days if sbar_b > med_b, else flat. Blocks
    without a median (or sbar, or both closes) are skipped. Always-long benchmark over the same blocks."""
    sbar, med = smoothed(s, hist_first or min(s.index[0], first), last)
    c = close.copy()
    rows = []
    for j in range(10**6):
        b = day_label(ms(first) + j * H * DAY)
        if b > last:
            break
        e = day_label(ms(b) + H * DAY)
        if pd.isna(med.get(b)) or pd.isna(sbar.get(b)) or b not in c.index or e not in c.index:
            continue
        price = float(c[e] / c[b] - 1)
        fsum, hours = funding_paid(fund, b)
        long = bool(sbar[b] > med[b])
        gross = price - fsum
        r = {"start": b, "end": e, "sbar": float(sbar[b]), "median": float(med[b]), "long": int(long),
             "price": price, "funding_paid": fsum, "funding_hours": hours, "gross_long": gross}
        for m, cst in COST.items():
            r[f"bench_{m}x"] = gross - cst
            r[f"book_{m}x"] = (gross - cst) if long else 0.0
        r["book_gross"] = gross if long else 0.0
        rows.append(r)
    return pd.DataFrame(rows)


def simple_t(x):
    x = np.asarray(x, float)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def gates(corr, blocks):
    g1 = bool(corr["rho"] > 0 and corr["p_one"] is not None and corr["p_one"] < 0.05)
    b2 = blocks.book_2x if len(blocks) else pd.Series(dtype=float)
    t2 = simple_t(b2)
    g2 = bool(len(b2) and b2.mean() > 0 and np.isfinite(t2) and t2 >= 2)
    g3 = bool(len(blocks) and blocks.book_1x.mean() > blocks.bench_1x.mean())
    return {"G1_circular_p_one_lt_0.05_rho_gt_0": g1, "G2_book_2x_mean_gt_0_t_ge_2": g2,
            "G3_book_1x_beats_always_long": g3}, {"book_2x_t": t2}


def verdict(g):
    return "SIGNAL" if all(g.values()) else "NULL"


def summ(x):
    x = np.asarray(x, float)
    return {"n": int(len(x)), "mean_pct": float(x.mean() * 100) if len(x) else None, "t": simple_t(x),
            "sum_pct": float(x.sum() * 100)}


def main():
    from lab import prereg
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    log(f"inputs: {check_inputs(LANE / 'PREREG.md')} files match the PREREG")
    check_pin()
    log(f"data: {PIN[:12]} lit/ trees match")
    reader = GitReader()
    perp, spot_qv, fund = load_lit(reader)
    bb = load_buyback(INTAKE / "em_buyback_usdc_all.json")
    first = max(FIRST_BUYBACK, FIRST_PERP)
    log(f"perp {perp.index[0]}..{perp.index[-1]} ({len(perp)}), spot {spot_qv.index[0]}..{spot_qv.index[-1]} "
        f"({len(spot_qv)}), funding days {len(fund)} ({int(fund.hours.sum())} h), buyback {bb.index[0]}.."
        f"{bb.index[-1]} ({len(bb)})")
    s = share(bb, perp.qv, spot_qv)
    r7 = fwd_return(perp.close, H)
    r1 = fwd_return(perp.close, 1)
    x, y, used = paired(s, r7, first, LAST_T)
    corr = circular_null(x, y)
    corr.update(first=used[0], last=used[-1])
    blocks = book(s, perp.close, fund, first, LAST_T)
    g, gd = gates(corr, blocks)
    res = {"prereg_sha": prereg.sha256_file(LANE / "PREREG.md"), "data_commit": PIN, "sample_end": SAMPLE_END,
           "signal_denominator": "LIT perp + LIT/USDC spot quote volume (lit/perp_candles_1d, lit/spot_candles_1d)",
           "correlation_7d": corr, "book": {f"{m}x": summ(blocks[f"book_{m}x"]) for m in COST},
           "benchmark_always_long": {f"{m}x": summ(blocks[f"bench_{m}x"]) for m in COST},
           "blocks": {"n": int(len(blocks)), "long": int(blocks.long.sum()),
                      "first": blocks.start.iloc[0], "last": blocks.start.iloc[-1],
                      "funding_hours_min": int(blocks.funding_hours.min()),
                      "book_gross": summ(blocks.book_gross)},
           "gates": g, "gate_detail": gd, "verdict": verdict(g), "trials": 2}
    x1, y1, u1 = paired(s, r1, first, day_label(ms(SAMPLE_END) - DAY))
    c1 = circular_null(x1, y1)
    c1.update(first=u1[0], last=u1[-1])
    ds = s - s.reindex(days(s.index[0], s.index[-1])).shift(H)
    xd, yd, ud = paired(ds, r7, first, LAST_T)
    cd = circular_null(xd, yd)
    cd.update(first=ud[0], last=ud[-1])
    sd = s.reindex(used)
    res["reported"] = {"correlation_1d": c1, "change_signal_7d": cd,
                       "share_pct": {"median": float(sd.median() * 100), "p10": float(sd.quantile(.1) * 100),
                                     "p90": float(sd.quantile(.9) * 100)}}
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    blocks.to_csv(out / "blocks.csv", index=False, float_format="%.8g", lineterminator="\n")
    pd.DataFrame({"day": used, "share": x, "r7": y}).to_csv(out / "pairs.csv", index=False, float_format="%.8g",
                                                            lineterminator="\n")
    (out / "verdict.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    for k in ("correlation_7d", "book", "benchmark_always_long", "blocks", "gates", "gate_detail", "reported"):
        log(k, json.dumps(res[k], default=float))
    log("verdict", res["verdict"])


if __name__ == "__main__":
    main()
