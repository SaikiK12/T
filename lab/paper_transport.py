"""Small, public HTTP content decoding with inherited, never-reset campaign spend."""
from contextlib import contextmanager
import gzip
import hashlib
import io
import json
from email.message import Message
from pathlib import Path
from urllib import error, request, parse
import zlib

from lab.runtime_transport import Budget, TransportStop, append


class InheritedBudget(Budget):
    def __init__(self, folder, policy, baseline, frozen_baseline):
        self.baseline, self.frozen_baseline = Path(baseline), Path(frozen_baseline)
        super().__init__(folder, policy)

    def records(self):
        try:
            raw, expected = self.baseline.read_bytes(), self.frozen_baseline.read_bytes()
        except OSError:
            raise TransportStop("legacy budget unavailable; no counter reset") from None
        if not expected.endswith(b"\n") or not raw.startswith(expected) or not raw.endswith(b"\n"):
            raise TransportStop("legacy budget missing, cut or divergent; no counter reset")
        try:
            old = [json.loads(x) for x in raw.splitlines()]
            if self.events.exists():
                current = self.events.read_bytes()
                if current and not current.endswith(b"\n"):
                    raise TransportStop("cut new budget journal; no request permitted")
            return old + super().records()
        except (OSError, ValueError):
            raise TransportStop("invalid accumulated budget; no retry/reset") from None


class ContentResponse(io.BytesIO):
    def __init__(self, raw, response):
        super().__init__(raw)
        self.code = self.status = response.code
        self.url = response.url
        self.headers = Message()
        for k, v in response.headers.items():
            if k.lower() not in ("content-encoding", "content-length"):
                self.headers[k] = v
        self.headers["Content-Length"] = str(len(raw))

    def getcode(self):
        return self.code


def content_bytes(raw, encoding, limit):
    if encoding in ("", "identity"):
        if len(raw) > limit:
            raise TransportStop("decoded content limit exceeded")
        return raw
    if encoding != "gzip":
        raise TransportStop("unregistered HTTP content encoding")
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decoded = d.decompress(raw, limit + 1)
    if len(decoded) > limit or not d.eof or d.unused_data or d.unconsumed_tail:
        raise TransportStop("cut, concatenated or oversized gzip content")
    return decoded


@contextmanager
def fence(folder, policy, *, baseline, frozen_baseline):
    """Charge wire bytes, retain both hashes; decode only standard HTTP gzip.

    Existing source blocks and old START/END spend are inherited. This is a
    separately frozen transport, never an edit of the R420/native transports.
    """
    folder = Path(folder)
    original = request.OpenerDirector.open
    redirect = request.HTTPRedirectHandler.redirect_request

    def no_redirect(self, req, fp, code, msg, headers, newurl):
        raise TransportStop("redirect refused; no target request sent")

    def opened(self, fullurl, *args, **kwargs):
        req = fullurl if isinstance(fullurl, request.Request) else request.Request(fullurl)
        if req.get_method() != "GET":
            raise TransportStop("only registered public GET allowed")
        url = req.full_url
        selected = [(prefix, cap) for prefix, cap in policy["wire_caps"].items() if url.startswith(prefix)]
        if not selected:
            raise TransportStop("source outside paper-priority contract")
        _, cap = max(selected, key=lambda x: len(x[0]))
        effective = dict(policy, response_cap=cap)
        budget = InheritedBudget(folder, effective, baseline, frozen_baseline)
        rid, cap, host, key = budget.reserve(req)
        # Honest content negotiation, never browser impersonation or denial retry.
        req.add_header("Accept-Encoding", "gzip")
        response, wire, complete, ended, saved = None, b"", False, False, False
        status, encoding = None, ""
        try:
            try:
                response = original(self, req, *args, **kwargs)
            except error.HTTPError as exc:
                response = exc
            status = response.code
            if status in (401, 403, 404, 429, 451) or 300 <= status < 400:
                # Persist a known denial even if its body cannot be stored/read.
                budget.block(host if status in (403, 451) else key, "HTTP " + str(status))
            encoding = response.headers.get("Content-Encoding", "").lower().strip()
            try:
                wire = response.read(cap + 1)
            except BaseException as exc:
                wire = bytes(getattr(exc, "partial", b""))[:cap + 1]
                raise
            length = response.headers.get("Content-Length")
            complete = len(wire) <= cap and (length is None or int(length) == len(wire))
            body = folder / "raw" / (rid + ".wire.gz")
            body.parent.mkdir(parents=True, exist_ok=True)
            with body.open("xb") as f:
                f.write(gzip.compress(wire, mtime=0))
            saved = True
            if not complete:
                budget.block(key, "wire body oversized or incomplete")
                raise TransportStop("wire body limit/completeness failure")
            if status != 200:
                raise TransportStop("HTTP " + str(status) + ": " + key)
            if "html" in response.headers.get("Content-Type", "").lower():
                budget.block(key, "HTML/bot response")
                raise TransportStop("HTML/bot response refused")
            try:
                decoded = content_bytes(wire, encoding, policy["max_decoded_bytes"])
            except (TransportStop, zlib.error) as exc:
                budget.block(key, "content decoding failed")
                raise TransportStop(str(exc)) from None
            if decoded.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                budget.block(key, "HTML/bot content despite response type")
                raise TransportStop("HTML/bot content refused")
            if "json" in response.headers.get("Content-Type", "").lower():
                try:
                    obj = json.loads(decoded)
                except ValueError:
                    budget.block(key, "invalid public JSON content")
                    raise TransportStop("invalid public JSON content") from None
                if isinstance(obj, dict) and (obj.get("error") or obj.get("success") is False
                                               or obj.get("code") not in (None, 0, 200, "0", "200")):
                    budget.block(key, "public JSON error envelope")
                    raise TransportStop("public JSON error envelope")
            append(budget.events, dict(event="CONTENT", id=rid, wire_bytes=len(wire),
                   wire_sha256=hashlib.sha256(wire).hexdigest(), content_bytes=len(decoded),
                   content_sha256=hashlib.sha256(decoded).hexdigest(), content_encoding=encoding,
                   stored_wire=str(body.relative_to(folder))))
            budget.finish(rid, len(wire), complete=True, status=status,
                          body_sha256=hashlib.sha256(wire).hexdigest())
            ended = True
            return ContentResponse(decoded, response)
        except BaseException as exc:
            if isinstance(exc, TransportStop) and response is None:
                budget.block(key, "redirect refused")
            if not saved:
                body = folder / "raw" / (rid + ".wire.gz")
                body.parent.mkdir(parents=True, exist_ok=True)
                if not body.exists():
                    try:
                        with body.open("xb") as f:
                            f.write(gzip.compress(wire, mtime=0))
                    except OSError:
                        pass  # retained reservation is the authority if storage failed
            if not ended:
                budget.finish(rid, len(wire), complete=complete, status=status,
                              body_sha256=hashlib.sha256(wire).hexdigest())
            if isinstance(exc, TransportStop):
                raise
            raise TransportStop("network/content failure; request and uncertain spend retained") from None
        finally:
            if response is not None:
                response.close()

    request.OpenerDirector.open, request.HTTPRedirectHandler.redirect_request = opened, no_redirect
    try:
        yield
    finally:
        request.OpenerDirector.open, request.HTTPRedirectHandler.redirect_request = original, redirect
