"""R400 frozen raw-tape equation discovery, then one delayed forward evaluation.

prepare: earliest available finished development window, before Nov 4.
score: the fixed Nov 4-10 window, once, no earlier than Nov 11. No networking.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab import path_response as rule,prereg  # noqa: E402

LANE=ROOT/"experiments/path_response_v1"
PREPARE_BEFORE=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)
SCORE_AFTER=dt.datetime(2026,11,11,tzinfo=dt.timezone.utc)
DEVELOPMENT=("2026-10-29",)
FORWARD=tuple((dt.date(2026,11,4)+dt.timedelta(days=i)).isoformat() for i in range(7))


def now():
    return dt.datetime.now(dt.timezone.utc)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def verify_inputs(lane=LANE,root=ROOT):
    stamp=prereg.verify(lane/"PREREG.md")
    block=re.search(r"```inputs\n(.*?)```",(lane/"PREREG.md").read_text(),re.S)
    if block is None: raise prereg.PreregError("frozen inputs block missing")
    for line in block.group(1).strip().splitlines():
        want,relative=line.split()
        p=(root/relative).resolve()
        if not p.is_relative_to(root.resolve()) or digest(p)!=want:
            raise prereg.PreregError("frozen input changed: "+relative)
    return stamp


def write_new(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(payload,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    with path.open("xb") as f: f.write(raw)
    return hashlib.sha256(raw).hexdigest()


def source_paths(data,day):
    return [data/kind/coin/(day+".parquet") for coin in rule.COINS for kind in ("bbo","trade")]


def available(data,dates,instant):
    # Only stable finished files. No _parts, live status, price or outcome read.
    return [day for day in dates if all(p.is_file() and instant.timestamp()-p.stat().st_mtime>=900
                                       for p in source_paths(data,day))]


def manifest(data,days):
    return [dict(path=str(p.relative_to(data)),bytes=p.stat().st_size,sha256=digest(p))
            for day in days for p in source_paths(data,day)]


def check_manifest(data,records):
    for r in records:
        p=data/r["path"]
        if not p.is_file() or p.stat().st_size!=r["bytes"] or digest(p)!=r["sha256"]:
            raise rule.DataError("data changed during read: "+r["path"])


def load_windows(data,days):
    frames=[];coverage={}
    for day in days:
        for coin in rule.COINS:
            b=pd.read_parquet(data/"bbo"/coin/(day+".parquet"))
            q=pd.read_parquet(data/"trade"/coin/(day+".parquet"))
            frame,qc=rule.make_samples(b,q,day,coin)
            coverage[day+"/"+coin]=qc
            if qc["eligible"]<rule.MIN_COVERAGE*qc["expected"]:
                raise rule.DataError("feature coverage below 80%: "+day+"/"+coin)
            if frame.label_valid.mean()<.99:
                raise rule.DataError("label coverage below 99%: "+day+"/"+coin)
            frames.append(frame)
    return pd.concat(frames,ignore_index=True),coverage


def run(mode,data=ROOT/"data/rawtape",lane=LANE):
    """No bypass flags: verify before QC/market statistics, fail closed on drift."""
    data,lane=Path(data),Path(lane)
    spec=verify_inputs(lane)
    instant=now();results=lane/"results"
    common=dict(round="R400",prereg_sha256=spec,created_utc=instant.isoformat(),
                gate_eligible=False)
    if mode=="prepare":
        if instant>=PREPARE_BEFORE:
            return dict(**common,status="BLOCKED",reason="artifact deadline passed; no late training")
        days=available(data,DEVELOPMENT,instant)[:1]
        if not days:
            return dict(**common,status="BLOCKED",reason="one stable complete development window required",
                        available_days=days,market_fit=False)
        expected=json.loads((lane/"training_manifest.json").read_text())
        check_manifest(data,expected)
        results.mkdir(parents=True,exist_ok=True)
        # Exclusive first-look claim is never removed, including on failure.
        write_new(results/"prepare.started.json",dict(**common,days=days))
        records=manifest(data,days)
        write_new(results/"development_inputs.json",records)
        frame,qc=load_windows(data,days)
        with (results/"development_samples.csv").open("x") as f:
            frame.to_csv(f,index=False,float_format="%.17g")
        frame=frame.loc[frame.label_valid].copy()
        cut=int(dt.datetime.fromisoformat(days[0]+"T15:00:00+00:00").timestamp()*1e6)
        train=frame.loc[frame.decision_us<=cut-30_000_000]
        selection=frame.loc[frame.decision_us>=cut+30_000_000]
        artifact=rule.choose_equation(train,selection)
        check_manifest(data,records)
        # Do not publish an artifact that ran past the prospective cutoff.
        if now()>=PREPARE_BEFORE:
            raise rule.DataError("preparation crossed the artifact deadline")
        artifact.update(common,days=days,source_files=records,coverage=qc,
                        samples_sha256=digest(results/"development_samples.csv"),completed_utc=now().isoformat(),
                        runtime=dict(python=sys.version.split()[0],numpy=np.__version__,pandas=pd.__version__),
                        training_observations=len(train),selection_observations=len(selection))
        sha=write_new(results/"model.json",artifact)
        with (results/"model.sha256").open("x") as f: f.write(sha+"\n")
        status="NO_NEW_EQUATION" if artifact["selected_index"] is None else "PREPARED"
        return dict(**common,status=status,model_sha256=sha,days=days,
                    selected_equation=artifact["selected_text"],refit_status=artifact["refit_status"],
                    market_fit=True,prospective_observations=0)
    if mode!="score": raise ValueError("unknown mode")
    if instant<SCORE_AFTER:
        return dict(**common,status="BLOCKED",reason="forward window not finished; no interim read")
    model_path=results/"model.json"
    want=(results/"model.sha256").read_text().strip()
    if digest(model_path)!=want: raise rule.DataError("model artifact hash mismatch")
    artifact=json.loads(model_path.read_text())
    if artifact["prereg_sha256"]!=spec or dt.datetime.fromisoformat(artifact["created_utc"])>=PREPARE_BEFORE:
        raise rule.DataError("wrong preregistration or late artifact")
    if artifact["refit_status"]!="ready": raise rule.DataError("selected-domain refit failed")
    if artifact["selected_index"] is None:
        return dict(**common,status="NO_NEW_EQUATION",reason="no extra equation selected; forward data not read",
                    model_sha256=want,market_fit=False)
    days=available(data,FORWARD,instant)
    # Once the calendar closes this is terminal, including missing-file failure.
    write_new(results/"score.started.json",dict(**common,days=days,model_sha256=want))
    if len(days)<rule.MIN_FORWARD_DAYS:
        report=dict(**common,status="INCONCLUSIVE",reason="fewer than five complete forward days",
                    available_days=days,model_sha256=want,market_fit=False)
        write_new(results/"forward.json",report);return report
    records=manifest(data,days);write_new(results/"forward_inputs.json",records)
    frame,qc=load_windows(data,days)
    report=rule.evaluate(frame,artifact)
    check_manifest(data,records)
    report.update(common,status="SCORED",model_sha256=want,source_files=records,coverage=qc)
    write_new(results/"forward.json",report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","score"))
    p.add_argument("--data",type=Path,default=ROOT/"data/rawtape")
    args=p.parse_args()
    try:
        report=run(args.mode,args.data)
    except (rule.DataError,prereg.PreregError,FileExistsError,FileNotFoundError) as exc:
        print(json.dumps(dict(status="REFUSED",reason=str(exc),gate_eligible=False)),flush=True)
        raise SystemExit(2)
    print(json.dumps(report,sort_keys=True,allow_nan=False),flush=True)
    if report["status"]=="BLOCKED": raise SystemExit(3)


if __name__=="__main__": main()
