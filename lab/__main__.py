"""Common entry point over existing tools; default is help, never a live tick."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {"status": "project_status.py", "check": "check.py", "find": "repository_index.py", "forward": "orchestrate_forward.py",
         "export": "dashboard_data.py", "panel": "panel.py", "engine": "build_engine.py",
         "benchmark": "benchmark_evaluation.py", "account": "paper_account.py"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(*TOOLS, "integrity"), nargs="?")
    # Parse only the command here so child --help/flags reach the actual tool.
    raw = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(raw[:1])
    rest = raw[1:]
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "integrity":
        # Metadata only. Neither command opens market arrays or appends rounds.
        commands = ("check_research_integrity.py", "check_method_intake.py")
    else:
        commands = (TOOLS[args.command],)
        if args.command == "find" and not any(flag in rest for flag in ("-h", "--help")):
            rest = ["--find", *rest]
        if args.command == "forward" and "--python" not in rest:
            rest = ["--python", sys.executable, *rest]
    for name in commands:
        code = subprocess.run((sys.executable, str(ROOT / "scripts" / name), *rest), cwd=ROOT).returncode
        if code:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
