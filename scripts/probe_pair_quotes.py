"""R312 bounded first-seen public REST evidence: capture -> seal -> report.

One immutable capture per frozen lane. No accounts, orders, retries, daemon,
historical downloads or fee discovery. Run report only after seal is committed
and pushed. Its fixed six symbols are controls/diagnostics, not an alpha search.
"""
import argparse
import concurrent.futures
import csv
from dataclasses import asdict
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.executable_quotes import (Receipt, common_quantity, lighter_book, mexc_book,
                                   pair_costs, positive, receipt_quality)  # noqa: E402
from scripts.record_lighter_book import BASE as LIGHTER, LOCK as LIGHTER_LOCK  # noqa: E402

LANE = ROOT / "experiments/pair_quotes_v1"
MEXC = "https://contract.mexc.com/api/v1/contract"
SYMBOLS = ("BTC", "WIF", "SKR", "ROBO", "MEGA", "XPD")
MAX_REQUESTS, MAX_BYTES, MAX_SECONDS = 48, 8 * 1024**2, 180


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def verify_code(lane=LANE, root=ROOT):
    prereg.verify(lane / "PREREG.md")
    manifest = json.loads((lane / "code_inputs.json").read_text())
    for name, expected in manifest["sha256"].items():
        if sha(root / name) != expected:
            raise ValueError("frozen code/input changed: " + name)
    if sha(lane / "code_inputs.json") not in (lane / "PREREG.md").read_text():
        raise ValueError("code manifest not pinned by PREREG")


class Stop(RuntimeError):
    pass


class Capture:
    def __init__(self, out, *, opener=urllib.request.urlopen, clock=time):
        self.out, self.opener, self.clock = Path(out), opener, clock
        self.out.mkdir()  # one run only; failed/incomplete captures cannot reset a budget
        self.started = clock.monotonic()
        self.records, self.total, self.last_lighter = [], 0, None
        self.guard = threading.Lock()

    def elapsed(self):
        return self.clock.monotonic() - self.started

    def pace_lighter(self):
        if self.last_lighter is not None:
            wait = max(0., 1.1 - (self.clock.monotonic() - self.last_lighter))
            if self.elapsed() + wait >= MAX_SECONDS:
                raise Stop("duration budget reached before Lighter pacing")
            self.clock.sleep(wait)

    def get(self, name, url, lighter=False):
        # A single Lighter lock is held for this entire bounded run; MEXC and
        # Lighter book calls may overlap, but only one Lighter call is in flight.
        if lighter:
            self.pace_lighter()
        record = {"name": name, "url": url, "error": None, "response_bytes": 0}
        with self.guard:
            if len(self.records) >= MAX_REQUESTS or self.total >= MAX_BYTES or self.elapsed() >= MAX_SECONDS:
                raise Stop("declared capture budget exhausted")
            self.records.append(record)  # count attempts including failures
        start_utc, start_mono = self.clock.time_ns(), self.clock.monotonic_ns()
        if lighter:
            self.last_lighter = self.clock.monotonic()
        body, response = b"", None
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "quant-lab-R312-public/1",
                                                          "Accept": "application/json", "Accept-Encoding": "identity"})
            timeout = min(8., MAX_SECONDS - self.elapsed())
            if timeout <= 0:
                raise Stop("duration budget reached")
            try:
                response = self.opener(request, timeout=timeout)
            except urllib.error.HTTPError as exc:
                response = exc  # preserve failed response bodies too
            with response:
                # Pair calls run concurrently; reserve disjoint half budgets,
                # cap each body at 1 MiB, and never read limit+1 over the cap.
                with self.guard:
                    limit = min(1024 * 1024, (MAX_BYTES - self.total) // 2)
                if limit <= 0:
                    raise Stop("response byte budget exhausted")
                body = response.read(limit)
                record["http_status"] = response.status
            if len(body) == limit:
                raise Stop("response reached per-body/remaining byte cap")
            if not 200 <= response.status < 300:
                raise ValueError("HTTP " + str(response.status))
        except Exception as exc:
            record["error"] = type(exc).__name__ + ": " + str(exc)
        finally:
            record["receipt"] = asdict(Receipt(start_utc, self.clock.time_ns(), start_mono,
                                               self.clock.monotonic_ns()))
            record["response_bytes"] = len(body)
            record["sha256"] = hashlib.sha256(body).hexdigest()
            path = name + ".json.gz"
            (self.out / path).write_bytes(gzip.compress(body, mtime=0))
            record["body"] = path
            with self.guard:
                self.total += len(body)
        if record["error"]:
            return None
        try:
            return json.loads(body)
        except (ValueError, UnicodeError) as exc:
            record["error"] = "JSON: " + str(exc)
            return None

    def save(self, complete=False):
        write(self.out / "receipts.json", {"requests": len(self.records), "response_bytes": self.total,
              "duration_seconds": self.elapsed(), "complete": complete,
              "monotonic_scope": "one capture process only", "records": self.records})


def capture(lane=LANE):
    verify_code(lane)
    c = Capture(lane / "evidence")
    LIGHTER_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LIGHTER_LOCK.open("a") as lock:
        locked, complete = False, False
        try:
            while not locked and c.elapsed() < MAX_SECONDS:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except BlockingIOError:
                    time.sleep(.05)
            if not locked:
                raise Stop("existing Lighter writer held the public API lock")
            listing = c.get("lighter_markets", LIGHTER + "/orderBookDetails?filter=perp", True)
            if not listing or listing.get("code") != 200:
                raise Stop("no valid public Lighter market identity table")
            with (ROOT / "experiments/xfund_lt_v1/symbols.csv").open() as f:
                frozen = {r["lighter"]: r for r in csv.DictReader(f) if r["mexc"] and r["lighter"]}
            details = listing["order_book_details"]
            pairs = []
            for symbol in SYMBOLS:
                row = frozen[symbol]
                matches = [r for r in details if r.get("symbol") == symbol and r.get("market_type") == "perp"]
                if len(matches) != 1:
                    pairs.append({"symbol": symbol, "error": "missing or ambiguous Lighter identity"})
                    write(c.out / "pairs.json", pairs)
                    continue
                market_id = int(matches[0]["market_id"])
                pairs.append({"symbol": symbol, "mexc": row["mexc"], "market_id": market_id})
                write(c.out / "pairs.json", pairs)
                c.get(symbol + "_mexc_meta", MEXC + "/detail?symbol=" + row["mexc"])
                c.get(symbol + "_lighter_meta", LIGHTER + "/orderBookDetails?market_id=" + str(market_id), True)
                c.get(symbol + "_fair", MEXC + "/fair_price/" + row["mexc"])
                for i in (0, 1):
                    # Align request launches after pacing, rather than making
                    # MEXC's quote age while the Lighter worker waits for quota.
                    c.pace_lighter()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                        futures = [pool.submit(c.get, f"{symbol}_mexc_book_{i}", MEXC + "/depth/" + row["mexc"] + "?limit=50"),
                                   pool.submit(c.get, f"{symbol}_lighter_book_{i}", LIGHTER + "/orderBookOrders?market_id=" + str(market_id) + "&limit=100", True)]
                        for future in futures:
                            future.result()
                c.save()
            write(c.out / "pairs.json", pairs)
            complete = len(pairs) == len(SYMBOLS) and all("error" not in p for p in pairs) and not any(r["error"] for r in c.records)
        except Exception as exc:
            write(c.out / "stop.json", {"error": type(exc).__name__ + ": " + str(exc)})
        finally:
            c.save(complete)
            if locked:
                fcntl.flock(lock, fcntl.LOCK_UN)
    return c.out


def seal(lane=LANE):
    verify_code(lane)
    path = lane / "evidence_inputs.json"
    if path.exists():
        raise ValueError("evidence input identity already sealed")
    files = sorted(p for p in (lane / "evidence").iterdir() if p.is_file())
    if not files or not (lane / "evidence/receipts.json").exists():
        raise ValueError("no captured receipts")
    write(path, {"code_manifest_sha256": sha(lane / "code_inputs.json"),
                 "sha256": {str(p.relative_to(lane)): sha(p) for p in files}})
    return path


def report(lane=LANE):
    verify_code(lane)
    manifest = json.loads((lane / "evidence_inputs.json").read_text())
    if manifest["code_manifest_sha256"] != sha(lane / "code_inputs.json"):
        raise ValueError("evidence bound to different code")
    actual = {str(p.relative_to(lane)) for p in (lane / "evidence").iterdir() if p.is_file()}
    if actual != set(manifest["sha256"]):
        raise ValueError("captured file set changed")
    for name, expected in manifest["sha256"].items():
        if sha(lane / name) != expected:
            raise ValueError("sealed evidence changed: " + name)
    source = json.loads((lane / "evidence/receipts.json").read_text())
    if source["requests"] > MAX_REQUESTS or source["response_bytes"] > MAX_BYTES or source["duration_seconds"] > MAX_SECONDS:
        raise ValueError("declared acquisition cap exceeded")
    records = {r["name"]: r for r in source["records"]}

    def get(name):
        r = records[name]
        if r["error"]:
            raise ValueError(name + ": " + r["error"])
        raw = gzip.decompress((lane / "evidence" / r["body"]).read_bytes())
        if hashlib.sha256(raw).hexdigest() != r["sha256"]:
            raise ValueError("response body identity mismatch")
        return json.loads(raw), Receipt(**r["receipt"])

    rows = []
    for symbol in SYMBOLS:
        for i in (0, 1):
            row = {"symbol": symbol, "observation": i, "execution_ready": False}
            rows.append(row)  # failures/inactivity never disappear
            try:
                m, mr = get(symbol + "_mexc_meta")
                mm = m["data"]
                if isinstance(mm, list):
                    found = [r for r in mm if r["symbol"] == symbol + "_USDT"]
                    if len(found) != 1:
                        raise ValueError("ambiguous MEXC metadata")
                    mm = found[0]
                l, lr = get(symbol + "_lighter_meta")
                found = [r for r in l["order_book_details"] if r["symbol"] == symbol and r["market_type"] == "perp"]
                if m.get("success") is not True or l.get("code") != 200 or len(found) != 1:
                    raise ValueError("invalid metadata response")
                lm = found[0]
                identity = next(p for p in json.loads((lane / "evidence/pairs.json").read_text()) if p["symbol"] == symbol)
                if identity.get("error") or lm["market_id"] != identity["market_id"] or mm["symbol"] != identity["mexc"]:
                    raise ValueError("captured pair identity changed")
                mb, mbr = get(f"{symbol}_mexc_book_{i}")
                lb, lbr = get(f"{symbol}_lighter_book_{i}")
                books = (mexc_book(symbol + "_USDT", mb, mm, mbr), lighter_book(symbol, lb, lbr))
                now = max(b.receipt.received_mono_ns for b in books)
                row.update(receipt_quality(books, now))
                row["metadata_age_ms"] = {"mexc": (now-mr.received_mono_ns)/1e6,
                                          "lighter": (now-lr.received_mono_ns)/1e6}
                row["metadata_fresh"] = all(0 <= x <= 5000 for x in row["metadata_age_ms"].values())
                row["venue_reported_active"] = (mm.get("state") == 0 and mm.get("apiAllowed") is True
                                                and lm.get("status") == "active" and lm.get("is_frozen") is False)
                row["session_calendar_verified"] = False
                row["tradfi_control"] = symbol == "XPD" or any("tradfi" in x for x in mm.get("conceptPlate", []))
                row["execution_blockers"].append("market_session_calendar_not_verified")
                if not row["venue_reported_active"]:
                    row["execution_blockers"].append("venue_inactive_or_API_disabled")
                if not row["metadata_fresh"]:
                    row["execution_blockers"].append("metadata_not_contemporaneous")
                row["books"] = [{"venue": b.venue, "mid": b.mid, "bid": b.bids[0].price,
                                 "ask": b.asks[0].price, "timestamp_role": b.timestamp_role,
                                 "reported_timestamp_ms": b.reported_timestamp_ms, "version": b.version,
                                 "receipt_latency_ms": b.receipt.latency_ns/1e6} for b in books]
                q, step = common_quantity(mm, lm, max(b.mid for b in books))
                row["common_step_base"] = str(step)
                row["conditional_cost"] = pair_costs(*books, q)
                if row["conditional_cost"]["displayed_fillable"]:
                    if q * positive(books[1].bids[0].price) < positive(lm["min_quote_amount"]):
                        raise ValueError("Lighter quote minimum not met on sell side")
                fair, fr = get(symbol + "_fair")
                if fair.get("success") is not True or fair["data"].get("symbol") != symbol + "_USDT":
                    raise ValueError("invalid fair-price identity")
                fair_price, index = positive(fair["data"]["fairPrice"]), positive(lm["index_price"])
                row["funding_notional_observation"] = {
                    "mexc_fair_price": float(fair_price), "mexc_fair_quote_usd": float(q*fair_price),
                    "mexc_system_timestamp_ms": fair["data"].get("timestamp"),
                    "mexc_fair_receipt_age_ms": (now-fr.received_mono_ns)/1e6,
                    "lighter_index_price": float(index), "lighter_index_quote_usd": float(q*index),
                    "lighter_index_receipt_age_ms": (now-lr.received_mono_ns)/1e6,
                    "settlement_notional_verified": False}
            except (ValueError, KeyError, TypeError, StopIteration) as exc:
                row["error"] = type(exc).__name__ + ": " + str(exc)
    out = {"registry_id": "R312", "evidence_manifest_sha256": sha(lane/"evidence_inputs.json"),
           "economic_scope": "same-snapshot displayed round-trip cost, not executed PnL or a funding forecast",
           "fee_bp_per_side": {"mexc": 10, "lighter": 4}, "base_leg_budget_usd": 250,
           "fee_interpretation": "explicit charge reserve using R310 total-cost values PLUS displayed crossing; not verified account fees or an exact parent cost replay",
           "capital_usd": 10000, "capital_per_venue_usd": 5000, "predictive_trials": 0,
           "acquisition": {k: source[k] for k in ("requests", "response_bytes", "duration_seconds")},
           "observations": rows}
    path = lane / "results.json"
    encoded = json.dumps(out, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if path.exists() and path.read_text() != encoded:
        raise ValueError("refusing to replace different measured results")
    if not path.exists():
        path.write_text(encoded)
    return path


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("capture", "seal", "report"))
    a = p.parse_args()
    print({"capture": capture, "seal": seal, "report": report}[a.command]())
