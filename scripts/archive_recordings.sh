#!/bin/sh
# Pack the live recordings into the `data-archive` branch and push it (the owner chose this place on 2026-10-29).
# Run it once a day: every run that finds something new adds at least one chunk, and git keeps every chunk for good.
#
#   sh scripts/archive_recordings.sh            # pack, commit, push
#   ARCHIVE_WT=/path sh scripts/archive_recordings.sh
#   ARCHIVE_TRAILERS="Co-Authored-By: ..." sh scripts/archive_recordings.sh   # appended to the commit message
#
# The archive lives in its own checkout (a git worktree of this repository, default ../T-data-archive), never inside the
# working tree. --public leaves out data/news (third-party text on a public repo). --budget-mb 900 stops adding chunks before
# the branch passes 900 MB; the script then says so and the owner decides where the rest goes. Nothing here uses a key or
# places an order, and nothing is deleted.
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
WT="${ARCHIVE_WT:-$(cd .. && pwd)/T-data-archive}"
BUDGET="${ARCHIVE_BUDGET_MB:-900}"

if [ ! -d "$WT/.git" ] && [ ! -f "$WT/.git" ]; then
  git fetch -q origin data-archive
  git worktree add -q -B data-archive "$WT" origin/data-archive
else
  git -C "$WT" pull -q --ff-only origin data-archive
fi

"$PY" scripts/handover.py pack --out "$WT" --public --budget-mb "$BUDGET"

if [ -z "$(git -C "$WT" status --porcelain)" ]; then
  echo "archive: nothing new to commit"
  exit 0
fi
msg="Archive of the live recordings up to $(date -u +%Y-%m-%d)"
if [ -n "${ARCHIVE_TRAILERS:-}" ]; then
  msg="$msg

$ARCHIVE_TRAILERS"
fi
git -C "$WT" add -A
git -C "$WT" commit -q -m "$msg"
git -C "$WT" push -q origin data-archive
echo "archive: pushed $(git -C "$WT" rev-parse --short HEAD); branch is $(du -sm --exclude=.git "$WT" | cut -f1) MB of $BUDGET MB"
