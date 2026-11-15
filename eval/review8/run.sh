#!/bin/bash
# usage: run.sh <per-scene timeout> files...   (skips scenes with a finished .out)
cd $HOME/mnt/sim_waves/engine
TO=$1; shift
one(){ b=$(basename $1 .yaml); o=../eval/review8/$b.out; grep -q '^\[exit' $o 2>/dev/null && return; s=$(date +%s); timeout $TO python3 -m simwaves run $1 > $o.tmp 2>&1; echo "[exit $? in $(( $(date +%s)-s ))s]" >> $o.tmp; mv $o.tmp $o; }
export -f one; export TO
printf '%s\n' "$@" | xargs -P2 -I{} bash -c 'one {}'
