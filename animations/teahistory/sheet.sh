#!/usr/bin/env bash
# Лист кадров для самопроверки: sheet.sh in.mp4 out.png "t1 t2 ..."
in=$1; outp=$2; times=${3:-"0 1.5 3.4 5.0 6.4 7.4 8.1 8.6 9.3 11.0 12.0 13.6 14.6 15.8 17.2 19.9"}
tmp=$(mktemp -d); i=0
for t in $times; do ffmpeg -loglevel error -y -ss $t -i "$in" -frames:v 1 -vf "scale=270:480,drawtext=text='$t':x=8:y=8:fontsize=26:fontcolor=red" "$tmp/$(printf %02d $i).png"; i=$((i+1)); done
n=$i; cols=8; rows=$(( (n+cols-1)/cols ))
ffmpeg -loglevel error -y -framerate 1 -i "$tmp/%02d.png" -vf "tile=${cols}x${rows}" -frames:v 1 "$outp"; rm -rf "$tmp"; echo "$outp"
