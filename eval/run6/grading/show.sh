#!/bin/bash
# show.sh <id> : author copy, corpus record, answer, final scene, rerun output
cd "$HOME/mnt/sim_waves"
id=$1
sec=$(echo $id | sed 's/^B4_//; s/_[0-9]*$//'); num=$(echo $id | sed 's/.*_//')
echo "=================== $id"
echo "--- PROBLEM"; cat eval/run6/problems/$id.yaml
echo "--- CORPUS (diff vs problem)"; diff <(cat eval/run6/problems/$id.yaml) corpus/book4_waves/$sec/$num.yaml | grep '^[<>]' | cut -c1-1500
echo "--- ANSWER"; cat eval/run6/work/$id.answer.yaml
fs=$(grep -m1 '^final_scene:' eval/run6/work/$id.answer.yaml | sed 's/final_scene: *//; s/[" ]//g')
echo "--- SCENE $fs"; grep -v '^\s*$' eval/run6/work/$fs
echo "--- RERUN"; cut -c1-600 eval/run6/grading/out/$id.txt
