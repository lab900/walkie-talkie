#!/bin/bash
# chain-r5.sh — wave 5's six phases again, on the e9cd3be harness (tmo(), relay_busy, WT_HARNESS_SLOW=1.5),
# to measure the wave's wall time against wave 5's 48 min (the timing audit's estimate: 46 → 32 min).
# Through `tart exec`, detached: tart exec wt-lab sh -c "nohup bash ~/wt-lab/chain-r5.sh >/dev/null 2>&1 </dev/null &"
C=~/wt-lab/night/explore/chain-explore.log
echo "R5 wave start $(date -u +%T)" >> $C
bash ~/wt-lab/chain-explore.sh R5a 2700 "TW41,TW42,TW43,TA6,TW4,TW8a,TW11,TW20"
bash ~/wt-lab/chain-explore.sh R5b 2700 "TW4,TX3,TX6b,TX9,TX13"
bash ~/wt-lab/chain-explore.sh R5c 1800 "TQ2,TQ4"
bash ~/wt-lab/chain-explore.sh R5t 1800 "TS1"
WT_SOAK_GAP=2 bash ~/wt-lab/chain-explore.sh R5e 2400 "TS3"
bash ~/wt-lab/chain-explore.sh R5d 1800 "TM1,TM2,TW39,TX8b,TX10"
echo "R5 wave end $(date -u +%T)" >> $C
