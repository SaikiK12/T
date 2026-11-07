"""R419 public Coinbase CDE/Kraken raw packets; inactive until Claude runs --execute."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab import prereg  # noqa: E402
from lab.eea_pair_capture import capture  # noqa: E402

LANE=ROOT/"experiments/eea_pair_capture_v1"
OUT=ROOT/"data/recorders/eea_pair_capture_v1"


def verify_inputs():
    sha=prereg.verify(LANE/"PREREG.md")
    manifest=LANE/"inputs.json"
    rel=manifest.relative_to(ROOT).as_posix()
    if f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {rel}" not in (LANE/"PREREG.md").read_text():
        raise ValueError("frozen manifest mismatch")
    inputs=json.loads(manifest.read_text())["sha256"]
    for name,wanted in inputs.items():
        p=ROOT/name
        if not p.resolve().is_relative_to(ROOT) or hashlib.sha256(p.read_bytes()).hexdigest()!=wanted:
            raise ValueError("frozen input changed: "+name)
    for name in [*inputs,rel,"experiments/eea_pair_capture_v1/PREREG.md","experiments/eea_pair_capture_v1/PREREG.sha256"]:
        blob=subprocess.run(["git","show","HEAD:"+name],cwd=ROOT,check=True,capture_output=True).stdout
        if blob!=(ROOT/name).read_bytes():
            raise ValueError("input not committed: "+name)
    return sha


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true",help="Operational owner only: capture one hour; never starts a daemon")
    args=parser.parse_args(argv)
    if not args.execute:
        print(json.dumps(dict(state="INACTIVE",capture_started=False,operational_owner="Claude",pnl=None)))
        return 0
    sha=verify_inputs()
    commit=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    config=LANE/"capture.json"
    result=capture(OUT,json.loads(config.read_text()),provenance=dict(
        prereg_sha256=sha,input_commit=commit,config_sha256=hashlib.sha256(config.read_bytes()).hexdigest()))
    verify_inputs()
    print(json.dumps(dict(prereg_sha256=sha,**result)))
    return 1 if result["state"] in ("FAILED","BUDGET_STOP","STOPPED") else 0


if __name__=="__main__":
    raise SystemExit(main())
