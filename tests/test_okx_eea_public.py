"""Public-probe boundaries using synthetic responses in temporary directories."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error

from lab.okx_eea_public import HOST, NoRedirect, ProbeStopped, PublicProbe, xperp_candidates


class Response(io.BytesIO):
    status = 200


def instrument(base):
    return dict(instFamily=base + "-USD_UM", instId=base + "-USD_UM-310404", instType="FUTURES",
                ctType="linear", ctValCcy=base, settleCcy="USD", state="live",
                listTime="1775251200000", expTime="1933017600000")


class EeaProbeTests(unittest.TestCase):
    def test_uses_only_official_eea_host_without_browser_header_or_auth(self):
        calls = []
        def open_(req, timeout):
            calls.append((req, timeout))
            return Response(b'{"code":"0","data":[]}')
        with tempfile.TemporaryDirectory() as tmp:
            p = PublicProbe(Path(tmp) / "out", opener=open_)
            p.get("/api/v5/public/instruments", instType="FUTURES")
            req, timeout = calls[0]
            self.assertTrue(req.full_url.startswith(HOST + "/api/v5/public/"))
            self.assertNotIn("User-agent", req.headers)
            self.assertNotIn("Authorization", req.headers)
            self.assertEqual(timeout, 20)
            self.assertEqual(len(list((Path(tmp) / "out").glob("*.receipt.json"))), 1)

    def test_403_and_451_stop_without_retry_or_host_fallback(self):
        for status in (403, 451, 429):
            calls = []
            def blocked(req, timeout):
                calls.append(req.full_url)
                raise urllib.error.HTTPError(req.full_url, status, "blocked", {}, None)
            with tempfile.TemporaryDirectory() as tmp:
                p = PublicProbe(Path(tmp) / "out", opener=blocked)
                for _ in range(2):
                    with self.assertRaises(ProbeStopped): p.get("/api/v5/public/instruments", instType="FUTURES")
                self.assertEqual(len(calls), 1)
                receipt = json.loads(next((Path(tmp) / "out").glob("*.receipt.json")).read_text())
                self.assertEqual(receipt["http_status"], status)

    def test_html_bot_response_and_timeout_stop(self):
        for opener in (lambda req, timeout: Response(b"<html>challenge</html>"),
                       lambda req, timeout: (_ for _ in ()).throw(TimeoutError("timeout"))):
            with tempfile.TemporaryDirectory() as tmp:
                p = PublicProbe(Path(tmp) / "out", opener=opener)
                with self.assertRaises(ProbeStopped): p.get("/api/v5/public/instruments", instType="FUTURES")
                self.assertTrue(p.stopped)

    def test_no_private_or_order_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = PublicProbe(Path(tmp) / "out")
            for path in ("/api/v5/account/trade-fee", "/api/v5/trade/order", "https://www.okx.com/api/v5/public/instruments"):
                with self.assertRaises(ValueError): p.get(path)
            self.assertEqual(p.requests, 0)

    def test_response_and_request_caps_are_hard(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = PublicProbe(Path(tmp) / "out", max_bytes=10, opener=lambda req, timeout: Response(b"0123456789more"))
            with self.assertRaises(ProbeStopped): p.get("/api/v5/public/instruments", instType="FUTURES")
            self.assertEqual(p.bytes, 10)
            self.assertTrue(p.stopped)
        with tempfile.TemporaryDirectory() as tmp:
            p = PublicProbe(Path(tmp) / "out", max_requests=1, opener=lambda req, timeout: Response(b'{"code":"0","data":[]}'))
            p.get("/api/v5/public/instruments", instType="FUTURES")
            with self.assertRaises(ProbeStopped): p.get("/api/v5/public/instruments", instType="FUTURES")

    def test_refuses_existing_capture_and_redirect(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError): PublicProbe(tmp)
        with self.assertRaises(ProbeStopped): NoRedirect().redirect_request(None, None, 302, "", {}, "https://www.okx.com/")

    def test_only_five_year_linear_eea_futures_bind(self):
        rows = [instrument(x) for x in ("BTC", "ETH")]
        self.assertEqual(set(xperp_candidates({"data": rows})), {"BTC", "ETH"})
        for changes in (dict(instType="SWAP"), dict(ctType="inverse"), dict(expTime="1775251200001"),
                        dict(settleCcy="USDT"), dict(instId="BTC-USD-SWAP")):
            with self.subTest(changes=changes):
                with self.assertRaises(ProbeStopped):
                    xperp_candidates({"data": [{**rows[0], **changes}, rows[1]]})
        with self.assertRaises(ProbeStopped): xperp_candidates({"data": rows + [rows[0]]})


if __name__ == "__main__":
    unittest.main()
