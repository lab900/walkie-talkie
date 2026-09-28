#!/bin/bash
# run-wphase.sh NAME CAP_SECONDS IDS — run-phase.sh for the Wispr lab run of 2026-09-28:
# launched over SSH with nohup (tart exec dead this boot), WT_ALLOW_WISPR_KILL=1, load sampled every 30 s.
name=$1; cap=$2; ids=$3
N=$HOME/wt-lab/night/wispr; mkdir -p "$N"
cd "$HOME/wt-lab/evals/plan" || exit 9
export WT_LAB=1 WT_LOOPBACK="BlackHole 2ch" HANDS_OFF=1 WT_ALLOW_WISPR_KILL=1 WT_COLD_WHISPER=kill WT_ALLOW_SPAWN=1 WT_ALLOW_RELAUNCH=1
export PATH="$HOME/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$HOME/Library/Python/3.9/bin"
echo "start $name cap=${cap}s ids=$ids $(date)" >> "$N/run-$name.log"
( while true; do echo "$(date +%H:%M:%S) $(uptime | sed "s/.*load averages*: //")" >> "$N/load-$name.log"; sleep 30; done ) &
l=$!
/usr/bin/python3 -u harness.py --only "$ids" --report "$N/report-lab-$name.md" >> "$N/run-$name.log" 2>&1 &
p=$!
( sleep "$cap"; echo "CAP hit $(date)" >> "$N/run-$name.log"; kill -INT $p 2>/dev/null; sleep 30; kill -9 $p 2>/dev/null ) &
w=$!
wait $p; rc=$?
kill $w $l 2>/dev/null
echo "rc=$rc $(date)" >> "$N/run-$name.log"
echo "PHASEDONE $name" >> "$N/run-$name.log"
