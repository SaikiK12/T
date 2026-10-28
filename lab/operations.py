"""Shared operational catalog for execution and read-only views.

Descriptors identify existing lanes, dependencies and presentation metadata. They
are not a second methods queue, an active-writer claim or a statistical policy.
Frozen specifications and registry rows remain authoritative for research.
"""
from dataclasses import dataclass

OBJECTIVE = ("Net executable MEXC altcoin-perpetual strategies, followed by genuinely new prospective paper evidence. "
             "Independent research axes share the canonical methods queue, provenance and gates. "
             "Real-money decisions remain with the owner.")

SEED_SHA256 = "3ea686670c35c9946a560cc29cd1087b79cbeef40a78208840ab3b3e86aa0ec5"

@dataclass(frozen=True)
class Requirement:
    path: str
    sha256: str | None = None


@dataclass(frozen=True)
class Task:
    name: str
    argv: tuple[str, ...]
    needs: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    timeout: float = 900
    files: tuple[Requirement, ...] = ()
    shared_lock: str | None = None
    lock_wait: float = 300
    checks: tuple[str, ...] = ()


def forward_tasks(python=".venv/bin/python"):
    """Edges follow direct reads, not the old shell command order.

    R215's R214 reference comparison is conditional (forward_mexc.score), so
    its failure must not stop the MEXC book. R218 unconditionally reads R215's
    tickets after scoring (forward_mexc_sq.main), so R215 is mandatory there.
    R220 builds eligibility/ranks from R200 (forward_carry.journal_grid); it
    does not need R215. R224 reads only R200's latest signal universe. The
    point-in-time recorders read nothing from the lanes and run next; the
    digest reads only their files and runs last. R266 reads only the recorders'
    calendar snapshot and ticker files, so they are optional for it. R268 reads the
    notice journal and ticker files the same way and runs right after them; so
    does R270. R278/R279/R294 fetch their own carry inputs under separate locks.
    R285 reads R278/R279, flow and event journals, so those lanes are optional
    for it; R294 is not a sleeve in its frozen book. R355 only makes sure its own daemon
    (scripts/forward_settlehop.py run) is up; the daemon decides at hh:00:20. R364 does the same for
    scripts/forward_settlelit.py, whose daemon decides at T - 1 h + 20 s for each 4 h settlement T.

    R200 is listed first, so it starts first: it reads nothing from the
    recorders, and scripts/forward_lag.py counts an hour it computes more than
    60 minutes after the bar's close as late.
    """
    carry_locks = {"R278": ".xfund.lock", "R279": ".xfund_kc.lock", "R294": ".xfund_lt.lock"}

    def task(name, script, needs=(), optional=(), timeout=900, files=()):
        lock = carry_locks.get(name)
        wait = 0 if lock else 300
        if name in {"REC_NOTICES", "R268", "R270", "R272"}:
            lock = ".notices.lock"
        return Task(name, (python, "scripts/" + script), needs, optional, timeout, files, lock, wait,
                    ("flow_signals",) if name == "R200" else ("funding_snapshot",) if name == "REC_FUNDING" else ("unlock_journal",) if name == "R266" else ())

    return (
        task("R200", "forward_tick.py", timeout=1500),
        task("REC_TICKER", "record_mexc_ticker.py", timeout=120),
        task("REC_FUNDING", "record_funding_board.py", timeout=120),
        task("REC_DERIBIT", "record_deribit_chain.py", timeout=120),
        task("REC_LIGHTER", "record_lighter_book.py", timeout=600),   # backgrounded in forward_all.sh
        task("REC_DEX", "record_dex_prices.py", timeout=60),     # starts the 5-minute daemon if it is down
        task("REC_WALLETS", "record_wallets.py", timeout=120),
        task("REC_NOTICES", "record_notices.py", timeout=300),
        task("REC_UNLOCKS", "record_unlocks.py", timeout=300),
        task("REC_TAPE", "record_tape.py", timeout=60),
        task("REC_HFT", "record_hft.py", timeout=60),
        task("REC_NEWS", "record_news.py", timeout=60),
        task("R268", "forward_delist.py", (), ("REC_TICKER", "REC_NOTICES"), timeout=300),
        task("R270", "forward_montag.py", (), ("REC_TICKER", "REC_NOTICES"), timeout=300),
        task("R272", "forward_announce.py", (), ("REC_TICKER", "REC_NOTICES"), timeout=300),
        task("R214", "forward_delayed.py", ("R200",)),
        task("R215", "forward_mexc.py", ("R200",), ("R214",),
             files=(Requirement("experiments/venue_gap_v1/results/tradfi_symbols.json"),)),
        task("R224", "record_mexc_depth.py", ("R200",), timeout=300,
             files=(Requirement("experiments/venue_gap_v1/results/tradfi_symbols.json"),)),
        task("R218", "forward_mexc_sq.py", ("R200", "R215")),
        task("R220", "forward_carry.py", ("R200",)),
        task("R221", "forward_seq.py", ("R215", "R218"), timeout=300),
        task("R225", "forward_vt.py", ("R215", "R218"), timeout=300,
             files=(Requirement("experiments/sizing_v1/results/daily.npz", SEED_SHA256),)),
        task("R266", "forward_unlocks.py", (), ("REC_TICKER", "REC_UNLOCKS"), timeout=600),
        task("R278", "forward_xfund.py", timeout=1500),
        task("R279", "forward_xfund_kc.py", timeout=1500),
        task("R294", "forward_xfund_lt.py", timeout=1500),
        task("R355", "forward_settlehop.py", timeout=60),   # starts the lane's hourly daemon if it is down
        task("R364", "forward_settlelit.py", timeout=60),   # starts the lane's settlement daemon if it is down
        task("R285", "forward_xbook.py", (),
             ("R278", "R279", "R215", "R218", "R266", "R268", "R270", "R272"), timeout=300),
        task("LAG", "forward_lag.py", ("R200", "R214", "R215", "R218", "R220", "R225"), timeout=120),
        task("PANEL", "panel.py", (), ("LAG",), timeout=120),  # A failed lane must not hide operational status.
        task("CATALOG", "catalog.py", (), ("PANEL",), timeout=60),
        task("DASH", "dashboard_data.py", (), ("LAG", "PANEL", "REC_FUNDING"), timeout=120),
        task("REC_DIGEST", "record_digest.py", (), ("REC_TICKER", "REC_FUNDING", "REC_NOTICES", "REC_UNLOCKS"),
             timeout=300),
    )


@dataclass(frozen=True)
class Lane:
    rid: str
    path: str
    what: str
    venue: str
    mode: str
    needed: int
    rule: str
    books: tuple[tuple[str, str], ...] = ()
    kind: str = "daily"
    unit: str = ""                       # an event lane's observation unit; default "scored notices"

    @property
    def status_path(self):
        return f"experiments/{self.path}/journal/status.json"


LANES = (
    Lane('R215', 'mexc_fwd', 'flow books A and B, one bar late', 'MEXC', 'API', 90,
         'R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate', (('A', 'flow book A on MEXC'), ('B', 'top-vs-crowd on MEXC'))),
    Lane('R218', 'mexc_fwd_sq', 'flow book X2 (k squared)', 'MEXC', 'API', 90,
         'R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate', (('X2', 'flow book X2 (k squared) on MEXC'),)),
    Lane('R220', 'carry_fwd', 'funding carry (R191 rule)', 'MEXC + Binance', 'manual-web', 90,
         'go_real at 90 on-time days', (('MEXC', 'funding carry, MEXC'), ('BIN', 'funding carry, Binance'))),
    Lane('R200', 'flow72_fwd2', 'flow books A and B', 'Binance', 'API', 90,
         'go_real at 90 scored days, NW t >= 2', (('A', 'flow book A, Binance'), ('B', 'top-vs-crowd, Binance'))),
    Lane('R214', 'flow72_fwd3', 'A and B one bar late (delay check)', 'Binance', 'API', 90,
         'same days as R200', (('A', 'A one bar late'), ('B', 'B one bar late'))),
    Lane('R225', 'vt_fwd', 'volatility target on A, B, X2', 'MEXC', 'API', 365,
         'risk-only decision at 365 on-time days; reported beside R215/R218', (('A', 'volatility target A'), ('B', 'volatility target B'), ('X2', 'volatility target X2'))),
    Lane('R266', 'unlocks_fwd', 'unlock short, D-7 to unlock', 'MEXC', 'manual-web', 120,
         '120 scored tickets', (), kind="event"),
    Lane('R268', 'delist_fwd', 'spot delisting-notice short +1 h', 'MEXC', 'API', 12,
         '12 scored notices', (), kind="event"),
    Lane('R270', 'montag_fwd', 'Monitoring Tag short +24 h', 'MEXC', 'manual-web', 12,
         '12 scored notices', (), kind="event"),
    Lane('R272', 'announce_fwd', 'funding-frequency long 1 h; pre-listing short 168 h', 'MEXC', 'API + manual-web', 12,
         '12 scored notices per book', (), kind="event"),
    Lane('R278', 'xfund_fwd', 'cross-venue funding carry, books A, B, C', 'Gate, Hyperliquid, Binance, MEXC', 'manual-web', 90,
         'NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3%', (('A', 'cross-venue carry, Gate + Hyperliquid'), ('B', 'cross-venue carry, Binance + MEXC'), ('C', 'cross-venue carry, Gate + MEXC (post hoc)'))),
    Lane('R279', 'xfund_kc_fwd', 'cross-venue funding carry on KuCoin, books A, B', 'Gate, Binance, KuCoin', 'manual-web', 90,
         'NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3%', (('A', 'cross-venue carry, Gate + KuCoin'), ('B', 'cross-venue carry, Binance + KuCoin'))),
    Lane('R294', 'xfund_lt_fwd', 'cross-venue funding carry on Lighter, book A', 'MEXC, Lighter', 'API', 90,
         'NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3%', (('A', 'cross-venue carry, MEXC + Lighter'),)),
    Lane("R355", "settlehop_fwd", "settlement hop on the displayed funding rate (MEXC decided, Gate reported)",
         "MEXC + Lighter", "manual-web", 80,
         "futility at 20/40 hops; PASS at 40 if CR1 t >= 2.97, else at 80 or 2028-03-01 if t >= 2.10; 2x > 0",
         kind="event", unit="scored hops"),
    Lane("R364", "settlelit_fwd", "settlement scalp on Lighter against Binance's deep lump (T - 10 s to T + 60 s)",
         "Lighter (Binance's rate)", "API", 80,
         "futility at 20/40 hops; PASS at 40 if CR1 t >= 2.80, else at 80 or 2027-10-28 if t >= 1.98; 2x > 0",
         kind="event", unit="scored hops"),
    Lane("R285", "xbook_fwd", "cross-family derived book", "Multiple venues", "mixed", 180,
         "180/365 final-day sequential looks; native and gate decisions remain separate", kind="derived"),
)

LABELS = {
    "REC_TICKER": ("Market data collection", "MEXC funding and ticker snapshots", "recorders"),
    "REC_FUNDING": ("Market data collection", "Six-venue funding board snapshots", "recorders"),
    "REC_NOTICES": ("Market data collection", "Exchange announcement snapshots", "recorders"),
    "REC_UNLOCKS": ("Market data collection", "Token unlock calendar snapshots", "recorders"),
    "REC_DIGEST": ("Data integrity", "Recorder provenance digests", "recorders"),
    "R200": ("Prospective paper", "Binance positioning books", "flow72_fwd2"),
    "R214": ("Prospective paper", "Binance delayed-entry control", "flow72_fwd3"),
    "R215": ("Prospective paper", "MEXC positioning books", "mexc_fwd"),
    "R218": ("Prospective paper", "MEXC agreement-weighted book", "mexc_fwd_sq"),
    "R220": ("Prospective paper", "Funding carry books", "carry_fwd"),
    "R221": ("Evidence decisions", "MEXC sequential evidence review", "mexc_seq"),
    "R224": ("Execution measurement", "MEXC order-book execution costs", "mexc_costs"),
    "R225": ("Prospective paper", "MEXC volatility-targeted books", "vt_fwd"),
    "R266": ("Prospective paper", "MEXC token unlock events", "unlocks_fwd"),
    "R268": ("Prospective paper", "MEXC delisting announcement events", "delist_fwd"),
    "R270": ("Prospective paper", "MEXC monitoring-tag events", "montag_fwd"),
    "R272": ("Prospective paper", "MEXC funding-change and prelisting events", "announce_fwd"),
    # These share vt_fwd/tick.log in the shell; it cannot identify their outcomes.
    "LAG": ("Data integrity", "Forward processing-lag report", "vt_fwd"),
    "PANEL": ("Reporting", "Canonical research panel refresh", "vt_fwd"),
    "DASH": ("Reporting", "Control room dataset export", "vt_fwd"),
}
LABELS.update({
    "REC_DERIBIT": ("Market data collection", "Deribit option chain snapshots", "recorders"),
    "REC_LIGHTER": ("Market data collection", "Lighter order-book snapshots", "recorders"),
    "REC_DEX": ("Market data collection", "DEX price recorder supervision", "recorders"),
    "REC_WALLETS": ("Market data collection", "Public wallet snapshots", "recorders"),
    "REC_TAPE": ("Market data collection", "Order-flow tape recorder supervision", "recorders"),
    "REC_HFT": ("Market data collection", "100 ms BTC/ETH feed recorder supervision", "recorders"),
    "REC_NEWS": ("Market data collection", "News recorder supervision", "recorders"),
    "R278": ("Prospective paper", "Cross-venue funding carry", "xfund_fwd"),
    "R279": ("Prospective paper", "KuCoin cross-venue carry", "xfund_kc_fwd"),
    "R294": ("Prospective paper", "Lighter cross-venue carry", "xfund_lt_fwd"),
    "R355": ("Prospective paper", "Settlement hop on the displayed funding rate", "settlehop_fwd"),
    "R364": ("Prospective paper", "Lighter settlement scalp on Binance's predicted rate", "settlelit_fwd"),
    "R285": ("Prospective paper", "Cross-family derived book", "xbook_fwd"),
    "CATALOG": ("Reporting", "Repository catalogs", "vt_fwd"),
})

# These projections read only existing evidence. Metadata freshness is not a gate.
import csv
import json
import math
from pathlib import Path
import time


def num(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def rows_csv(path):
    try:
        with Path(path).open(newline="") as stream:
            return list(csv.DictReader(stream))
    except OSError:
        return []


ISO = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

def lane_age(root, lane, now):
    EXP = Path(root) / "experiments"
    NOW = now
    p = EXP / lane / "journal" / "status.json"
    return (round((NOW - p.stat().st_mtime) / 3600, 2), ISO(p.stat().st_mtime)) if p.exists() else (None, None)


def forward_days(root):
    """One row per lane, book and day: the daily books' paper net at 1x/2x/3x, replay or on-time."""
    EXP = Path(root) / "experiments"
    out = []
    spec = {"flow72_fwd2": ("R200", "net", "Binance flow books"), "flow72_fwd3": ("R214", "net", "Binance flow books"),
            "mexc_fwd": ("R215", "net", "MEXC flow books"), "mexc_fwd_sq": ("R218", "net", "MEXC flow books"),
            "carry_fwd": ("R220", "net", "Funding carry")}
    for lane, (rid, col, group) in spec.items():
        for r in rows_csv(EXP / lane / "journal" / "tickets.csv"):
            kind = r.get("kind") or ("replay" if r.get("late") == "1" else "ontime")
            out.append({"key": f"{lane}|{r['book']}|{r['day']}", "day": r["day"], "round": rid, "lane": lane,
                        "book": r["book"], "series": f"{rid} {r['book']}", "group": group, "kind": kind,
                        "net": num(r[col]),
                        "net_2x": num(r.get("net_2x")), "net_3x": num(r.get("net_3x"))})
    carry = {"xfund_fwd": ("R278", {"A": "Gate + Hyperliquid", "B": "Binance + MEXC", "C": "Gate + MEXC (post hoc)"}),
             "xfund_kc_fwd": ("R279", {"A": "Gate + KuCoin", "B": "Binance + KuCoin"}),
             "xfund_lt_fwd": ("R294", {"A": "MEXC + Lighter"})}
    for lane, (rid, sets) in carry.items():
        done = {(r["book"], r["day"], r["run"]) for r in rows_csv(EXP / lane / "journal" / "decisions.csv")}
        for r in rows_csv(EXP / lane / "journal" / "days.csv"):
            if (r["book"], r["day"], r["run"]) not in done:   # a run cut short; the lane ignores its rows too
                continue
            out.append({"key": f"{lane}|{r['book']}|{r['day']}|{r['run']}", "day": r["day"], "round": rid,
                        "lane": lane, "book": r["book"], "series": f"{rid} {r['book']} {sets.get(r['book'], '')}",
                        "group": "Cross-venue funding carry", "kind": r["kind"],
                        "net": num(r["net"]), "net_2x": num(r["net_2x"]), "net_3x": num(r["net_3x"])})
    for r in rows_csv(EXP / "vt_fwd" / "journal" / "days.csv"):
        out.append({"key": f"vt_fwd|{r['book']}|{r['day']}", "day": r["day"], "round": "R225", "lane": "vt_fwd",
                    "book": r["book"], "series": f"R225 {r['book']}", "group": "Volatility-targeted (MEXC)",
                    "kind": r["kind"],
                    "net": num(r["net_vt"]), "net_2x": num(r["net_vt_2x"]), "net_3x": num(r["net_vt_3x"])})
    return sorted(out, key=lambda r: (r["series"], r["day"]))


def forward_lanes(root, days, now):
    EXP = Path(root) / "experiments"
    from .runtime import digest
    policy = Path(root) / "docs/GATES.md"
    policy_sha = digest(policy) if policy.is_file() else None
    out = []
    for descriptor in LANES:
        rid, lane, what, venue, mode, need, rule = (descriptor.rid, descriptor.path, descriptor.what,
                                                 descriptor.venue, descriptor.mode, descriptor.needed, descriptor.rule)
        s = read_json(EXP / lane / "journal" / "status.json")
        age, at = lane_age(root, lane, now)
        mine = [d for d in days if d["lane"] == lane]
        ontime = [d for d in mine if d["kind"] == "ontime"]
        daily = descriptor.kind == "daily"
        by_book, progress_note = {}, None
        if daily:
            books = sorted(dict(descriptor.books) or {d["book"]: d["book"] for d in mine})
            dates = [{d["day"] for d in ontime if d["book"] == book} for book in books]
            common = set.intersection(*dates) if dates else set()
            by_book = {book: len(dates[i]) for i, book in enumerate(books)}
            scored = len(common)
            unit = "on-time days"  # Native labels; strict 60-minute eligibility remains unassessed.
            progress_note = "Only dates present for every listed book count here; inspect per-book counts."
            tickets, open_ = len({d["day"] for d in mine}), None
            # Preserve unknown returns: no observations or any missing cost row means unknown aggregate.
            def total(column):
                selected = [d for d in ontime if d["day"] in common and d["book"] in books]
                values = [num(d.get(column)) for d in selected]
                keys = {(d["book"], d["day"]) for d in selected}
                complete = len(values) == len(keys) == len(common) * len(books)
                return (sum(values) / len(books) if values and complete and all(v is not None for v in values)
                        else None)
            net, net2, net3 = (total(col) for col in ("net", "net_2x", "net_3x"))
        else:
            books = []
            scored = num(s.get("scored", s.get("scored_notices")))
            scored = int(scored) if scored is not None and scored >= 0 and scored.is_integer() else None
            unit = descriptor.unit or ("scored tickets" if lane == "unlocks_fwd" else "scored notices")
            tickets, open_ = s.get("tickets"), s.get("open")
            net = num(s.get("mean_net"))
            net2 = num(s.get("mean_net_2x"))
            net3 = None
        if descriptor.kind == "derived":
            scored = None
            unit = "native final days (strict eligibility unassessed)"
            tickets, open_, net, net2, net3 = s.get("final_days"), None, None, None, None
            progress_note = "Derived book; inspect its native decisions and strict on-time projection separately."
        if lane == "announce_fwd":
            books = ["FF", "PL"]
            for book in books:
                count = num((s.get("books", {}).get(book) or {}).get("scored_notices"))
                by_book[book] = int(count) if count is not None and count >= 0 and count.is_integer() else None
            # Two separate frozen decisions: 12 FF notices must not stand in for 12 PL notices.
            scored = min(by_book.values()) if all(v is not None for v in by_book.values()) else None
            unit = "scored notices per book (least observed book)"
            progress_note = "FF and PL each require 12 scored notices; progress is unknown if either count is absent."
        out.append({"round": rid, "lane": lane, "display_name": f"{what[:1].upper()}{what[1:]} · {venue}",
                    "what": what, "venue": venue, "mode": mode,
                    "books": " ".join(books) or None, "kind": "daily book" if daily else descriptor.kind,
                    "tickets": tickets, "open": open_, "scored": scored, "needed": need, "unit": unit,
                    "progress": round(min(scored / need, 1), 4) if scored is not None else None,
                    "scored_by_book": by_book or None, "progress_note": progress_note,
                    "net_pct": None if net is None else net * 100,
                    "net_2x_pct": None if net2 is None else net2 * 100,
                    "net_3x_pct": None if net3 is None else net3 * 100,
                    "decision": s.get("decision") or rule, "updated_at": at, "age_h": age,
                    "gate_eligibility": "UNASSESSED", "gate_policy": "docs/GATES.md", "gate_policy_sha256": policy_sha,
                    "decision_group": "flow72" if rid in {"R200", "R214", "R215", "R218", "R225"} else "UNRECONCILED"})
    return out
