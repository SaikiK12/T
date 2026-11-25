"""Rebuild docs/OWNER_LEDGER.md: every message the owner typed in this session, verbatim, from the session transcript,
with secrets redacted and notifications, hooks, summaries and subagent reports excluded.

Why: the owner, 2026-11-25: "Tu connais pas tout, souviens-toi de tout ça et autre truc que j'ai déjà dit avant tes
compressions." The context is summarized when it grows long; this file keeps the words. Run at the open step.

usage: python scripts/owner_ledger.py [--transcript PATH] [--out docs/OWNER_LEDGER.md]
"""
import argparse
import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = [
    "# The owner's messages, verbatim (the ledger that survives my context compressions)", "",
    "- **Why this file.** The owner, 2026-11-25: \"Tu connais pas tout, souviens-toi de tout ça et autre truc que j'ai "
    "déjà",
    "  dit avant tes compressions.\" My context is summarized when it grows long, and summaries lose words. This file "
    "keeps",
    "  the words.",
    "- **What it holds.** Every message the owner typed in this session (from 2026-11-17), extracted from the session",
    "  transcript with `scripts/owner_ledger.py`.",
    "  - Secrets are redacted (an API key the owner pasted on 2026-11-17 is kept only in "
    "`/root/.config/databento/env`).",
    "  - Notifications, hooks and subagent reports are excluded.",
    "- **Earlier messages** (before 2026-11-17) live in `CLAUDE.md` (\"The owner, in their words\") and "
    "`docs/STATUS.md`.",
    "- **The open step reads the newest entries every cycle.** The standing instructions they produced are in "
    "`CLAUDE.md`.", ""]
SKIP_START = ("<task-notification", "This session is being continued", "This session's worker process was restarted",
              "<system-reminder", "<command-", "Caveat:", "Stop hook feedback", "Another Claude session sent")


def is_owner(s):
    if not s or s.startswith(SKIP_START):
        return False
    if "SYSTEM NOTIFICATION" in s[:300] or "agent-message" in s[:200] or "Subagent hand-back" in s[:400]:
        return False
    return True


def redact(s):
    s = re.sub(r"\bdb-[A-Za-z0-9]{8,}\b", "[API key redacted]", s)
    s = re.sub(r"\b(sk|pk|ghp|gho|xox[abp])[-_][A-Za-z0-9_-]{12,}\b", "[token redacted]", s)
    return s


def messages(path):
    out, seen = [], set()
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "user":
                continue
            c = d.get("message", {}).get("content")
            texts = [c] if isinstance(c, str) else [it.get("text", "") for it in (c or [])
                                                     if isinstance(it, dict) and it.get("type") == "text"]
            for t in texts:
                s = t.strip()
                if not is_owner(s):
                    continue
                ts = d.get("timestamp", "")[:16].replace("T", " ")
                if (ts, s[:80]) in seen:
                    continue
                seen.add((ts, s[:80]))
                out.append((ts, redact(s)))
    return out


def render(msgs):
    lines = list(HEADER)
    for ts, s in msgs:
        lines += [f"## {ts} UTC", ""]
        lines += [("> " + p) if p.strip() else ">" for p in s.splitlines()]
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", default=None)
    ap.add_argument("--out", default=str(ROOT / "docs" / "OWNER_LEDGER.md"))
    a = ap.parse_args()
    paths = [a.transcript] if a.transcript else sorted(glob.glob("/root/.claude/projects/-home-user-T/*.jsonl"))
    msgs = []
    for p in paths:
        msgs += messages(p)
    msgs.sort()
    Path(a.out).write_text(render(msgs))
    print(len(msgs), "owner messages written to", a.out)


if __name__ == "__main__":
    main()
