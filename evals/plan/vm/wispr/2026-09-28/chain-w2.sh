#!/bin/bash
until grep -q PHASEDONE ~/wt-lab/night/wispr/run-W1r.log; do sleep 5; done
sleep 10
end=$(date -j -f "%Y-%m-%d %H:%M:%S" "$(date +%Y-%m-%d) 08:17:00" +%s); now=$(date +%s); cap=$((end-now))
[ $cap -lt 120 ] && { echo "no time for W2 (cap $cap)" >> ~/wt-lab/night/wispr/run-W2.log; echo PHASEDONE W2 >> ~/wt-lab/night/wispr/run-W2.log; exit 0; }
exec bash ~/wt-lab/run-wphase.sh W2 $cap "TW1,TW2,TW5,TW7,TW12,TW13,TW14,TW19,TW22"
