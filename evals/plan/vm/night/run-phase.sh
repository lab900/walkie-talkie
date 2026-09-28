#!/bin/bash
# run-phase.sh NAME CAP_SECONDS IDS — one harness process over IDS, INT at the cap, KILL 30 s later.
# Night run 2026-09-26 (docs/vm-lab.md). Writes ~/wt-lab/night/report-vm-NAME.md + run-NAME.log.
name=$1; cap=$2; ids=$3
N=$HOME/wt-lab/night; mkdir -p "$N"
cd "$HOME/wt-lab/evals/plan" || exit 9
export WT_LAB=1 WT_LOOPBACK="BlackHole 2ch" HANDS_OFF=1 WT_COLD_WHISPER=kill WT_ALLOW_SPAWN=1 WT_ALLOW_RELAUNCH=1
export PATH="$HOME/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
echo "start $name cap=${cap}s $(date)" >> "$N/run-$name.log"
/usr/bin/python3 -u harness.py --only "$ids" --report "$N/report-vm-$name.md" >> "$N/run-$name.log" 2>&1 &
p=$!
( sleep "$cap"; echo "CAP hit $(date)" >> "$N/run-$name.log"; kill -INT $p 2>/dev/null; sleep 30; kill -9 $p 2>/dev/null ) &
w=$!
wait $p; rc=$?
kill $w 2>/dev/null
echo "rc=$rc $(date)" >> "$N/run-$name.log"
echo "PHASEDONE $name" >> "$N/run-$name.log"
