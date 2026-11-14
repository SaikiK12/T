"""R433 lighter_flow_v1 (M441): does Lighter's public, account-level taker flow carry information that persists out of
sample, and can a slow follower (or fader) of the accounts that were informed on earlier days make money after the
book cost? Lighter commodity perps WTI, BRENTOIL and NATGAS, recorded public stream 2026-10-28..11-06. Files only, no
orders, no account is linked to a person.

Design (frozen in experiments/lighter_flow_v1/PREREG.md):
- Clocks: trades carry Lighter's trade timestamp T (ms) and quotes Lighter's ticker last_updated_at `upd` (us); both
  are Lighter's clock, so every lookup (markout mid, entry and exit touch) is an as-of read in Lighter's clock. The
  local receive clock (`t`, drifting by up to about 1.5 s against Lighter on these files) is used only to tag each row
  with the recorder session that received it and to drop trades replayed on reconnect or queued over 5 s.
- Train days 2026-10-28 and 2026-10-29 score taker accounts by a shrunk mean signed markout at horizon h:
  score_h(a) = sum_i M_i(h) / (n_a + K), M_i(h) = side_i * 1e4 * ln(mid(T_i + h) / price_i), pooled over the three
  markets, accounts with >= N_MIN eligible train taker trades. R426's seen fragment (10-29 01:31:45-01:35:30) is
  excluded from scoring.
- Test days 2026-10-30 and 11-02..11-06: a test-day taker trade by one of the TOP 10 accounts (score > 0) is a follow
  signal; by one of the BOTTOM 10 (score < 0) a fade signal. Entry E = T + delay at the touch as of E (buy at the ask,
  sell at the bid), exit E + h at the opposite touch; one open position per market and cell (a signal while a position
  is open is skipped). Standard account: 0 fee; the 300 ms taker delay is inside the delay.
- Part A (persistence, information only): Spearman rank correlation of train score with test mean markout per account,
  and the informed accounts' test markout minus everyone else's.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "lighter_flow_v1"
DATA = ROOT / "data" / "lighter_trades"
MARKETS = ("WTI", "BRENTOIL", "NATGAS")
TRAIN_DAYS = ("2026-10-28", "2026-10-29")
TEST_DAYS = ("2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06")
SEEN = ("2026-10-29T01:31:45Z", "2026-10-29T01:35:30Z")   # R426's already-read fragment, excluded from scoring
HORIZONS = (10_000, 60_000, 300_000)        # ms
DELAYS = (300, 1_300, 5_300)                # ms after the signal trade's T; 300 = taker delay only (counterfactual)
DIRECTIONS = ("follow", "fade")
PRIMARY = dict(direction="follow", h=60_000, delay=1_300)
N_MIN, K_SHRINK, TOP = 20, 20.0, 10
EDGE_MS = 2_000                             # session-edge margin for the local/Lighter clock offset
QUEUE_MS = 5_000                            # a trade received over 5 s after T would not have been seen in time
NOTIONAL = 1_000.0                          # USD per trade, thin-touch diagnostic only
PREMIUM_TAKER_BP = 2.8                      # docs/VENUE_STRUCTURE.md, Premium account, sensitivity only
COST_MULTS = (1, 2, 3)
N_PLACEBO, BOOT, SEED = 200, 2000, 433
MIN_TRADES = 100
TRIALS = len(DIRECTIONS) * len(HORIZONS) * len(DELAYS) + len(HORIZONS) + len(HORIZONS)   # 18 + 3 controls + 3 Part A
US = 1000


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def check_inputs(prereg_path, root=ROOT):
    """Every file in the PREREG's inputs block must still hash to its frozen sha256; then every data file listed in
    the frozen data manifest must hash to its listed sha256, and no listed folder may hold an unlisted file."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    shas = {}
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
        shas[rel] = got
    man = json.loads((root / "experiments/lighter_flow_v1/data_manifest.json").read_text())
    listed = set(man["files"])
    for rel, want in man["files"].items():
        if prereg.sha256_file(root / rel) != want:
            raise prereg.PreregError(f"{rel}: data file changed since the manifest")
    present = {str(p.relative_to(root)) for p in (root / man["root"]).rglob("*.parquet")}
    if present != listed:
        raise prereg.PreregError(f"data folder differs from manifest: {len(present ^ listed)} files")
    return shas


def build_manifest(root=ROOT):
    files = sorted((root / "data/lighter_trades").rglob("*.parquet"))
    return {"root": "data/lighter_trades",
            "files": {str(p.relative_to(root)): prereg.sha256_file(p) for p in files}}


# ---------- loading ----------
def sessions(path):
    s = pd.read_csv(path)
    us = lambda c: pd.to_datetime(c, utc=True).dt.tz_localize(None).values.astype("datetime64[us]").astype(np.int64)
    st = us(s.start_utc)
    en = us(s.end_utc) + 999_999
    o = np.argsort(st, kind="stable")
    return st[o], en[o]


def session_of(t_us, st, en):
    """Index of the recorder session whose [start, end] contains the local receive time, else -1."""
    i = np.searchsorted(st, t_us, "right") - 1
    ok = (i >= 0) & (t_us <= en[np.clip(i, 0, None)])
    return np.where(ok, i, -1)


def load_kind(kind, sym, data=DATA):
    fs = sorted((data / kind / sym).glob("*/*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True) if fs else None


def make_quotes(q, st, en):
    """Quotes sorted by Lighter's update time, each tagged with the session that received it."""
    q = q[(q.bid > 0) & (q.ask > q.bid)].copy()
    q["sess"] = session_of(q.t.values, st, en)
    q = q[q.sess >= 0].sort_values(["upd", "t"], kind="stable")
    return dict(u=q.upd.values.astype(np.int64), s=q.sess.values, bid=q.bid.values, ask=q.ask.values,
                bq=q.bq.values, aq=q.aq.values)


def make_trades(tr, st, en, sym):
    """Ordinary taker trades with the taker's account and side (+1 buy, -1 sell). R427's convention: maker_ask=1
    means the ask was the maker, so the bid account is the taker and bought."""
    tr = tr.drop_duplicates("trade_id").copy()
    tr["taker"] = np.where(tr.maker_ask == 1, tr.bid_acct, tr.ask_acct)
    tr["side"] = np.where(tr.maker_ask == 1, 1, -1)
    tr["sess"] = session_of(tr.t.values, st, en)
    T_us = tr["T"].values.astype(np.int64) * US
    start = np.where(tr.sess >= 0, st[np.clip(tr.sess, 0, None)], 0)
    tr["replay"] = (tr.sess < 0) | (T_us < start + EDGE_MS * US)
    tr["queued"] = (tr.t.values - T_us) > QUEUE_MS * US
    tr["day"] = pd.to_datetime(tr["T"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    tr["mkt"] = sym
    return tr.sort_values(["T", "trade_id"], kind="stable").reset_index(drop=True)


def eligible(tr):
    return (tr.liq == 0) & (tr.taker >= 0) & ~tr.replay & ~tr.queued & (tr.px > 0)


# ---------- as-of reads in Lighter's clock ----------
def asof(Q, x_ms, sess, st, en):
    """Touch as of Lighter time x (ms) from quotes received in session `sess`; NaN when x lies within EDGE_MS of the
    session's edges (local clock offset) or no quote of that session precedes x."""
    x_us = np.asarray(x_ms, np.int64) * US
    sess = np.asarray(sess)
    i = np.searchsorted(Q["u"], x_us, "right") - 1
    ic = np.clip(i, 0, None)
    sc = np.clip(sess, 0, None)
    ok = (i >= 0) & (sess >= 0) & (Q["s"][ic] == sess)
    ok &= (x_us >= st[sc] + EDGE_MS * US) & (x_us <= en[sc] - EDGE_MS * US)
    nan = np.nan
    return (np.where(ok, Q["bid"][ic], nan), np.where(ok, Q["ask"][ic], nan),
            np.where(ok, Q["bq"][ic], nan), np.where(ok, Q["aq"][ic], nan))


def markouts(tr, Q, h, st, en):
    """M_i(h) = side * 1e4 * ln(mid(T + h) / price), the mid as of T + h in the trade's own session."""
    b, a, _, _ = asof(Q, tr["T"].values + h, tr.sess.values, st, en)
    return tr.side.values * 1e4 * np.log((b + a) / 2 / tr.px.values)


# ---------- scores and sets ----------
def scores(m, acct, n_min=N_MIN, k=K_SHRINK):
    """Shrunk mean markout per account over finite markouts; accounts with fewer than n_min are dropped."""
    d = pd.DataFrame(dict(m=m, a=acct))
    d = d[np.isfinite(d.m)]
    g = d.groupby("a").m.agg(["sum", "count"])
    g = g[g["count"] >= n_min]
    return (g["sum"] / (g["count"] + k)).rename("score"), g["count"].rename("n")


def pick(score, top=TOP):
    s = score.sort_values(kind="stable")
    informed = s[s > 0].iloc[::-1].head(top).index.to_numpy()
    uninformed = s[s < 0].head(top).index.to_numpy()
    return informed, uninformed


# ---------- trading simulation ----------
def simulate(sig, Qs, delay, h, sign, st, en, notional=NOTIONAL):
    """sig: DataFrame of signal trades (T, side, sess, mkt). sign +1 follows, -1 fades. One open position per market:
    a signal whose entry falls before the previous exit in that market is skipped. Returns one row per trade."""
    out = []
    for mk, g in sig.groupby("mkt", sort=True):
        Q = Qs[mk]
        g = g.sort_values(["T", "trade_id"], kind="stable")
        E = g["T"].values + delay
        X = E + h
        bE, aE, bqE, aqE = asof(Q, E, g.sess.values, st, en)
        bX, aX, bqX, aqX = asof(Q, X, g.sess.values, st, en)
        d = sign * g.side.values
        last_exit = -np.inf
        for j in range(len(g)):
            if not (np.isfinite(bE[j]) and np.isfinite(bX[j])) or E[j] < last_exit:
                continue
            last_exit = X[j]
            mE, mX = (bE[j] + aE[j]) / 2, (bX[j] + aX[j]) / 2
            gross = d[j] * 1e4 * np.log(mX / mE)
            if d[j] > 0:
                cost = 1e4 * (np.log(aE[j] / mE) + np.log(mX / bX[j]))
                thin = aqE[j] * aE[j] < notional or bqX[j] * bX[j] < notional
            else:
                cost = 1e4 * (np.log(mE / bE[j]) + np.log(aX[j] / mX))
                thin = bqE[j] * bE[j] < notional or aqX[j] * aX[j] < notional
            out.append((mk, int(g["T"].values[j]), int(E[j]), int(d[j]), gross, cost, bool(thin),
                        g.day.values[j], int(g.taker.values[j])))
    df = pd.DataFrame(out, columns=["mkt", "T", "E", "dir", "gross", "cost", "thin", "day", "acct"])
    df["block"] = df.E // 3_600_000
    for k in COST_MULTS:
        df[f"net{k}"] = df.gross - k * df.cost
    df["net_premium"] = df.gross - df.cost - 2 * PREMIUM_TAKER_BP
    return df


def block_boot(values, blocks, rng, boot=BOOT):
    """Mean, 95% percentile interval and one-sided p (share of resampled means <= 0) resampling whole blocks."""
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    v, blocks = v[ok], np.asarray(blocks)[ok]
    if len(v) == 0:
        return dict(n=0, mean=None, lo=None, hi=None, p_le0=None, blocks=0)
    u, inv = np.unique(blocks, return_inverse=True)
    s, c = np.bincount(inv, v, len(u)), np.bincount(inv, None, len(u))
    pick_ = rng.integers(0, len(u), (boot, len(u)))
    means = s[pick_].sum(1) / np.maximum(c[pick_].sum(1), 1)
    return dict(n=int(len(v)), mean=float(v.mean()), lo=float(np.percentile(means, 2.5)),
                hi=float(np.percentile(means, 97.5)), p_le0=float((means <= 0).mean()), blocks=int(len(u)))


def block_boot_diff(v, cls, blocks, rng, boot=BOOT):
    """Mean of class 1 minus mean of class 0, resampling whole blocks (both classes move together)."""
    v, cls, blocks = np.asarray(v, float), np.asarray(cls), np.asarray(blocks)
    ok = np.isfinite(v)
    v, cls, blocks = v[ok], cls[ok], blocks[ok]
    u, inv = np.unique(blocks, return_inverse=True)
    s1 = np.bincount(inv, np.where(cls == 1, v, 0.0), len(u))
    n1 = np.bincount(inv, (cls == 1).astype(float), len(u))
    s0 = np.bincount(inv, np.where(cls == 0, v, 0.0), len(u))
    n0 = np.bincount(inv, (cls == 0).astype(float), len(u))
    p = rng.integers(0, len(u), (boot, len(u)))
    diff = s1[p].sum(1) / np.maximum(n1[p].sum(1), 1) - s0[p].sum(1) / np.maximum(n0[p].sum(1), 1)
    point = s1.sum() / max(n1.sum(), 1) - s0.sum() / max(n0.sum(), 1)
    return dict(diff=float(point), lo=float(np.percentile(diff, 2.5)), hi=float(np.percentile(diff, 97.5)),
                n1=int(n1.sum()), n0=int(n0.sum()))


def spearman(x, y):
    rx, ry = pd.Series(x).rank().values, pd.Series(y).rank().values
    if len(rx) < 3 or rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def verdict(df, ci, placebo_pct, n_min=MIN_TRADES):
    """PASS: n >= n_min, mean net at 1x > 0 with block lower bound > 0, mean net at 2x > 0, and the actual mean beats
    at least 95% of random-account placebo sets. Fewer trades: INCONCLUSIVE. Else NULL."""
    if len(df) < n_min:
        return "INCONCLUSIVE"
    if (df.net1.mean() > 0 and ci["lo"] is not None and ci["lo"] > 0 and df.net2.mean() > 0
            and placebo_pct is not None and placebo_pct >= 0.95):
        return "PASS"
    return "NULL"


# ---------- data assembly ----------
def assemble(data=DATA):
    st, en = sessions(data / "sessions.csv")
    Qs, T = {}, []
    for mk in MARKETS:
        Qs[mk] = make_quotes(load_kind("quote", mk, data), st, en)
        T.append(make_trades(load_kind("trade", mk, data), st, en, mk))
    tr = pd.concat(T, ignore_index=True)
    tr = tr[tr.day.isin(TRAIN_DAYS + TEST_DAYS)].reset_index(drop=True)
    return tr, Qs, st, en


def seen_mask(tr):
    a = pd.Timestamp(SEEN[0]).value // 10**6
    b = pd.Timestamp(SEEN[1]).value // 10**6
    return (tr["T"] >= a) & (tr["T"] <= b)


def plumbing(data=DATA):
    """Counts only: trades per day/market after each filter, account counts, and whether entry/exit touches would be
    covered by a recorded session. No markout, mid change or return is computed."""
    tr, Qs, st, en = assemble(data)
    el = eligible(tr)
    out = dict(trades=int(len(tr)), by_filter=dict(liq=int((tr.liq == 1).sum()), replay=int(tr.replay.sum()),
                                                   queued=int(tr.queued.sum()), eligible=int(el.sum())),
               seen_fragment_trades=int(seen_mask(tr).sum()))
    per = tr[el].groupby(["day", "mkt"]).size().unstack(fill_value=0)
    out["eligible_by_day_market"] = {d: {m: int(v) for m, v in r.items()} for d, r in per.iterrows()}
    trn = tr[el & tr.day.isin(TRAIN_DAYS) & ~seen_mask(tr)]
    tst = tr[el & tr.day.isin(TEST_DAYS)]
    c = trn.taker.value_counts()
    out["train_taker_accounts"] = int(len(c))
    out["train_accounts_ge_nmin"] = int((c >= N_MIN).sum())
    out["test_taker_accounts"] = int(tst.taker.nunique())
    out["test_trades_by_train_accounts_ge_nmin"] = int(tst.taker.isin(c[c >= N_MIN].index).sum())
    cov = {}
    for h in HORIZONS:
        for dl in DELAYS:
            ok = np.zeros(len(tst), bool)
            for mk in MARKETS:
                g = tst.mkt.values == mk
                b1 = asof(Qs[mk], tst["T"].values[g] + dl, tst.sess.values[g], st, en)[0]
                b2 = asof(Qs[mk], tst["T"].values[g] + dl + h, tst.sess.values[g], st, en)[0]
                ok[g] = np.isfinite(b1) & np.isfinite(b2)
            cov[f"h{h // 1000}s_d{dl}ms"] = round(float(ok.mean()), 4)
    out["test_covered_share"] = cov
    out["quotes"] = {mk: int(len(Qs[mk]["u"])) for mk in MARKETS}
    return out


# ---------- the run ----------
def run(data=DATA, lane=LANE, rng_seed=SEED, verify=True):
    if verify:
        sha = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {sha[:12]}; {len(check_inputs(lane / 'PREREG.md'))} inputs match; trials {TRIALS}")
    rng = np.random.default_rng(rng_seed)
    tr, Qs, st, en = assemble(data)
    el = eligible(tr)
    train = tr[el & tr.day.isin(TRAIN_DAYS) & ~seen_mask(tr)].reset_index(drop=True)
    test = tr[el & tr.day.isin(TEST_DAYS)].reset_index(drop=True)
    res = dict(trials=TRIALS, n_train=int(len(train)), n_test=int(len(test)), cells=[], partA=[])
    sets, train_scores = {}, {}
    for h in HORIZONS:
        m = np.full(len(train), np.nan)
        for mk in MARKETS:
            g = train.mkt.values == mk
            m[g] = markouts(train[g], Qs[mk], h, st, en)
        sc, n = scores(m, train.taker.values)
        train_scores[h] = (sc, n)
        sets[h] = pick(sc)
        res[f"eligible_accounts_h{h // 1000}s"] = int(len(sc))
    rows, primary = [], None
    for h in HORIZONS:
        inf, uninf = sets[h]
        for direction, accts, sign in (("follow", inf, 1), ("fade", uninf, -1)):
            sig = test[test.taker.isin(accts)]
            for dl in DELAYS:
                df = simulate(sig, Qs, dl, h, sign, st, en)
                ci = block_boot(df.net1, df.block, rng) if len(df) else block_boot([], [], rng)
                row = dict(direction=direction, h_s=h // 1000, delay_ms=dl, n=int(len(df)),
                           gross=float(df.gross.mean()) if len(df) else None,
                           cost=float(df.cost.mean()) if len(df) else None,
                           net1=float(df.net1.mean()) if len(df) else None,
                           net2=float(df.net2.mean()) if len(df) else None,
                           net3=float(df.net3.mean()) if len(df) else None,
                           net_premium=float(df.net_premium.mean()) if len(df) else None,
                           lo=ci["lo"], hi=ci["hi"], blocks=ci["blocks"],
                           thin=float(df.thin.mean()) if len(df) else None)
                rows.append(row)
                if (direction, h, dl) == (PRIMARY["direction"], PRIMARY["h"], PRIMARY["delay"]):
                    primary = (df, ci)
    for h in HORIZONS:          # controls: follow every eligible test taker
        df = simulate(test, Qs, 1_300, h, 1, st, en)
        ci = block_boot(df.net1, df.block, rng)
        rows.append(dict(direction="control_all", h_s=h // 1000, delay_ms=1_300, n=int(len(df)),
                         gross=float(df.gross.mean()), cost=float(df.cost.mean()), net1=float(df.net1.mean()),
                         net2=float(df.net2.mean()), net3=float(df.net3.mean()),
                         net_premium=float(df.net_premium.mean()), lo=ci["lo"], hi=ci["hi"], blocks=ci["blocks"],
                         thin=float(df.thin.mean())))
    res["cells"] = rows
    # placebo for the primary cell: random sets of TOP accounts among the eligible ones
    df, ci = primary
    sc, _ = train_scores[PRIMARY["h"]]
    pool = sc.index.to_numpy()
    plc = []
    for _ in range(N_PLACEBO):
        accts = rng.choice(pool, size=min(TOP, len(pool)), replace=False)
        d = simulate(test[test.taker.isin(accts)], Qs, PRIMARY["delay"], PRIMARY["h"], 1, st, en)
        plc.append(float(d.net1.mean()) if len(d) else np.nan)
    plc = np.array(plc)
    pct = float(np.mean(plc[np.isfinite(plc)] < df.net1.mean())) if len(df) and np.isfinite(plc).any() else None
    v = verdict(df, ci, pct)
    res["primary"] = dict(PRIMARY, n=int(len(df)), ci=ci, placebo_pct=pct,
                          placebo_mean=float(np.nanmean(plc)) if np.isfinite(plc).any() else None,
                          by_market={k: dict(n=int(len(g)), net1=float(g.net1.mean())) for k, g in df.groupby("mkt")},
                          by_day={k: dict(n=int(len(g)), net1=float(g.net1.mean())) for k, g in df.groupby("day")},
                          costs={f"{k}x": float(df[f"net{k}"].mean()) for k in COST_MULTS} if len(df) else None,
                          verdict=v)
    # Part A: persistence of account markouts out of sample
    for h in HORIZONS:
        mt = np.full(len(test), np.nan)
        for mk in MARKETS:
            g = test.mkt.values == mk
            mt[g] = markouts(test[g], Qs[mk], h, st, en)
        sc, _ = train_scores[h]
        d = pd.DataFrame(dict(m=mt, a=test.taker.values))
        d = d[np.isfinite(d.m)]
        tm = d.groupby("a").m.agg(["mean", "count"])
        tm = tm[(tm["count"] >= 10) & tm.index.isin(sc.index)]
        x, y = sc.loc[tm.index].values, tm["mean"].values
        ic = spearman(x, y)
        perm = np.array([spearman(x, rng.permutation(y)) for _ in range(2000)]) if len(x) >= 3 else np.array([])
        p = float(np.mean(np.abs(perm) >= abs(ic))) if len(perm) and np.isfinite(ic) else None
        inf, _ = sets[h]
        blk = test["T"].values // 3_600_000
        diff = block_boot_diff(mt, test.taker.isin(inf).astype(int).values, blk, rng)
        res["partA"].append(dict(h_s=h // 1000, accounts=int(len(tm)), spearman=ic, perm_p=p,
                                 informed_minus_rest=diff))
    res["informed_accounts"] = {f"h{h // 1000}s": [int(a) for a in sets[h][0]] for h in HORIZONS}
    res["uninformed_accounts"] = {f"h{h // 1000}s": [int(a) for a in sets[h][1]] for h in HORIZONS}
    return res, df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--manifest", action="store_true")
    a = ap.parse_args()
    if a.manifest:
        (LANE / "data_manifest.json").write_text(json.dumps(build_manifest(), indent=0, sort_keys=True))
        return
    if a.plumbing:
        (LANE / "plumbing.json").write_text(json.dumps(plumbing(), indent=1))
        return
    res, df = run()
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    pd.DataFrame(res["cells"]).to_csv(out / "cells.csv", index=False)
    df.to_csv(out / "trades_primary.csv", index=False)
    log("verdict", res["primary"]["verdict"], "n", res["primary"]["n"], "ci", res["primary"]["ci"])


if __name__ == "__main__":
    main()
