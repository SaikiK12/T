#!/bin/sh
# Hourly forward ticks that do not depend on the Claude session being idle: at minute 6 of every hour run
# scripts/forward_all.sh (which holds a lock, so an overlapping cron tick exits at once, and each hour is computed
# once). Start detached: setsid nohup sh scripts/forward_loop.sh >/dev/null 2>&1 &  (pid in .forward_loop.pid)
cd "$(dirname "$0")/.." || exit 1
echo $$ > .forward_loop.pid
while true; do
  now=$(date -u +%s)
  next=$(( (now / 3600 + 1) * 3600 + 360 ))
  sleep $(( next - now ))
  sh scripts/forward_all.sh
  echo "$(date -u +%FT%TZ) forward_loop tick done" >> experiments/forward_lag/loop.log
done
