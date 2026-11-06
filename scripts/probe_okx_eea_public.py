"""Inactive manual capability handoff. Never scheduled by the forward loop.

Do not run to evade an existing 403/451/bot restriction. Reachability must first
be resolved through the venue's normal permitted access. No account is needed
for these public paths. An outcome or paper measurement requires a new PREREG.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.okx_eea_public import ProbeStopped, PublicProbe, capabilities  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True, help="new immutable capture directory")
    p.add_argument("--run", action="store_true")
    args = p.parse_args(argv)
    if not args.run:
        p.error("--run required; this is an inactive handoff, not an automatic recorder")
    probe = PublicProbe(args.output)
    try:
        report = dict(state="CAPABILITY_COUNTS_ONLY", **capabilities(probe))
    except ProbeStopped as exc:
        report = dict(state="BLOCKED", reason=str(exc), history_available=None, paper_lane_ready=False)
    report.update(requests=probe.requests, response_bytes=probe.bytes, real_orders_allowed=False)
    (args.output / "capabilities.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["state"] == "CAPABILITY_COUNTS_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
