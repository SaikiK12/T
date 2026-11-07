"""Freeze/registry/network guards for the bounded content runner."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from lab import prereg,registry
from lab import m090_capture as m
from scripts import record_m090_content as runner
from tests.m090_fixture import Authority


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca=Authority()

    @classmethod
    def tearDownClass(cls):
        cls.ca.close()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="test_m090_runner_")
        self.root=Path(self.temp.name)
        for n in runner.DIRECT:
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(runner.ROOT/n,p)
        folder=self.root/"trust";folder.mkdir()
        for n in ("root","chain"):
            (folder/(n+".pem")).write_bytes(self.ca.trust[n])
        (folder/"chain.source.pem").write_bytes(self.ca.trust["chain"])
        policy={k:v for k,v in self.ca.trust.items() if k not in ("root","chain","crls")}
        (folder/"policy.json").write_bytes(m.encode(policy))
        names=runner.DIRECT|{"trust/"+p.name for p in folder.iterdir()}
        spec=dict(trust_directory="trust",archive="data/capture",files={n:m.sha((self.root/n).read_bytes()) for n in names})
        self.lane=self.root/"experiments/test";self.lane.mkdir(parents=True)
        raw=m.encode(spec);(self.lane/"inputs.json").write_bytes(raw)
        (self.lane/"PREREG.md").write_text("- **Registry id:** R1\n- **Inputs manifest SHA-256:** "+m.sha(raw)+"\n")
        digest=prereg.freeze(self.lane/"PREREG.md")
        (self.root/"registry").mkdir()
        registry.append(self.root/"registry/rounds.csv",id="R1",status="REGISTERED",verdict="PENDING",trials=0,prereg_sha=digest)
        self.calls=[]

    def tearDown(self):
        self.temp.cleanup()

    def exchange(self,url,data):
        self.calls.append(url)
        if data is not None:
            return self.ca.sign(data)
        if url.startswith("https://test.invalid"):
            return self.ca.trust["crls"]
        if url==m.DISPLAY:
            return m.encode(dict(success=True,data=dict(symbol="BTC_USDT",nextSettleTime=100000037,fundingRate=".001")))
        return m.encode(dict(success=True,data=dict(currentPage=1,totalPage=1,
                    resultList=[dict(symbol="BTC_USDT",settleTime=12345679,fundingRate=".002")])))

    def capture(self):
        with patch.object(runner,"network",return_value=self.exchange),redirect_stdout(StringIO()):
            return runner.run(self.root,self.lane,"capture","first")

    def test_frozen_run_and_head_pinned_replay_produce_identical_receipts(self):
        first=self.capture()
        with redirect_stdout(StringIO()):
            again=runner.run(self.root,self.lane,"audit","replay",first["journal_head_sha256"])
        self.assertEqual(first,again)
        self.assertEqual((self.lane/"runs/first/result.json").read_bytes(),(self.lane/"runs/replay/result.json").read_bytes())
        self.assertEqual(len(self.calls),5)

    def test_code_or_manifest_drift_blocks_before_network(self):
        p=self.root/"lab/m090_capture.py";raw=p.read_bytes();p.write_bytes(raw+b"\n# drift\n")
        with self.assertRaisesRegex(ValueError,"frozen input drift"):
            self.capture()
        p.write_bytes(raw)
        p=self.lane/"inputs.json";p.write_bytes(p.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError,"manifest differs"):
            self.capture()
        self.assertEqual(self.calls,[])

    def test_result_overwrite_and_wrong_external_head_are_refused(self):
        self.capture()
        with self.assertRaisesRegex(ValueError,"never overwrite"):
            self.capture()
        with self.assertRaisesRegex(ValueError,"retained head"):
            runner.run(self.root,self.lane,"audit","bad","0"*64)

    def test_network_method_endpoint_redirect_and_path_guards(self):
        exchange=runner.network(self.ca.trust)
        for url,data in (("https://unknown.invalid",None),(m.DISPLAY,b"wrong"),(self.ca.trust["url"],None)):
            with self.assertRaisesRegex(ValueError,"unexpected public"):
                exchange(url,data)
        with self.assertRaises(ValueError):
            runner.NoRedirect().redirect_request()
        for p in ("../escape","/absolute",""):
            with self.assertRaises(ValueError):
                runner.safe(self.root,p)


if __name__=="__main__":
    unittest.main()
