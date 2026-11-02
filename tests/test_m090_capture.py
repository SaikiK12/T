"""Real offline signatures and failure/restart/source-identity checks."""
from pathlib import Path
import tempfile
import unittest
from lab import m090_capture as m
from tests.m090_fixture import Authority


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca = Authority()
        cls.data = b"Invented engineering bytes."
        cls.q = m.query(cls.data,cls.ca.trust["policy"])
        cls.reply = cls.ca.sign(cls.q)

    @classmethod
    def tearDownClass(cls):
        cls.ca.close()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test_m090_capture_")
        self.root = Path(self.temp.name)/"archive"
        self.display = m.encode(dict(success=True,data=dict(symbol="BTC_USDT",nextSettleTime=100000037,fundingRate=".0001")))
        self.history = m.encode(dict(success=True,data=dict(currentPage=1,totalPage=20,
            resultList=[dict(symbol="BTC_USDT",settleTime=12345679,fundingRate="-.0002")])))
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def exchange(self,url,data):
        self.calls.append(url)
        if url.startswith("https://test.invalid/"):
            return self.ca.trust["crls"]
        if data is not None:
            self.assertTrue((self.root/"journal.jsonl").exists())
            self.assertTrue((self.root/"checkpoint.json").exists())
            return self.ca.sign(data)
        return self.display if url==m.DISPLAY else self.history

    def capture(self):
        return m.capture(self.root,self.ca.trust,"f"*64,self.exchange)

    def test_valid_signatures_and_absent_accuracy_never_qualify_utc(self):
        result = m.verify_timestamp(self.data,self.q,self.reply,self.ca.trust)
        self.assertTrue(result["revocation_checked_at_signed_time"])
        self.assertIn("unspecified",result["reported_accuracy"].lower())
        self.assertIsNone(result["utc_interval"])
        self.assertFalse(result["forecast_eligible"])

    def test_even_reported_accuracy_does_not_qualify_a_forecast_in_this_lane(self):
        result = m.verify_timestamp(self.data,self.q,self.ca.sign(self.q,True),self.ca.trust)
        self.assertFalse(result["forecast_eligible"])
        self.assertIsNone(result["utc_interval"])

    def test_changed_payload_reply_nonce_signer_policy_and_crl_are_rejected(self):
        cases = [(self.data+b"!",self.q,self.reply,self.ca.trust),
                 (self.data,m.query(self.data,self.ca.trust["policy"]),self.reply,self.ca.trust),
                 (self.data,self.q,self.reply[:-1]+bytes([self.reply[-1]^1]),self.ca.trust)]
        cases += [(self.data,self.q,self.reply,dict(self.ca.trust,**change)) for change in
                  (dict(signer_sha256="0"*64),dict(policy="1.2.3.4.6"),dict(crls=b"bad"))]
        for args in cases:
            with self.subTest(case=args[3].get("policy")),self.assertRaises(ValueError):
                m.verify_timestamp(*args)

    def test_revoked_signer_is_rejected(self):
        ca = Authority()
        try:
            q = m.query(self.data,ca.trust["policy"]); reply = ca.sign(q)
            m.openssl(["ca","-config",ca.path/"config","-revoke",ca.path/"signer.pem"])
            m.openssl(["ca","-gencrl","-config",ca.path/"config","-out",ca.path/"revoked"])
            with self.assertRaisesRegex(ValueError,"revoked"):
                m.verify_timestamp(self.data,q,reply,dict(ca.trust,crls=(ca.path/"revoked").read_bytes()))
        finally:
            ca.close()

    def test_complete_capture_and_head_pinned_replay_are_identical(self):
        result = self.capture()
        again = m.audit(self.root,self.ca.trust,"f"*64,result["journal_head_sha256"])
        self.assertEqual(result,again)
        self.assertEqual(len(self.calls),5)
        self.assertEqual(result["inputs"]["target_ms"],100000037)
        self.assertEqual(result["inputs"]["previous_ms"],12345679)
        self.assertEqual(result["prospective_events"],0)
        self.assertFalse(result["scoring_enabled"])

    def test_completed_restart_makes_zero_network_calls(self):
        result = self.capture()
        def forbidden(*_):
            raise AssertionError("must not refetch")
        self.assertEqual(m.capture(self.root,self.ca.trust,"f"*64,forbidden),result)

    def test_wrong_retained_head_and_policy_are_rejected(self):
        self.capture()
        for policy,head in (("f"*64,"0"*64),("0"*64,None)):
            with self.assertRaises(ValueError):
                m.audit(self.root,self.ca.trust,policy,head)

    def test_body_tamper_survives_rewritten_inventory_but_fails_manifest(self):
        self.capture()
        p = self.root/"display.json";p.write_bytes(p.read_bytes()+b" ")
        inventory = m.inventory(self.root);inventory.pop("complete.json")
        (self.root/"complete.json").write_bytes(m.encode(inventory))
        with self.assertRaisesRegex(ValueError,"manifest"):
            m.audit(self.root,self.ca.trust,"f"*64)

    def test_partial_tail_is_preserved_and_blocks_restart(self):
        self.capture()
        p = self.root/"journal.jsonl";p.write_bytes(p.read_bytes()+b"partial")
        saved = p.read_bytes()
        with self.assertRaises(ValueError):
            self.capture()
        self.assertEqual(p.read_bytes(),saved)

    def test_interrupted_capture_is_retained_without_refetch(self):
        def fail(url,data):
            if url==m.DISPLAY:
                raise OSError("invented failure")
            return self.exchange(url,data)
        with self.assertRaises(OSError):
            m.capture(self.root,self.ca.trust,"f"*64,fail)
        calls = len(self.calls)
        with self.assertRaisesRegex(ValueError,"incomplete/orphan"):
            self.capture()
        self.assertEqual(len(self.calls),calls)

    def test_other_writer_lock_is_preserved(self):
        self.root.mkdir();p=self.root/".writer.lock";p.write_text("another writer")
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(p.read_text(),"another writer")

    def test_symlink_and_large_archive_are_rejected_before_read(self):
        self.root.mkdir();(self.root/"link").symlink_to(self.root.parent/"outside")
        with self.assertRaises(ValueError):
            m.inventory(self.root)
        other=self.root.parent/"large";other.mkdir()
        with (other/"sparse").open("wb") as f:
            f.truncate(m.ARCHIVE_LIMIT+1)
        with self.assertRaises(ValueError):
            m.inventory(other)

    def test_malformed_source_is_archived_as_invalid_input(self):
        self.display=b"[]"
        result=self.capture()
        self.assertIsNone(result["inputs"])
        self.assertEqual(result["input_error"],"ValueError")

    def test_exact_events_duplicate_keys_bool_and_nonfinite_are_strict(self):
        for raw in (b"[]",b"null",b'{"success":true,"success":true}'):
            with self.assertRaises(ValueError):
                m.parse_inputs(raw,self.history)
        for value in (True,"NaN","Infinity",2):
            d=m.decode(self.display);d["data"]["fundingRate"]=value
            with self.assertRaises(ValueError):
                m.parse_inputs(m.encode(d),self.history)
        h=m.decode(self.history);h["data"]["resultList"][0]["settleTime"]=100000037
        with self.assertRaises(ValueError):
            m.parse_inputs(self.display,m.encode(h))


if __name__ == "__main__":
    unittest.main()
