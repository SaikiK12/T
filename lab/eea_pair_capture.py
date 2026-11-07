"""Bounded raw Coinbase CDE/Kraken observations; no rate normalization, signal or PnL."""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, build_opener


CB = "https://api.coinbase.com/api/v3/brokerage/market/"
KR = "https://futures.kraken.com/derivatives/api/v3/"
PAIRS = (("btc", "BIP-20DEC30-CDE", "PF_XBTUSD", "BTC", "0.01"),
         ("eth", "ETP-20DEC30-CDE", "PF_ETHUSD", "ETH", "0.1"))
SOURCES = {"kraken_metadata": KR+"instruments"}
for _key, _cb, _kr, _base, _size in PAIRS:
    SOURCES.update({
        _key+"_cde_product": CB+"products/"+_cb,
        _key+"_cde_book": CB+"product_book?product_id="+_cb+"&limit=100",
        _key+"_kraken_ticker": KR+"tickers/"+_kr,
        _key+"_kraken_book": KR+"orderbook?symbol="+_kr})
ALLOWLIST = frozenset(SOURCES.values())
# A second observation of the same four books, not a retry of failed requests.
BOOK_REOBSERVATIONS = {n+"_delayed": u for n, u in SOURCES.items() if n.endswith("_book")}
SOURCES.update(BOOK_REOBSERVATIONS)
PERMANENT_HTTP = frozenset((401, 403, 404, 429, 451))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_get(url, limit):
    """Only fixed public GETs, urllib's own UA, no auth, redirects or retries."""
    if url not in ALLOWLIST:
        raise ValueError("URL outside frozen public allowlist")
    try:
        response = build_opener(NoRedirect).open(url, timeout=15)
    except HTTPError as exc:
        response = exc
    with response:
        return response.code, response.read(limit+1), response.headers.get("Content-Type", "")


def schema_counts(name, obj):
    """Identity/schema only. Preserve empty books and unknown funding as such."""
    name = name.removesuffix("_delayed")
    if not isinstance(obj, dict):
        raise ValueError("expected public JSON object")
    if name == "kraken_metadata":
        if obj.get("result") != "success" or not isinstance(obj.get("instruments"), list):
            raise ValueError("Kraken instruments envelope")
        for _, _, symbol, base, _ in PAIRS:
            found = [x for x in obj["instruments"] if x.get("symbol") == symbol]
            if len(found) != 1 or (found[0].get("base"), found[0].get("quote"), found[0].get("contractSize")) != (base, "USD", 1):
                raise ValueError("Kraken linear instrument identity")
            if not found[0].get("marginSchedules", {}).get("europa", {}).get("retail"):
                raise ValueError("EEA retail margin schedule missing")
        return dict(instrument_rows=len(obj["instruments"]), named_pairs_present=2)
    key = name.split("_", 1)[0]
    _, cb, kr, base, size = next(p for p in PAIRS if p[0] == key)
    if name.endswith("cde_product"):
        f = obj.get("future_product_details", {})
        if (obj.get("product_id"), obj.get("product_type"), obj.get("quote_currency_id"),
                f.get("venue"), f.get("contract_root_unit")) != (cb, "FUTURE", "USD", "cde", base):
            raise ValueError("CDE product identity")
        if Decimal(f.get("contract_size", "NaN")) != Decimal(size) or Decimal(obj.get("base_increment", "NaN")) != 1:
            raise ValueError("CDE contract unit changed")
        return dict(funding_rate_present=f.get("funding_rate") not in (None, ""),
                    funding_time_present=f.get("funding_time") not in (None, ""),
                    funding_is_verified_settled_cash=False, owner_access_verified=False)
    if name.endswith("cde_book"):
        book = obj.get("pricebook", {})
        if book.get("product_id") != cb:
            raise ValueError("CDE book identity")
        if not all(isinstance(book.get(s), list) for s in ("bids", "asks")):
            raise ValueError("CDE book sides missing")
        if any(not {"price", "size"}.issubset(x) for s in ("bids", "asks") for x in book[s]):
            raise ValueError("CDE raw book fields missing")
        return dict(bid_rows=len(book["bids"]), ask_rows=len(book["asks"]))
    if obj.get("result") != "success":
        raise ValueError("Kraken envelope")
    if name.endswith("kraken_ticker"):
        ticker = obj.get("ticker", {})
        if ticker.get("symbol") != kr:
            raise ValueError("Kraken ticker identity")
        return dict(absolute_rate_present=ticker.get("fundingRate") not in (None, ""),
                    relative_rate_present=ticker.get("relativeFundingRate") not in (None, ""),
                    raw_rate_is_verified_settled_cash=False)
    book = obj.get("orderBook", {})
    if not all(isinstance(book.get(s), list) for s in ("bids", "asks")):
        raise ValueError("Kraken book sides missing")
    if any(not isinstance(x, list) or len(x) != 2 for s in ("bids", "asks") for x in book[s]):
        raise ValueError("Kraken raw book fields missing")
    # Kraken's book body does not echo the symbol: the fixed URL/receipt binds it.
    return dict(bid_rows=len(book["bids"]), ask_rows=len(book["asks"]), identity_from_request=True)


def append(path, row):
    with path.open("a") as handle:
        handle.write(json.dumps(row, sort_keys=True)+"\n")
        handle.flush()
        import os
        os.fsync(handle.fileno())


def usage(journal):
    """Unfinished STARTs retain their full byte reservation after a crash."""
    starts, finished = {}, {}
    if journal.exists():
        for line in journal.read_text().splitlines():
            row = json.loads(line)  # cut/corrupt journal stops; never repair it
            if row["event"] == "START":
                if row["request_id"] in starts:
                    raise ValueError("duplicate request reservation")
                starts[row["request_id"]] = row
            elif row["event"] == "END":
                rid = row["request_id"]
                if rid not in starts or rid in finished:
                    raise ValueError("unmatched request completion")
                finished[rid] = row
            else:
                raise ValueError("unknown journal event")
    used = sum(finished[rid]["charged_body_bytes"] if rid in finished else row["reserved_body_bytes"]
               for rid, row in starts.items())
    return len(starts), used


def exclusive_json(path, obj):
    with path.open("x") as handle:
        handle.write(json.dumps(obj, sort_keys=True, indent=2)+"\n")


@contextmanager
def writer(out):
    if out.resolve() != out.absolute():
        raise ValueError("capture path contains a symlink")
    out.mkdir(parents=True, exist_ok=True)
    with (out/"writer.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def capture(out, config, *, fetch=public_get, wall_ns=time.time_ns, mono_ns=time.monotonic_ns,
            sleeper=time.sleep, provenance=None):
    """One bounded UTC-hour packet, for the operational owner only.

    No daemon, scheduler, process management, history query, order, account,
    private API, normalised funding, fee arithmetic, trading rule or PnL.
    """
    now = wall_ns()
    if not config["start_ns"] <= now < config["end_ns"]:
        return dict(state="OUTSIDE_FROZEN_WINDOW", requests=0)
    out = Path(out)
    try:
        with writer(out):
            if (out/"STOPPED.json").exists():
                return dict(state="STOPPED", requests=0)
            stamp = datetime.fromtimestamp(now//1_000_000_000, timezone.utc).strftime("%Y%m%dT%H")
            packet = out/"packets"/stamp
            if packet.exists():
                return dict(state="HOUR_ALREADY_RESERVED", requests=0)
            packet.mkdir(parents=True)
            journal = out/"requests.jsonl"
            today = stamp[:8]
            metadata_packet = next((p for p in sorted((out/"packets").glob(today+"T*"))
                                    if (p/"kraken_metadata.body.gz").exists() and (p/"packet.json").exists()
                                    and "kraken_metadata" in json.loads((p/"packet.json").read_text()).get("counts", {})), None)
            names = ([] if metadata_packet else ["kraken_metadata"]) + [n for n in SOURCES if n != "kraken_metadata"]
            result = dict(state="CAPTURED", hour=stamp, counts={}, requests=0, body_bytes=0,
                          funding_cash=None, pnl=None, actual_fills=False,
                          reobservation_delay_seconds=config["reobservation_delay_seconds"],
                          provenance=provenance,
                          kraken_metadata_packet=(metadata_packet or packet).name)
            for name in names:
                used_requests, used_bytes = usage(journal)
                limit = config["metadata_response_cap"] if name == "kraken_metadata" else config["response_cap"]
                disk = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
                if (used_requests >= config["max_requests"] or used_bytes+limit+1 > config["max_body_bytes"]
                        or disk+limit+4096 > config["max_stored_bytes"]):
                    result["state"] = "BUDGET_STOP"
                    break
                if name == next(iter(BOOK_REOBSERVATIONS)):
                    # The gap follows the entire first group. Actual individual
                    # delays are in the receipts; none is asserted to be exact.
                    sleeper(config["reobservation_delay_seconds"])
                started = wall_ns()
                if not config["start_ns"] <= started < config["end_ns"]:
                    result["state"] = "WINDOW_ENDED"
                    break
                rid = stamp+"/"+name
                url = SOURCES[name]
                append(journal, dict(event="START", request_id=rid, url=url, started_utc_ns=started,
                                     started_mono_ns=mono_ns(), reserved_body_bytes=limit+1))
                result["requests"] += 1
                status, raw, content_type, error, permanent = None, b"", "", None, False
                complete = False
                try:
                    status, raw, content_type = fetch(url, limit)
                    complete = len(raw) <= limit
                    permanent = status in PERMANENT_HTTP or 300 <= status < 400
                    if not complete:
                        permanent = True
                        raise ValueError("response body cap exceeded")
                    if status != 200:
                        raise ValueError("HTTP "+str(status))
                    if "html" in content_type.lower():
                        permanent = True
                        raise ValueError("HTML/bot response")
                    obj = json.loads(raw)
                    result["counts"][name] = schema_counts(name, obj)
                except (OSError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
                    error = type(exc).__name__+": "+str(exc)[:300]
                    if status == 200:
                        permanent = True
                received = wall_ns()
                body = name+".body.gz"
                with (packet/body).open("xb") as handle:
                    handle.write(gzip.compress(raw, mtime=0))
                charge = len(raw) if complete else limit+1
                append(journal, dict(event="END", request_id=rid, status=status, received_utc_ns=received,
                                     received_mono_ns=mono_ns(), body=stamp+"/"+body,
                                     body_sha256=hashlib.sha256(raw).hexdigest(), bytes_read=len(raw),
                                     charged_body_bytes=charge, response_complete=complete, error=error))
                result["body_bytes"] += len(raw)
                if error:
                    result.update(state="FAILED", failed_source=name, error=error)
                    if permanent:
                        exclusive_json(out/"STOPPED.json", dict(hour=stamp, source=name, error=error,
                                                               resume_requires_new_review=True))
                    break
            exclusive_json(packet/"packet.json", result)
            return result
    except BlockingIOError:
        return dict(state="WRITER_BUSY", requests=0)
