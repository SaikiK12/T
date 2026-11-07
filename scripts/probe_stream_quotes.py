"""R313 bounded public WS quote-access measurement: capture -> seal -> report.

No daemon, reconnects, incremental reconstruction, order endpoints or activation.
The frozen R312 common-lot and cost kernel is reused without modification.
"""
import argparse
import asyncio
from collections import Counter
import csv
import fcntl
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.stream_quotes import FrameClock, NS, Replay, SYMBOLS, entry_cash_drift  # noqa: E402
from scripts.record_lighter_book import BASE as LT_HTTP, LOCK as LT_LOCK  # noqa: E402
from scripts.record_tape import LIGHTER_WS, MEXC as MX_WS  # noqa: E402

LANE = ROOT / "experiments/stream_quotes_v1"
MX_HTTP = "https://contract.mexc.com/api/v1/contract"
REST_BYTES, STREAM_BYTES, FRAME_BYTES, MAX_MESSAGES = 2*1024**2, 4*1024**2, 64*1024, 20000
STREAM_SECONDS, TOTAL_SECONDS = 65, 120


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, sort_keys=True, indent=2, allow_nan=False)+"\n")


def verify(lane=LANE):
    prereg.verify(lane/"PREREG.md")
    identity = json.loads((lane/"code_inputs.json").read_text())
    if sha(lane/"code_inputs.json") not in (lane/"PREREG.md").read_text():
        raise ValueError("unbound code identity")
    for p, expected in identity["sha256"].items():
        if sha(ROOT/p) != expected:
            raise ValueError("frozen code/input drift: "+p)
    if importlib.metadata.version("websockets") != identity["websockets_version"]:
        raise ValueError("WebSocket runtime version drift")
    with (ROOT/"experiments/xfund_lt_v1/symbols.csv").open() as f:
        rows = {r["lighter"]:r for r in csv.DictReader(f) if r["mexc"] and r["lighter"]}
    if any(s not in rows or rows[s]["mexc"] != s+"_USDT" or not rows[s]["binance"] for s in SYMBOLS):
        raise ValueError("fixed R288 symbol identity mismatch")


class BudgetStop(RuntimeError):
    pass


class NoHTTPRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # a redirect is a failed attempt, not an uncounted GET


class Metadata:
    def __init__(self, out, opener=None):
        self.out = Path(out)
        self.opener = opener or urllib.request.build_opener(NoHTTPRedirect()).open
        self.records, self.total = [], 0
        self.start = time.monotonic()

    def get(self, name, url):
        if len(self.records) >= 7 or self.total >= REST_BYTES or time.monotonic()-self.start >= 20:
            raise BudgetStop("metadata request/byte/time budget")
        record = {"name": name, "url": url, "started_utc_ns": time.time_ns(), "started_mono_ns": time.monotonic_ns(), "error": None}
        self.records.append(record)
        body = b""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "quant-lab-R313-public/1", "Accept-Encoding": "identity"})
            try:
                response = self.opener(req, timeout=min(3., 20-(time.monotonic()-self.start)))
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                limit = min(1024**2, REST_BYTES-self.total)
                body = response.read(limit)
                record["http_status"] = response.status
            if len(body) == limit or not 200 <= response.status < 300:
                raise BudgetStop("truncated or failed metadata response")
            value = json.loads(body)
        except Exception as exc:
            record["error"] = type(exc).__name__+": "+str(exc)
            value = None
        record.update(received_utc_ns=time.time_ns(), received_mono_ns=time.monotonic_ns(), bytes=len(body),
                      sha256=hashlib.sha256(body).hexdigest(), body=name+".json.gz")
        self.total += len(body)
        (self.out/record["body"]).write_bytes(gzip.compress(body, mtime=0))
        return value


def no_redirect_connector():
    from websockets.asyncio.client import connect
    class OneHandshake(connect):
        def process_redirect(self, exc):
            return exc  # no automatic second handshake at a redirect target
    return OneHandshake


async def stream(venue, subscriptions, out, anchor, *, connector=None):
    connector = connector or no_redirect_connector()
    url = {"mexc": MX_WS, "lighter": LIGHTER_WS}[venue]
    status = {"url": url, "handshake_attempts": 1, "opened_mono_ns": None, "closed_mono_ns": None,
              "messages": 0, "payload_bytes": 0, "reason": "not_started"}
    deadline = anchor.mono_ns + STREAM_SECONDS*NS
    try:
        # Use the selected runtime's inherited CA trust. An old recorder's
        # root-only CA path is not portable to the current worker identity.
        ctx = ssl.create_default_context()
        async with connector(url, ssl=ctx, open_timeout=5, close_timeout=1,
                             max_size=FRAME_BYTES, max_queue=1, compression=None, ping_interval=None) as ws:
            status["opened_mono_ns"] = time.monotonic_ns()
            for subscription in subscriptions:
                await ws.send(json.dumps(subscription))
            last_ping = time.monotonic()
            with gzip.GzipFile(filename=str(out/(venue+".jsonl.gz")), mode="wb", mtime=0) as journal:
                while time.monotonic_ns() < deadline:
                    # Reserve a full maximum-sized frame BEFORE asking for it.
                    # No read of cap+1, no dropping a consumed oversized body.
                    if status["payload_bytes"]+FRAME_BYTES > STREAM_BYTES or status["messages"] >= MAX_MESSAGES:
                        status["reason"] = "payload_or_message_cap"
                        break
                    if time.monotonic()-last_ping >= 15:
                        await ws.send(json.dumps({"method": "ping"} if venue == "mexc" else {"type": "ping"}))
                        last_ping = time.monotonic()
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=min(1., max(.001, (deadline-time.monotonic_ns())/NS)))
                    except asyncio.TimeoutError:
                        continue
                    utc, mono = time.time_ns(), time.monotonic_ns()
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    size = len(raw.encode())
                    if size > FRAME_BYTES:
                        raise ValueError("transport violated declared maximum frame")
                    status["payload_bytes"] += size
                    status["messages"] += 1
                    frame = {"venue": venue, "number": status["messages"], "utc_ns": utc, "mono_ns": mono, "raw": raw}
                    journal.write((json.dumps(frame, sort_keys=True, separators=(",", ":"))+"\n").encode())
                    if venue == "lighter" and json.loads(raw).get("type") == "ping":
                        await ws.send('{"type":"pong"}')
                else:
                    status["reason"] = "duration_complete"
    except Exception as exc:
        status["reason"] = type(exc).__name__+": "+str(exc)
    finally:
        status["closed_mono_ns"] = time.monotonic_ns()
    return status


def capture(lane=LANE):
    verify(lane)
    out = lane/"evidence"
    out.mkdir()  # cannot reset a failed capture or its budget
    begin = time.monotonic()
    meta, mapping, errors = {}, {}, []
    network = Metadata(out)
    LT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LT_LOCK.open("a") as lock:
        locked = False
        try:
            while time.monotonic()-begin < 10:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError:
                    time.sleep(.05)
            if not locked:
                raise BudgetStop("existing public API writer held lock")
            network.start = time.monotonic()
            listing = network.get("lighter_metadata", LT_HTTP+"/orderBookDetails?filter=perp")
            for symbol in SYMBOLS:
                try:
                    m = network.get(symbol+"_mexc_metadata", MX_HTTP+"/detail?symbol="+symbol+"_USDT")
                    if not m or m.get("success") is not True or not listing or listing.get("code") != 200:
                        raise ValueError("metadata_failed")
                    mm = m["data"]
                    if isinstance(mm, list):
                        mm, = [x for x in mm if x["symbol"] == symbol+"_USDT"]
                    lm, = [x for x in listing["order_book_details"] if x["symbol"] == symbol and x["market_type"] == "perp"]
                    if mm["symbol"] != symbol+"_USDT":
                        raise ValueError("MEXC metadata identity mismatch")
                    meta[symbol] = {"mexc": mm, "lighter": lm}
                    mapping[int(lm["market_id"])] = symbol
                except (KeyError, ValueError, TypeError, BudgetStop) as exc:
                    errors.append(symbol+":"+type(exc).__name__+":"+str(exc))
                    if isinstance(exc, BudgetStop):
                        break
            write(out/"metadata.json", {"symbols": list(SYMBOLS), "metadata": meta, "names": mapping, "errors": errors})
            anchor = FrameClock(time.time_ns(), time.monotonic_ns())
            write(out/"anchor.json", vars(anchor))
            mxsubs = [{"method": name, "param": {"symbol": s+"_USDT", **({"limit": 5} if name == "sub.depth.full" else {})}}
                      for s in SYMBOLS if s in meta for name in ("sub.depth.full", "sub.fair.price")]
            ltsubs = [{"type": "subscribe", "channel": f"{kind}/{m}"} for m in sorted(mapping) for kind in ("ticker", "market_stats")]
            async def both():
                return await asyncio.gather(stream("mexc", mxsubs, out, anchor), stream("lighter", ltsubs, out, anchor))
            connections = asyncio.run(both())
            write(out/"connections.json", dict(zip(("mexc", "lighter"), connections)))
        except Exception as exc:
            errors.append(type(exc).__name__+": "+str(exc))
        finally:
            write(out/"receipts.json", {"records": network.records, "requests": len(network.records),
                  "response_bytes": network.total, "duration_seconds": time.monotonic()-begin, "errors": errors})
            if locked:
                fcntl.flock(lock, fcntl.LOCK_UN)
    return out


def seal(lane=LANE):
    verify(lane)
    path = lane/"evidence_inputs.json"
    if path.exists():
        raise ValueError("evidence already sealed")
    files = sorted(p for p in (lane/"evidence").iterdir() if p.is_file())
    write(path, {"code_manifest_sha256": sha(lane/"code_inputs.json"),
                 "sha256": {str(p.relative_to(lane)): sha(p) for p in files}})
    return path


def report(lane=LANE):
    verify(lane)
    identity = json.loads((lane/"evidence_inputs.json").read_text())
    actual = {str(p.relative_to(lane)) for p in (lane/"evidence").iterdir() if p.is_file()}
    if actual != set(identity["sha256"]) or identity["code_manifest_sha256"] != sha(lane/"code_inputs.json"):
        raise ValueError("evidence/code inventory drift")
    for p, expected in identity["sha256"].items():
        if sha(lane/p) != expected:
            raise ValueError("sealed evidence drift")
    read = lambda name: json.loads((lane/"evidence"/name).read_text())
    receipts = read("receipts.json")
    if receipts["requests"] > 7 or receipts["response_bytes"] > REST_BYTES or receipts["duration_seconds"] > TOTAL_SECONDS:
        raise ValueError("collection cap exceeded")
    records = receipts.get("records", [])
    if len(records) != receipts["requests"] or sum(r["bytes"] for r in records) != receipts["response_bytes"]:
        raise ValueError("metadata receipt counters disagree")
    bodies = {}
    for record in records:
        raw = gzip.decompress((lane/"evidence"/record["body"]).read_bytes())
        if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ValueError("metadata raw body disagrees with receipt")
        if not record["error"]:
            bodies[record["name"]] = json.loads(raw)
    connections = read("connections.json") if (lane/"evidence/connections.json").exists() else {}
    frames = []
    for venue, status in connections.items():
        if status["handshake_attempts"] > 1 or status["payload_bytes"] > STREAM_BYTES or status["messages"] > MAX_MESSAGES:
            raise ValueError("stream cap exceeded")
        path = lane/"evidence"/(venue+".jsonl.gz")
        venue_frames = []
        if path.exists():
            with gzip.open(path, "rt") as f:
                venue_frames = [json.loads(line) for line in f]
        if len(venue_frames) != status["messages"] or sum(len(f["raw"].encode()) for f in venue_frames) != status["payload_bytes"]:
            raise ValueError("stream receipt counters disagree")
        for i, frame in enumerate(venue_frames, 1):
            if frame["venue"] != venue or frame["number"] != i or len(frame["raw"].encode()) > FRAME_BYTES:
                raise ValueError("stream frame identity/order/size mismatch")
            if not status["opened_mono_ns"] <= frame["mono_ns"] <= status["closed_mono_ns"]:
                raise ValueError("frame lies outside its connection")
            if i > 1 and frame["mono_ns"] < venue_frames[i-2]["mono_ns"]:
                raise ValueError("receive monotonic clock regressed")
        frames.extend(venue_frames)
    anchor_data = read("anchor.json") if (lane/"evidence/anchor.json").exists() else {"utc_ns": 0, "mono_ns": 0}
    anchor = FrameClock(**anchor_data)
    mapping = read("metadata.json") if (lane/"evidence/metadata.json").exists() else {"metadata": {}, "names": {}}
    for symbol, pair in mapping["metadata"].items():
        if symbol not in SYMBOLS:
            raise ValueError("unexpected symbol in fixed capture")
        mx = bodies[symbol+"_mexc_metadata"]["data"]
        if isinstance(mx, list):
            mx, = [m for m in mx if m["symbol"] == symbol+"_USDT"]
        lt, = [m for m in bodies["lighter_metadata"]["order_book_details"] if m["symbol"] == symbol and m["market_type"] == "perp"]
        if pair != {"mexc":mx,"lighter":lt}:
            raise ValueError("parsed metadata disagrees with raw inputs")
    if mapping["names"] != {str(p["lighter"]["market_id"]):s for s,p in mapping["metadata"].items()}:
        raise ValueError("market id mapping disagrees with raw metadata")
    replay = Replay(frames, mapping["metadata"], {int(k):v for k,v in mapping["names"].items()}, anchor, connections)
    rows = []
    for grid in range(5, 61, 5):
        immediate = {}
        for symbol in SYMBOLS:
            row, books = replay.observe(symbol, anchor.mono_ns+grid*NS)
            row.update(grid_second=grid, access_delay_ms=0)
            immediate[symbol] = row, books
            rows.append(row)
        for symbol in SYMBOLS:
            before, before_books = immediate[symbol]
            quantity = before["quantity_base"]
            row, books = replay.observe(symbol, anchor.mono_ns+grid*NS+300_000_000, quantity,
                                        allow_new_quantity=False)
            row.update(grid_second=grid, access_delay_ms=300)
            row["entry_quote_cash_drift"] = None
            if (before["cost"] and before["cost"]["displayed_fillable"] and not before["book_flags"]
                    and row["cost"] and row["cost"]["displayed_fillable"] and not row["book_flags"]):
                row["entry_quote_cash_drift"] = entry_cash_drift(before_books, books, quantity)
            rows.append(row)
    encoded = "".join(json.dumps(r,sort_keys=True,separators=(",", ":"),allow_nan=False)+"\n" for r in rows).encode()
    result_path = lane/"observations.jsonl.gz"
    body = gzip.compress(encoded,mtime=0)
    if result_path.exists() and result_path.read_bytes() != body:
        raise ValueError("refusing to overwrite different observations")
    if not result_path.exists():
        result_path.write_bytes(body)
    summary = {"registry_id": "R313", "evidence_manifest_sha256": sha(lane/"evidence_inputs.json"),
               "observations_sha256": sha(result_path), "rows": len(rows), "predictive_trials": 0,
               "scope": "source-stamped public quote-access cost diagnostic, not fills, expectancy or paper scoring",
               "charge_reserve_bp": [10,4], "capital_usd": 10000, "capital_per_venue_usd": 5000,
               "access_delay_ms": [0,300], "parser_errors": dict(replay.errors), "pairs": []}
    for symbol in SYMBOLS:
        for delay in (0,300):
            subset = [r for r in rows if r["symbol"] == symbol and r["access_delay_ms"] == delay]
            valid = [r for r in subset if r["cost"] and r["cost"]["displayed_fillable"] and not r["book_flags"]]
            tiers = [{"multiple": k, "n": len(valid),
                      "round_trip_cost_usd_range": [min(vals),max(vals)] if vals else None}
                     for k in (1,2,3) for vals in [[r["cost"]["scenarios"][k-1]["round_trip_cost_usd"] for r in valid]]]
            summary["pairs"].append({"symbol":symbol, "delay_ms":delay, "grids":len(subset), "valid_cost_grids":len(valid),
                                     "book_flags":dict(Counter(f for r in subset for f in r["book_flags"])), "cost_tiers":tiers,
                                     "fresh_fair_index_grids":sum(all(not x["flags"] for x in r["references"]) for r in subset)})
    path = lane/"results.json"
    text = json.dumps(summary,sort_keys=True,indent=2,allow_nan=False)+"\n"
    if path.exists() and path.read_text() != text:
        raise ValueError("refusing to overwrite different results")
    if not path.exists():
        path.write_text(text)
    return path


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=("capture","seal","report"))
    a = p.parse_args()
    print({"capture":capture,"seal":seal,"report":report}[a.command]())
