"""Measure the bot-commit noise on a branch, so the claim in the note is reproducible.

Reads the GitHub API (GITHUB_TOKEN from the environment, never written to a file) or a saved
commits JSON. No repo writes, no notification changes.

usage: python scripts/commit_noise.py [--branch claude/yo-9a1k5w] [--json /path/commits.json]
"""
import argparse
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path

API = "https://api.github.com/repos/SaikiK12/T/commits"
BOT = "github-actions[bot]"


def fetch(branch, token, per_page=100):
    req = urllib.request.Request(
        f"{API}?sha={branch}&per_page={per_page}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def summarise(commits):
    bot = [c for c in commits if c["commit"]["author"]["name"] == BOT]
    kinds = Counter(c["commit"]["message"].split("\n")[0].split(":")[0] for c in bot)
    return {
        "commits": len(commits),
        "bot_commits": len(bot),
        "bot_share": len(bot) / len(commits) if commits else 0.0,
        "newest": commits[0]["commit"]["author"]["date"] if commits else None,
        "oldest": commits[-1]["commit"]["author"]["date"] if commits else None,
        "by_kind": dict(kinds.most_common()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--branch", default="claude/yo-9a1k5w")
    ap.add_argument("--json", help="a saved commits payload instead of the API")
    a = ap.parse_args()
    commits = json.loads(Path(a.json).read_text()) if a.json else fetch(a.branch, os.environ["GITHUB_TOKEN"])
    print(json.dumps({"branch": a.branch, **summarise(commits)}, indent=1))


if __name__ == "__main__":
    main()
