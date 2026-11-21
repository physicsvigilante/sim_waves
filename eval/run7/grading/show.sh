#!/bin/bash
# usage: show.sh B4_single_10
cd $HOME/mnt/sim_waves
id=$1; rest=${id#B4_}; sec=${rest%_*}; num=${rest##*_}
echo "=== CORPUS"; cat corpus/book4_waves/$sec/$num.yaml
echo "=== ANSWER"; cat eval/run7/work/$id.answer.yaml
fs=$(grep '^final_scene:' eval/run7/work/$id.answer.yaml | awk '{print $2}')
echo "=== SCENE $fs"; cat eval/run7/work/$fs
echo "=== OUTPUT"; cat eval/run7/grading/out/$id.txt
