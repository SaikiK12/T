"""One tiny historical-source qualification, not a forward loop or native journal writer.

Default is a read-only plan. --acquire permits at most two public32-row tails,
once, with counts/schema/time bounds only. Rate values are never summarized.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research/intake/funding_notional_20261103/cde_rate_contract_20261107"
CAP = 32768
SYMBOLS = {"btc": "BIPZ30", "eth": "ETPZ30"}


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def acquire():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "ACQUISITION_STARTED.json").open("x") as f:
        f.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(), max_calls=2,
                               max_new_client_bytes=2 * (CAP + 1), historical_allowance_reset=False)) + "\n")
    receipts = []
    for coin, symbol in SYMBOLS.items():
        url = f"https://www.coinbase.com/api/mda/v1/instruments/CDE/{symbol}/funding?result_limit=32"
        record = dict(organization="Coinbase", publication_date="undated public hourly data",
                      url=url, started_utc=datetime.now(timezone.utc).isoformat(),
                      started_mono_ns=time.monotonic_ns(), max_response_bytes=CAP,
                      scope="counts, schemas, identities and time bounds only; no rate-value comparison",
                      auth=False, user_agent="Python urllib default", redirects=False)
        with (OUT / "requests.jsonl").open("a") as f:
            f.write(json.dumps(dict(event="START", coin=coin, **record)) + "\n")
            f.flush()
        raw, status, complete, problem = b"", None, False, None
        try:
            try:
                response = request.build_opener(NoRedirect).open(url, timeout=20)
            except error.HTTPError as exc:
                response = exc
            with response:
                status = response.code
                record["content_type"] = response.headers.get("Content-Type", "")
                raw = response.read(CAP + 1)
            complete = len(raw) <= CAP
            if not complete or status != 200 or "html" in record["content_type"].lower():
                raise ValueError("public tail denied/over-limit/unusable; stop without retry")
            j = json.loads(raw)
            rows = j.get("results")
            if not isinstance(rows, list) or len(rows) > 32:
                raise ValueError("tail schema/limit drift")
            if any(x.get("symbol") != symbol or not isinstance(x.get("funding_rate"), str)
                   or not isinstance(x.get("event_time"), str) for x in rows):
                raise ValueError("tail identity/field type drift")
            times = [x["event_time"] for x in rows]
            record["counts_only"] = dict(rows=len(rows), unique_timestamps=len(set(times)),
                                         oldest=min(times) if times else None, newest=max(times) if times else None)
        except (OSError, ValueError, TypeError) as exc:
            problem = type(exc).__name__ + ": " + str(exc)
        record.update(status=status, received_utc=datetime.now(timezone.utc).isoformat(),
                      received_mono_ns=time.monotonic_ns(), bytes_read=len(raw), response_complete=complete,
                      charged_bytes=len(raw) if complete else CAP + 1,
                      sha256=hashlib.sha256(raw).hexdigest(), body=coin + ".body.gz", error=problem)
        with (OUT / record["body"]).open("xb") as f:
            f.write(gzip.compress(raw, mtime=0))
        with (OUT / (coin + ".receipt.json")).open("x") as f:
            f.write(json.dumps(record, indent=2) + "\n")
        with (OUT / "requests.jsonl").open("a") as f:
            f.write(json.dumps(dict(event="END", coin=coin, **record)) + "\n")
        receipts.append(record)
        if problem:
            break
    with (OUT / "acquisition.json").open("x") as f:
        f.write(json.dumps(dict(requests=receipts, total_requests=len(receipts),
                               total_charged_bytes=sum(r["charged_bytes"] for r in receipts),
                               rate_values_compared=False, new_forward_tick=False), indent=2) + "\n")
    print(json.dumps([dict(coin=r["body"].split(".")[0], status=r["status"], bytes=r["bytes_read"],
                           counts_only=r.get("counts_only"), error=r["error"]) for r in receipts]))
    return 1 if any(r["error"] for r in receipts) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    raise SystemExit(acquire() if args.acquire else print("INACTIVE: bounded historical source qualification only"))
