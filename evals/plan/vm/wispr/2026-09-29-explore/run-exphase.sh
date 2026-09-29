#!/bin/bash
# run-exphase.sh NAME CAP_SECONDS IDS — the exploratory run (2026-09-29 morning), after run-w5phase.sh.
# **Launch only through `tart exec`** (docs/vm-lab.md): over SSH the harness reads BlackHole as zeros.
# Every phase runs through cases_wispr_explore.py (it registers the TE cases, patches the marker count, calls harness.main()).
name=$1; cap=$2; ids=$3
N=$HOME/wt-lab/night/explore; mkdir -p "$N"
cd "$HOME/wt-lab/evals/plan" || exit 9
export WT_LAB=1 WT_LOOPBACK="BlackHole 2ch" HANDS_OFF=1 WT_ALLOW_WISPR_KILL=1 WT_COLD_WHISPER=kill WT_ALLOW_SPAWN=1 WT_ALLOW_RELAUNCH=1 WT_KEEP_TAKES=1
export WT_HARNESS_SLOW="${WT_HARNESS_SLOW:-1.5}"   # e9cd3be: every timeout is p99×1.5+1 s × this (the guest runners use 1.5)
export PATH="$HOME/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$HOME/Library/Python/3.9/bin"
entry=cases_wispr_explore.py   # always: it patches the marker count (see the module) and runs harness.main()
echo "start $name cap=${cap}s ids=$ids entry=$entry $(date)" >> "$N/run-$name.log"
( while true; do echo "$(date +%H:%M:%S) $(uptime | sed "s/.*load averages*: //")" >> "$N/load-$name.log"; sleep 30; done ) &
l=$!
/usr/bin/python3 -u $entry --only "$ids" --report "$N/report-lab-$name.md" >> "$N/run-$name.log" 2>&1 &
p=$!
( sleep "$cap"; echo "CAP hit $(date)" >> "$N/run-$name.log"; kill -INT $p 2>/dev/null; sleep 30; kill -9 $p 2>/dev/null ) &
w=$!
wait $p; rc=$?
kill $w $l 2>/dev/null
echo "rc=$rc $(date)" >> "$N/run-$name.log"
echo "PHASEDONE $name" >> "$N/run-$name.log"
