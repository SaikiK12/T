"""Finite raw Lighter participant/BBO windows with conservative, nonrenewable reservations."""
import asyncio
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
from urllib import error, request

STREAM = "wss://mainnet.zklighter.elliot.ai/stream"
HTTP = "https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id="
MAX_FRAME = 262144


class SourceStop(RuntimeError):
    pass


def append(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
        f.flush()


def records(folder):
    path = Path(folder) / "events.jsonl"
    if not path.exists():
        if Path(folder).exists() and any(Path(folder).iterdir()):
            raise SourceStop("capture journal missing beside prior state; no reset")
        return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise SourceStop("cut capture journal; no reset or new attempt")
    try:
        return [json.loads(x) for x in raw.splitlines()]
    except ValueError as exc:
        raise SourceStop("invalid capture journal") from exc


def choose_slot(config, now):
    if now.tzinfo is None:
        raise ValueError("capture needs an aware UTC clock")
    utc = now.astimezone(timezone.utc)
    eligible = [s for s in config["slots"]
                if datetime.fromisoformat(s["start"]) <= utc < datetime.fromisoformat(s["end"])]
    if len(eligible) > 1:
        raise ValueError("overlapping frozen observation windows")
    return eligible[0] if eligible else None


def inherited_source_block(raw):
    """A prior denial of the same host/path cannot be retried through this new composition."""
    if not raw or not raw.endswith(b"\n"):
        raise SourceStop("missing/cut inherited source-stop ledger")
    for line in raw.splitlines():
        row = json.loads(line)
        key = str(row.get("key", ""))
        if row.get("event") == "BLOCK" and (key == "mainnet.zklighter.elliot.ai"
                                               or key.startswith("mainnet.zklighter.elliot.ai/")):
            return True
    return False


def reserve(folder, config, slot, now):
    """Each attempted slot keeps its FULL reservation, including failures/unknown reads."""
    if choose_slot(config, now) != slot:
        raise SourceStop("capture start is outside its frozen window")
    rows = records(folder)
    if any(x["event"] == "SOURCE_BLOCK" for x in rows):
        raise SourceStop("source previously stopped; no next-window retry")
    starts = [x for x in rows if x["event"] == "SLOT_STARTED"]
    finished = {x["slot"] for x in rows if x["event"] == "SLOT_FINISHED"}
    if any(x["slot"] not in finished for x in starts):
        raise SourceStop("unfinished capture; uncertain spend retained")
    if any(x["slot"] == slot["id"] for x in starts):
        return None
    if slot not in config["slots"]:
        raise SourceStop("slot outside frozen campaign")
    calls = sum(x["reserved_calls"] for x in starts) + config["slot_reserved_calls"]
    size = sum(x["reserved_bytes"] for x in starts) + config["slot_reserved_bytes"]
    if calls > config["max_source_calls"] or size > config["max_source_bytes"]:
        raise SourceStop("original finite campaign reservation exhausted")
    target = Path(folder) / "slots" / slot["id"]
    if target.exists():
        raise SourceStop("unreconciled prior slot directory")
    target.mkdir(parents=True)
    append(Path(folder) / "events.jsonl", dict(event="SLOT_STARTED", slot=slot["id"],
           actual_started_utc=now.astimezone(timezone.utc).isoformat(), planned=slot,
           reserved_calls=config["slot_reserved_calls"], reserved_bytes=config["slot_reserved_bytes"],
           cumulative_reserved_calls=calls, cumulative_reserved_bytes=size,
           source_calls_before_reservation=0, no_refund=True))
    return target


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceStop("HTTP redirect refused")


def deny_ws_redirects(connection):
    # websockets16 follows redirects even for a single async-context connect.
    # Its documented implementation hook must return the original exception
    # to stop before constructing any request to the Location target.
    connection.process_redirect = lambda exc: exc
    return connection


def metadata_get(url, cap):
    if not url.startswith(HTTP) or not url[len(HTTP):].isdigit():
        raise SourceStop("unregistered metadata URL")
    response = None
    try:
        try:
            response = request.build_opener(NoRedirect).open(url, timeout=20)
        except error.HTTPError as exc:
            response = exc
        status = response.getcode()
        body = response.read(cap + 1)
        return status, body, str(response.headers.get("Content-Type", ""))
    finally:
        if response is not None:
            response.close()


def classify(message, markets):
    """Schema/identity counts only; preserve numeric strings without scoring them."""
    if not isinstance(message, dict) or message.get("error") or message.get("type") == "error":
        raise SourceStop("invalid/error public websocket envelope")
    kind = message.get("type")
    if kind in ("connected", "ping", "pong"):
        return None, kind, 0
    if kind not in ("subscribed/ticker", "update/ticker", "subscribed/trade", "update/trade"):
        raise SourceStop("unregistered websocket message type")
    channel = str(message.get("channel", ""))
    parts = channel.split(":")
    if len(parts) != 2 or not parts[1].isdigit():
        raise SourceStop("missing market channel identity")
    market = parts[1]
    if market not in markets or parts[0] != kind.split("/")[1]:
        raise SourceStop("wrong websocket channel or instrument")
    if kind.endswith("ticker"):
        ticker = message.get("ticker") or {}
        stamp = ticker.get("last_updated_at", message.get("last_updated_at"))
        clock_ok = (type(stamp) is int and stamp > 0) or (isinstance(stamp, str) and stamp.isdigit() and int(stamp) > 0)
        if not clock_ok:
            raise SourceStop("ticker publication clock absent")
        for side in ("a", "b"):
            level = ticker.get(side) or {}
            if any(not isinstance(level.get(k), str) or not level[k] for k in ("price", "size")):
                raise SourceStop("ticker BBO strings absent")
        return market, kind, 1
    ordinary = message.get("trades") or []
    liquidations = message.get("liquidation_trades") or []
    if not isinstance(ordinary, list) or not isinstance(liquidations, list):
        raise SourceStop("trade lists absent")
    for row in ordinary + liquidations:
        if type(row.get("is_maker_ask")) is not bool:
            raise SourceStop("maker-side boolean absent")
        for key in ("trade_id", "ask_account_id", "bid_account_id", "timestamp", "transaction_time"):
            if type(row.get(key)) is not int or row[key] < 0:
                raise SourceStop("trade identity/clock absent: " + key)
        if row.get("market_id", int(market)) != int(market):
            raise SourceStop("trade market identity mismatch")
        for key in ("price", "size", "taker_position_size_before", "maker_position_size_before",
                    "taker_entry_quote_before", "maker_entry_quote_before"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise SourceStop("public trade state string absent: " + key)
    return market, kind, len(ordinary) + len(liquidations)


async def capture(folder, config, slot, *, http_get=metadata_get, connect=None, clock=None):
    """One finite slot, once; the caller must have published the runtime reservation first."""
    now = (clock or (lambda: datetime.now(timezone.utc)))()
    target = reserve(folder, config, slot, now)
    if target is None:
        return dict(state="SLOT_ALREADY_ATTEMPTED", slot=slot["id"], source_calls=0)
    rows_path = Path(folder) / "events.jsonl"
    calls = body_bytes = frames = 0
    by_market = {mid: {k: 0 for k in ("subscribed/ticker", "update/ticker", "subscribed/trade", "update/trade",
                                     "bootstrap_trade_rows", "update_trade_rows")} for mid in config["markets"]}
    result = dict(state="STARTED", slot=slot["id"], actual_started_utc=now.isoformat(), source_calls=0,
                  decoded_application_bytes=0, frames=0, counts=by_market, pnl=None, markout=None,
                  real_orders_allowed=False, full_day=False, R367_usable_day=False)
    try:
        for mid, symbol in config["markets"].items():
            url = HTTP + mid
            append(rows_path, dict(event="HTTP_STARTED", slot=slot["id"], url=url, utc_ns=time.time_ns()))
            calls += 1
            status, data, content_type = http_get(url, config["metadata_response_cap"])
            body_bytes += len(data)
            (target / (mid + ".metadata.gz")).write_bytes(gzip.compress(data, mtime=0))
            receipt = dict(url=url, status=status, body_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           received_utc_ns=time.time_ns(), content_type=content_type)
            (target / (mid + ".metadata.receipt.json")).write_text(json.dumps(receipt, indent=2) + "\n")
            if status != 200 or len(data) > config["metadata_response_cap"] or "html" in content_type.lower():
                raise SourceStop("metadata HTTP/content stop: " + str(status))
            obj = json.loads(data, parse_float=str)
            items = obj.get("order_book_details") or []
            if (obj.get("code") != 200 or len(items) != 1 or items[0].get("market_id") != int(mid)
                    or items[0].get("symbol") != symbol or items[0].get("status") != "active"):
                raise SourceStop("metadata instrument identity/status mismatch")
        if connect is None:
            from websockets.asyncio.client import connect
        from websockets.http11 import MAX_BODY_SIZE
        if MAX_BODY_SIZE > config["slot_reserved_bytes"] - body_bytes:
            raise SourceStop("handshake error-body bound exceeds reserved bytes")
        append(rows_path, dict(event="WS_STARTED", slot=slot["id"], url=STREAM, utc_ns=time.time_ns()))
        calls += 1
        with (target / "messages.jsonl.gz").open("xb") as raw_file:
            with gzip.GzipFile(fileobj=raw_file, mode="wb", mtime=0) as raw:
                connection = deny_ws_redirects(connect(STREAM, open_timeout=20, close_timeout=5,
                                                       ping_interval=20, ping_timeout=20,
                                                       max_size=MAX_FRAME, max_queue=1, compression=None))
                async with connection as ws:
                    for mid in config["markets"]:
                        for topic in ("ticker", "trade"):
                            await ws.send(json.dumps(dict(type="subscribe", channel=topic + "/" + mid)))
                            calls += 1
                    if calls > config["slot_reserved_calls"]:
                        raise SourceStop("source request reservation exceeded")
                    capture_started = time.monotonic()
                    deadline = capture_started + slot["duration_seconds"]
                    result["state"] = "CAPTURED_WINDOW"
                    while time.monotonic() < deadline:
                        if body_bytes + MAX_FRAME > config["slot_payload_cap"]:
                            result["state"] = "PARTIAL_PAYLOAD_LIMIT"
                            break
                        try:
                            message = await asyncio.wait_for(ws.recv(), max(0.001, deadline - time.monotonic()))
                        except asyncio.TimeoutError:
                            break
                        data = message.encode("utf-8") if isinstance(message, str) else bytes(message)
                        received_ns, mono_ns = time.time_ns(), time.monotonic_ns()
                        body_bytes += len(data)
                        frames += 1
                        raw.write((json.dumps(dict(received_utc_ns=received_ns, received_monotonic_ns=mono_ns,
                                   bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                                   body_b64=base64.b64encode(data).decode("ascii"))) + "\n").encode())
                        if len(data) > MAX_FRAME or body_bytes > config["slot_payload_cap"]:
                            raise SourceStop("frame/payload cap exceeded")
                        decoded = json.loads(data, parse_float=str)
                        market, kind, count = classify(decoded, config["markets"])
                        if kind == "ping":
                            await ws.send('{"type":"pong"}')
                        if market is not None:
                            by_market[market][kind] += 1
                            if kind.endswith("trade"):
                                key = "bootstrap_trade_rows" if kind.startswith("subscribed/") else "update_trade_rows"
                                by_market[market][key] += count
                        if frames >= config["max_frames"]:
                            result["state"] = "PARTIAL_FRAME_LIMIT"
                            break
                    result["observed_stream_seconds"] = time.monotonic() - capture_started
                    if (result["state"] == "CAPTURED_WINDOW"
                            and result["observed_stream_seconds"] + 0.01 < slot["duration_seconds"]):
                        result["state"] = "PARTIAL_EARLY_TIMEOUT"
        result["both_markets_have_live_ticker_and_trade"] = all(
            x["update/ticker"] > 0 and x["update_trade_rows"] > 0 for x in by_market.values())
    except BaseException as exc:
        result.update(state="SOURCE_STOP", error=type(exc).__name__ + ": " + str(exc))
        response = getattr(exc, "response", None)
        handshake_body = getattr(response, "body", None)
        if isinstance(handshake_body, (bytes, bytearray)):
            handshake_body = bytes(handshake_body)
            body_bytes += len(handshake_body)
            with (target / "handshake_error.body.gz").open("xb") as f:
                f.write(gzip.compress(handshake_body, mtime=0))
            result.update(handshake_error_status=getattr(response, "status_code", None),
                          handshake_error_body_bytes=len(handshake_body),
                          handshake_error_body_sha256=hashlib.sha256(handshake_body).hexdigest())
        append(rows_path, dict(event="SOURCE_BLOCK", slot=slot["id"], reason=result["error"], utc_ns=time.time_ns()))
    finally:
        result.update(source_calls=calls, decoded_application_bytes=body_bytes, frames=frames,
                      actual_finished_utc=datetime.now(timezone.utc).isoformat(),
                      reserved_bytes=config["slot_reserved_bytes"], reserved_calls=config["slot_reserved_calls"],
                      byte_scope="decoded application bodies; fixed reservation additionally retains buffer/unknown spend; not measured network wire",
                      reservation_refunded=False)
        (target / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        append(rows_path, dict(event="SLOT_FINISHED", slot=slot["id"], state=result["state"],
                               source_calls=calls, decoded_application_bytes=body_bytes,
                               utc_ns=time.time_ns(), reservation_refunded=False))
    return result
