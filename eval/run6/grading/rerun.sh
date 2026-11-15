#!/bin/bash
# re-run every final scene; outputs to eval/run6/grading/out/<id>.txt
cd "$HOME/mnt/sim_waves/engine"
mkdir -p ../eval/run6/grading/out
for a in ../eval/run6/work/*.answer.yaml; do
  id=$(basename $a .answer.yaml)
  fs=$(grep -m1 '^final_scene:' $a | sed 's/final_scene: *//; s/[" ]//g')
  if [ -f ../eval/run6/grading/out/$id.txt ]; then continue; fi
  ( echo "FINAL: $fs"; timeout 170 python3 -m simwaves run ../eval/run6/work/$fs 2>&1; echo "EXIT: $?" ) > ../eval/run6/grading/out/$id.txt.tmp
  mv ../eval/run6/grading/out/$id.txt.tmp ../eval/run6/grading/out/$id.txt
done
