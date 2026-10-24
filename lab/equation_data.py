"""Input adapters for the frozen equation family; no network and no hidden gap fill."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lab.equations import DAY, HOUR, Panel
from lab import xfund


def _rules(row, venue):
    """Current public metadata only; never represented as historical PIT rules."""
    try:
        if venue == "mexc":
            if int(row["type"]) != 1 or row.get("settleCoin") != "USDT":
                raise ValueError("nonlinear/non-USDT contract")
            size = float(row["contractSize"])
            step = size * float(row["volUnit"])
            minimum = size * float(row["minVol"])
            quote = 0.
        else:
            decimals = int(row["supported_size_decimals"])
            if not 0 <= decimals <= 12:
                raise ValueError("invalid size precision")
            step, minimum, quote = 10.**(-decimals), float(row["min_base_amount"]), float(row["min_quote_amount"])
        if step <= 0 or minimum < 0 or quote < 0 or not np.isfinite([step, minimum, quote]).all():
            raise ValueError("invalid lot fields")
        return (step, minimum, quote), True
    except (KeyError, ValueError, TypeError):
        return (1., 0., 0.), False


def load_panel(root, table, start_ms, end_ms):
    root = Path(root)
    with open(table, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("mexc") and r.get("lighter")]
    if not rows or any(not r.get("binance") for r in rows):
        raise ValueError("only the frozen open Binance-overlap universe is permitted")
    times = np.arange(start_ms, end_ms+HOUR, HOUR, dtype=np.int64)
    n, shape = len(rows), (len(times), len(rows), 2)
    price = np.full(shape, np.nan)
    fresh = np.zeros(shape, bool)
    rates = np.zeros(shape)
    funding_ok = np.zeros(shape, bool)
    settled = np.zeros(shape, bool)
    steps, minima, min_quote = np.ones((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
    metadata_ok = np.ones(n, bool)
    coverage = {"price_rows": {}, "funding_rows": {}, "historical_rule_vintages": False,
                "funding_notional": "contemporaneous traded-close proxy, not fair/mark", "quote_coverage": {}}
    metadata = {}
    for venue in ("mexc", "lighter"):
        records = json.loads((root / (venue + "_contracts_current.json")).read_text())
        metadata[venue] = {r["symbol"]: r for r in records}
    for i, row in enumerate(rows):
        for v, venue in enumerate(("mexc", "lighter")):
            symbol = row[venue]
            rules, ok = _rules(metadata[venue].get(symbol, {}), venue)
            steps[i, v], minima[i, v], min_quote[i, v] = rules
            metadata_ok[i] &= ok
            path = root / venue / "prices" / (symbol + ".parquet")
            fpath = root / venue / "funding" / (symbol + ".parquet")
            p = pd.read_parquet(path)
            f = pd.read_parquet(fpath)
            if p.t.duplicated().any() or f.t.duplicated().any():
                raise ValueError("duplicate source clock")
            if len(p):
                if np.any(p.t.to_numpy(np.int64) % HOUR):
                    raise ValueError("nonhourly price timestamp")
                ix = (p.t.to_numpy(np.int64) + HOUR - start_ms) // HOUR
                inside = (ix >= 0) & (ix < len(times))
                ix = ix[inside]
                vals = p.close.to_numpy(float)[inside]
                vol = p["vol" if venue == "mexc" else "volume"].to_numpy(float)[inside]
                price[ix, i, v] = np.where(vals > 0, vals, np.nan)
                fresh[ix, i, v] = np.isfinite(vals) & (vals > 0) & np.isfinite(vol) & (vol > 0)
            if len(f):
                ts = f.t.to_numpy(np.int64)
                if np.any(ts % HOUR):
                    raise ValueError("nonhourly settlement clock; refusing implicit timestamp floor")
                ii = (ts-start_ms)//HOUR
                inside = (ii >= 0) & (ii < len(times))
                ii, ts = ii[inside], ts[inside]
                rr = f.rate.to_numpy(float)[inside]
                if not np.isfinite(rr).all():
                    raise ValueError("nonfinite funding event")
                if venue == "mexc":
                    cycles = f.cycle_h.to_numpy(float)[inside]
                    for j in range(1, len(ii)):
                        gap = ii[j]-ii[j-1]
                        # A missing settlement is not a zero. A documented
                        # cycle on BOTH sides must explain this exact gap;
                        # a schedule transition does not certify no payment.
                        cs = [c for c in (cycles[j-1], cycles[j]) if np.isfinite(c) and c > 0]
                        if len(cs) == 2 and all(abs(gap-c) < 1e-9 for c in cs):
                            funding_ok[ii[j-1]+1:ii[j]+1, i, v] = True
                rates[ii, i, v] = rr
                funding_ok[ii, i, v] = True
                settled[ii, i, v] = True
            key = venue + "/" + symbol
            coverage["price_rows"][key], coverage["funding_rows"][key] = len(p), len(f)
            if len(p) and len(ix):
                lo, hi = max(0, int(ix.min())), min(len(times)-1, int(ix.max()))
                good_price = np.isfinite(price[lo:hi+1, i, v])
                coverage["quote_coverage"][key] = {
                    "first_close_ms": int(times[lo]), "last_close_ms": int(times[hi]),
                    "missing_price_within_span": int((~good_price).sum()),
                    "known_nontradable_within_span": int((good_price & ~fresh[lo:hi+1, i, v]).sum()),
                    "unknown_funding_within_span": int((~funding_ok[lo:hi+1, i, v]).sum())}
            else:
                coverage["quote_coverage"][key] = None
    panel = Panel(times, tuple(r["key"] for r in rows), price, fresh, rates, funding_ok,
                  steps, minima, min_quote, metadata_ok, settled).validate()
    coverage["metadata_admissible_pairs"] = int(metadata_ok.sum())
    return panel, coverage


def parent_states(panel, start_ms, end_ms):
    """R288 parameter control with R294's causal three-stale-day exit.

    The untouched original xfund Book also supplies a separate legacy accounting
    view. Its last_fresh archive-end exit is NOT allowed to drive primary targets.
    """
    nd = (len(panel.times)-1)//24+1
    series = []
    for i in range(len(panel.keys)):
        sv = []
        for v in range(2):
            close, fresh = xfund.daily_prices(panel.times-HOUR, panel.prices[:, i, v],
                                               panel.fresh[:, i, v].astype(float), HOUR,
                                               int(panel.times[0]), nd)
            fund, count = np.zeros(nd), np.zeros(nd, int)
            for d in range(1, nd):
                a, b = (d-1)*24+1, d*24+1
                fund[d] = panel.rates[a:b, i, v].sum()
                count[d] = (panel.settlement[a:b, i, v].sum() if panel.settlement is not None else
                            np.count_nonzero(panel.rates[a:b, i, v]))
            sv.append(xfund.Daily.build(close, fresh, fund, count))
        series.append(sv)
    u = xfund.Universe(panel.keys, ["mexc", "lighter"], series, int(panel.times[0]), nd)
    book = xfund.Book([0, 1], 14, .05, 20)
    old = xfund.Book([0, 1], 14, .05, 20)
    states = np.zeros((nd, len(panel.keys)), int)
    legacy = []
    first = (start_ms-int(panel.times[0]))//DAY
    last = (end_ms-int(panel.times[0]))//DAY
    for d in range(first, last):
        def stale(p, day):
            lo = max(0, day-2)
            return (not u.series[p.coin][p.lo].fresh[lo:day+1].any() or
                    not u.series[p.coin][p.hi].fresh[lo:day+1].any())
        book.exits(u, d, forced_fn=stale)
        book.entries(u, d)
        for p in book.open:
            states[d, p.coin] = 1 if p.lo == 0 else -1
        ex, en = old.exits(u, d), old.entries(u, d)
        gross, funding = old.interval(u, d)
        legacy.append({"origin_ms": int(panel.times[0])+d*DAY, "gross": gross/40,
                       "funding": funding/40, "legs": 2*(len(ex)+len(en)), "held": len(old.open)})
    if legacy:
        legacy[-1]["legs"] += 2*len(old.open)
    return states, legacy
