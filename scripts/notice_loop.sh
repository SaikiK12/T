#!/bin/sh
# Every 5 minutes: record Binance's notice catalogs, then ticket R272 announce_fwd, so an event ticket is written
# minutes after a notice and enters at the next full hour. The hourly scripts/forward_all.sh runs the same two steps;
# both take .notices.lock, so the catalogs have one writer at a time (a cycle that cannot get it in 60 s is skipped).
# Start detached: setsid nohup sh scripts/notice_loop.sh >/dev/null 2>&1 &  (pid in .notice_loop.pid)
cd "$(dirname "$0")/.." || exit 1
echo $$ > .notice_loop.pid
PY=.venv/bin/python
mkdir -p data/logs
while true; do
  now=$(date -u +%s)
  sleep $(( 300 - now % 300 + 20 ))
  flock -w 60 .notices.lock sh -c "timeout 240 $PY scripts/record_notices.py >> data/logs/notice_loop.log 2>&1;
    timeout 240 $PY scripts/forward_announce.py >> data/logs/notice_loop.log 2>&1"
done
