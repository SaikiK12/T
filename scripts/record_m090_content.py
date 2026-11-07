"""One frozen public M090 signed-content capture or head-pinned offline audit."""
import argparse
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab import prereg,registry  # noqa: E402
from lab import m090_capture as m  # noqa: E402

DIRECT={"lab/m090_capture.py","scripts/record_m090_content.py","scripts/m090_history_rule.py",
        "lab/prereg.py","lab/registry.py","lab/__init__.py"}


def safe(root,name):
    if not isinstance(name,str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("unsafe input path")
    p=root/name
    if any(x.is_symlink() for x in [p,*p.parents]):
        raise ValueError("symlink input path")
    p.resolve().relative_to(root.resolve())
    return p


def frozen(root,lane):
    digest=prereg.verify(lane/"PREREG.md")
    text=(lane/"PREREG.md").read_text()
    want=re.search(r"^- \*\*Inputs manifest SHA-256:\*\* ([0-9a-f]{64})$",text,re.M)
    raw=(lane/"inputs.json").read_bytes()
    if not want or m.sha(raw)!=want[1]:
        raise ValueError("manifest differs from frozen spec")
    spec=m.decode(raw)
    for name,sha in spec["files"].items():
        if m.sha(safe(root,name).read_bytes())!=sha:
            raise ValueError("frozen input drift: "+name)
    folder=safe(root,spec["trust_directory"])
    policy=m.decode((folder/"policy.json").read_bytes())
    required=DIRECT|{spec["trust_directory"]+"/"+n for n in ("policy.json","root.pem","chain.pem","chain.source.pem")}
    if set(spec["files"])!=required or len(policy["crl_urls"])!=2:
        raise ValueError("missing direct inputs/CRLs")
    identity=re.search(r"^- \*\*Registry id:\*\* (R[0-9]+)$",text,re.M)
    row=next((r for r in registry.rows(root/"registry/rounds.csv") if identity and r["id"]==identity[1]),None)
    if row is None or row["prereg_sha"]!=digest or int(row["trials"])!=0:
        raise ValueError("registered identity/hash/trials mismatch")
    trust=dict(policy,root=(folder/"root.pem").read_bytes(),chain=(folder/"chain.pem").read_bytes())
    return spec,trust,m.sha((folder/"policy.json").read_bytes())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*_):
        raise ValueError("redirect not allowed")


def network(trust):
    allowed={m.DISPLAY,m.HISTORY,trust["url"],*trust["crl_urls"]}
    opener=urllib.request.build_opener(NoRedirect())
    count=0
    def exchange(url,data):
        nonlocal count
        if url not in allowed or (data is not None)!=(url==trust["url"]):
            raise ValueError("unexpected public endpoint/method")
        count+=1
        if count>5:
            raise ValueError("request budget")
        headers={"User-Agent":"T-M090-content-engineering/2"}
        if data is not None:
            headers.update({"Content-Type":"application/timestamp-query","Accept":"application/timestamp-reply"})
        with opener.open(urllib.request.Request(url,data=data,headers=headers),timeout=20) as response:
            if response.status!=200 or response.geturl()!=url:
                raise ValueError("HTTP status/final endpoint differs")
            return m.bounded(response.read(m.LIMIT+1))
    return exchange


def run(root,lane,action,run_id,expected_head=None):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",run_id):
        raise ValueError("invalid result id")
    spec,trust,policy_sha=frozen(root,lane)
    output=lane/"runs"/run_id
    if output.exists():
        raise ValueError("result exists; never overwrite")
    archive=safe(root,spec["archive"])
    if action=="capture":
        m.capture(archive,trust,policy_sha,network(trust))
    elif action!="audit":
        raise ValueError("unknown action")
    with m.writer(archive):
        result=m.audit(archive,trust,policy_sha,expected_head)
        result.update(prereg_sha256=prereg.verify(lane/"PREREG.md"),
                      inputs_sha256=m.sha((lane/"inputs.json").read_bytes()),archive=spec["archive"],
                      program_trials=registry.program_trials(root/"registry/rounds.csv"))
        frozen(root,lane)
        output.mkdir(parents=True,exist_ok=False)
        m.durable(output/"result.json",m.encode(result))
    print(m.encode(dict(journal_head_sha256=result["journal_head_sha256"],inputs=result["inputs"],
                        timestamp=result["timestamp"],scoring_enabled=False,prospective_events=0)).decode(),end="")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lane",required=True)
    p.add_argument("--action",choices=("capture","audit"),required=True)
    p.add_argument("--run-id",required=True)
    p.add_argument("--expected-head")
    a=p.parse_args()
    run(ROOT,safe(ROOT,a.lane),a.action,a.run_id,a.expected_head)


if __name__=="__main__":
    main()
