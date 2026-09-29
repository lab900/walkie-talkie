#!/bin/bash
# since.sh HH:MM [HH:MM] — today's (09-29) relay.log lines from the first line at/after the first time, up to the second.
L=~/.walkie-talkie/relay.log
a=$(grep -n "^09-29 $1" $L | head -1 | cut -d: -f1)
if [ -n "$2" ]; then b=$(grep -n "^09-29 $2" $L | head -1 | cut -d: -f1); fi
[ -n "$a" ] && sed -n "${a},${b:-\$}p" $L
